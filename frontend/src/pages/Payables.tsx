import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import SaveIcon from "@mui/icons-material/Save";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  IconButton,
  MenuItem,
  Stack,
  TextField,
} from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, downloadFile } from "../api/api";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { StatusChip } from "../components/StatusChip";
import { Payable, PaymentStatus } from "../types";
import { addDaysIso, currentMonthRange, DateRange, nextMonthRange, previousMonthRange, todayIso } from "../utils/dateRanges";
import { formatCurrency, formatDate } from "../utils/format";

interface PayableFormState {
  description: string;
  category: string;
  amount: string;
  due_date: string;
  payment_date: string;
  status: PaymentStatus;
  supplier: string;
  notes: string;
}

interface PaymentFormState {
  payment_date: string;
  notes: string;
}

interface PayableFilters {
  search: string;
  status: string;
  category: string;
  due_from: string;
  due_to: string;
}

const emptyForm: PayableFormState = {
  description: "",
  category: "",
  amount: "",
  due_date: "",
  payment_date: "",
  status: "pendente",
  supplier: "",
  notes: "",
};

const emptyPaymentForm: PaymentFormState = {
  payment_date: new Date().toISOString().slice(0, 10),
  notes: "",
};

const statusOptions: Array<{ value: PaymentStatus; label: string }> = [
  { value: "pendente", label: "Pendente" },
  { value: "pago", label: "Pago" },
  { value: "atrasado", label: "Atrasado" },
  { value: "cancelado", label: "Cancelado" },
];

