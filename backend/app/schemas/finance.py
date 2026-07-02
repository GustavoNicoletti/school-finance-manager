from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.models.finance import PaymentStatus, ReceivableType


class ReceivableBase(BaseModel):
    student_id: int
    description: str = Field(min_length=2, max_length=180)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    paid_amount: Decimal = Field(default=Decimal("0.00"), ge=0, max_digits=12, decimal_places=2)
    due_date: date
    payment_date: date | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    type: ReceivableType = ReceivableType.TUITION
    notes: str | None = None


class ReceivableCreate(ReceivableBase):
    pass


class ReceivableUpdate(BaseModel):
    student_id: int | None = None
    description: str | None = Field(default=None, min_length=2, max_length=180)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    paid_amount: Decimal | None = Field(default=None, ge=0, max_digits=12, decimal_places=2)
    due_date: date | None = None
    payment_date: date | None = None
    status: PaymentStatus | None = None
    type: ReceivableType | None = None
    notes: str | None = None


class ReceivableRead(ReceivableBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PayableBase(BaseModel):
    description: str = Field(min_length=2, max_length=180)
    category: str | None = Field(default=None, max_length=100)
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    due_date: date
    payment_date: date | None = None
    status: PaymentStatus = PaymentStatus.PENDING
    supplier: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class PayableCreate(PayableBase):
    pass


class PayableUpdate(BaseModel):
    description: str | None = Field(default=None, min_length=2, max_length=180)
    category: str | None = Field(default=None, max_length=100)
    amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    due_date: date | None = None
    payment_date: date | None = None
    status: PaymentStatus | None = None
    supplier: str | None = Field(default=None, max_length=150)
    notes: str | None = None


class PayableRead(PayableBase):
    id: int
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ReceivablePayment(BaseModel):
    paid_amount: Decimal | None = Field(default=None, gt=0, max_digits=12, decimal_places=2)
    payment_date: date | None = None
    notes: str | None = None


class ReceivableBatchCreate(BaseModel):
    reference_month: date
    due_date: date
    amount: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    type: ReceivableType = ReceivableType.TUITION
    description_prefix: str = Field(default="Mensalidade", min_length=2, max_length=120)
    class_name: str | None = Field(default=None, max_length=80)
    only_active_students: bool = True
    notes: str | None = None


class ReceivableBatchResult(BaseModel):
    reference_month: date
    due_date: date
    amount: Decimal
    type: ReceivableType
    total_students: int
    created_count: int
    skipped_count: int
    description: str
    created_ids: list[int]
    skipped_students: list[str]


class PayablePayment(BaseModel):
    payment_date: date | None = None
    notes: str | None = None


class DelinquencyItem(BaseModel):
    student_id: int
    student_name: str
    class_name: str | None = None
    phone: str | None = None
    overdue_count: int
    overdue_amount: Decimal
    oldest_due_date: date


class CashFlowEntry(BaseModel):
    date: date
    expected_revenue: Decimal
    received_revenue: Decimal
    paid_expenses: Decimal
    balance: Decimal


class CashFlowSummary(BaseModel):
    start_date: date
    end_date: date
    expected_revenue: Decimal
    received_revenue: Decimal
    paid_expenses: Decimal
    balance: Decimal
    entries: list[CashFlowEntry]
