import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos";
import GroupsIcon from "@mui/icons-material/Groups";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import TrendingDownIcon from "@mui/icons-material/TrendingDown";
import TrendingUpIcon from "@mui/icons-material/TrendingUp";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { Alert, Box, Button, CircularProgress, Stack, TextField, Typography } from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import { Link as RouterLink } from "react-router-dom";

import { api } from "../api/api";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { StatusChip } from "../components/StatusChip";
import { SystemStatus } from "../components/SystemStatus";
import { DashboardSummary, DelinquencyItem, Payable, PaymentStatus, Receivable } from "../types";
import { formatCurrency, formatDate, formatMonthYear, formatSignedCurrency, formatSignedNumber } from "../utils/format";

interface DueAgendaItem {
  id: string;
  description: string;
  due_date: string;
  amount: string;
  status: PaymentStatus;
}

function currentMonthInput() {
  const today = new Date();
  return `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
}

function monthParts(monthInput: string) {
  const [yearString, monthString] = monthInput.split("-");
  return {
    year: Number(yearString),
    month: Number(monthString),
  };
}

function monthRange(monthInput: string) {
  const { year, month } = monthParts(monthInput);
  const lastDay = new Date(year, month, 0).getDate();
  const monthLabel = String(month).padStart(2, "0");

  return {
    start: `${year}-${monthLabel}-01`,
    end: `${year}-${monthLabel}-${String(lastDay).padStart(2, "0")}`,
  };
}

function shiftMonth(monthInput: string, delta: number) {
  const { year, month } = monthParts(monthInput);
  const date = new Date(year, month - 1 + delta, 1);
  return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;
}

function metricTrend(delta: string | number, comparisonMonth: string, positiveIsGood: boolean) {
  const numericDelta = Number(delta ?? 0);
  const comparisonLabel = formatMonthYear(comparisonMonth);

  if (numericDelta === 0) {
    return {
      text: `Sem variacao vs ${comparisonLabel}`,
      color: "text.secondary",
    };
  }

  const improved = positiveIsGood ? numericDelta > 0 : numericDelta < 0;
  return {
    text: `${formatSignedCurrency(numericDelta)} vs ${comparisonLabel}`,
    color: improved ? "success.main" : "error.main",
  };
}

function countTrend(delta: number, comparisonMonth: string, positiveIsGood: boolean) {
  const numericDelta = Number(delta ?? 0);
  const comparisonLabel = formatMonthYear(comparisonMonth);

  if (numericDelta === 0) {
    return {
      text: `Sem variacao vs ${comparisonLabel}`,
      color: "text.secondary",
    };
  }

  const improved = positiveIsGood ? numericDelta > 0 : numericDelta < 0;
  return {
    text: `${formatSignedNumber(numericDelta)} vs ${comparisonLabel}`,
    color: improved ? "success.main" : "error.main",
  };
}

export function Dashboard() {
  const [referenceMonth, setReferenceMonth] = useState(currentMonthInput());
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [delinquency, setDelinquency] = useState<DelinquencyItem[]>([]);
  const [upcomingReceivables, setUpcomingReceivables] = useState<DueAgendaItem[]>([]);
  const [upcomingPayables, setUpcomingPayables] = useState<DueAgendaItem[]>([]);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(true);

  const riskAlert = useMemo(() => {
    if (!summary) {
      return null;
    }

    if (Number(summary.saldo_mes) < 0 && Number(summary.variacao_saldo) < 0) {
      return {
        severity: "warning" as const,
        message: `Saldo do mes negativo em ${formatCurrency(summary.saldo_mes)} e pior em ${formatSignedCurrency(summary.variacao_saldo)} frente a ${formatMonthYear(summary.mes_comparacao)}.`,
      };
    }

    if (summary.quantidade_inadimplentes > 0 && Number(summary.variacao_quantidade_inadimplentes) > 0) {
      return {
        severity: "info" as const,
        message: `A inadimplencia subiu para ${summary.quantidade_inadimplentes} alunos, com variacao de ${formatSignedNumber(summary.variacao_quantidade_inadimplentes)} frente a ${formatMonthYear(summary.mes_comparacao)}.`,
      };
    }

    return {
      severity: "success" as const,
      message: "Nenhum risco financeiro critico identificado para hoje.",
    };
  }, [summary]);

  useEffect(() => {
    async function loadDashboard() {
      const range = monthRange(referenceMonth);
      setLoading(true);
      setError("");

      try {
        const summaryResponse = await api.get<DashboardSummary>("/dashboard", {
          params: {
            reference_date: range.end,
          },
        });
        const [delinquencyResponse, receivablesResponse, payablesResponse] = await Promise.all([
          api.get<DelinquencyItem[]>("/finance/delinquency", {
            params: {
              as_of_date: summaryResponse.data.data_referencia,
              limit: 5,
            },
          }),
          api.get<Receivable[]>("/finance/receivables", {
            params: {
              due_from: range.start,
              due_to: range.end,
              limit: 12,
            },
          }),
          api.get<Payable[]>("/finance/payables", {
            params: {
              due_from: range.start,
              due_to: range.end,
              limit: 12,
            },
          }),
        ]);

        setSummary(summaryResponse.data);
        setDelinquency(delinquencyResponse.data);
        setUpcomingReceivables(
          receivablesResponse.data
            .filter((item) => item.status !== "pago" && item.status !== "cancelado")
            .slice(0, 6)
            .map((item) => ({
              id: `receivable-${item.id}`,
              description: item.description,
              due_date: item.due_date,
              amount: item.amount,
              status: item.status,
            })),
        );
        setUpcomingPayables(
          payablesResponse.data
            .filter((item) => item.status !== "pago" && item.status !== "cancelado")
            .slice(0, 6)
            .map((item) => ({
              id: `payable-${item.id}`,
              description: item.description,
              due_date: item.due_date,
              amount: item.amount,
              status: item.status,
            })),
        );
      } catch (err) {
        setError(err instanceof Error ? err.message : "Nao foi possivel carregar o dashboard.");
      } finally {
        setLoading(false);
      }
    }

    loadDashboard();
  }, [referenceMonth]);

  if (loading) {
    return (
      <Stack alignItems="center" py={8}>
        <CircularProgress />
      </Stack>
    );
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Dashboard financeiro"
        subtitle={
          summary
            ? `Visao executiva de ${formatMonthYear(summary.mes_referencia)} entre ${formatDate(summary.periodo_inicio)} e ${formatDate(summary.periodo_fim)}, com inadimplencia medida ate ${formatDate(summary.data_referencia)}.`
            : "Visao executiva do caixa, inadimplencia e vencimentos do periodo."
        }
        actions={
          <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems={{ xs: "stretch", md: "center" }}>
            <Stack direction="row" spacing={1} alignItems="center">
              <Button size="small" variant="outlined" onClick={() => setReferenceMonth((current) => shiftMonth(current, -1))} aria-label="Mes anterior">
                <ArrowBackIosNewIcon fontSize="small" />
              </Button>
              <TextField
                size="small"
                type="month"
                label="Mes"
                value={referenceMonth}
                onChange={(event) => setReferenceMonth(event.target.value)}
                InputLabelProps={{ shrink: true }}
                sx={{ minWidth: 170 }}
              />
              <Button size="small" variant="outlined" onClick={() => setReferenceMonth((current) => shiftMonth(current, 1))} aria-label="Mes seguinte">
                <ArrowForwardIosIcon fontSize="small" />
              </Button>
            </Stack>
            <SystemStatus />
          </Stack>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {riskAlert ? <Alert severity={riskAlert.severity}>{riskAlert.message}</Alert> : null}

      {summary ? (
        <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", sm: "repeat(2, 1fr)", xl: "repeat(4, 1fr)" }}>
          <StatCard title="Alunos ativos" value={summary.total_alunos_ativos} icon={<GroupsIcon color="primary" />} />
          <StatCard
            title="Receita prevista"
            value={formatCurrency(summary.receita_prevista_mes)}
            trend={metricTrend(summary.variacao_receita_prevista, summary.mes_comparacao, true).text}
            trendColor={metricTrend(summary.variacao_receita_prevista, summary.mes_comparacao, true).color}
            icon={<TrendingUpIcon color="success" />}
          />
          <StatCard
            title="Receita recebida"
            value={formatCurrency(summary.receita_recebida_mes)}
            helper={`Saldo atual ${formatCurrency(summary.saldo_mes)}`}
            trend={metricTrend(summary.variacao_receita_recebida, summary.mes_comparacao, true).text}
            trendColor={metricTrend(summary.variacao_receita_recebida, summary.mes_comparacao, true).color}
            icon={<AccountBalanceWalletIcon color="primary" />}
          />
          <StatCard
            title="Despesas pagas"
            value={formatCurrency(summary.despesas_mes)}
            trend={metricTrend(summary.variacao_despesas, summary.mes_comparacao, false).text}
            trendColor={metricTrend(summary.variacao_despesas, summary.mes_comparacao, false).color}
            icon={<TrendingDownIcon color="error" />}
          />
          <StatCard
            title="Despesas pendentes"
            value={formatCurrency(summary.despesas_pendentes_mes)}
            trend={metricTrend(summary.variacao_despesas_pendentes, summary.mes_comparacao, false).text}
            trendColor={metricTrend(summary.variacao_despesas_pendentes, summary.mes_comparacao, false).color}
          />
          <StatCard
            title="Saldo do mes"
            value={formatCurrency(summary.saldo_mes)}
            trend={metricTrend(summary.variacao_saldo, summary.mes_comparacao, true).text}
            trendColor={metricTrend(summary.variacao_saldo, summary.mes_comparacao, true).color}
          />
          <StatCard
            title="Inadimplentes"
            value={summary.quantidade_inadimplentes}
            helper={formatCurrency(summary.valor_total_inadimplente)}
            trend={countTrend(summary.variacao_quantidade_inadimplentes, summary.mes_comparacao, false).text}
            trendColor={countTrend(summary.variacao_quantidade_inadimplentes, summary.mes_comparacao, false).color}
            icon={<WarningAmberIcon color="warning" />}
          />
          <StatCard
            title="Custo real por aluno"
            value={formatCurrency(summary.custo_medio_por_aluno)}
            helper="Despesas do mes por vencimento, pagas e pendentes, por aluno ativo."
            trend={metricTrend(summary.variacao_custo_medio_por_aluno, summary.mes_comparacao, false).text}
            trendColor={metricTrend(summary.variacao_custo_medio_por_aluno, summary.mes_comparacao, false).color}
          />
          <StatCard
            title="Custo caixa por aluno"
            value={formatCurrency(summary.custo_caixa_por_aluno)}
            helper="Despesas efetivamente pagas no mes por aluno ativo."
            trend={metricTrend(summary.variacao_custo_caixa_por_aluno, summary.mes_comparacao, false).text}
            trendColor={metricTrend(summary.variacao_custo_caixa_por_aluno, summary.mes_comparacao, false).color}
          />
          <StatCard title="Receber em aberto" value={upcomingReceivables.length} icon={<ReceiptLongIcon color="secondary" />} />
        </Box>
      ) : null}

      <Box display="grid" gap={3} gridTemplateColumns={{ xs: "1fr", xl: "1.2fr 1fr" }}>
        <Stack spacing={1.5}>
          <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
              <Box>
                <Typography variant="h6" fontWeight={700}>
                  Inadimplencia critica
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Alunos que pedem contato prioritario do financeiro ao fim do periodo.
                </Typography>
              </Box>
            <Button component={RouterLink} to="/delinquency" endIcon={<ArrowForwardIcon />}>
              Ver lista completa
            </Button>
          </Stack>
          <DataTable
            rows={delinquency}
            getRowId={(row) => row.student_id}
            emptyText="Nenhum aluno em atraso no momento."
            columns={[
              { key: "student_name", label: "Aluno" },
              { key: "class_name", label: "Turma" },
              { key: "overdue_count", label: "Parcelas", align: "right" },
              { key: "oldest_due_date", label: "Mais antiga", render: (row) => formatDate(row.oldest_due_date) },
              { key: "overdue_amount", label: "Valor", align: "right", render: (row) => formatCurrency(row.overdue_amount) },
            ]}
          />
        </Stack>

        <Stack spacing={3}>
          <Stack spacing={1.5}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
              <Box>
                <Typography variant="h6" fontWeight={700}>
                  Recebimentos do periodo
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Contas com vencimento dentro do mes selecionado.
                </Typography>
              </Box>
              <Button component={RouterLink} to="/receivables" endIcon={<ArrowForwardIcon />}>
                Abrir contas
              </Button>
            </Stack>
            <DataTable
              rows={upcomingReceivables}
              getRowId={(row) => row.id}
              emptyText="Nenhum recebimento pendente no periodo."
              columns={[
                { key: "description", label: "Descricao" },
                { key: "due_date", label: "Vencimento", render: (row) => formatDate(row.due_date) },
                { key: "amount", label: "Valor", align: "right", render: (row) => formatCurrency(row.amount) },
                { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
              ]}
            />
          </Stack>

          <Stack spacing={1.5}>
            <Stack direction="row" justifyContent="space-between" alignItems="center" spacing={2}>
              <Box>
                <Typography variant="h6" fontWeight={700}>
                  Pagamentos do periodo
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  Despesas com vencimento dentro do mes selecionado.
                </Typography>
              </Box>
              <Button component={RouterLink} to="/payables" endIcon={<ArrowForwardIcon />}>
                Abrir despesas
              </Button>
            </Stack>
            <DataTable
              rows={upcomingPayables}
              getRowId={(row) => row.id}
              emptyText="Nenhum pagamento pendente no periodo."
              columns={[
                { key: "description", label: "Descricao" },
                { key: "due_date", label: "Vencimento", render: (row) => formatDate(row.due_date) },
                { key: "amount", label: "Valor", align: "right", render: (row) => formatCurrency(row.amount) },
                { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
              ]}
            />
          </Stack>
        </Stack>
      </Box>
    </Stack>
  );
}
