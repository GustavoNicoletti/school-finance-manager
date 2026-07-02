import FileDownloadIcon from "@mui/icons-material/FileDownload";
import { Alert, Box, Button, Stack, TextField } from "@mui/material";
import { useEffect, useState } from "react";

import { api, downloadFile } from "../api/api";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { DelinquencyItem } from "../types";
import { formatCurrency, formatDate } from "../utils/format";

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

export function Delinquency() {
  const [items, setItems] = useState<DelinquencyItem[]>([]);
  const [asOfDate, setAsOfDate] = useState(todayIso());
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function loadReport() {
    setError("");
    setLoading(true);
    try {
      const { data } = await api.get<DelinquencyItem[]>("/finance/delinquency", {
        params: { as_of_date: asOfDate || undefined },
      });
      setItems(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar inadimplencia.");
    } finally {
      setLoading(false);
    }
  }

  async function exportReport() {
    try {
      await downloadFile("/finance/delinquency/export.xlsx", "inadimplencia.xlsx", { as_of_date: asOfDate || undefined });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar inadimplencia.");
    }
  }

  useEffect(() => {
    loadReport();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Inadimplencia"
        subtitle="Alunos com contas vencidas em aberto."
        actions={
          <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={exportReport}>
            Exportar Excel
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "240px auto" }}>
        <TextField
          label="Data de referencia"
          type="date"
          value={asOfDate}
          onChange={(event) => setAsOfDate(event.target.value)}
          InputLabelProps={{ shrink: true }}
        />
        <Button variant="outlined" onClick={() => loadReport()}>
          Filtrar
        </Button>
      </Box>
      <DataTable
        rows={items}
        loading={loading}
        getRowId={(row) => row.student_id}
        columns={[
          { key: "student_name", label: "Aluno" },
          { key: "class_name", label: "Turma" },
          { key: "phone", label: "Telefone" },
          { key: "overdue_count", label: "Parcelas", align: "right" },
          { key: "oldest_due_date", label: "Mais antiga", render: (row) => formatDate(row.oldest_due_date) },
          { key: "overdue_amount", label: "Valor em aberto", align: "right", render: (row) => formatCurrency(row.overdue_amount) },
        ]}
      />
    </Stack>
  );
}
