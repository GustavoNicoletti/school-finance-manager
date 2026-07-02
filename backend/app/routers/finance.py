import csv
from datetime import date
from decimal import Decimal
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.finance import Payable, PaymentStatus, Receivable, ReceivableType
from app.models.student import Student
from app.models.user import Role, User
from app.schemas.finance import (
    CashFlowSummary,
    DelinquencyItem,
    PayableCreate,
    PayablePayment,
    PayableRead,
    PayableUpdate,
    ReceivableBatchCreate,
    ReceivableBatchResult,
    ReceivableCreate,
    ReceivablePayment,
    ReceivableRead,
    ReceivableUpdate,
)
from app.services.audit_service import model_snapshot, register_audit
from app.services.export_service import ExcelReportConfig, ExcelReportSection, build_excel_report
from app.services.finance_service import generate_receivable_batch, get_cash_flow, get_delinquency_report


router = APIRouter(prefix="/finance", tags=["Financeiro"])
financial_admin_roles = (Role.ADMINISTRADOR, Role.DIRETOR)


def _ensure_student_exists(db: Session, student_id: int) -> None:
    if not db.get(Student, student_id):
        raise HTTPException(status_code=400, detail="Aluno informado nao foi encontrado.")


def _month_bounds(value: date) -> tuple[date, date]:
    first_day = value.replace(day=1)
    next_month = first_day.replace(year=first_day.year + 1, month=1) if first_day.month == 12 else first_day.replace(month=first_day.month + 1)
    return first_day, next_month


def _ensure_can_change_paid_record(record_status: PaymentStatus, current_user: User, entity_name: str) -> None:
    if record_status == PaymentStatus.PAID and current_user.role not in financial_admin_roles:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Apenas administrador ou diretor podem alterar {entity_name} ja pago.",
        )


def _validate_receivable_amounts(amount: Decimal, paid_amount: Decimal) -> None:
    if paid_amount > amount:
        raise HTTPException(status_code=400, detail="O valor pago nao pode ser maior que o valor da conta.")


def _validate_receivable_state(
    *,
    amount: Decimal,
    paid_amount: Decimal,
    status_value: PaymentStatus,
    payment_date: date | None,
) -> None:
    _validate_receivable_amounts(amount, paid_amount)
    if paid_amount > 0 and payment_date is None:
        raise HTTPException(status_code=400, detail="Informe a data de pagamento quando houver valor pago.")
    if status_value == PaymentStatus.PAID and payment_date is None:
        raise HTTPException(status_code=400, detail="Contas pagas exigem data de pagamento.")
    if status_value == PaymentStatus.PAID and paid_amount != amount:
        raise HTTPException(status_code=400, detail="Uma conta paga deve ter valor pago igual ao valor total.")
    if status_value == PaymentStatus.CANCELED and (paid_amount > 0 or payment_date is not None):
        raise HTTPException(status_code=400, detail="Nao e possivel cancelar uma conta com pagamento registrado.")


def _validate_payable_state(*, status_value: PaymentStatus, payment_date: date | None) -> None:
    if status_value == PaymentStatus.PAID and payment_date is None:
        raise HTTPException(status_code=400, detail="Contas pagas exigem data de pagamento.")
    if status_value != PaymentStatus.PAID and payment_date is not None:
        raise HTTPException(status_code=400, detail="A data de pagamento so pode ser informada para contas pagas.")


def _ensure_receivable_manual_paid_transition_is_not_allowed(
    *,
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    if current_status != PaymentStatus.PAID and new_status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail="Use o endpoint de baixa para registrar pagamento em contas a receber.",
        )


