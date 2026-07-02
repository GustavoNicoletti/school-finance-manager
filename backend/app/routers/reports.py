from __future__ import annotations

from datetime import date
from decimal import Decimal
from enum import Enum

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func, or_
from sqlalchemy.orm import Session, selectinload

from app.core.database import get_db
from app.core.dependencies import require_permissions
from app.core.permissions import Permission
from app.models.finance import Payable, PaymentStatus, Receivable, ReceivableType
from app.models.guardian import Guardian
from app.models.student import Student, StudentStatus
from app.models.user import User
from app.services.export_service import (
    ExcelReportConfig,
    ExcelReportSection,
    PdfReportConfig,
    build_excel_report,
    build_pdf_report,
)
from app.services.finance_service import get_cash_flow


router = APIRouter(prefix="/reports", tags=["Relatorios"])

MAX_REPORT_RANGE_DAYS = 366


class FinancePeriodField(str, Enum):
    DUE_DATE = "due_date"
    PAYMENT_DATE = "payment_date"
    CREATED_AT = "created_at"


PERIOD_FIELD_LABELS = {
    FinancePeriodField.DUE_DATE: "Vencimento",
    FinancePeriodField.PAYMENT_DATE: "Pagamento",
    FinancePeriodField.CREATED_AT: "Cadastro",
}


def _xlsx_response(config: ExcelReportConfig) -> Response:
    return Response(
        content=build_excel_report(config),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{config.filename}"'},
    )


def _pdf_response(config: PdfReportConfig) -> Response:
    return Response(
        content=build_pdf_report(config),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{config.filename}"'},
    )


def _validate_period(start_date: date | None, end_date: date | None) -> None:
    if start_date and end_date:
        if end_date < start_date:
            raise HTTPException(status_code=400, detail="A data final deve ser maior ou igual a data inicial.")
        if (end_date - start_date).days > MAX_REPORT_RANGE_DAYS:
            raise HTTPException(status_code=400, detail="O periodo maximo para relatorios e de 366 dias.")


def _date_filters(label_start: str, label_end: str, start_date: date | None, end_date: date | None) -> list[ExcelReportSection]:
    return [
        ExcelReportSection(label_start, start_date or "Nao informado"),
        ExcelReportSection(label_end, end_date or "Nao informado"),
    ]


def _apply_date_filter(query, column, start_date: date | None, end_date: date | None):
    if start_date:
        query = query.filter(column >= start_date)
    if end_date:
        query = query.filter(column <= end_date)
    return query


def _apply_datetime_date_filter(query, column, start_date: date | None, end_date: date | None):
    date_column = func.date(column)
    return _apply_date_filter(query, date_column, start_date, end_date)


def _finance_period_column(model: type[Receivable] | type[Payable], period_field: FinancePeriodField):
    if period_field == FinancePeriodField.CREATED_AT:
        return func.date(model.created_at)
    return getattr(model, period_field.value)


def _age_on(birth_date: date | None, reference_date: date | None = None) -> int | str:
    if birth_date is None:
        return ""
    today = reference_date or date.today()
    return today.year - birth_date.year - ((today.month, today.day) < (birth_date.month, birth_date.day))


def _open_receivable_amount(receivable: Receivable) -> Decimal:
    return max(receivable.amount - receivable.paid_amount, Decimal("0.00"))


def _days_overdue(due_date: date, status_value: PaymentStatus, reference_date: date | None = None) -> int:
    if status_value in (PaymentStatus.PAID, PaymentStatus.CANCELED):
        return 0
    today = reference_date or date.today()
    return max((today - due_date).days, 0)


