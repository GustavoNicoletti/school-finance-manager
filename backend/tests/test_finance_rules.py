from datetime import date
from decimal import Decimal

import pytest
from sqlalchemy.exc import IntegrityError

from app.models.audit import AuditLog
from app.models.finance import Payable, PaymentStatus, Receivable, ReceivableType
from app.models.student import Student, StudentStatus
from app.models.user import Role
from .conftest import auth_headers, create_user


def test_batch_receivable_generation_is_idempotent(client, db):
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)
    student = Student(full_name="Aluno Teste", status=StudentStatus.ACTIVE, class_name="1 Ano")
    db.add(student)
    db.commit()

    payload = {
        "reference_month": "2026-09-01",
        "due_date": "2026-09-05",
        "amount": "900.00",
        "type": "mensalidade",
        "description_prefix": "Mensalidade",
        "only_active_students": True,
    }
    headers = auth_headers(client, "finance@example.com")

    first = client.post("/api/finance/receivables/generate-batch", json=payload, headers=headers)
    second = client.post("/api/finance/receivables/generate-batch", json=payload, headers=headers)

    assert first.status_code == 201
    assert first.json()["created_count"] == 1
    assert second.status_code == 201
    assert second.json()["created_count"] == 0
    assert second.json()["skipped_count"] == 1