def _ensure_payable_manual_paid_transition_is_not_allowed(
    *,
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    if current_status != PaymentStatus.PAID and new_status == PaymentStatus.PAID:
        raise HTTPException(
            status_code=400,
            detail="Use o endpoint de baixa para registrar pagamento em contas a pagar.",
        )


def _ensure_canceled_receivable_is_not_reactivated(
    *,
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    if current_status == PaymentStatus.CANCELED and new_status != PaymentStatus.CANCELED:
        raise HTTPException(status_code=400, detail="Nao e permitido reativar uma conta a receber cancelada.")


def _ensure_canceled_payable_is_not_reactivated(
    *,
    current_status: PaymentStatus,
    new_status: PaymentStatus,
) -> None:
    if current_status == PaymentStatus.CANCELED and new_status != PaymentStatus.CANCELED:
        raise HTTPException(status_code=400, detail="Nao e permitido reativar uma conta a pagar cancelada.")


def _commit_finance_transaction(db: Session, duplicate_message: str | None = None) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        detail = duplicate_message or "Nao foi possivel concluir a operacao financeira."
        raise HTTPException(status_code=400, detail=detail) from exc


def _ensure_receivable_not_duplicated(
    db: Session,
    *,
    student_id: int,
    receivable_type: ReceivableType,
    due_date: date,
    ignore_id: int | None = None,
) -> None:
    if receivable_type != ReceivableType.TUITION:
        return

    month_start, next_month_start = _month_bounds(due_date)
    query = db.query(Receivable.id).filter(
        Receivable.student_id == student_id,
        Receivable.type == receivable_type,
        Receivable.status != PaymentStatus.CANCELED,
        Receivable.due_date >= month_start,
        Receivable.due_date < next_month_start,
    )
    if ignore_id is not None:
        query = query.filter(Receivable.id != ignore_id)
    if query.first():
        raise HTTPException(status_code=400, detail="Ja existe uma mensalidade para este aluno no mes informado.")


def _csv_response(filename: str, headers: list[str], rows: list[list[object]]) -> Response:
    output = StringIO()
    writer = csv.writer(output, delimiter=";")
    writer.writerow(headers)
    writer.writerows(rows)
    return Response(
        content=f"\ufeff{output.getvalue()}",
        media_type="text/csv; charset=utf-8",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _xlsx_response(config: ExcelReportConfig) -> Response:
    return Response(
        content=build_excel_report(config),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{config.filename}"'},
    )


def _receivable_update_action(previous: dict, new: Receivable) -> str:
    if previous.get("status") != PaymentStatus.CANCELED.value and new.status == PaymentStatus.CANCELED:
        return "cancel"
    previous_amount = Decimal(str(previous.get("amount", "0")))
    if new.amount != previous_amount:
        return "discount" if new.amount < previous_amount else "edit_value"
    return "update"


def _payable_update_action(previous: dict, new: Payable) -> str:
    if previous.get("status") != PaymentStatus.CANCELED.value and new.status == PaymentStatus.CANCELED:
        return "cancel"
    previous_amount = Decimal(str(previous.get("amount", "0")))
    if new.amount != previous_amount:
        return "edit_value"
    return "update"


@router.get("/delinquency", response_model=list[DelinquencyItem])
def delinquency_report(
    as_of_date: date | None = None,
    limit: int | None = Query(default=None, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DELINQUENCY_VIEW.value)),
) -> list[DelinquencyItem]:
    items = get_delinquency_report(db, as_of_date or date.today())
    return items[:limit] if limit is not None else items


@router.get("/delinquency/export.csv")
def export_delinquency_report(
    as_of_date: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DELINQUENCY_VIEW.value)),
) -> Response:
    items = get_delinquency_report(db, as_of_date or date.today())
    return _csv_response(
        "inadimplencia.csv",
        ["aluno", "turma", "telefone", "parcelas", "mais_antiga", "valor_em_aberto"],
        [[item.student_name, item.class_name or "", item.phone or "", item.overdue_count, item.oldest_due_date, item.overdue_amount] for item in items],
    )


@router.get("/delinquency/export.xlsx")
def export_delinquency_report_excel(
    as_of_date: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DELINQUENCY_VIEW.value)),
) -> Response:
    reference_date = as_of_date or date.today()
    items = get_delinquency_report(db, reference_date)
    total_amount = sum((item.overdue_amount for item in items), Decimal("0.00"))
    return _xlsx_response(
        ExcelReportConfig(
            filename="inadimplencia.xlsx",
            sheet_name="Inadimplencia",
            title="Relatorio de Inadimplencia",
            headers=["Aluno", "Turma", "Telefone", "Parcelas", "Mais antiga", "Valor em aberto"],
            rows=[[item.student_name, item.class_name or "", item.phone or "", item.overdue_count, item.oldest_due_date, item.overdue_amount] for item in items],
            filters=[ExcelReportSection("Data de referencia", reference_date)],
            summary=[
                ExcelReportSection("Total de alunos", len(items)),
                ExcelReportSection("Valor total em aberto", total_amount),
            ],
            currency_columns={6},
            date_columns={5},
            integer_columns={4},
        )
    )