def _student_report_payload(
    db: Session,
    *,
    status_filter: StudentStatus | None,
    class_name: str | None,
    created_from: date | None,
    created_to: date | None,
) -> tuple[list[list[object]], list[ExcelReportSection], list[ExcelReportSection]]:
    _validate_period(created_from, created_to)
    query = db.query(Student).options(selectinload(Student.guardians))
    if status_filter:
        query = query.filter(Student.status == status_filter)
    if class_name:
        query = query.filter(Student.class_name.ilike(f"%{class_name}%"))
    query = _apply_datetime_date_filter(query, Student.created_at, created_from, created_to)

    students = query.order_by(Student.full_name).all()
    rows = [
        [
            student.full_name,
            student.class_name or "",
            student.status.value,
            _age_on(student.birth_date),
            ", ".join(guardian.full_name for guardian in student.guardians) or "Sem responsavel",
            student.phone or "",
            "Sim" if student.medical_information else "Nao",
            student.created_at.date(),
        ]
        for student in students
    ]
    filters = [
        ExcelReportSection("Status", status_filter.value if status_filter else "Todos"),
        ExcelReportSection("Turma", class_name or "Todas"),
        *_date_filters("Cadastro inicial", "Cadastro final", created_from, created_to),
    ]
    summary = [
        ExcelReportSection("Quantidade de alunos", len(students)),
        ExcelReportSection("Alunos ativos", sum(1 for student in students if student.status == StudentStatus.ACTIVE)),
        ExcelReportSection("Sem responsavel vinculado", sum(1 for student in students if not student.guardians)),
        ExcelReportSection("Com informacao medica", sum(1 for student in students if student.medical_information)),
    ]
    return rows, filters, summary


def _guardian_report_payload(
    db: Session,
    *,
    kinship: str | None,
    created_from: date | None,
    created_to: date | None,
) -> tuple[list[list[object]], list[ExcelReportSection], list[ExcelReportSection]]:
    _validate_period(created_from, created_to)
    query = db.query(Guardian).options(selectinload(Guardian.students))
    if kinship:
        query = query.filter(Guardian.kinship.ilike(f"%{kinship}%"))
    query = _apply_datetime_date_filter(query, Guardian.created_at, created_from, created_to)

    guardians = query.order_by(Guardian.full_name).all()
    rows = [
        [
            guardian.full_name,
            guardian.kinship or "",
            guardian.phone or "",
            guardian.email or "",
            guardian.cpf or "",
            len(guardian.students),
            ", ".join(student.full_name for student in guardian.students) or "",
            guardian.created_at.date(),
        ]
        for guardian in guardians
    ]
    filters = [
        ExcelReportSection("Parentesco", kinship or "Todos"),
        *_date_filters("Cadastro inicial", "Cadastro final", created_from, created_to),
    ]
    summary = [
        ExcelReportSection("Quantidade de responsaveis", len(guardians)),
        ExcelReportSection("Com e-mail cadastrado", sum(1 for guardian in guardians if guardian.email)),
        ExcelReportSection("Sem telefone", sum(1 for guardian in guardians if not guardian.phone)),
        ExcelReportSection("Sem aluno vinculado", sum(1 for guardian in guardians if not guardian.students)),
    ]
    return rows, filters, summary


