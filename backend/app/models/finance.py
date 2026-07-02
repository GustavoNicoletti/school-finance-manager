from datetime import date, datetime
from decimal import Decimal
from enum import Enum

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Index, Numeric, String, Text, func, text
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PaymentStatus(str, Enum):
    PENDING = "pendente"
    PAID = "pago"
    OVERDUE = "atrasado"
    CANCELED = "cancelado"


class ReceivableType(str, Enum):
    TUITION = "mensalidade"
    EXTRA_FEE = "taxa_extra"
    MATERIAL = "material"
    OTHER = "outro"


class Receivable(Base):
    __tablename__ = "receivables"
    __table_args__ = (
        CheckConstraint("amount > 0", name="ck_receivables_amount_positive"),
        CheckConstraint("paid_amount >= 0", name="ck_receivables_paid_amount_non_negative"),
        CheckConstraint("paid_amount <= amount", name="ck_receivables_paid_amount_lte_amount"),
        Index(
            "ux_receivables_tuition_student_month_active",
            "student_id",
            text("EXTRACT(YEAR FROM due_date)"),
            text("EXTRACT(MONTH FROM due_date)"),
            "type",
            unique=True,
            postgresql_where=text("type = 'mensalidade' AND status <> 'cancelado'"),
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("students.id", ondelete="CASCADE"), nullable=False, index=True)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False, default=Decimal("0.00"))
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, values_callable=lambda enum: [item.value for item in enum], name="payment_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    type: Mapped[ReceivableType] = mapped_column(
        SAEnum(ReceivableType, values_callable=lambda enum: [item.value for item in enum], name="receivable_type"),
        nullable=False,
        default=ReceivableType.TUITION,
    )
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    student = relationship("Student", back_populates="receivables")


class Payable(Base):
    __tablename__ = "payables"
    __table_args__ = (CheckConstraint("amount > 0", name="ck_payables_amount_positive"),)

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    description: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str | None] = mapped_column(String(100), nullable=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    due_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[PaymentStatus] = mapped_column(
        SAEnum(PaymentStatus, values_callable=lambda enum: [item.value for item in enum], name="payable_status"),
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    supplier: Mapped[str | None] = mapped_column(String(150), nullable=True)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