@router.get("/cash-flow", response_model=CashFlowSummary)
def cash_flow_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.CASH_FLOW_VIEW.value)),
) -> CashFlowSummary:
    if end_date < start_date:
        raise HTTPException(status_code=400, detail="A data final deve ser maior ou igual a data inicial.")
    if (end_date - start_date).days > 366:
        raise HTTPException(status_code=400, detail="O periodo maximo para consulta e de 366 dias.")
    return get_cash_flow(db, start_date, end_date)


@router.get("/cash-flow/export.csv")
def export_cash_flow_report(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.CASH_FLOW_VIEW.value)),
) -> Response:
    summary = cash_flow_report(start_date=start_date, end_date=end_date, db=db, _=_)
    return _csv_response(
        "fluxo_caixa.csv",
        ["data", "receita_prevista", "receita_recebida", "despesas_pagas", "saldo"],
        [[entry.date, entry.expected_revenue, entry.received_revenue, entry.paid_expenses, entry.balance] for entry in summary.entries],
    )


@router.get("/cash-flow/export.xlsx")
def export_cash_flow_report_excel(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.CASH_FLOW_VIEW.value)),
) -> Response:
    summary = cash_flow_report(start_date=start_date, end_date=end_date, db=db, _=_)
    return _xlsx_response(
        ExcelReportConfig(
            filename="fluxo_caixa.xlsx",
            sheet_name="Fluxo de Caixa",
            title="Relatorio de Fluxo de Caixa",
            headers=["Data", "Receita prevista", "Receita recebida", "Despesas pagas", "Saldo"],
            rows=[[entry.date, entry.expected_revenue, entry.received_revenue, entry.paid_expenses, entry.balance] for entry in summary.entries],
            filters=[
                ExcelReportSection("Data inicial", start_date),
                ExcelReportSection("Data final", end_date),
            ],
            summary=[
                ExcelReportSection("Receita prevista", summary.expected_revenue),
                ExcelReportSection("Receita recebida", summary.received_revenue),
                ExcelReportSection("Despesas pagas", summary.paid_expenses),
                ExcelReportSection("Saldo", summary.balance),
            ],
            currency_columns={2, 3, 4, 5},
            date_columns={1},
        )
    )