def _receivable_report_payload(
    db: Session,
    *,
    student_id: int | None,
    description: str | None,
    status_filter: PaymentStatus | None,
    type_filter: ReceivableType | None,
    period_field: FinancePeriodField,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[list[object]], list[ExcelReportSection], list[ExcelReportSection]]:
    _validate_period(date_from, date_to)
    query = db.query(Receivable, Student.full_name).join(Student, Receivable.student_id == Student.id)
    if student_id is not None:
        query = query.filter(Receivable.student_id == student_id)
    if description:
        query = query.filter(Receivable.description.ilike(f"%{description}%"))
    if status_filter:
        query = query.filter(Receivable.status == status_filter)
    if type_filter:
        query = query.filter(Receivable.type == type_filter)
    query = _apply_date_filter(query, _finance_period_column(Receivable, period_field), date_from, date_to)

    rows_data = query.order_by(Receivable.due_date.desc()).all()
    rows = [
        [
            student_name,
            item.description,
            item.type.value,
            item.status.value,
            item.amount,
            item.paid_amount,
            _open_receivable_amount(item),
            item.due_date,
            item.payment_date or "",
            _days_overdue(item.due_date, item.status),
            item.notes or "",
        ]
        for item, student_name in rows_data
    ]
    total_amount = sum((item.amount for item, _student_name in rows_data), Decimal("0.00"))
    total_paid = sum((item.paid_amount for item, _student_name in rows_data), Decimal("0.00"))
    total_open = sum((_open_receivable_amount(item) for item, _student_name in rows_data), Decimal("0.00"))
    selected_student = db.get(Student, student_id) if student_id is not None else None
    filters = [
        ExcelReportSection("Aluno", selected_student.full_name if selected_student else "Todos"),
        ExcelReportSection("Descricao", description or "Todas"),
        ExcelReportSection("Status", status_filter.value if status_filter else "Todos"),
        ExcelReportSection("Tipo", type_filter.value if type_filter else "Todos"),
        ExcelReportSection("Periodo por", PERIOD_FIELD_LABELS[period_field]),
        *_date_filters("Data inicial", "Data final", date_from, date_to),
    ]
    summary = [
        ExcelReportSection("Quantidade de contas", len(rows_data)),
        ExcelReportSection("Valor total", total_amount),
        ExcelReportSection("Valor total pago", total_paid),
        ExcelReportSection("Saldo em aberto", total_open),
        ExcelReportSection("Contas em atraso", sum(1 for item, _student_name in rows_data if _days_overdue(item.due_date, item.status) > 0)),
    ]
    return rows, filters, summary


def _payable_report_payload(
    db: Session,
    *,
    description: str | None,
    supplier: str | None,
    status_filter: PaymentStatus | None,
    category: str | None,
    period_field: FinancePeriodField,
    date_from: date | None,
    date_to: date | None,
) -> tuple[list[list[object]], list[ExcelReportSection], list[ExcelReportSection]]:
    _validate_period(date_from, date_to)
    query = db.query(Payable)
    if description:
        query = query.filter(Payable.description.ilike(f"%{description}%"))
    if supplier:
        query = query.filter(Payable.supplier.ilike(f"%{supplier}%"))
    if status_filter:
        query = query.filter(Payable.status == status_filter)
    if category:
        query = query.filter(Payable.category.ilike(f"%{category}%"))
    query = _apply_date_filter(query, _finance_period_column(Payable, period_field), date_from, date_to)

    payables = query.order_by(Payable.due_date.desc()).all()
    rows = [
        [
            item.description,
            item.category or "",
            item.supplier or "",
            item.status.value,
            item.amount,
            item.due_date,
            item.payment_date or "",
            _days_overdue(item.due_date, item.status),
            item.notes or "",
        ]
        for item in payables
    ]
    total_amount = sum((item.amount for item in payables), Decimal("0.00"))
    total_paid = sum((item.amount for item in payables if item.status == PaymentStatus.PAID), Decimal("0.00"))
    total_pending = sum((item.amount for item in payables if item.status not in (PaymentStatus.PAID, PaymentStatus.CANCELED)), Decimal("0.00"))
    filters = [
        ExcelReportSection("Descricao", description or "Todas"),
        ExcelReportSection("Fornecedor", supplier or "Todos"),
        ExcelReportSection("Status", status_filter.value if status_filter else "Todos"),
        ExcelReportSection("Categoria", category or "Todas"),
        ExcelReportSection("Periodo por", PERIOD_FIELD_LABELS[period_field]),
        *_date_filters("Data inicial", "Data final", date_from, date_to),
    ]
    summary = [
        ExcelReportSection("Quantidade de contas", len(payables)),
        ExcelReportSection("Valor total", total_amount),
        ExcelReportSection("Valor total pago", total_paid),
        ExcelReportSection("Valor pendente", total_pending),
        ExcelReportSection("Contas em atraso", sum(1 for item in payables if _days_overdue(item.due_date, item.status) > 0)),
    ]
    return rows, filters, summary


