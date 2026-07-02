import { Alert, Autocomplete, Box, Button, MenuItem, Stack, TextField } from "@mui/material";
import { useEffect, useMemo, useState } from "react";

import { api } from "../api/api";
import { getCachedUsers } from "../api/lookups";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { AuditLog, User } from "../types";
import { formatDateTime } from "../utils/format";

const actions = [
  { value: "", label: "Todas" },
  { value: "create", label: "Criacao" },
  { value: "update", label: "Atualizacao" },
  { value: "delete", label: "Exclusao" },
  { value: "mark_paid", label: "Baixa financeira" },
];

const emptyFilters = {
  entity: "",
  entity_id: "",
  user_id: null as number | null,
  action: "",
};

export function Audit() {
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [users, setUsers] = useState<User[]>([]);
  const [filters, setFilters] = useState(emptyFilters);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const selectedUser = useMemo(
    () => users.find((user) => user.id === filters.user_id) ?? null,
    [filters.user_id, users],
  );
  const userNameMap = useMemo(() => new Map(users.map((user) => [user.id, user.full_name])), [users]);

  async function loadLogs() {
    const { data } = await api.get<AuditLog[]>("/audit", {
      params: {
        entity: filters.entity || undefined,
        entity_id: filters.entity_id || undefined,
        user_id: filters.user_id || undefined,
        action: filters.action || undefined,
      },
    });
    setLogs(data);
  }

  async function loadUsers() {
    const data = await getCachedUsers();
    setUsers(data);
  }

  async function refreshPage() {
    setError("");
    setLoading(true);
    try {
      await Promise.all([loadLogs(), loadUsers()]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar a auditoria.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshPage();
  }, []);

  return (
    <Stack spacing={3}>
      <PageHeader title="Auditoria" subtitle="Historico das alteracoes registradas no sistema." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(5, 1fr)" }}>
        <TextField label="Entidade" value={filters.entity} onChange={(event) => setFilters({ ...filters, entity: event.target.value })} />
        <TextField
          label="ID do registro"
          type="number"
          value={filters.entity_id}
          onChange={(event) => setFilters({ ...filters, entity_id: event.target.value })}
        />
        <Autocomplete
          options={users}
          value={selectedUser}
          onChange={(_, value) => setFilters({ ...filters, user_id: value?.id ?? null })}
          getOptionLabel={(option) => option.full_name}
          isOptionEqualToValue={(option, value) => option.id === value.id}
          renderInput={(params) => <TextField {...params} label="Usuario" />}
        />
        <TextField select label="Acao" value={filters.action} onChange={(event) => setFilters({ ...filters, action: event.target.value })}>
          {actions.map((item) => (
            <MenuItem key={item.value} value={item.value}>
              {item.label}
            </MenuItem>
          ))}
        </TextField>
        <Button variant="outlined" onClick={() => refreshPage()}>
          Filtrar
        </Button>
      </Box>
      <DataTable
        rows={logs}
        loading={loading}
        getRowId={(row) => row.id}
        columns={[
          { key: "created_at", label: "Data", render: (row) => formatDateTime(row.created_at) },
          { key: "user_id", label: "Usuario", render: (row) => (row.user_id ? userNameMap.get(row.user_id) ?? `Usuario #${row.user_id}` : "-") },
          { key: "action", label: "Acao" },
          { key: "entity", label: "Entidade" },
          { key: "entity_id", label: "Registro", render: (row) => row.entity_id ?? "-" },
        ]}
      />
    </Stack>
  );
}