@router.get("/receivables", response_model=list[ReceivableRead])
def list_receivables(
    search: str | None = None,
    student_id: int | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    type_filter: ReceivableType | None = Query(default=None, alias="type"),
    due_from: date | None = None,
    due_to: date | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> list[Receivable]:
    query = db.query(Receivable)
    if search:
        query = query.join(Student, Receivable.student_id == Student.id).filter(
            Student.full_name.ilike(f"%{search}%") | Receivable.description.ilike(f"%{search}%")
        )
    if student_id is not None:
        query = query.filter(Receivable.student_id == student_id)
    if status_filter:
        query = query.filter(Receivable.status == status_filter)
    if type_filter:
        query = query.filter(Receivable.type == type_filter)
    if due_from:
        query = query.filter(Receivable.due_date >= due_from)
    if due_to:
        query = query.filter(Receivable.due_date <= due_to)
    return query.order_by(Receivable.due_date.desc()).offset(skip).limit(limit).all()


@router.get("/receivables/export.csv")
def export_receivables(
    search: str | None = None,
    student_id: int | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    type_filter: ReceivableType | None = Query(default=None, alias="type"),
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> Response:
    query = db.query(Receivable, Student.full_name).join(Student, Receivable.student_id == Student.id)
    if search:
        query = query.filter(Student.full_name.ilike(f"%{search}%") | Receivable.description.ilike(f"%{search}%"))
    if student_id is not None:
        query = query.filter(Receivable.student_id == student_id)
    if status_filter:
        query = query.filter(Receivable.status == status_filter)
    if type_filter:
        query = query.filter(Receivable.type == type_filter)
    if due_from:
        query = query.filter(Receivable.due_date >= due_from)
    if due_to:
        query = query.filter(Receivable.due_date <= due_to)
    rows = query.order_by(Receivable.due_date.desc()).all()
    return _csv_response(
        "contas_a_receber.csv",
        ["aluno", "descricao", "tipo", "status", "valor", "valor_pago", "vencimento", "pagamento", "observacoes"],
        [
            [student_name, item.description, item.type.value, item.status.value, item.amount, item.paid_amount, item.due_date, item.payment_date or "", item.notes or ""]
            for item, student_name in rows
        ],
    )


@router.get("/receivables/export.xlsx")
def export_receivables_excel(
    search: str | None = None,
    student_id: int | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    type_filter: ReceivableType | None = Query(default=None, alias="type"),
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> Response:
    query = db.query(Receivable, Student.full_name).join(Student, Receivable.student_id == Student.id)
    if search:
        query = query.filter(Student.full_name.ilike(f"%{search}%") | Receivable.description.ilike(f"%{search}%"))
    if student_id is not None:
        query = query.filter(Receivable.student_id == student_id)
    if status_filter:
        query = query.filter(Receivable.status == status_filter)
    if type_filter:
        query = query.filter(Receivable.type == type_filter)
    if due_from:
        query = query.filter(Receivable.due_date >= due_from)
    if due_to:
        query = query.filter(Receivable.due_date <= due_to)
    rows = query.order_by(Receivable.due_date.desc()).all()
    total_amount = sum((item.amount for item, _student_name in rows), Decimal("0.00"))
    total_paid = sum((item.paid_amount for item, _student_name in rows), Decimal("0.00"))
    return _xlsx_response(
        ExcelReportConfig(
            filename="contas_a_receber.xlsx",
            sheet_name="Contas a Receber",
            title="Relatorio de Contas a Receber",
            headers=["Aluno", "Descricao", "Tipo", "Status", "Valor", "Valor pago", "Vencimento", "Pagamento", "Observacoes"],
            rows=[
                [student_name, item.description, item.type.value, item.status.value, item.amount, item.paid_amount, item.due_date, item.payment_date or "", item.notes or ""]
                for item, student_name in rows
            ],
            filters=[
                ExcelReportSection("Busca", search or "Todos"),
                ExcelReportSection("Aluno", student_id or "Todos"),
                ExcelReportSection("Status", status_filter.value if status_filter else "Todos"),
                ExcelReportSection("Tipo", type_filter.value if type_filter else "Todos"),
                ExcelReportSection("Vencimento inicial", due_from or "Nao informado"),
                ExcelReportSection("Vencimento final", due_to or "Nao informado"),
            ],
            summary=[
                ExcelReportSection("Quantidade de contas", len(rows)),
                ExcelReportSection("Valor total", total_amount),
                ExcelReportSection("Valor total pago", total_paid),
                ExcelReportSection("Saldo em aberto", total_amount - total_paid),
            ],
            currency_columns={5, 6},
            date_columns={7, 8},
            status_column=4,
        )
    )


@router.post("/receivables/generate-batch", response_model=ReceivableBatchResult, status_code=status.HTTP_201_CREATED)
def create_receivable_batch(
    payload: ReceivableBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.RECEIVABLES_MANAGE.value)),
) -> ReceivableBatchResult:
    _, result = generate_receivable_batch(db, payload)
    db.commit()
    register_audit(
        db,
        user=current_user,
        action="bulk_generate",
        entity="ReceivableBatch",
        entity_id=None,
        new_value=result.model_dump(mode="json"),
    )
    return result


@router.post("/receivables", response_model=ReceivableRead, status_code=status.HTTP_201_CREATED)
def create_receivable(
    payload: ReceivableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.RECEIVABLES_MANAGE.value)),
) -> Receivable:
    _ensure_student_exists(db, payload.student_id)
    _validate_receivable_state(
        amount=payload.amount,
        paid_amount=payload.paid_amount,
        status_value=payload.status,
        payment_date=payload.payment_date,
    )
    _ensure_receivable_not_duplicated(db, student_id=payload.student_id, receivable_type=payload.type, due_date=payload.due_date)
    receivable = Receivable(**payload.model_dump())
    db.add(receivable)
    _commit_finance_transaction(db, duplicate_message="Ja existe uma mensalidade para este aluno no mes informado.")
    db.refresh(receivable)
    register_audit(db, user=current_user, action="create", entity="Receivable", entity_id=receivable.id, new_value=model_snapshot(receivable))
    return receivable


