from collections import defaultdict
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.finance import Payable, PaymentStatus, Receivable, ReceivableType
from app.models.student import Student, StudentStatus
from app.schemas.finance import (
    CashFlowEntry,
    CashFlowSummary,
    DelinquencyItem,
    ReceivableBatchCreate,
    ReceivableBatchResult,
)


def _money(value: Decimal | int | float | None) -> Decimal:
    if value is None:
        return Decimal("0.00")
    return Decimal(value).quantize(Decimal("0.01"))


def _date_range(start_date: date, end_date: date) -> list[date]:
    days = (end_date - start_date).days
    return [start_date + timedelta(days=offset) for offset in range(days + 1)]


def get_delinquency_report(db: Session, as_of_date: date) -> list[DelinquencyItem]:
    overdue_amount = func.sum(Receivable.amount - Receivable.paid_amount)
    rows = (
        db.query(
            Student.id.label("student_id"),
            Student.full_name.label("student_name"),
            Student.class_name.label("class_name"),
            Student.phone.label("phone"),
            func.count(Receivable.id).label("overdue_count"),
            overdue_amount.label("overdue_amount"),
            func.min(Receivable.due_date).label("oldest_due_date"),
        )
        .join(Receivable, Receivable.student_id == Student.id)
        .filter(
            Receivable.status != PaymentStatus.PAID,
            Receivable.status != PaymentStatus.CANCELED,
            or_(Receivable.status == PaymentStatus.OVERDUE, Receivable.due_date < as_of_date),
        )
        .group_by(Student.id, Student.full_name, Student.class_name, Student.phone)
        .order_by(overdue_amount.desc())
        .all()
    )

    return [
        DelinquencyItem(
            student_id=row.student_id,
            student_name=row.student_name,
            class_name=row.class_name,
            phone=row.phone,
            overdue_count=row.overdue_count,
            overdue_amount=_money(row.overdue_amount),
            oldest_due_date=row.oldest_due_date,
        )
        for row in rows
    ]


def get_cash_flow(db: Session, start_date: date, end_date: date) -> CashFlowSummary:
    expected_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    received_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))
    expenses_by_date: dict[date, Decimal] = defaultdict(lambda: Decimal("0.00"))

    expected_rows = (
        db.query(Receivable.due_date, func.coalesce(func.sum(Receivable.amount), 0))
        .filter(
            Receivable.due_date >= start_date,
            Receivable.due_date <= end_date,
            Receivable.status != PaymentStatus.CANCELED,
        )
        .group_by(Receivable.due_date)
        .all()
    )
    for due_date, amount in expected_rows:
        expected_by_date[due_date] = _money(amount)

    received_rows = (
        db.query(Receivable.payment_date, func.coalesce(func.sum(Receivable.paid_amount), 0))
        .filter(
            Receivable.payment_date >= start_date,
            Receivable.payment_date <= end_date,
            Receivable.status == PaymentStatus.PAID,
        )
        .group_by(Receivable.payment_date)
        .all()
    )
    for payment_date, amount in received_rows:
        received_by_date[payment_date] = _money(amount)

    expense_rows = (
        db.query(Payable.payment_date, func.coalesce(func.sum(Payable.amount), 0))
        .filter(
            Payable.payment_date >= start_date,
            Payable.payment_date <= end_date,
            Payable.status == PaymentStatus.PAID,
        )
        .group_by(Payable.payment_date)
        .all()
    )
    for payment_date, amount in expense_rows:
        expenses_by_date[payment_date] = _money(amount)

    entries: list[CashFlowEntry] = []
    for current_date in _date_range(start_date, end_date):
        expected = expected_by_date[current_date]
        received = received_by_date[current_date]
        expenses = expenses_by_date[current_date]
        entries.append(
            CashFlowEntry(
                date=current_date,
                expected_revenue=expected,
                received_revenue=received,
                paid_expenses=expenses,
                balance=received - expenses,
            )
        )

    expected_total = sum((entry.expected_revenue for entry in entries), Decimal("0.00"))
    received_total = sum((entry.received_revenue for entry in entries), Decimal("0.00"))
    expenses_total = sum((entry.paid_expenses for entry in entries), Decimal("0.00"))

    return CashFlowSummary(
        start_date=start_date,
        end_date=end_date,
        expected_revenue=_money(expected_total),
        received_revenue=_money(received_total),
        paid_expenses=_money(expenses_total),
        balance=_money(received_total - expenses_total),
        entries=entries,
    )


def generate_receivable_batch(db: Session, payload: ReceivableBatchCreate) -> tuple[list[Receivable], ReceivableBatchResult]:
    reference_month = payload.reference_month.replace(day=1)
    next_month = reference_month.replace(year=reference_month.year + 1, month=1) if reference_month.month == 12 else reference_month.replace(month=reference_month.month + 1)
    description = f"{payload.description_prefix.strip()} {reference_month.strftime('%m/%Y')}"

    student_query = db.query(Student)
    if payload.only_active_students:
        student_query = student_query.filter(Student.status == StudentStatus.ACTIVE)
    if payload.class_name:
        student_query = student_query.filter(Student.class_name == payload.class_name.strip())

    students = student_query.order_by(Student.full_name).all()
    student_ids = [student.id for student in students]

    existing_keys = set()
    if student_ids:
        existing_rows = (
            db.query(Receivable.student_id, Receivable.type, Receivable.description)
            .filter(
                Receivable.student_id.in_(student_ids),
                Receivable.type == payload.type,
                Receivable.status != PaymentStatus.CANCELED,
                Receivable.due_date >= reference_month,
                Receivable.due_date < next_month,
            )
            .all()
        )
        existing_keys = {(student_id, receivable_type) for student_id, receivable_type, _ in existing_rows}

    created_items: list[Receivable] = []
    skipped_students: list[str] = []
    for student in students:
        key = (student.id, payload.type)
        if key in existing_keys:
            skipped_students.append(student.full_name)
            continue

        receivable = Receivable(
            student_id=student.id,
            description=description,
            amount=payload.amount,
            paid_amount=Decimal("0.00"),
            due_date=payload.due_date,
            payment_date=None,
            status=PaymentStatus.PENDING,
            type=payload.type,
            notes=payload.notes,
        )
        db.add(receivable)
        created_items.append(receivable)

    if created_items:
        db.flush()

    result = ReceivableBatchResult(
        reference_month=reference_month,
        due_date=payload.due_date,
        amount=payload.amount,
        type=payload.type,
        total_students=len(students),
        created_count=len(created_items),
        skipped_count=len(skipped_students),
        description=description,
        created_ids=[item.id for item in created_items],
        skipped_students=skipped_students,
    )
    return created_items, result
