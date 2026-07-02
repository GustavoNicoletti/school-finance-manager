import AssessmentIcon from "@mui/icons-material/Assessment";
import FileDownloadIcon from "@mui/icons-material/FileDownload";
import PictureAsPdfIcon from "@mui/icons-material/PictureAsPdf";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { ReactNode, useEffect, useMemo, useState } from "react";

import { downloadFile } from "../api/api";
import { getCachedStudents } from "../api/lookups";
import { useAuth } from "../auth/AuthContext";
import { canAccess } from "../auth/permissions";
import { PageHeader } from "../components/PageHeader";
import { PermissionKey, PaymentStatus, ReceivableType, Student, StudentStatus } from "../types";
import { studentOptionLabel } from "../utils/lookups";

const reportPermissions: PermissionKey[] = [
  "students_view",
  "guardians_view",
  "receivables_view",
  "payables_view",
  "delinquency_view",
  "cash_flow_view",
];

const periodFieldOptions = [
  { value: "due_date", label: "Vencimento" },
  { value: "payment_date", label: "Pagamento" },
  { value: "created_at", label: "Cadastro" },
];

const paymentStatusOptions: Array<{ value: PaymentStatus; label: string }> = [
  { value: "pendente", label: "Pendente" },
  { value: "pago", label: "Pago" },
  { value: "atrasado", label: "Atrasado" },
  { value: "cancelado", label: "Cancelado" },
];

const receivableTypeOptions: Array<{ value: ReceivableType; label: string }> = [
  { value: "mensalidade", label: "Mensalidade" },
  { value: "taxa_extra", label: "Taxa extra" },
  { value: "material", label: "Material" },
  { value: "outro", label: "Outro" },
];

const studentStatusOptions: Array<{ value: StudentStatus; label: string }> = [
  { value: "ativo", label: "Ativo" },
  { value: "inativo", label: "Inativo" },
  { value: "transferido", label: "Transferido" },
];

function todayIso() {
  return new Date().toISOString().slice(0, 10);
}

function monthStartIso() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10);
}

function monthEndIso() {
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth() + 1, 0).toISOString().slice(0, 10);
}