@router.get("/receivables/{receivable_id}", response_model=ReceivableRead)
def get_receivable(
    receivable_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> Receivable:
    receivable = db.get(Receivable, receivable_id)
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber nao encontrada.")
    return receivable


@router.put("/receivables/{receivable_id}", response_model=ReceivableRead)
def update_receivable(
    receivable_id: int,
    payload: ReceivableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.RECEIVABLES_MANAGE.value)),
) -> Receivable:
    receivable = db.get(Receivable, receivable_id)
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber nao encontrada.")
    _ensure_can_change_paid_record(receivable.status, current_user, "conta a receber")
    if payload.student_id is not None:
        _ensure_student_exists(db, payload.student_id)

    previous = model_snapshot(receivable)
    data = payload.model_dump(exclude_unset=True)
    new_amount = data.get("amount", receivable.amount)
    new_paid_amount = data.get("paid_amount", receivable.paid_amount)
    new_student_id = data.get("student_id", receivable.student_id)
    new_type = data.get("type", receivable.type)
    new_due_date = data.get("due_date", receivable.due_date)
    new_status = data.get("status", receivable.status)
    new_payment_date = data.get("payment_date", receivable.payment_date)
    _ensure_receivable_manual_paid_transition_is_not_allowed(current_status=receivable.status, new_status=new_status)
    _ensure_canceled_receivable_is_not_reactivated(current_status=receivable.status, new_status=new_status)
    _validate_receivable_state(
        amount=new_amount,
        paid_amount=new_paid_amount,
        status_value=new_status,
        payment_date=new_payment_date,
    )
    _ensure_receivable_not_duplicated(db, student_id=new_student_id, receivable_type=new_type, due_date=new_due_date, ignore_id=receivable.id)

    for field, value in data.items():
        setattr(receivable, field, value)

    _commit_finance_transaction(db, duplicate_message="Ja existe uma mensalidade para este aluno no mes informado.")
    db.refresh(receivable)
    register_audit(
        db,
        user=current_user,
        action=_receivable_update_action(previous, receivable),
        entity="Receivable",
        entity_id=receivable.id,
        previous_value=previous,
        new_value=model_snapshot(receivable),
    )
    return receivable


@router.delete("/receivables/{receivable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_receivable(
    receivable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.RECEIVABLES_MANAGE.value)),
) -> None:
    receivable = db.get(Receivable, receivable_id)
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber nao encontrada.")
    _ensure_can_change_paid_record(receivable.status, current_user, "conta a receber")
    previous = model_snapshot(receivable)
    db.delete(receivable)
    db.commit()
    register_audit(db, user=current_user, action="delete", entity="Receivable", entity_id=receivable_id, previous_value=previous)


