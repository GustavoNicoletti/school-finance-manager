import CheckCircleIcon from "@mui/icons-material/CheckCircle";
import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import PlaylistAddIcon from "@mui/icons-material/PlaylistAdd";
import SaveIcon from "@mui/icons-material/Save";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Stack,
  Switch,
  TextField,
} from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api, downloadFile } from "../api/api";
import { getCachedStudents } from "../api/lookups";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { StatusChip } from "../components/StatusChip";
import { PaymentStatus, Receivable, ReceivableBatchResult, ReceivableType, Student } from "../types";
import { addDaysIso, currentMonthRange, DateRange, nextMonthRange, previousMonthRange, todayIso } from "../utils/dateRanges";
import { formatCurrency, formatDate } from "../utils/format";
import { studentOptionLabel } from "../utils/lookups";

interface ReceivableFormState {
  student_id: number | null;
  description: string;
  amount: string;
  paid_amount: string;
  due_date: string;
  payment_date: string;
  status: PaymentStatus;
  type: ReceivableType;
  notes: string;
}

interface PaymentFormState {
  paid_amount: string;
  payment_date: string;
  notes: string;
}

interface BatchFormState {
  reference_month: string;
  due_date: string;
  amount: string;
  type: ReceivableType;
  description_prefix: string;
  class_name: string;
  only_active_students: boolean;
  notes: string;
}

interface ReceivableFilters {
  search: string;
  student_id: number | null;
  status: string;
  type: string;
  due_from: string;
  due_to: string;
}

const emptyForm: ReceivableFormState = {
  student_id: null,
  description: "",
  amount: "",
  paid_amount: "0.00",
  due_date: "",
  payment_date: "",
  status: "pendente",
  type: "mensalidade",
  notes: "",
};

const emptyPaymentForm: PaymentFormState = {
  paid_amount: "",
  payment_date: new Date().toISOString().slice(0, 10),
  notes: "",
};

function currentMonthInput() {
  return new Date().toISOString().slice(0, 7);
}

function defaultDueDateForMonth(monthInput: string) {
  return `${monthInput}-05`;
}

function createDefaultBatchForm(): BatchFormState {
  const month = currentMonthInput();
  return {
    reference_month: month,
    due_date: defaultDueDateForMonth(month),
    amount: "",
    type: "mensalidade",
    description_prefix: "Mensalidade",
    class_name: "",
    only_active_students: true,
    notes: "",
  };
}

const statusOptions: Array<{ value: PaymentStatus; label: string }> = [
  { value: "pendente", label: "Pendente" },
  { value: "pago", label: "Pago" },
  { value: "atrasado", label: "Atrasado" },
  { value: "cancelado", label: "Cancelado" },
];

const typeOptions: Array<{ value: ReceivableType; label: string }> = [
  { value: "mensalidade", label: "Mensalidade" },
  { value: "taxa_extra", label: "Taxa extra" },
  { value: "material", label: "Material" },
  { value: "outro", label: "Outro" },
];

