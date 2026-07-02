from datetime import date
from decimal import Decimal

from app.models.finance import PaymentStatus, Receivable, ReceivableType
from app.models.student import Student, StudentStatus
from app.schemas.finance import ReceivableBatchCreate
from app.services.finance_service import generate_receivable_batch, get_cash_flow


def test_generate_receivable_batch_respects_active_students_and_class_filter(db) -> None:
    db.add_all(
        [
            Student(full_name="Alice", status=StudentStatus.ACTIVE, class_name="1 Ano"),
            Student(full_name="Bruno", status=StudentStatus.INACTIVE, class_name="1 Ano"),
            Student(full_name="Carla", status=StudentStatus.ACTIVE, class_name="2 Ano"),
        ]
    )
    db.commit()

    payload = ReceivableBatchCreate(
        reference_month=date(2026, 9, 1),
        due_date=date(2026, 9, 5),
        amount=Decimal("850.00"),
        type=ReceivableType.TUITION,
        description_prefix="Mensalidade",
        class_name="1 Ano",
        only_active_students=True,
    )

    created_items, result = generate_receivable_batch(db, payload)

    assert result.total_students == 1
    assert result.created_count == 1
    assert result.skipped_count == 0
    assert [item.student_id for item in created_items] == [1]
    assert created_items[0].description == "Mensalidade 09/2026"


def test_generate_receivable_batch_skips_existing_non_canceled_tuition(db) -> None:
    student = Student(full_name="Aluno Existente", status=StudentStatus.ACTIVE, class_name="1 Ano")
    db.add(student)
    db.flush()
    db.add(
        Receivable(
            student_id=student.id,
            description="Mensalidade 09/2026",
            amount=Decimal("900.00"),
            paid_amount=Decimal("0.00"),
            due_date=date(2026, 9, 10),
            status=PaymentStatus.PENDING,
            type=ReceivableType.TUITION,
        )
    )
    db.commit()

    payload = ReceivableBatchCreate(
        reference_month=date(2026, 9, 1),
        due_date=date(2026, 9, 5),
        amount=Decimal("900.00"),
        type=ReceivableType.TUITION,
        description_prefix="Mensalidade",
    )

    created_items, result = generate_receivable_batch(db, payload)

    assert created_items == []
    assert result.created_count == 0
    assert result.skipped_count == 1
    assert result.skipped_students == ["Aluno Existente"]


def test_cash_flow_service_returns_zero_filled_days_and_totals(db) -> None:
    student = Student(full_name="Aluno Fluxo", status=StudentStatus.ACTIVE)
    db.add(student)
    db.flush()
    db.add(
        Receivable(
            student_id=student.id,
            description="Mensalidade",
            amount=Decimal("500.00"),
            paid_amount=Decimal("500.00"),
            due_date=date(2026, 9, 1),
            payment_date=date(2026, 9, 3),
            status=PaymentStatus.PAID,
            type=ReceivableType.TUITION,
        )
    )
    db.commit()

    summary = get_cash_flow(db, date(2026, 9, 1), date(2026, 9, 3))

    assert [entry.date.isoformat() for entry in summary.entries] == ["2026-09-01", "2026-09-02", "2026-09-03"]
    assert [entry.expected_revenue for entry in summary.entries] == [
        Decimal("500.00"),
        Decimal("0.00"),
        Decimal("0.00"),
    ]
    assert [entry.received_revenue for entry in summary.entries] == [
        Decimal("0.00"),
        Decimal("0.00"),
        Decimal("500.00"),
    ]
    assert summary.expected_revenue == Decimal("500.00")
    assert summary.received_revenue == Decimal("500.00")
    assert summary.paid_expenses == Decimal("0.00")
    assert summary.balance == Decimal("500.00")