@router.post("/receivables/{receivable_id}/mark-paid", response_model=ReceivableRead)
def mark_receivable_paid(
    receivable_id: int,
    payload: ReceivablePayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.RECEIVABLES_MANAGE.value)),
) -> Receivable:
    receivable = db.get(Receivable, receivable_id)
    if not receivable:
        raise HTTPException(status_code=404, detail="Conta a receber nao encontrada.")
    if receivable.status == PaymentStatus.CANCELED:
        raise HTTPException(status_code=400, detail="Nao e possivel dar baixa em uma conta cancelada.")
    _ensure_can_change_paid_record(receivable.status, current_user, "conta a receber")

    previous = model_snapshot(receivable)
    paid_amount = payload.paid_amount if payload.paid_amount is not None else receivable.amount
    payment_date = payload.payment_date or date.today()
    status_value = (
        PaymentStatus.PAID
        if paid_amount >= receivable.amount
        else PaymentStatus.OVERDUE
        if receivable.due_date < date.today()
        else PaymentStatus.PENDING
    )
    _validate_receivable_state(
        amount=receivable.amount,
        paid_amount=paid_amount,
        status_value=status_value,
        payment_date=payment_date,
    )

    receivable.paid_amount = paid_amount
    receivable.payment_date = payment_date
    if payload.notes:
        receivable.notes = f"{receivable.notes}\n{payload.notes}" if receivable.notes else payload.notes
    receivable.status = status_value

    _commit_finance_transaction(db)
    db.refresh(receivable)
    register_audit(
        db,
        user=current_user,
        action="mark_paid",
        entity="Receivable",
        entity_id=receivable.id,
        previous_value=previous,
        new_value=model_snapshot(receivable),
    )
    return receivable


