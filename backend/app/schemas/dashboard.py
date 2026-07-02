from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class DashboardSummary(BaseModel):
    reference_month: str = Field(serialization_alias="mes_referencia")
    period_start: date = Field(serialization_alias="periodo_inicio")
    period_end: date = Field(serialization_alias="periodo_fim")
    reference_date: date = Field(serialization_alias="data_referencia")
    comparison_month: str = Field(serialization_alias="mes_comparacao")
    total_active_students: int = Field(serialization_alias="total_alunos_ativos")
    expected_revenue_month: Decimal = Field(serialization_alias="receita_prevista_mes")
    received_revenue_month: Decimal = Field(serialization_alias="receita_recebida_mes")
    expenses_month: Decimal = Field(serialization_alias="despesas_mes")
    pending_expenses_month: Decimal = Field(serialization_alias="despesas_pendentes_mes")
    monthly_balance: Decimal = Field(serialization_alias="saldo_mes")
    overdue_students_count: int = Field(serialization_alias="quantidade_inadimplentes")
    total_overdue_amount: Decimal = Field(serialization_alias="valor_total_inadimplente")
    average_cost_per_student: Decimal = Field(serialization_alias="custo_medio_por_aluno")
    cash_cost_per_student: Decimal = Field(serialization_alias="custo_caixa_por_aluno")
    expected_revenue_delta: Decimal = Field(serialization_alias="variacao_receita_prevista")
    received_revenue_delta: Decimal = Field(serialization_alias="variacao_receita_recebida")
    expenses_delta: Decimal = Field(serialization_alias="variacao_despesas")
    pending_expenses_delta: Decimal = Field(serialization_alias="variacao_despesas_pendentes")
    monthly_balance_delta: Decimal = Field(serialization_alias="variacao_saldo")
    overdue_students_delta: int = Field(serialization_alias="variacao_quantidade_inadimplentes")
    total_overdue_amount_delta: Decimal = Field(serialization_alias="variacao_valor_inadimplente")
    average_cost_per_student_delta: Decimal = Field(serialization_alias="variacao_custo_medio_por_aluno")
    cash_cost_per_student_delta: Decimal = Field(serialization_alias="variacao_custo_caixa_por_aluno")

    model_config = ConfigDict(populate_by_name=True)