def _delinquency_report_payload(
    db: Session,
    *,
    as_of_date: date,
    due_from: date | None,
    due_to: date | None,
) -> tuple[list[list[object]], list[ExcelReportSection], list[ExcelReportSection]]:
    _validate_period(due_from, due_to)
    overdue_amount = func.sum(Receivable.amount - Receivable.paid_amount)
    query = (
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
    )
    query = _apply_date_filter(query, Receivable.due_date, due_from, due_to)
    result_rows = (
        query.group_by(Student.id, Student.full_name, Student.class_name, Student.phone)
        .order_by(overdue_amount.desc())
        .all()
    )
    rows = [
        [
            row.student_name,
            row.class_name or "",
            row.phone or "",
            row.overdue_count,
            row.oldest_due_date,
            _days_overdue(row.oldest_due_date, PaymentStatus.OVERDUE, as_of_date),
            Decimal(row.overdue_amount or 0).quantize(Decimal("0.01")),
        ]
        for row in result_rows
    ]
    total_amount = sum((row[6] for row in rows), Decimal("0.00"))
    max_days = max((row[5] for row in rows), default=0)
    filters = [
        ExcelReportSection("Data de referencia", as_of_date),
        *_date_filters("Vencimento inicial", "Vencimento final", due_from, due_to),
    ]
    summary = [
        ExcelReportSection("Total de alunos", len(rows)),
        ExcelReportSection("Valor total em aberto", total_amount),
        ExcelReportSection("Maior atraso em dias", max_days),
    ]
    return rows, filters, summary


@router.get("/students.xlsx")
def export_students_excel(
    status_filter: StudentStatus | None = Query(default=None, alias="status"),
    class_name: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.STUDENTS_VIEW.value)),
) -> Response:
    rows, filters, summary = _student_report_payload(
        db,
        status_filter=status_filter,
        class_name=class_name,
        created_from=created_from,
        created_to=created_to,
    )
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_alunos.xlsx",
            sheet_name="Alunos",
            title="Relatorio de Alunos",
            headers=["Aluno", "Turma", "Status", "Idade", "Responsaveis", "Telefone", "Info medica", "Cadastro"],
            rows=rows,
            filters=filters,
            summary=summary,
            date_columns={8},
            integer_columns={4},
            status_column=3,
        )
    )


@router.get("/students.pdf")
def export_students_pdf(
    status_filter: StudentStatus | None = Query(default=None, alias="status"),
    class_name: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.STUDENTS_VIEW.value)),
) -> Response:
    rows, filters, summary = _student_report_payload(
        db,
        status_filter=status_filter,
        class_name=class_name,
        created_from=created_from,
        created_to=created_to,
    )
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_alunos.pdf",
            title="Relatorio de Alunos",
            headers=["Aluno", "Turma", "Status", "Idade", "Responsaveis", "Telefone", "Info medica", "Cadastro"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )


@router.get("/guardians.xlsx")
def export_guardians_excel(
    kinship: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.GUARDIANS_VIEW.value)),
) -> Response:
    rows, filters, summary = _guardian_report_payload(db, kinship=kinship, created_from=created_from, created_to=created_to)
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_responsaveis.xlsx",
            sheet_name="Responsaveis",
            title="Relatorio de Responsaveis",
            headers=["Responsavel", "Parentesco", "Telefone", "E-mail", "CPF", "Qtd alunos", "Alunos", "Cadastro"],
            rows=rows,
            filters=filters,
            summary=summary,
            date_columns={8},
            integer_columns={6},
        )
    )