@router.get("/payables", response_model=list[PayableRead])
def list_payables(
    search: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    skip: int = 0,
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> list[Payable]:
    query = db.query(Payable)
    if search:
        query = query.filter(Payable.description.ilike(f"%{search}%") | Payable.supplier.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(Payable.status == status_filter)
    if category:
        query = query.filter(Payable.category.ilike(f"%{category}%"))
    if due_from:
        query = query.filter(Payable.due_date >= due_from)
    if due_to:
        query = query.filter(Payable.due_date <= due_to)
    return query.order_by(Payable.due_date.desc()).offset(skip).limit(limit).all()


@router.get("/payables/export.csv")
def export_payables(
    search: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> Response:
    query = db.query(Payable)
    if search:
        query = query.filter(Payable.description.ilike(f"%{search}%") | Payable.supplier.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(Payable.status == status_filter)
    if category:
        query = query.filter(Payable.category.ilike(f"%{category}%"))
    if due_from:
        query = query.filter(Payable.due_date >= due_from)
    if due_to:
        query = query.filter(Payable.due_date <= due_to)
    rows = query.order_by(Payable.due_date.desc()).all()
    return _csv_response(
        "contas_a_pagar.csv",
        ["descricao", "categoria", "fornecedor", "status", "valor", "vencimento", "pagamento", "observacoes"],
        [[item.description, item.category or "", item.supplier or "", item.status.value, item.amount, item.due_date, item.payment_date or "", item.notes or ""] for item in rows],
    )


@router.get("/payables/export.xlsx")
def export_payables_excel(
    search: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> Response:
    query = db.query(Payable)
    if search:
        query = query.filter(Payable.description.ilike(f"%{search}%") | Payable.supplier.ilike(f"%{search}%"))
    if status_filter:
        query = query.filter(Payable.status == status_filter)
    if category:
        query = query.filter(Payable.category.ilike(f"%{category}%"))
    if due_from:
        query = query.filter(Payable.due_date >= due_from)
    if due_to:
        query = query.filter(Payable.due_date <= due_to)
    rows = query.order_by(Payable.due_date.desc()).all()
    total_amount = sum((item.amount for item in rows), Decimal("0.00"))
    total_paid = sum((item.amount for item in rows if item.status == PaymentStatus.PAID), Decimal("0.00"))
    return _xlsx_response(
        ExcelReportConfig(
            filename="contas_a_pagar.xlsx",
            sheet_name="Contas a Pagar",
            title="Relatorio de Contas a Pagar",
            headers=["Descricao", "Categoria", "Fornecedor", "Status", "Valor", "Vencimento", "Pagamento", "Observacoes"],
            rows=[[item.description, item.category or "", item.supplier or "", item.status.value, item.amount, item.due_date, item.payment_date or "", item.notes or ""] for item in rows],
            filters=[
                ExcelReportSection("Busca", search or "Todos"),
                ExcelReportSection("Status", status_filter.value if status_filter else "Todos"),
                ExcelReportSection("Categoria", category or "Todas"),
                ExcelReportSection("Vencimento inicial", due_from or "Nao informado"),
                ExcelReportSection("Vencimento final", due_to or "Nao informado"),
            ],
            summary=[
                ExcelReportSection("Quantidade de contas", len(rows)),
                ExcelReportSection("Valor total", total_amount),
                ExcelReportSection("Valor total pago", total_paid),
                ExcelReportSection("Valor pendente", total_amount - total_paid),
            ],
            currency_columns={5},
            date_columns={6, 7},
            status_column=4,
        )
    )


@router.post("/payables", response_model=PayableRead, status_code=status.HTTP_201_CREATED)
def create_payable(
    payload: PayableCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.PAYABLES_MANAGE.value)),
) -> Payable:
    _validate_payable_state(status_value=payload.status, payment_date=payload.payment_date)
    payable = Payable(**payload.model_dump())
    db.add(payable)
    _commit_finance_transaction(db)
    db.refresh(payable)
    register_audit(db, user=current_user, action="create", entity="Payable", entity_id=payable.id, new_value=model_snapshot(payable))
    return payable


@router.get("/payables/{payable_id}", response_model=PayableRead)
def get_payable(
    payable_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> Payable:
    payable = db.get(Payable, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar nao encontrada.")
    return payable


@router.put("/payables/{payable_id}", response_model=PayableRead)
def update_payable(
    payable_id: int,
    payload: PayableUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.PAYABLES_MANAGE.value)),
) -> Payable:
    payable = db.get(Payable, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar nao encontrada.")
    _ensure_can_change_paid_record(payable.status, current_user, "conta a pagar")
    previous = model_snapshot(payable)
    data = payload.model_dump(exclude_unset=True)
    new_status = data.get("status", payable.status)
    new_payment_date = data.get("payment_date", payable.payment_date)
    _ensure_payable_manual_paid_transition_is_not_allowed(current_status=payable.status, new_status=new_status)
    _ensure_canceled_payable_is_not_reactivated(current_status=payable.status, new_status=new_status)
    _validate_payable_state(status_value=new_status, payment_date=new_payment_date)

    for field, value in data.items():
        setattr(payable, field, value)

    _commit_finance_transaction(db)
    db.refresh(payable)
    register_audit(
        db,
        user=current_user,
        action=_payable_update_action(previous, payable),
        entity="Payable",
        entity_id=payable.id,
        previous_value=previous,
        new_value=model_snapshot(payable),
    )
    return payable


@router.delete("/payables/{payable_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payable(
    payable_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.PAYABLES_MANAGE.value)),
) -> None:
    payable = db.get(Payable, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar nao encontrada.")
    _ensure_can_change_paid_record(payable.status, current_user, "conta a pagar")
    previous = model_snapshot(payable)
    db.delete(payable)
    db.commit()
    register_audit(db, user=current_user, action="delete", entity="Payable", entity_id=payable_id, previous_value=previous)


@router.post("/payables/{payable_id}/mark-paid", response_model=PayableRead)
def mark_payable_paid(
    payable_id: int,
    payload: PayablePayment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permissions(Permission.PAYABLES_MANAGE.value)),
) -> Payable:
    payable = db.get(Payable, payable_id)
    if not payable:
        raise HTTPException(status_code=404, detail="Conta a pagar nao encontrada.")
    if payable.status == PaymentStatus.CANCELED:
        raise HTTPException(status_code=400, detail="Nao e possivel dar baixa em uma conta cancelada.")
    _ensure_can_change_paid_record(payable.status, current_user, "conta a pagar")

    previous = model_snapshot(payable)
    payable.status = PaymentStatus.PAID
    payable.payment_date = payload.payment_date or date.today()
    _validate_payable_state(status_value=payable.status, payment_date=payable.payment_date)
    if payload.notes:
        payable.notes = f"{payable.notes}\n{payload.notes}" if payable.notes else payload.notes

    _commit_finance_transaction(db)
    db.refresh(payable)
    register_audit(
        db,
        user=current_user,
        action="mark_paid",
        entity="Payable",
        entity_id=payable.id,
        previous_value=previous,
        new_value=model_snapshot(payable),
    )
    return payable