function previousMonthRange() {
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  const end = new Date(now.getFullYear(), now.getMonth(), 0);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

function currentMonthRange() {
  return { from: monthStartIso(), to: monthEndIso() };
}

function nextThirtyDaysRange() {
  const start = new Date();
  const end = new Date();
  end.setDate(end.getDate() + 30);
  return {
    from: start.toISOString().slice(0, 10),
    to: end.toISOString().slice(0, 10),
  };
}

function cleanParams(params?: Record<string, unknown>) {
  if (!params) {
    return undefined;
  }
  return Object.fromEntries(
    Object.entries(params).filter(([, value]) => value !== "" && value !== null && value !== undefined),
  );
}

interface PeriodButtonsProps {
  onChange: (range: { from: string; to: string }) => void;
  onClear: () => void;
  clearLabel?: string;
}

function PeriodButtons({ onChange, onClear, clearLabel = "Sem periodo" }: PeriodButtonsProps) {
  return (
    <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
      <Button variant="text" onClick={() => onChange(currentMonthRange())}>
        Este mes
      </Button>
      <Button variant="text" onClick={() => onChange(previousMonthRange())}>
        Mes anterior
      </Button>
      <Button variant="text" onClick={() => onChange(nextThirtyDaysRange())}>
        Proximos 30 dias
      </Button>
      <Button variant="text" color="inherit" onClick={onClear}>
        {clearLabel}
      </Button>
    </Stack>
  );
}

interface ReportSectionProps {
  title: string;
  subtitle: string;
  onExcel: () => Promise<void>;
  onPdf: () => Promise<void>;
  children: ReactNode;
}

function ReportSection({ title, subtitle, onExcel, onPdf, children }: ReportSectionProps) {
  return (
    <Paper variant="outlined" sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={2}
          justifyContent="space-between"
          alignItems={{ xs: "flex-start", md: "center" }}
        >
          <Box>
            <Typography variant="h6">{title}</Typography>
            <Typography variant="body2" color="text.secondary">
              {subtitle}
            </Typography>
          </Box>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
            <Button variant="outlined" startIcon={<FileDownloadIcon />} onClick={() => void onExcel()}>
              Excel
            </Button>
            <Button variant="outlined" color="secondary" startIcon={<PictureAsPdfIcon />} onClick={() => void onPdf()}>
              PDF
            </Button>
          </Stack>
        </Stack>
        {children}
      </Stack>
    </Paper>
  );
}

export function Reports() {
  const { user } = useAuth();
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [students, setStudents] = useState<Student[]>([]);

  const [studentFilters, setStudentFilters] = useState({ status: "", class_name: "", created_from: "", created_to: "" });
  const [guardianFilters, setGuardianFilters] = useState({ kinship: "", created_from: "", created_to: "" });
  const [receivableFilters, setReceivableFilters] = useState({
    student_id: null as number | null,
    description: "",
    status: "",
    type: "",
    period_field: "due_date",
    date_from: monthStartIso(),
    date_to: todayIso(),
  });
  const [payableFilters, setPayableFilters] = useState({
    description: "",
    supplier: "",
    status: "",
    category: "",
    period_field: "due_date",
    date_from: monthStartIso(),
    date_to: todayIso(),
  });
  const [delinquencyFilters, setDelinquencyFilters] = useState({ as_of_date: todayIso(), due_from: "", due_to: "" });
  const [cashFlowFilters, setCashFlowFilters] = useState({ start_date: monthStartIso(), end_date: todayIso() });

  const visibleSections = useMemo(
    () => ({
      students: canAccess(user, { permissions: ["students_view"] }),
      guardians: canAccess(user, { permissions: ["guardians_view"] }),
      receivables: canAccess(user, { permissions: ["receivables_view"] }),
      payables: canAccess(user, { permissions: ["payables_view"] }),
      delinquency: canAccess(user, { permissions: ["delinquency_view"] }),
      cashFlow: canAccess(user, { permissions: ["cash_flow_view"] }),
    }),
    [user],
  );

  useEffect(() => {
    if (!visibleSections.receivables) {
      return;
    }

    void getCachedStudents()
      .then(setStudents)
      .catch(() => {
        setStudents([]);
      });
  }, [visibleSections.receivables]);

  const selectedReceivableStudent = useMemo(
    () => students.find((student) => student.id === receivableFilters.student_id) ?? null,
    [receivableFilters.student_id, students],
  );

  async function runExport(path: string, filename: string, params?: Record<string, unknown>) {
    setError("");
    setSuccess("");
    try {
      await downloadFile(path, filename, cleanParams(params));
      setSuccess("Relatorio gerado com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel gerar o relatorio.");
    }
  }

  return (
    <Stack spacing={3}>
      <PageHeader
        title="Relatorios"
        subtitle="Monte exportacoes em Excel ou PDF com os filtros que fizerem sentido para a escola."
        actions={
          <Stack direction="row" spacing={1} alignItems="center">
            <AssessmentIcon color="primary" />
            <Typography variant="body2" color="text.secondary">
              Exportacoes orientadas por modulo
            </Typography>
          </Stack>
        }
      />

      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}

      {visibleSections.students ? (
        <ReportSection
          title="Alunos"
          subtitle="Lista de alunos com turma, status e responsaveis vinculados."
          onExcel={() => runExport("/reports/students.xlsx", "relatorio_alunos.xlsx", studentFilters)}
          onPdf={() => runExport("/reports/students.pdf", "relatorio_alunos.pdf", studentFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
            <TextField
              select
              label="Status"
              value={studentFilters.status}
              onChange={(event) => setStudentFilters({ ...studentFilters, status: event.target.value })}
            >
              <MenuItem value="">Todos</MenuItem>
              {studentStatusOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Turma" value={studentFilters.class_name} onChange={(event) => setStudentFilters({ ...studentFilters, class_name: event.target.value })} />
            <TextField
              label="Cadastro inicial"
              type="date"
              value={studentFilters.created_from}
              onChange={(event) => setStudentFilters({ ...studentFilters, created_from: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Cadastro final"
              type="date"
              value={studentFilters.created_to}
              onChange={(event) => setStudentFilters({ ...studentFilters, created_to: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setStudentFilters({ ...studentFilters, created_from: range.from, created_to: range.to })}
            onClear={() => setStudentFilters({ ...studentFilters, created_from: "", created_to: "" })}
          />
        </ReportSection>
      ) : null}

      {visibleSections.guardians ? (
        <ReportSection
          title="Responsaveis"
          subtitle="Cadastros de responsaveis com contato e alunos associados."
          onExcel={() => runExport("/reports/guardians.xlsx", "relatorio_responsaveis.xlsx", guardianFilters)}
          onPdf={() => runExport("/reports/guardians.pdf", "relatorio_responsaveis.pdf", guardianFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(3, 1fr)" }}>
            <TextField label="Parentesco" value={guardianFilters.kinship} onChange={(event) => setGuardianFilters({ ...guardianFilters, kinship: event.target.value })} />
            <TextField
              label="Cadastro inicial"
              type="date"
              value={guardianFilters.created_from}
              onChange={(event) => setGuardianFilters({ ...guardianFilters, created_from: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Cadastro final"
              type="date"
              value={guardianFilters.created_to}
              onChange={(event) => setGuardianFilters({ ...guardianFilters, created_to: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setGuardianFilters({ ...guardianFilters, created_from: range.from, created_to: range.to })}
            onClear={() => setGuardianFilters({ ...guardianFilters, created_from: "", created_to: "" })}
          />
        </ReportSection>
      ) : null}

      {visibleSections.receivables ? (
        <ReportSection
          title="Contas a receber"
          subtitle="Mensalidades, taxas e demais cobrancas com filtros financeiros."
          onExcel={() => runExport("/reports/receivables.xlsx", "relatorio_contas_receber.xlsx", receivableFilters)}
          onPdf={() => runExport("/reports/receivables.pdf", "relatorio_contas_receber.pdf", receivableFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(6, 1fr)" }}>
            <Autocomplete
              options={students}
              value={selectedReceivableStudent}
              getOptionLabel={studentOptionLabel}
              isOptionEqualToValue={(option, value) => option.id === value.id}
              onChange={(_event, student) => setReceivableFilters({ ...receivableFilters, student_id: student?.id ?? null })}
              renderInput={(params) => <TextField {...params} label="Aluno" placeholder="Todos os alunos" />}
            />
            <TextField
              label="Descricao"
              value={receivableFilters.description}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, description: event.target.value })}
            />
            <TextField
              select
              label="Status"
              value={receivableFilters.status}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, status: event.target.value })}
            >
              <MenuItem value="">Todos</MenuItem>
              {paymentStatusOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Tipo"
              value={receivableFilters.type}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, type: event.target.value })}
            >
              <MenuItem value="">Todos</MenuItem>
              {receivableTypeOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Periodo por"
              value={receivableFilters.period_field}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, period_field: event.target.value })}
            >
              {periodFieldOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Data inicial"
              type="date"
              value={receivableFilters.date_from}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, date_from: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Data final"
              type="date"
              value={receivableFilters.date_to}
              onChange={(event) => setReceivableFilters({ ...receivableFilters, date_to: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setReceivableFilters({ ...receivableFilters, date_from: range.from, date_to: range.to })}
            onClear={() => setReceivableFilters({ ...receivableFilters, date_from: "", date_to: "" })}
          />
        </ReportSection>
      ) : null}

      {visibleSections.payables ? (
        <ReportSection
          title="Contas a pagar"
          subtitle="Despesas, fornecedores e compromissos do periodo."
          onExcel={() => runExport("/reports/payables.xlsx", "relatorio_contas_pagar.xlsx", payableFilters)}
          onPdf={() => runExport("/reports/payables.pdf", "relatorio_contas_pagar.pdf", payableFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(6, 1fr)" }}>
            <TextField
              label="Descricao"
              value={payableFilters.description}
              onChange={(event) => setPayableFilters({ ...payableFilters, description: event.target.value })}
            />
            <TextField
              label="Fornecedor"
              value={payableFilters.supplier}
              onChange={(event) => setPayableFilters({ ...payableFilters, supplier: event.target.value })}
            />
            <TextField
              select
              label="Status"
              value={payableFilters.status}
              onChange={(event) => setPayableFilters({ ...payableFilters, status: event.target.value })}
            >
              <MenuItem value="">Todos</MenuItem>
              {paymentStatusOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField label="Categoria" value={payableFilters.category} onChange={(event) => setPayableFilters({ ...payableFilters, category: event.target.value })} />
            <TextField
              select
              label="Periodo por"
              value={payableFilters.period_field}
              onChange={(event) => setPayableFilters({ ...payableFilters, period_field: event.target.value })}
            >
              {periodFieldOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              label="Data inicial"
              type="date"
              value={payableFilters.date_from}
              onChange={(event) => setPayableFilters({ ...payableFilters, date_from: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Data final"
              type="date"
              value={payableFilters.date_to}
              onChange={(event) => setPayableFilters({ ...payableFilters, date_to: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setPayableFilters({ ...payableFilters, date_from: range.from, date_to: range.to })}
            onClear={() => setPayableFilters({ ...payableFilters, date_from: "", date_to: "" })}
          />
        </ReportSection>
      ) : null}

      {visibleSections.delinquency ? (
        <ReportSection
          title="Inadimplencia"
          subtitle="Panorama dos alunos com parcelas vencidas em aberto."
          onExcel={() => runExport("/reports/delinquency.xlsx", "relatorio_inadimplencia.xlsx", delinquencyFilters)}
          onPdf={() => runExport("/reports/delinquency.pdf", "relatorio_inadimplencia.pdf", delinquencyFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(3, 260px)" }}>
            <TextField
              label="Data de referencia"
              type="date"
              value={delinquencyFilters.as_of_date}
              onChange={(event) => setDelinquencyFilters({ ...delinquencyFilters, as_of_date: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Vencimento inicial"
              type="date"
              value={delinquencyFilters.due_from}
              onChange={(event) => setDelinquencyFilters({ ...delinquencyFilters, due_from: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Vencimento final"
              type="date"
              value={delinquencyFilters.due_to}
              onChange={(event) => setDelinquencyFilters({ ...delinquencyFilters, due_to: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setDelinquencyFilters({ ...delinquencyFilters, due_from: range.from, due_to: range.to })}
            onClear={() => setDelinquencyFilters({ ...delinquencyFilters, due_from: "", due_to: "" })}
          />
        </ReportSection>
      ) : null}

      {visibleSections.cashFlow ? (
        <ReportSection
          title="Fluxo de caixa"
          subtitle="Comparativo diario de entradas previstas, recebidas e despesas pagas."
          onExcel={() => runExport("/reports/cash-flow.xlsx", "relatorio_fluxo_caixa.xlsx", cashFlowFilters)}
          onPdf={() => runExport("/reports/cash-flow.pdf", "relatorio_fluxo_caixa.pdf", cashFlowFilters)}
        >
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(2, 280px)" }}>
            <TextField
              label="Data inicial"
              type="date"
              value={cashFlowFilters.start_date}
              onChange={(event) => setCashFlowFilters({ ...cashFlowFilters, start_date: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
            <TextField
              label="Data final"
              type="date"
              value={cashFlowFilters.end_date}
              onChange={(event) => setCashFlowFilters({ ...cashFlowFilters, end_date: event.target.value })}
              InputLabelProps={{ shrink: true }}
            />
          </Box>
          <PeriodButtons
            onChange={(range) => setCashFlowFilters({ start_date: range.from, end_date: range.to })}
            onClear={() => setCashFlowFilters({ start_date: monthStartIso(), end_date: todayIso() })}
            clearLabel="Periodo padrao"
          />
        </ReportSection>
      ) : null}

      {!canAccess(user, { permissions: reportPermissions, mode: "any" }) ? (
        <Alert severity="warning">Seu perfil nao possui acesso aos relatorios disponiveis no momento.</Alert>
      ) : null}
    </Stack>
  );
}