@router.get("/guardians.pdf")
def export_guardians_pdf(
    kinship: str | None = None,
    created_from: date | None = None,
    created_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.GUARDIANS_VIEW.value)),
) -> Response:
    rows, filters, summary = _guardian_report_payload(db, kinship=kinship, created_from=created_from, created_to=created_to)
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_responsaveis.pdf",
            title="Relatorio de Responsaveis",
            headers=["Responsavel", "Parentesco", "Telefone", "E-mail", "CPF", "Qtd alunos", "Alunos", "Cadastro"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )


@router.get("/receivables.xlsx")
def export_receivables_excel(
    student_id: int | None = None,
    description: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    type_filter: ReceivableType | None = Query(default=None, alias="type"),
    period_field: FinancePeriodField = FinancePeriodField.DUE_DATE,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> Response:
    rows, filters, summary = _receivable_report_payload(
        db,
        student_id=student_id,
        description=description,
        status_filter=status_filter,
        type_filter=type_filter,
        period_field=period_field,
        date_from=date_from,
        date_to=date_to,
    )
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_contas_receber.xlsx",
            sheet_name="Contas a Receber",
            title="Relatorio de Contas a Receber",
            headers=["Aluno", "Descricao", "Tipo", "Status", "Valor", "Valor pago", "Em aberto", "Vencimento", "Pagamento", "Dias atraso", "Observacoes"],
            rows=rows,
            filters=filters,
            summary=summary,
            currency_columns={5, 6, 7},
            date_columns={8, 9},
            integer_columns={10},
            status_column=4,
        )
    )


@router.get("/receivables.pdf")
def export_receivables_pdf(
    student_id: int | None = None,
    description: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    type_filter: ReceivableType | None = Query(default=None, alias="type"),
    period_field: FinancePeriodField = FinancePeriodField.DUE_DATE,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.RECEIVABLES_VIEW.value)),
) -> Response:
    rows, filters, summary = _receivable_report_payload(
        db,
        student_id=student_id,
        description=description,
        status_filter=status_filter,
        type_filter=type_filter,
        period_field=period_field,
        date_from=date_from,
        date_to=date_to,
    )
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_contas_receber.pdf",
            title="Relatorio de Contas a Receber",
            headers=["Aluno", "Descricao", "Tipo", "Status", "Valor", "Valor pago", "Em aberto", "Vencimento", "Pagamento", "Dias atraso", "Observacoes"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )


@router.get("/payables.xlsx")
def export_payables_excel(
    description: str | None = None,
    supplier: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    period_field: FinancePeriodField = FinancePeriodField.DUE_DATE,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> Response:
    rows, filters, summary = _payable_report_payload(
        db,
        description=description,
        supplier=supplier,
        status_filter=status_filter,
        category=category,
        period_field=period_field,
        date_from=date_from,
        date_to=date_to,
    )
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_contas_pagar.xlsx",
            sheet_name="Contas a Pagar",
            title="Relatorio de Contas a Pagar",
            headers=["Descricao", "Categoria", "Fornecedor", "Status", "Valor", "Vencimento", "Pagamento", "Dias atraso", "Observacoes"],
            rows=rows,
            filters=filters,
            summary=summary,
            currency_columns={5},
            date_columns={6, 7},
            integer_columns={8},
            status_column=4,
        )
    )


@router.get("/payables.pdf")
def export_payables_pdf(
    description: str | None = None,
    supplier: str | None = None,
    status_filter: PaymentStatus | None = Query(default=None, alias="status"),
    category: str | None = None,
    period_field: FinancePeriodField = FinancePeriodField.DUE_DATE,
    date_from: date | None = None,
    date_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.PAYABLES_VIEW.value)),
) -> Response:
    rows, filters, summary = _payable_report_payload(
        db,
        description=description,
        supplier=supplier,
        status_filter=status_filter,
        category=category,
        period_field=period_field,
        date_from=date_from,
        date_to=date_to,
    )
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_contas_pagar.pdf",
            title="Relatorio de Contas a Pagar",
            headers=["Descricao", "Categoria", "Fornecedor", "Status", "Valor", "Vencimento", "Pagamento", "Dias atraso", "Observacoes"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )


@router.get("/delinquency.xlsx")
def export_delinquency_excel(
    as_of_date: date | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DELINQUENCY_VIEW.value)),
) -> Response:
    rows, filters, summary = _delinquency_report_payload(db, as_of_date=as_of_date or date.today(), due_from=due_from, due_to=due_to)
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_inadimplencia.xlsx",
            sheet_name="Inadimplencia",
            title="Relatorio de Inadimplencia",
            headers=["Aluno", "Turma", "Telefone", "Parcelas", "Mais antiga", "Maior atraso dias", "Valor em aberto"],
            rows=rows,
            filters=filters,
            summary=summary,
            currency_columns={7},
            date_columns={5},
            integer_columns={4, 6},
        )
    )


@router.get("/delinquency.pdf")
def export_delinquency_pdf(
    as_of_date: date | None = None,
    due_from: date | None = None,
    due_to: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.DELINQUENCY_VIEW.value)),
) -> Response:
    rows, filters, summary = _delinquency_report_payload(db, as_of_date=as_of_date or date.today(), due_from=due_from, due_to=due_to)
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_inadimplencia.pdf",
            title="Relatorio de Inadimplencia",
            headers=["Aluno", "Turma", "Telefone", "Parcelas", "Mais antiga", "Maior atraso dias", "Valor em aberto"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )


@router.get("/cash-flow.xlsx")
def export_cash_flow_excel(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.CASH_FLOW_VIEW.value)),
) -> Response:
    _validate_period(start_date, end_date)
    summary_data = get_cash_flow(db, start_date, end_date)
    rows = [[entry.date, entry.expected_revenue, entry.received_revenue, entry.paid_expenses, entry.balance] for entry in summary_data.entries]
    filters = _date_filters("Data inicial", "Data final", start_date, end_date)
    summary = [
        ExcelReportSection("Receita prevista", summary_data.expected_revenue),
        ExcelReportSection("Receita recebida", summary_data.received_revenue),
        ExcelReportSection("Despesas pagas", summary_data.paid_expenses),
        ExcelReportSection("Saldo", summary_data.balance),
    ]
    return _xlsx_response(
        ExcelReportConfig(
            filename="relatorio_fluxo_caixa.xlsx",
            sheet_name="Fluxo de Caixa",
            title="Relatorio de Fluxo de Caixa",
            headers=["Data", "Receita prevista", "Receita recebida", "Despesas pagas", "Saldo"],
            rows=rows,
            filters=filters,
            summary=summary,
            currency_columns={2, 3, 4, 5},
            date_columns={1},
        )
    )


@router.get("/cash-flow.pdf")
def export_cash_flow_pdf(
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    _: User = Depends(require_permissions(Permission.CASH_FLOW_VIEW.value)),
) -> Response:
    _validate_period(start_date, end_date)
    summary_data = get_cash_flow(db, start_date, end_date)
    rows = [[entry.date, entry.expected_revenue, entry.received_revenue, entry.paid_expenses, entry.balance] for entry in summary_data.entries]
    filters = _date_filters("Data inicial", "Data final", start_date, end_date)
    summary = [
        ExcelReportSection("Receita prevista", summary_data.expected_revenue),
        ExcelReportSection("Receita recebida", summary_data.received_revenue),
        ExcelReportSection("Despesas pagas", summary_data.paid_expenses),
        ExcelReportSection("Saldo", summary_data.balance),
    ]
    return _pdf_response(
        PdfReportConfig(
            filename="relatorio_fluxo_caixa.pdf",
            title="Relatorio de Fluxo de Caixa",
            headers=["Data", "Receita prevista", "Receita recebida", "Despesas pagas", "Saldo"],
            rows=rows,
            filters=filters,
            summary=summary,
        )
    )