function emptyToNull(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

function createDefaultFilters(): ReceivableFilters {
  const currentRange = currentMonthRange();
  return {
    search: "",
    student_id: null,
    status: "",
    type: "",
    due_from: currentRange.from,
    due_to: currentRange.to,
  };
}

export function Receivables() {
  const [receivables, setReceivables] = useState<Receivable[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [form, setForm] = useState<ReceivableFormState>(emptyForm);
  const [filters, setFilters] = useState<ReceivableFilters>(() => createDefaultFilters());
  const [editingId, setEditingId] = useState<number | null>(null);
  const [paymentTarget, setPaymentTarget] = useState<Receivable | null>(null);
  const [paymentForm, setPaymentForm] = useState<PaymentFormState>(emptyPaymentForm);
  const [batchDialogOpen, setBatchDialogOpen] = useState(false);
  const [batchForm, setBatchForm] = useState<BatchFormState>(() => createDefaultBatchForm());
  const [batchResult, setBatchResult] = useState<ReceivableBatchResult | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedStudent = useMemo(
    () => students.find((student) => student.id === form.student_id) ?? null,
    [form.student_id, students],
  );
  const selectedFilterStudent = useMemo(
    () => students.find((student) => student.id === filters.student_id) ?? null,
    [filters.student_id, students],
  );
  const classOptions = useMemo(
    () =>
      Array.from(new Set(students.map((student) => student.class_name?.trim()).filter((value): value is string => Boolean(value)))).sort((a, b) =>
        a.localeCompare(b),
      ),
    [students],
  );
  const studentNameMap = useMemo(() => new Map(students.map((student) => [student.id, studentOptionLabel(student)])), [students]);
  const formAmount = Number(form.amount || 0);
  const formPaidAmount = Number(form.paid_amount || 0);
  const formAmountIsValid = form.amount.length === 0 || formAmount > 0;
  const formPaidIsValid = form.paid_amount.length === 0 || (formPaidAmount >= 0 && formPaidAmount <= formAmount);
  const batchAmount = Number(batchForm.amount || 0);
  const batchAmountIsValid = batchForm.amount.length > 0 && batchAmount > 0;
  const batchDescriptionIsValid = batchForm.description_prefix.trim().length >= 2;
  const paymentOutstanding = paymentTarget ? Number(paymentTarget.amount) - Number(paymentTarget.paid_amount) : 0;
  const paymentAmount = Number(paymentForm.paid_amount || 0);
  const paymentAmountIsValid =
    !paymentTarget || paymentForm.paid_amount.length === 0 || (paymentAmount > 0 && paymentAmount <= paymentOutstanding);
  const summary = useMemo(() => {
    const today = todayIso();
    const weekAhead = addDaysIso(7);

    const openBalance = receivables.reduce((total, item) => {
      if (item.status === "cancelado" || item.status === "pago") {
        return total;
      }
      return total + (Number(item.amount) - Number(item.paid_amount));
    }, 0);

    const overdueBalance = receivables.reduce((total, item) => {
      const isOverdue = item.status === "atrasado" || (item.status !== "pago" && item.status !== "cancelado" && item.due_date < today);
      if (!isOverdue) {
        return total;
      }
      return total + (Number(item.amount) - Number(item.paid_amount));
    }, 0);

    const dueSoonCount = receivables.filter(
      (item) => item.status !== "pago" && item.status !== "cancelado" && item.due_date >= today && item.due_date <= weekAhead,
    ).length;

    const paidTotal = receivables.reduce((total, item) => total + Number(item.paid_amount), 0);

    return {
      openBalance,
      overdueBalance,
      dueSoonCount,
      paidTotal,
    };
  }, [receivables]);

  async function loadReceivables(activeFilters = filters) {
    const { data } = await api.get<Receivable[]>("/finance/receivables", {
      params: {
        search: activeFilters.search || undefined,
        student_id: activeFilters.student_id || undefined,
        status: activeFilters.status || undefined,
        type: activeFilters.type || undefined,
        due_from: activeFilters.due_from || undefined,
        due_to: activeFilters.due_to || undefined,
      },
    });
    setReceivables(data);
  }

  async function loadStudents() {
    const data = await getCachedStudents();
    setStudents(data);
  }

  async function refreshPage(activeFilters = filters) {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await Promise.all([loadReceivables(activeFilters), loadStudents()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar contas a receber.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshPage();
  }, []);

  async function applyFilters(nextFilters: ReceivableFilters) {
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

  function editReceivable(receivable: Receivable) {
    setEditingId(receivable.id);
    setForm({
      student_id: receivable.student_id,
      description: receivable.description,
      amount: String(receivable.amount),
      paid_amount: String(receivable.paid_amount),
      due_date: receivable.due_date,
      payment_date: receivable.payment_date ?? "",
      status: receivable.status,
      type: receivable.type,
      notes: receivable.notes ?? "",
    });
  }

  function openPaymentDialog(receivable: Receivable) {
    setPaymentTarget(receivable);
    setPaymentForm({
      paid_amount: String(Number(receivable.amount) - Number(receivable.paid_amount)),
      payment_date: new Date().toISOString().slice(0, 10),
      notes: "",
    });
  }

  function closePaymentDialog() {
    setPaymentTarget(null);
    setPaymentForm(emptyPaymentForm);
  }

  function openBatchDialog() {
    setBatchForm(createDefaultBatchForm());
    setBatchDialogOpen(true);
  }

  function closeBatchDialog() {
    setBatchDialogOpen(false);
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (!form.student_id) {
      setError("Selecione o aluno da conta a receber.");
      return;
    }

    const payload = {
      student_id: form.student_id,
      description: form.description.trim(),
      amount: Number(form.amount),
      paid_amount: Number(form.paid_amount || 0),
      due_date: form.due_date,
      payment_date: form.payment_date || null,
      status: form.status,
      type: form.type,
      notes: emptyToNull(form.notes),
    };

    try {
      if (editingId) {
        await api.put(`/finance/receivables/${editingId}`, payload);
      } else {
        await api.post("/finance/receivables", payload);
      }
      resetForm();
      await loadReceivables();
      setSuccess(editingId ? "Conta a receber atualizada." : "Conta a receber criada.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar a conta a receber.");
    }
  }

  async function handlePaymentSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!paymentTarget) {
      return;
    }

    try {
      await api.post(`/finance/receivables/${paymentTarget.id}/mark-paid`, {
        paid_amount: paymentForm.paid_amount ? Number(paymentForm.paid_amount) : undefined,
        payment_date: paymentForm.payment_date || undefined,
        notes: emptyToNull(paymentForm.notes),
      });
      closePaymentDialog();
      await loadReceivables();
      setSuccess("Recebimento registrado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel registrar o recebimento.");
    }
  }

  async function handleBatchSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    try {
      const { data } = await api.post<ReceivableBatchResult>("/finance/receivables/generate-batch", {
        reference_month: `${batchForm.reference_month}-01`,
        due_date: batchForm.due_date,
        amount: Number(batchForm.amount),
        type: batchForm.type,
        description_prefix: batchForm.description_prefix.trim(),
        class_name: emptyToNull(batchForm.class_name),
        only_active_students: batchForm.only_active_students,
        notes: emptyToNull(batchForm.notes),
      });
      setBatchResult(data);
      closeBatchDialog();
      await loadReceivables();
      setSuccess("Mensalidades geradas.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel gerar as mensalidades.");
    }
  }

  async function deleteReceivable(receivable: Receivable) {
    if (!window.confirm(`Excluir ${receivable.description}?`)) {
      return;
    }

    try {
      await api.delete(`/finance/receivables/${receivable.id}`);
      await loadReceivables();
      setSuccess("Conta a receber excluida.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir a conta a receber.");
    }
  }

  async function exportReceivables() {
    try {
      await downloadFile("/finance/receivables/export.xlsx", "contas_a_receber.xlsx", {
        search: filters.search || undefined,
        student_id: filters.student_id || undefined,
        status: filters.status || undefined,
        type: filters.type || undefined,
        due_from: filters.due_from || undefined,
        due_to: filters.due_to || undefined,
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel exportar contas a receber.");
    }
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Contas a receber"
        subtitle="Mensalidades, taxas e recebimentos por aluno."
        actions={
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={exportReceivables}>
              Exportar Excel
            </Button>
            <Button variant="contained" startIcon={<PlaylistAddIcon />} onClick={openBatchDialog}>
              Gerar em lote
            </Button>
          </Stack>
        }
      />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}
      {batchResult ? (
        <Alert severity={batchResult.created_count > 0 ? "success" : "info"} onClose={() => setBatchResult(null)}>
          {`${batchResult.description}: ${batchResult.created_count} contas criadas e ${batchResult.skipped_count} alunos ignorados por duplicidade.`}
        </Alert>
      ) : null}

      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
        <StatCard title="Em aberto" value={formatCurrency(summary.openBalance)} />
        <StatCard title="Em atraso" value={formatCurrency(summary.overdueBalance)} />
        <StatCard title="Vencem em 7 dias" value={summary.dueSoonCount} />
        <StatCard title="Total recebido" value={formatCurrency(summary.paidTotal)} />
      </Box>

      <Stack spacing={1.5}>
        <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(6, 1fr)" }}>
          <TextField label="Buscar" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
          <Autocomplete
            options={students}
            value={selectedFilterStudent}
            onChange={(_, value) => setFilters({ ...filters, student_id: value?.id ?? null })}
            getOptionLabel={studentOptionLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            renderInput={(params) => <TextField {...params} label="Aluno" />}
          />
          <TextField select label="Status" value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
            <MenuItem value="">Todos</MenuItem>
            {statusOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField select label="Tipo" value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })}>
            <MenuItem value="">Todos</MenuItem>
            {typeOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
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
        <Autocomplete
          options={students}
          value={selectedStudent}
          onChange={(_, value) => setForm({ ...form, student_id: value?.id ?? null })}
          getOptionLabel={studentOptionLabel}
          isOptionEqualToValue={(option, value) => option.id === value.id}
          renderInput={(params) => <TextField {...params} label="Aluno" required />}
        />
        <TextField
          label="Descricao"
          value={form.description}
          onChange={(event) => setForm({ ...form, description: event.target.value })}
          helperText="Ex.: Mensalidade 07/2026"
          required
        />
        <TextField
          label="Valor"
          type="number"
          value={form.amount}
          onChange={(event) => setForm({ ...form, amount: event.target.value })}
          error={!formAmountIsValid}
          helperText={!formAmountIsValid ? "Informe um valor maior que zero." : "Valor total da cobranca"}
          required
        />
        <TextField
          label="Valor pago"
          type="number"
          value={form.paid_amount}
          onChange={(event) => setForm({ ...form, paid_amount: event.target.value })}
          error={!formPaidIsValid}
          helperText={!formPaidIsValid ? "O valor pago nao pode ser maior que o valor da conta." : "Use zero quando ainda nao houver recebimento."}
        />
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
        <TextField select label="Tipo" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as ReceivableType })}>
          {typeOptions.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Observacoes"
          value={form.notes}
          onChange={(event) => setForm({ ...form, notes: event.target.value })}
          multiline
          minRows={2}
          sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}
        />
        <Stack direction="row" spacing={1} alignItems="center">
          <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={!form.student_id || !formAmountIsValid || !formPaidIsValid}>
            {editingId ? "Atualizar" : "Salvar"}
          </Button>
          {editingId ? <Button onClick={resetForm}>Cancelar</Button> : null}
        </Stack>
      </Box>

      <DataTable
        rows={receivables}
        loading={loading}
        initialPageSize={25}
        getRowId={(row) => row.id}
        emptyText="Nenhuma conta a receber encontrada para os filtros informados."
        columns={[
          { key: "description", label: "Descricao" },
          { key: "student_id", label: "Aluno", render: (row) => studentNameMap.get(row.student_id) ?? `Aluno #${row.student_id}` },
          { key: "type", label: "Tipo", render: (row) => <StatusChip value={row.type} /> },
          { key: "amount", label: "Valor", align: "right", render: (row) => formatCurrency(row.amount) },
          { key: "paid_amount", label: "Pago", align: "right", render: (row) => formatCurrency(row.paid_amount) },
          { key: "due_date", label: "Vencimento", render: (row) => formatDate(row.due_date) },
          { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
        ]}
        actions={(row) => (
          <>
            {row.status !== "pago" && row.status !== "cancelado" ? (
              <IconButton onClick={() => openPaymentDialog(row)} aria-label="Registrar recebimento">
                <CheckCircleIcon />
              </IconButton>
            ) : null}
            <IconButton onClick={() => editReceivable(row)} aria-label="Editar conta a receber">
              <EditIcon />
            </IconButton>
            <IconButton onClick={() => deleteReceivable(row)} aria-label="Excluir conta a receber">
              <DeleteIcon />
            </IconButton>
          </>
        )}
      />

      <Dialog open={Boolean(paymentTarget)} onClose={closePaymentDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handlePaymentSubmit}>
          <DialogTitle>Registrar recebimento</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
            <TextField
              label="Conta"
              value={paymentTarget ? `${paymentTarget.description} - ${studentNameMap.get(paymentTarget.student_id) ?? `Aluno #${paymentTarget.student_id}`}` : ""}
              InputProps={{ readOnly: true }}
            />
            <TextField
              label="Valor recebido"
              type="number"
              value={paymentForm.paid_amount}
              onChange={(event) => setPaymentForm({ ...paymentForm, paid_amount: event.target.value })}
              error={!paymentAmountIsValid}
              helperText={
                !paymentAmountIsValid
                  ? `Informe um valor entre zero e ${formatCurrency(paymentOutstanding)}.`
                  : `Saldo restante antes da baixa: ${formatCurrency(paymentOutstanding)}`
              }
            />
            <TextField
              label="Data do recebimento"
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
            <Button type="submit" variant="contained" disabled={!paymentAmountIsValid || paymentForm.paid_amount.length === 0}>
              Confirmar
            </Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog open={batchDialogOpen} onClose={closeBatchDialog} fullWidth maxWidth="sm">
        <Box component="form" onSubmit={handleBatchSubmit}>
          <DialogTitle>Gerar mensalidades em lote</DialogTitle>
          <DialogContent sx={{ display: "grid", gap: 2, pt: 2 }}>
            <TextField
              label="Mes de referencia"
              type="month"
              value={batchForm.reference_month}
              onChange={(event) =>
                setBatchForm((current) => ({
                  ...current,
                  reference_month: event.target.value,
                  due_date: defaultDueDateForMonth(event.target.value),
                }))
              }
              InputLabelProps={{ shrink: true }}
              required
            />
            <TextField
              label="Vencimento"
              type="date"
              value={batchForm.due_date}
              onChange={(event) => setBatchForm({ ...batchForm, due_date: event.target.value })}
              InputLabelProps={{ shrink: true }}
              required
            />
            <TextField
              label="Valor por aluno"
              type="number"
              value={batchForm.amount}
              onChange={(event) => setBatchForm({ ...batchForm, amount: event.target.value })}
              error={batchForm.amount.length > 0 && !batchAmountIsValid}
              helperText={!batchAmountIsValid && batchForm.amount.length > 0 ? "Informe um valor maior que zero." : "Mesmo valor para todos os alunos selecionados."}
              required
            />
            <TextField select label="Tipo" value={batchForm.type} onChange={(event) => setBatchForm({ ...batchForm, type: event.target.value as ReceivableType })}>
              {typeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Prefixo da descricao"
              value={batchForm.description_prefix}
              onChange={(event) => setBatchForm({ ...batchForm, description_prefix: event.target.value })}
              error={!batchDescriptionIsValid}
              helperText={!batchDescriptionIsValid ? "Use pelo menos 2 caracteres." : `Ex.: ${batchForm.description_prefix || "Mensalidade"} ${batchForm.reference_month.slice(5, 7)}/${batchForm.reference_month.slice(0, 4)}`}
              required
            />
            <TextField
              select
              label="Turma"
              value={batchForm.class_name}
              onChange={(event) => setBatchForm({ ...batchForm, class_name: event.target.value })}
            >
              <MenuItem value="">Todas as turmas</MenuItem>
              {classOptions.map((className) => (
                <MenuItem key={className} value={className}>
                  {className}
                </MenuItem>
              ))}
            </TextField>
            <FormControlLabel
              control={
                <Switch
                  checked={batchForm.only_active_students}
                  onChange={(event) => setBatchForm({ ...batchForm, only_active_students: event.target.checked })}
                />
              }
              label="Somente alunos ativos"
            />
            <TextField
              label="Observacoes"
              value={batchForm.notes}
              onChange={(event) => setBatchForm({ ...batchForm, notes: event.target.value })}
              multiline
              minRows={3}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={closeBatchDialog}>Cancelar</Button>
            <Button type="submit" variant="contained" disabled={!batchAmountIsValid || !batchDescriptionIsValid}>
              Gerar contas
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}
