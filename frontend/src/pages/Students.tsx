import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import { Autocomplete, Alert, Box, Button, IconButton, MenuItem, Stack, TextField } from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api/api";
import { getCachedGuardians, invalidateLookup } from "../api/lookups";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatusChip } from "../components/StatusChip";
import { Guardian, Student, StudentStatus } from "../types";
import { formatDate } from "../utils/format";
import { guardianOptionLabel, joinRelatedNames } from "../utils/lookups";

interface StudentFormState {
  full_name: string;
  birth_date: string;
  class_name: string;
  status: StudentStatus;
  phone: string;
  address: string;
  notes: string;
  medical_information: string;
  guardian_ids: number[];
}

const emptyForm: StudentFormState = {
  full_name: "",
  birth_date: "",
  class_name: "",
  status: "ativo",
  phone: "",
  address: "",
  notes: "",
  medical_information: "",
  guardian_ids: [],
};

const statusOptions: Array<{ value: StudentStatus; label: string }> = [
  { value: "ativo", label: "Ativo" },
  { value: "inativo", label: "Inativo" },
  { value: "transferido", label: "Transferido" },
];

function emptyToNull(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

export function Students() {
  const { user } = useAuth();
  const canWrite = hasPermission(user, "students_manage");

  const [students, setStudents] = useState<Student[]>([]);
  const [guardians, setGuardians] = useState<Guardian[]>([]);
  const [form, setForm] = useState<StudentFormState>(emptyForm);
  const [filters, setFilters] = useState({ search: "", status: "", class_name: "" });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedGuardians = useMemo(
    () => guardians.filter((guardian) => form.guardian_ids.includes(guardian.id)),
    [form.guardian_ids, guardians],
  );

  async function loadStudents(activeFilters = filters) {
    const { data } = await api.get<Student[]>("/students", {
      params: {
        search: activeFilters.search || undefined,
        status: activeFilters.status || undefined,
        class_name: activeFilters.class_name || undefined,
      },
    });
    setStudents(data);
  }

  async function loadGuardians() {
    const data = await getCachedGuardians();
    setGuardians(data);
  }

  async function refreshPage(activeFilters = filters) {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await Promise.all([loadStudents(activeFilters), loadGuardians()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar alunos.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshPage();
  }, []);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function editStudent(student: Student) {
    setEditingId(student.id);
    setForm({
      full_name: student.full_name,
      birth_date: student.birth_date ?? "",
      class_name: student.class_name ?? "",
      status: student.status,
      phone: student.phone ?? "",
      address: student.address ?? "",
      notes: student.notes ?? "",
      medical_information: student.medical_information ?? "",
      guardian_ids: student.guardian_ids,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const payload = {
      full_name: form.full_name.trim(),
      birth_date: form.birth_date || null,
      class_name: emptyToNull(form.class_name),
      status: form.status,
      phone: emptyToNull(form.phone),
      address: emptyToNull(form.address),
      notes: emptyToNull(form.notes),
      medical_information: emptyToNull(form.medical_information),
      guardian_ids: form.guardian_ids,
    };

    try {
      if (editingId) {
        await api.put(`/students/${editingId}`, payload);
      } else {
        await api.post("/students", payload);
      }
      invalidateLookup("students");
      resetForm();
      await loadStudents();
      setSuccess(editingId ? "Aluno atualizado com sucesso." : "Aluno cadastrado com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar o aluno.");
    }
  }

  async function deleteStudent(student: Student) {
    if (!window.confirm(`Excluir ${student.full_name}?`)) {
      return;
    }

    try {
      await api.delete(`/students/${student.id}`);
      invalidateLookup("students");
      await loadStudents();
      setSuccess("Aluno excluido com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir o aluno.");
    }
  }

  return (
    <Stack spacing={3}>
      <PageHeader title="Alunos" subtitle="Cadastro, turma e vinculos com responsaveis." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}
      {!canWrite ? <Alert severity="info">Seu perfil possui acesso somente para consulta nesta tela.</Alert> : null}

      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "2fr 1fr 1fr auto auto" }}>
        <TextField
          label="Buscar aluno ou responsavel"
          value={filters.search}
          onChange={(event) => setFilters({ ...filters, search: event.target.value })}
        />
        <TextField
          select
          label="Status"
          value={filters.status}
          onChange={(event) => setFilters({ ...filters, status: event.target.value })}
        >
          <MenuItem value="">Todos</MenuItem>
          {statusOptions.map((option) => (
            <MenuItem key={option.value} value={option.value}>
              {option.label}
            </MenuItem>
          ))}
        </TextField>
        <TextField
          label="Turma"
          value={filters.class_name}
          onChange={(event) => setFilters({ ...filters, class_name: event.target.value })}
        />
        <Button variant="outlined" onClick={() => refreshPage()}>
          Filtrar
        </Button>
        <Button
          variant="text"
          onClick={async () => {
            const clearedFilters = { search: "", status: "", class_name: "" };
            setFilters(clearedFilters);
            await refreshPage(clearedFilters);
          }}
        >
          Limpar
        </Button>
      </Box>

      {canWrite ? (
        <Box component="form" onSubmit={handleSubmit} display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
          <TextField
            label="Nome completo"
            value={form.full_name}
            onChange={(event) => setForm({ ...form, full_name: event.target.value })}
            required
          />
          <TextField
            label="Data de nascimento"
            type="date"
            value={form.birth_date}
            onChange={(event) => setForm({ ...form, birth_date: event.target.value })}
            InputLabelProps={{ shrink: true }}
          />
          <TextField label="Turma" value={form.class_name} onChange={(event) => setForm({ ...form, class_name: event.target.value })} />
          <TextField
            select
            label="Status"
            value={form.status}
            onChange={(event) => setForm({ ...form, status: event.target.value as StudentStatus })}
          >
            {statusOptions.map((option) => (
              <MenuItem key={option.value} value={option.value}>
                {option.label}
              </MenuItem>
            ))}
          </TextField>
          <TextField label="Telefone" value={form.phone} onChange={(event) => setForm({ ...form, phone: event.target.value })} />
          <TextField label="Endereco" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
          <Autocomplete
            multiple
            options={guardians}
            value={selectedGuardians}
            onChange={(_, value) => setForm({ ...form, guardian_ids: value.map((guardian) => guardian.id) })}
            getOptionLabel={guardianOptionLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            renderInput={(params) => <TextField {...params} label="Responsaveis" helperText="Selecione um ou mais responsaveis" />}
            sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}
          />
          <TextField label="Observacoes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
          <TextField
            label="Informacoes medicas"
            value={form.medical_information}
            onChange={(event) => setForm({ ...form, medical_information: event.target.value })}
            sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <Button type="submit" variant="contained" startIcon={<SaveIcon />}>
              {editingId ? "Atualizar" : "Salvar"}
            </Button>
            {editingId ? <Button onClick={resetForm}>Cancelar</Button> : null}
          </Stack>
        </Box>
      ) : null}

      <DataTable
        rows={students}
        loading={loading}
        initialPageSize={25}
        getRowId={(row) => row.id}
        emptyText="Nenhum aluno encontrado para os filtros informados."
        columns={[
          { key: "full_name", label: "Nome" },
          { key: "class_name", label: "Turma" },
          { key: "guardian_ids", label: "Responsaveis", render: (row) => joinRelatedNames(row.guardian_ids, guardians, guardianOptionLabel) },
          { key: "status", label: "Status", render: (row) => <StatusChip value={row.status} /> },
          { key: "birth_date", label: "Nascimento", render: (row) => formatDate(row.birth_date) },
        ]}
        actions={
          canWrite
            ? (row) => (
                <>
                  <IconButton onClick={() => editStudent(row)} aria-label="Editar aluno">
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => deleteStudent(row)} aria-label="Excluir aluno">
                    <DeleteIcon />
                  </IconButton>
                </>
              )
            : undefined
        }
      />
    </Stack>
  );
}
