import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import SaveIcon from "@mui/icons-material/Save";
import { Autocomplete, Alert, Box, Button, IconButton, Stack, TextField } from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api/api";
import { getCachedStudents, invalidateLookup } from "../api/lookups";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { Guardian, Student } from "../types";
import { formatCpf, formatPhone, isValidCpf, isValidEmail, isValidPhone, onlyDigits } from "../utils/input";
import { joinRelatedNames, studentOptionLabel } from "../utils/lookups";

interface GuardianFormState {
  full_name: string;
  cpf: string;
  phone: string;
  email: string;
  address: string;
  kinship: string;
  student_ids: number[];
}

const emptyForm: GuardianFormState = {
  full_name: "",
  cpf: "",
  phone: "",
  email: "",
  address: "",
  kinship: "",
  student_ids: [],
};

function emptyToNull(value: string) {
  const trimmedValue = value.trim();
  return trimmedValue.length > 0 ? trimmedValue : null;
}

export function Guardians() {
  const { user } = useAuth();
  const canWrite = hasPermission(user, "guardians_manage");

  const [guardians, setGuardians] = useState<Guardian[]>([]);
  const [students, setStudents] = useState<Student[]>([]);
  const [form, setForm] = useState<GuardianFormState>(emptyForm);
  const [search, setSearch] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedStudents = useMemo(
    () => students.filter((student) => form.student_ids.includes(student.id)),
    [form.student_ids, students],
  );
  const cpfHasValue = onlyDigits(form.cpf).length > 0;
  const cpfIsValid = !cpfHasValue || isValidCpf(form.cpf);
  const phoneHasValue = onlyDigits(form.phone).length > 0;
  const phoneIsValid = !phoneHasValue || isValidPhone(form.phone);
  const emailHasValue = form.email.trim().length > 0;
  const emailIsValid = !emailHasValue || isValidEmail(form.email);

  async function loadGuardians(activeSearch = search) {
    const { data } = await api.get<Guardian[]>("/guardians", { params: { search: activeSearch || undefined, limit: 500 } });
    setGuardians(data);
  }

  async function loadStudents() {
    const data = await getCachedStudents();
    setStudents(data);
  }

  async function refreshPage(activeSearch = search) {
    setError("");
    setSuccess("");
    setLoading(true);
    try {
      await Promise.all([loadGuardians(activeSearch), loadStudents()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar responsaveis.");
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

  function editGuardian(guardian: Guardian) {
    setEditingId(guardian.id);
    setForm({
      full_name: guardian.full_name,
      cpf: guardian.cpf ?? "",
      phone: guardian.phone ?? "",
      email: guardian.email ?? "",
      address: guardian.address ?? "",
      kinship: guardian.kinship ?? "",
      student_ids: guardian.student_ids,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const payload = {
      full_name: form.full_name.trim(),
      cpf: emptyToNull(form.cpf),
      phone: emptyToNull(form.phone),
      email: emptyToNull(form.email),
      address: emptyToNull(form.address),
      kinship: emptyToNull(form.kinship),
      student_ids: form.student_ids,
    };

    try {
      if (editingId) {
        await api.put(`/guardians/${editingId}`, payload);
      } else {
        await api.post("/guardians", payload);
      }
      invalidateLookup("guardians");
      resetForm();
      await loadGuardians();
      setSuccess(editingId ? "Responsavel atualizado com sucesso." : "Responsavel cadastrado com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar o responsavel.");
    }
  }

  async function deleteGuardian(guardian: Guardian) {
    if (!window.confirm(`Excluir ${guardian.full_name}?`)) {
      return;
    }

    try {
      await api.delete(`/guardians/${guardian.id}`);
      invalidateLookup("guardians");
      await loadGuardians();
      setSuccess("Responsavel excluido com sucesso.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir o responsavel.");
    }
  }

  return (
    <Stack spacing={3}>
      <PageHeader title="Responsaveis" subtitle="Contatos familiares e vinculos com alunos." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}
      {!canWrite ? <Alert severity="info">Seu perfil possui acesso somente para consulta nesta tela.</Alert> : null}

      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "1fr auto auto" }}>
        <TextField label="Buscar responsavel ou aluno" value={search} onChange={(event) => setSearch(event.target.value)} />
        <Button variant="outlined" onClick={() => refreshPage()}>
          Filtrar
        </Button>
        <Button
          variant="text"
          onClick={async () => {
            setSearch("");
            await refreshPage("");
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
            label="CPF"
            value={form.cpf}
            onChange={(event) => setForm({ ...form, cpf: formatCpf(event.target.value) })}
            error={!cpfIsValid}
            helperText={!cpfIsValid ? "CPF invalido." : "Opcional"}
          />
          <TextField
            label="Telefone"
            value={form.phone}
            onChange={(event) => setForm({ ...form, phone: formatPhone(event.target.value) })}
            error={!phoneIsValid}
            helperText={!phoneIsValid ? "Use telefone com DDD." : "Opcional"}
          />
          <TextField
            label="E-mail"
            type="email"
            value={form.email}
            onChange={(event) => setForm({ ...form, email: event.target.value })}
            error={!emailIsValid}
            helperText={!emailIsValid ? "Informe um e-mail valido." : "Opcional"}
          />
          <TextField label="Endereco" value={form.address} onChange={(event) => setForm({ ...form, address: event.target.value })} />
          <TextField label="Parentesco" value={form.kinship} onChange={(event) => setForm({ ...form, kinship: event.target.value })} />
          <Autocomplete
            multiple
            options={students}
            value={selectedStudents}
            onChange={(_, value) => setForm({ ...form, student_ids: value.map((student) => student.id) })}
            getOptionLabel={studentOptionLabel}
            isOptionEqualToValue={(option, value) => option.id === value.id}
            renderInput={(params) => <TextField {...params} label="Alunos vinculados" helperText="Selecione um ou mais alunos" />}
            sx={{ gridColumn: { xs: "1 / -1", md: "span 2" } }}
          />
          <Stack direction="row" spacing={1} alignItems="center">
            <Button type="submit" variant="contained" startIcon={<SaveIcon />} disabled={!cpfIsValid || !phoneIsValid || !emailIsValid}>
              {editingId ? "Atualizar" : "Salvar"}
            </Button>
            {editingId ? <Button onClick={resetForm}>Cancelar</Button> : null}
          </Stack>
        </Box>
      ) : null}

      <DataTable
        rows={guardians}
        loading={loading}
        initialPageSize={25}
        getRowId={(row) => row.id}
        emptyText="Nenhum responsavel encontrado para os filtros informados."
        columns={[
          { key: "full_name", label: "Nome" },
          { key: "cpf", label: "CPF" },
          { key: "phone", label: "Telefone" },
          { key: "email", label: "E-mail" },
          { key: "student_ids", label: "Alunos", render: (row) => joinRelatedNames(row.student_ids, students, studentOptionLabel) },
        ]}
        actions={
          canWrite
            ? (row) => (
                <>
                  <IconButton onClick={() => editGuardian(row)} aria-label="Editar responsavel">
                    <EditIcon />
                  </IconButton>
                  <IconButton onClick={() => deleteGuardian(row)} aria-label="Excluir responsavel">
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