function emptyToNull(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

function createDefaultFilters(): PayableFilters {
  const currentRange = currentMonthRange();
  return {
    search: "",
    status: "",
    category: "",
    due_from: currentRange.from,
    due_to: currentRange.to,
  };
}

export function Payables() {
  const [payables, setPayables] = useState<Payable[]>([]);
  const [form, setForm] = useState<PayableFormState>(emptyForm);
  const [filters, setFilters] = useState<PayableFilters>(() => createDefaultFilters());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [paymentTarget, setPaymentTarget] = useState<Payable | null>(null);
  const [paymentForm, setPaymentForm] = useState<PaymentFormState>(emptyPaymentForm);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);
  const formAmount = Number(form.amount || 0);
  const formAmountIsValid = form.amount.length === 0 || formAmount > 0;
  const summary = useMemo(() => {
    const today = todayIso();
    const weekAhead = addDaysIso(7);

    const openBalance = payables.reduce((total, item) => {
      if (item.status === "cancelado" || item.status === "pago") {
        return total;
      }
      return total + Number(item.amount);
    }, 0);

    const overdueBalance = payables.reduce((total, item) => {
      const isOverdue = item.status === "atrasado" || (item.status !== "pago" && item.status !== "cancelado" && item.due_date < today);
      if (!isOverdue) {
        return total;
      }
      return total + Number(item.amount);
    }, 0);

    const dueSoonCount = payables.filter(
      (item) => item.status !== "pago" && item.status !== "cancelado" && item.due_date >= today && item.due_date <= weekAhead,
    ).length;

    const paidTotal = payables.reduce((total, item) => (item.status === "pago" ? total + Number(item.amount) : total), 0);

    return {
      openBalance,
      overdueBalance,
      dueSoonCount,
      paidTotal,
    };
  }, [payables]);

  async function loadPayables(activeFilters = filters) {
    const { data } = await api.get<Payable[]>("/finance/payables", {
      params: {
        search: activeFilters.search || undefined,
        status: activeFilters.status || undefined,
        category: activeFilters.category || undefined,
        due_from: activeFilters.due_from || undefined,
        due_to: activeFilters.due_to || undefined,
      },
    });
    setPayables(data);
  }

  async function refreshPage(activeFilters = filters) {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await loadPayables(activeFilters);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar contas a pagar.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshPage();
  }, []);

  async function applyFilters(nextFilters: PayableFilters) {
    setFilters(nextFilters);
    await refreshPage(nextFilters);
  }

  async function applyPeriod(range: DateRange) {
    await applyFilters({ ...filters, due_from: range.from, due_to: range.to });
  }

  async function showAllPeriods() {
    await applyFilters({ ...filters, due_from: "", due_to: "" });
  }

  async function clearFilters() {
    await applyFilters(createDefaultFilters());
  }

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function editPayable(payable: Payable) {
    setEditingId(payable.id);
    setForm({
      description: payable.description,
      category: payable.category ?? "",
      amount: String(payable.amount),
      due_date: payable.due_date,
      payment_date: payable.payment_date ?? "",
      status: payable.status,
      supplier: payable.supplier ?? "",
      notes: payable.notes ?? "",
    });
  }

  function openPaymentDialog(payable: Payable) {
    setPaymentTarget(payable);
    setPaymentForm({
      payment_date: new Date().toISOString().slice(0, 10),
      notes: "",
    });
  }

  function closePaymentDialog() {
    setPaymentTarget(null);
    setPaymentForm(emptyPaymentForm);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const payload = {
      description: form.description.trim(),
      category: emptyToNull(form.category),
      amount: Number(form.amount),
      due_date: form.due_date,
      payment_date: form.payment_date || null,
      status: form.status,
      supplier: emptyToNull(form.supplier),
      notes: emptyToNull(form.notes),
    };

    try {
      if (editingId) {
        await api.put(`/finance/payables/${editingId}`, payload);
      } else {
        await api.post("/finance/payables", payload);
      }
      resetForm();
      await loadPayables();
      setSuccess(editingId ? "Conta a pagar atualizada." : "Conta a pagar criada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar a conta a pagar.");
    }
  }

  async function handlePaymentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!paymentTarget) {
      return;
    }

    try {
      await api.post(`/finance/payables/${paymentTarget.id}/mark-paid`, {
        payment_date: paymentForm.payment_date || undefined,
        notes: emptyToNull(paymentForm.notes),
      });
      closePaymentDialog();
      await loadPayables();
      setSuccess("Pagamento registrado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel registrar o pagamento.");
    }
  }

  async function deletePayable(payable: Payable) {
    if (!window.confirm(`Excluir ${payable.description}?`)) {
      return;
    }

    try {
      await api.delete(`/finance/payables/${payable.id}`);
      await loadPayables();
      setSuccess("Conta a pagar excluida.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir a conta a pagar.");
    }
  }

  async function exportPayables() {
    try {
      await downloadFile("/finance/payables/export.xlsx", "contas_a_pagar.xlsx", {
        search: filters.search || undefined,
        status: filters.status || undefined,
        category: filters.category || undefined,
        due_from: filters.due_from || undefined,
        due_to: filters.due_to || undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar contas a pagar.");
    }
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Contas a pagar"
        subtitle="Despesas, fornecedores e baixas financeiras."
        actions={
          <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={exportPayables}>
            Exportar Excel
          </Button>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}

      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
        <StatCard title="A pagar" value={formatCurrency(summary.openBalance)} />
        <StatCard title="Em atraso" value={formatCurrency(summary.overdueBalance)} />
        <StatCard title="Vencem em 7 dias" value={summary.dueSoonCount} />
        <StatCard title="Total pago" value={formatCurrency(summary.paidTotal)} />
      </Box>

      <Stack spacing={1.5}>
        <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(5, 1fr)" }}>
          <TextField label="Buscar" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
          <TextField select label="Status" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <MenuItem value="">Todos</MenuItem>
            {statusOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Categoria" value={filters.category} onChange={(event) => setFilters({ ...filters, category: event.target.value })} />
          <TextField
            label="Vencimento inicial"
            type="date"
            value={filters.due_from}
            onChange={(event) => setFilters({ ...filters, due_from: event.target.value })}
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            label="Vencimento final"
            type="date"
            value={filters.due_to}
            onChange={(event) => setFilters({ ...filters, due_to: event.target.value })}
            InputLabelProps={{ shrink: true }}
          />
        </Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1} flexWrap="wrap">
          <Button variant="outlined" onClick={() => void refreshPage()}>
            Filtrar
          </Button>
          <Button variant="text" onClick={() => void applyPeriod(currentMonthRange())}>
            Este mes
          </Button>
          <Button variant="text" onClick={() => void applyPeriod(previousMonthRange())}>
            Mes anterior
          </Button>
          <Button variant="text" onClick={() => void applyPeriod(nextMonthRange())}>
            Proximo mes
          </Button>
          <Button variant="text" color="inherit" onClick={() => void showAllPeriods()}>
            Ver tudo
          </Button>
          <Button variant="text" color="inherit" onClick={() => void clearFilters()}>
            Limpar
          </Button>
        </Stack>
      </Stack>

      <Box component="form" onSubmit={handleSubmit} display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
        <TextField
          label="Descricao"
          value={form.description}
          onChange={(event) => setForm({ ...form, description: event.target.value })}
          helperText="Ex.: Aluguel, folha, fornecedor"
          required
        />
        <TextField label="Categoria" value={form.category} onChange={(event) => setForm({ ...form, category: event.target.value })} />
        <TextField
          label="Valor"
          type="number"
          value={form.amount}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
          error={!formAmountIsValid}
          helperText={!formAmountIsValid ? "Informe um valor maior que zero." : "Valor total da despesa"}
          required
        />
        <TextField label="Fornecedor" value={form.supplier} onChange={(event) => setForm({ ...form, supplier: event.target.value })} />
        <TextField
          label="Vencimento"
          type="date"
          value={form.due_date}
          onChange={(event) => setForm({ ...form, due_date: event.target.value })}
          InputLabelProps={{ shrink: true }}
          required
        />
        <TextField
          label="Pagamento"
          type="date"
          value={form.payment_date}
          onChange={(event) => setForm({ ...form, payment_date: event.target.value })}
          InputLabelProps={{ shrink: true }}
        />
        <TextField select label="Status" value={form.status} onChange={(event) => setForm({ ...form, status: event.target.value as PaymentStatus })}>
          {statusOptions.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField label="Observacoes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} multiline minRows={2} />
        <Stack direction="row" spacing={1} alignItems="center">
          <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={!formAmountIsValid}>
            {editingId ? "Atualizar" : "Salvar"}
          </Button>
          {editingId ? <Button onClick={resetForm}>Cancelar</Button> : null}
        </Stack>
      </Box>

      <DataTable
        rows={payables}
        loading={loading}
        initialPageSize={25}
        getRowId={(row) => row.id}
        emptyText="Nenhuma conta a pagar encontrada para os filtros informados."
        columns={[
          { key: "description", label: "Descricao" },
          { key: "category", label: "Categoria" },
          { key: "supplier", label: "Fornecedor" },
          { key: "amount", label: "Valor", align: "right", render: (row) => formatCurrency(row.amount) },
          { key: "due_date", label: "Vencimento", render: (row) => formatDate(row.due_date) },
          { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
        ]}
        actions={(row) => (
          <>
            {row.status !== "pago" && row.status !== "cancelado" ? (
              <IconButton onClick={() => openPaymentDialog(row)} aria-label="Registrar pagamento">
                <CheckCircleIcon />
              </IconButton>
            ) : null}
            <IconButton onClick={() => editPayable(row)} aria-label="Editar conta a pagar">
              <EditIcon />
            </IconButton>
            <IconButton onClick={() => deletePayable(row)} aria-label="Excluir conta a pagar">
              <DeleteIcon />
            </IconButton>
          </>
        )}
      />

      <Dialog open={Boolean(paymentTarget)} onClose={closePaymentDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handlePaymentSubmit}>
          <DialogTitle>Registrar pagamento</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
            <TextField label="Conta" value={paymentTarget?.description ?? ""} InputProps={{ readOnly: true }} />
            <TextField
              label="Data do pagamento"
              type="date"
              value={paymentForm.payment_date}
              onChange={(event) => setPaymentForm({ ...paymentForm, payment_date: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Observacoes"
              value={paymentForm.notes}
              onChange={(event) => setPaymentForm({ ...paymentForm, notes: event.target.value })}
              multiline
              minRows={3}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closePaymentDialog}>Cancelar</Button>
            <Button type="submit" variant="contained">
              Confirmar
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
