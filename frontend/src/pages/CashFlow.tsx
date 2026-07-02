import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Alert, Box, Button, Stack, TextField } from "@mui/material";
import { useEffect, useState } from "react";

import { api, downloadFile } from "../api/api";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { CashFlowSummary } from "../types";
import { formatCurrency, formatDate } from "../utils/format";

function currentMonthRange() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), 1);
  const end = new Date(now.getFullYear(), now.getMonth() + 1, 0);
  return {
    start_date: start.toISOString().slice(0, 10),
    end_date: end.toISOString().slice(0, 10),
  };
}

export function CashFlow() {
  const [filters, setFilters] = useState(currentMonthRange());
  const [summary, setSummary] = useState<CashFlowSummary | null>(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadCashFlow() {
    setError("");
    setLoading(true);
    try {
      const { data } = await api.get<CashFlowSummary>("/finance/cash-flow", { params: filters });
      setSummary(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar o fluxo de caixa.");
    } finally {
      setLoading(false);
    }
  }

  async function exportCashFlow() {
    try {
      await downloadFile("/finance/cash-flow/export.xlsx", "fluxo_caixa.xlsx", filters);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar o fluxo de caixa.");
    }
  }

  useEffect(() => {
    loadCashFlow();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Fluxo de caixa"
        subtitle="Entradas, saidas e saldo por periodo."
        actions={
          <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={exportCashFlow}>
            Exportar Excel
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "240px 240px auto" }}>
        <TextField
          label="Data inicial"
          type="date"
          value={filters.start_date}
          onChange={(event) => setFilters({ ...filters, start_date: event.target.value })}
          InputLabelProps={{ shrink: true }}
        />
        <TextField
          label="Data final"
          type="date"
          value={filters.end_date}
          onChange={(event) => setFilters({ ...filters, end_date: event.target.value })}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="outlined" onClick={() => loadCashFlow()}>
          Filtrar
        </Button>
      </Box>
      {summary ? (
        <>
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
            <StatCard title="Receita prevista" value={formatCurrency(summary.expected_revenue)} />
            <StatCard title="Receita recebida" value={formatCurrency(summary.received_revenue)} />
            <StatCard title="Despesas pagas" value={formatCurrency(summary.paid_expenses)} />
            <StatCard title="Saldo" value={formatCurrency(summary.balance)} />
          </Box>
          <DataTable
            rows={summary.entries}
            loading={loading}
            getRowId={(row) => row.date}
            columns={[
              { key: "date", label: "Data", render: (row) => formatDate(row.date) },
              { key: "expected_revenue", label: "Previsto", align: "right", render: (row) => formatCurrency(row.expected_revenue) },
              { key: "received_revenue", label: "Recebido", align: "right", render: (row) => formatCurrency(row.received_revenue) },
              { key: "paid_expenses", label: "Despesas", align: "right", render: (row) => formatCurrency(row.paid_expenses) },
              { key: "balance", label: "Saldo", align: "right", render: (row) => formatCurrency(row.balance) },
            ]}
          />
        </>
      ) : null}
    </Stack>
  );
}