def test_database_blocks_duplicate_tuition_same_month(db):
    student = Student(full_name="Aluno Duplicado", status=StudentStatus.ACTIVE)
    db.add(student)
    db.commit()

    first = Receivable(
        student_id=student.id,
        description="Mensalidade 09/2026",
        amount=Decimal("700.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 9, 5),
        status=PaymentStatus.PENDING,
        type=ReceivableType.TUITION,
    )
    second = Receivable(
        student_id=student.id,
        description="Mensalidade reforco 09/2026",
        amount=Decimal("700.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 9, 20),
        status=PaymentStatus.PENDING,
        type=ReceivableType.TUITION,
    )
    db.add(first)
    db.commit()

    db.add(second)
    with pytest.raises(IntegrityError):
        db.commit()
    db.rollback()


def test_finance_user_cannot_change_paid_records_with_mark_paid(client, db):
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)
    student = Student(full_name="Aluno Pago", status=StudentStatus.ACTIVE, class_name="1 Ano")
    receivable = Receivable(
        student=student,
        description="Mensalidade paga",
        amount=Decimal("700.00"),
        paid_amount=Decimal("700.00"),
        due_date=date(2026, 9, 5),
        payment_date=date(2026, 9, 5),
        status=PaymentStatus.PAID,
        type=ReceivableType.TUITION,
    )
    payable = Payable(
        description="Conta paga",
        category="servicos",
        amount=Decimal("300.00"),
        due_date=date(2026, 9, 10),
        payment_date=date(2026, 9, 10),
        status=PaymentStatus.PAID,
    )
    db.add_all([student, receivable, payable])
    db.commit()

    headers = auth_headers(client, "finance@example.com")
    receivable_response = client.post(
        f"/api/finance/receivables/{receivable.id}/mark-paid",
        json={"paid_amount": "650.00", "payment_date": "2026-09-06"},
        headers=headers,
    )
    payable_response = client.post(
        f"/api/finance/payables/{payable.id}/mark-paid",
        json={"payment_date": "2026-09-11"},
        headers=headers,
    )

    db.refresh(receivable)
    db.refresh(payable)
    assert receivable_response.status_code == 403
    assert payable_response.status_code == 403
    assert receivable.paid_amount == Decimal("700.00")
    assert receivable.payment_date == date(2026, 9, 5)
    assert payable.payment_date == date(2026, 9, 10)


def test_receivable_update_cannot_mark_paid_directly_or_reactivate_canceled(client, db):
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)
    student = Student(full_name="Aluno Fluxo", status=StudentStatus.ACTIVE)
    receivable = Receivable(
        student=student,
        description="Mensalidade aberta",
        amount=Decimal("500.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 9, 5),
        status=PaymentStatus.PENDING,
        type=ReceivableType.TUITION,
    )
    canceled = Receivable(
        student=student,
        description="Mensalidade cancelada",
        amount=Decimal("450.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 10, 5),
        status=PaymentStatus.CANCELED,
        type=ReceivableType.EXTRA_FEE,
    )
    db.add_all([student, receivable, canceled])
    db.commit()

    headers = auth_headers(client, "finance@example.com")
    direct_paid = client.put(
        f"/api/finance/receivables/{receivable.id}",
        json={"status": "pago", "paid_amount": "500.00", "payment_date": "2026-09-05"},
        headers=headers,
    )
    reactivate = client.put(
        f"/api/finance/receivables/{canceled.id}",
        json={"status": "pendente"},
        headers=headers,
    )

    assert direct_paid.status_code == 400
    assert reactivate.status_code == 400


def test_payable_update_cannot_mark_paid_directly_or_reactivate_canceled(client, db):
    create_user(db, email="finance@example.com", role=Role.FINANCEIRO)
    payable = Payable(
        description="Servico aberto",
        category="servicos",
        amount=Decimal("320.00"),
        due_date=date(2026, 9, 9),
        status=PaymentStatus.PENDING,
    )
    canceled = Payable(
        description="Servico cancelado",
        category="servicos",
        amount=Decimal("280.00"),
        due_date=date(2026, 9, 12),
        status=PaymentStatus.CANCELED,
    )
    db.add_all([payable, canceled])
    db.commit()

    headers = auth_headers(client, "finance@example.com")
    direct_paid = client.put(
        f"/api/finance/payables/{payable.id}",
        json={"status": "pago", "payment_date": "2026-09-09"},
        headers=headers,
    )
    reactivate = client.put(
        f"/api/finance/payables/{canceled.id}",
        json={"status": "pendente"},
        headers=headers,
    )

    assert direct_paid.status_code == 400
    assert reactivate.status_code == 400


def test_receivable_financial_audit_tracks_discount_cancel_and_mark_paid(client, db):
    create_user(db, email="director@example.com", role=Role.DIRETOR)
    student = Student(full_name="Aluno Auditoria", status=StudentStatus.ACTIVE)
    receivable = Receivable(
        student=student,
        description="Mensalidade auditoria",
        amount=Decimal("600.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 9, 5),
        status=PaymentStatus.PENDING,
        type=ReceivableType.TUITION,
    )
    db.add_all([student, receivable])
    db.commit()

    headers = auth_headers(client, "director@example.com")
    discount = client.put(
        f"/api/finance/receivables/{receivable.id}",
        json={"amount": "550.00"},
        headers=headers,
    )
    assert discount.status_code == 200

    cancel = client.put(
        f"/api/finance/receivables/{receivable.id}",
        json={"status": "cancelado"},
        headers=headers,
    )
    assert cancel.status_code == 200

    open_receivable = Receivable(
        student_id=student.id,
        description="Mensalidade auditoria aberta",
        amount=Decimal("650.00"),
        paid_amount=Decimal("0.00"),
        due_date=date(2026, 10, 5),
        status=PaymentStatus.PENDING,
        type=ReceivableType.EXTRA_FEE,
    )
    db.add(open_receivable)
    db.commit()
    db.refresh(open_receivable)

    mark_paid = client.post(
        f"/api/finance/receivables/{open_receivable.id}/mark-paid",
        json={"paid_amount": "650.00", "payment_date": "2026-10-04"},
        headers=headers,
    )
    assert mark_paid.status_code == 200

    actions = [
        item.action
        for item in db.query(AuditLog)
        .filter(AuditLog.entity == "Receivable")
        .order_by(AuditLog.id.asc())
        .all()
    ]
    assert "discount" in actions
    assert "cancel" in actions
    assert "mark_paid" in actions


