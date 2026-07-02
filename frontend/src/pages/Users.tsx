import DeleteIcon from "@mui/icons-material/Delete";
import EditIcon from "@mui/icons-material/Edit";
import PersonOffIcon from "@mui/icons-material/PersonOff";
import SaveIcon from "@mui/icons-material/Save";
import VerifiedUserIcon from "@mui/icons-material/VerifiedUser";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import { FormEvent, useEffect, useMemo, useState } from "react";

import { api } from "../api/api";
import { getCachedRolePermissionMatrix, invalidateLookup } from "../api/lookups";
import { useAuth } from "../auth/AuthContext";
import { hasPermission } from "../auth/permissions";
import { DataTable } from "../components/DataTable";
import { PageHeader } from "../components/PageHeader";
import { StatCard } from "../components/StatCard";
import { PermissionDefinition, RolePermissionMatrix, RolePermissionProfile, User, UserRole } from "../types";
import { formatDateTime } from "../utils/format";
import { getPasswordStrength, isValidEmail } from "../utils/input";

interface UserFormState {
  full_name: string;
  email: string;
  password: string;
  role: UserRole;
  is_active: boolean;
}

const emptyForm: UserFormState = {
  full_name: "",
  email: "",
  password: "",
  role: "secretaria",
  is_active: true,
};

const roleOptions: Array<{ value: UserRole; label: string }> = [
  { value: "administrador", label: "Administrador" },
  { value: "diretor", label: "Diretor" },
  { value: "financeiro", label: "Financeiro" },
  { value: "secretaria", label: "Secretaria" },
  { value: "professor", label: "Professor" },
];

const roleLabels: Record<UserRole, string> = {
  administrador: "Administrador",
  diretor: "Diretor",
  financeiro: "Financeiro",
  secretaria: "Secretaria",
  professor: "Professor",
  responsavel: "Responsavel",
};

const statusOptions = [
  { value: "", label: "Todos" },
  { value: "true", label: "Ativos" },
  { value: "false", label: "Inativos" },
];

function roleLabel(role: UserRole) {
  return roleLabels[role] ?? role;
}

export function Users() {
  const { user: currentUser, refreshUser } = useAuth();

  const canViewUsers = hasPermission(currentUser, "users_view");
  const canManageUsers = hasPermission(currentUser, "users_manage");
  const canDeleteUsers = hasPermission(currentUser, "users_delete");
  const canManageRolePermissions = hasPermission(currentUser, "role_permissions_manage");

  const [users, setUsers] = useState<User[]>([]);
  const [form, setForm] = useState<UserFormState>(emptyForm);
  const [filters, setFilters] = useState({ search: "", role: "", is_active: "" });
  const [editingId, setEditingId] = useState<number | null>(null);
  const [rolePermissionMatrix, setRolePermissionMatrix] = useState<RolePermissionMatrix | null>(null);
  const [selectedRole, setSelectedRole] = useState<UserRole>("secretaria");
  const [selectedPermissions, setSelectedPermissions] = useState<string[]>([]);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [loading, setLoading] = useState(false);

  const userStats = useMemo(() => {
    const visibleUsers = users.filter((user) => user.role !== "responsavel");
    const activeUsers = visibleUsers.filter((user) => user.is_active).length;
    const inactiveUsers = visibleUsers.length - activeUsers;
    const adminCount = visibleUsers.filter((user) => user.role === "administrador" || user.role === "diretor").length;
    return { activeUsers, inactiveUsers, adminCount };
  }, [users]);
  const emailIsValid = form.email.trim().length === 0 || isValidEmail(form.email);
  const passwordStrength = getPasswordStrength(form.password);
  const passwordIsValid = editingId ? form.password.length === 0 || passwordStrength.valid : passwordStrength.valid;
  const selectedProfile = useMemo(
    () => rolePermissionMatrix?.profiles.find((profile) => profile.role === selectedRole) ?? null,
    [rolePermissionMatrix, selectedRole],
  );
  const groupedPermissions = useMemo(() => {
    const groups = new Map<string, PermissionDefinition[]>();
    for (const item of rolePermissionMatrix?.catalog ?? []) {
      const currentItems = groups.get(item.group) ?? [];
      currentItems.push(item);
      groups.set(item.group, currentItems);
    }
    return Array.from(groups.entries());
  }, [rolePermissionMatrix]);
  const selectedRoleIsAdministrator = selectedRole === "administrador";

  async function loadUsers() {
    const { data } = await api.get<User[]>("/users", {
      params: {
        search: filters.search || undefined,
        role: filters.role || undefined,
        is_active: filters.is_active || undefined,
      },
    });
    setUsers(data.filter((item) => item.role !== "responsavel"));
  }

  async function loadRolePermissions() {
    const data = await getCachedRolePermissionMatrix();
    setRolePermissionMatrix(data);
  }

  async function refreshPage() {
    setError("");
    setLoading(true);
    try {
      const tasks: Array<Promise<unknown>> = [];
      if (canViewUsers || canManageUsers) {
        tasks.push(loadUsers());
      }
      if (canManageRolePermissions) {
        tasks.push(loadRolePermissions());
      }
      await Promise.all(tasks);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel carregar usuarios e perfis.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refreshPage();
  }, []);

  useEffect(() => {
    if (selectedProfile) {
      setSelectedPermissions(selectedProfile.permissions);
    }
  }, [selectedProfile]);

  function resetForm() {
    setForm(emptyForm);
    setEditingId(null);
  }

  function editUser(user: User) {
    setEditingId(user.id);
    setForm({
      full_name: user.full_name,
      email: user.email,
      password: "",
      role: user.role,
      is_active: user.is_active,
    });
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const payload: Record<string, unknown> = {
      full_name: form.full_name.trim(),
      email: form.email.trim().toLowerCase(),
      role: form.role,
      is_active: form.is_active,
      password: form.password,
    };

    if (editingId && !form.password) {
      delete payload.password;
    }

    try {
      if (editingId) {
        await api.put(`/users/${editingId}`, payload);
        setSuccess("Usuario atualizado.");
      } else {
        await api.post("/users", payload);
        setSuccess("Usuario criado.");
      }
      invalidateLookup("users");
      resetForm();
      await loadUsers();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar o usuario.");
    }
  }

  async function deleteUser(user: User) {
    if (!window.confirm(`Excluir ${user.full_name}?`)) {
      return;
    }

    try {
      await api.delete(`/users/${user.id}`);
      invalidateLookup("users");
      await loadUsers();
      setSuccess("Usuario excluido.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel excluir o usuario.");
    }
  }

  async function toggleUserStatus(user: User) {
    try {
      await api.put(`/users/${user.id}`, { is_active: !user.is_active });
      invalidateLookup("users");
      await loadUsers();
      setSuccess(user.is_active ? "Usuario inativado." : "Usuario reativado.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel atualizar o status do usuario.");
    }
  }

  async function saveRolePermissions() {
    try {
      const { data } = await api.put<RolePermissionProfile>(`/role-permissions/${selectedRole}`, {
        permissions: selectedPermissions,
      });

      setRolePermissionMatrix((current) =>
        current
          ? {
              ...current,
              profiles: current.profiles.map((profile) => (profile.role === selectedRole ? data : profile)),
            }
          : current,
      );
      invalidateLookup("role-permissions");
      setSuccess(`Permissoes do perfil ${roleLabel(selectedRole)} atualizadas.`);

      if (currentUser?.role === selectedRole) {
        await refreshUser();
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Nao foi possivel salvar as permissoes do perfil.");
    }
  }

  function togglePermission(permissionKey: string) {
    setSelectedPermissions((current) =>
      current.includes(permissionKey) ? current.filter((item) => item !== permissionKey) : [...current, permissionKey],
    );
  }

  return (
    <Stack spacing={3}>
      <PageHeader title="Usuarios" subtitle="Gestao de logins e permissoes por perfil." />
      {error ? <Alert severity="error">{error}</Alert> : null}
      {success ? (
        <Alert severity="success" onClose={() => setSuccess("")}>
          {success}
        </Alert>
      ) : null}

      {canViewUsers || canManageUsers ? (
        <>
          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(3, 1fr)" }}>
            <StatCard title="Usuarios ativos" value={userStats.activeUsers} icon={<VerifiedUserIcon color="success" />} />
            <StatCard title="Usuarios inativos" value={userStats.inactiveUsers} icon={<PersonOffIcon color="disabled" />} />
            <StatCard title="Perfis administrativos" value={userStats.adminCount} />
          </Box>

          <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "2fr 1fr 1fr auto" }}>
            <TextField
              label="Buscar usuario"
              value={filters.search}
              onChange={(event) => setFilters({ ...filters, search: event.target.value })}
            />
            <TextField select label="Perfil" value={filters.role} onChange={(event) => setFilters({ ...filters, role: event.target.value })}>
              <MenuItem value="">Todos</MenuItem>
              {roleOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              label="Situacao"
              value={filters.is_active}
              onChange={(event) => setFilters({ ...filters, is_active: event.target.value })}
            >
              {statusOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </TextField>
            <Button variant="outlined" onClick={() => refreshPage()}>
              Filtrar
            </Button>
          </Box>

          {canManageUsers ? (
            <Box component="form" onSubmit={handleSubmit} display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "repeat(4, 1fr)" }}>
              <TextField
                label="Nome completo"
                value={form.full_name}
                onChange={(event) => setForm({ ...form, full_name: event.target.value })}
                required
              />
              <TextField
                label="E-mail"
                type="email"
                value={form.email}
                onChange={(event) => setForm({ ...form, email: event.target.value })}
                error={!emailIsValid}
                helperText={!emailIsValid ? "Informe um e-mail valido." : "O e-mail sera usado no login."}
                required
              />
              <TextField
                label={editingId ? "Nova senha" : "Senha"}
                type="password"
                value={form.password}
                onChange={(event) => setForm({ ...form, password: event.target.value })}
                required={!editingId}
                error={form.password.length > 0 && !passwordIsValid}
                helperText={editingId && !form.password ? "Deixe em branco para manter a senha atual." : passwordStrength.message}
              />
              <TextField
                select
                label="Perfil"
                value={form.role}
                onChange={(event) =>
                  setForm((current) => ({
                    ...current,
                    role: event.target.value as UserRole,
                  }))
                }
              >
                {roleOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <FormControlLabel
                control={<Switch checked={form.is_active} onChange={(event) => setForm({ ...form, is_active: event.target.checked })} />}
                label="Usuario ativo"
              />
              <Stack direction="row" spacing={1} alignItems="center">
                <Button
                  type="submit"
                  variant="contained"
                  startIcon={<SaveIcon />}
                  disabled={!emailIsValid || !passwordIsValid}
                >
                  {editingId ? "Atualizar" : "Salvar"}
                </Button>
                {editingId ? <Button onClick={resetForm}>Cancelar</Button> : null}
              </Stack>
            </Box>
          ) : (
            <Alert severity="info">Seu perfil pode consultar usuarios, mas nao alterar cadastros.</Alert>
          )}

          <DataTable
            rows={users}
            loading={loading}
            getRowId={(row) => row.id}
            columns={[
              {
                key: "full_name",
                label: "Usuario",
                render: (row) => (
                  <Stack spacing={0.25}>
                    <Typography variant="body2" fontWeight={600}>
                      {row.full_name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.email}
                    </Typography>
                  </Stack>
                ),
              },
              { key: "role", label: "Perfil", render: (row) => roleLabel(row.role) },
              { key: "is_active", label: "Situacao", render: (row) => (row.is_active ? "Ativo" : "Inativo") },
              { key: "updated_at", label: "Atualizado", render: (row) => formatDateTime(row.updated_at) },
            ]}
            actions={(row) =>
              canManageUsers || canDeleteUsers ? (
                <>
                  {canManageUsers ? (
                    <Tooltip title={row.is_active ? "Inativar usuario" : "Reativar usuario"}>
                      <IconButton onClick={() => toggleUserStatus(row)} aria-label="Alterar status do usuario">
                        <PersonOffIcon />
                      </IconButton>
                    </Tooltip>
                  ) : null}
                  {canManageUsers ? (
                    <Tooltip title={`Editar ${roleLabel(row.role)}`}>
                      <IconButton onClick={() => editUser(row)} aria-label="Editar usuario">
                        <EditIcon />
                      </IconButton>
                    </Tooltip>
                  ) : null}
                  {canDeleteUsers && row.id !== currentUser?.id ? (
                    <Tooltip title="Excluir usuario">
                      <IconButton onClick={() => deleteUser(row)} aria-label="Excluir usuario">
                        <DeleteIcon />
                      </IconButton>
                    </Tooltip>
                  ) : null}
                </>
              ) : null
            }
          />
        </>
      ) : (
        <Alert severity="info">Seu acesso atual foi liberado apenas para configuracao de perfis e permissoes.</Alert>
      )}

      {canManageRolePermissions && rolePermissionMatrix ? (
        <Paper variant="outlined" sx={{ p: 3, borderRadius: 2 }}>
          <Stack spacing={2.5}>
            <Stack spacing={0.5}>
              <Typography variant="h6" fontWeight={700}>
                Permissoes por perfil
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Escolha o que cada perfil pode visualizar e executar no sistema.
              </Typography>
            </Stack>

            <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", md: "320px 1fr" }}>
              <TextField
                select
                label="Perfil"
                value={selectedRole}
                onChange={(event) => setSelectedRole(event.target.value as UserRole)}
              >
                {roleOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </TextField>
              <Alert severity={selectedRoleIsAdministrator ? "info" : "success"}>
                {selectedRoleIsAdministrator
                  ? "O perfil Administrador sempre mantem acesso total por seguranca."
                  : `Configurando permissoes do perfil ${roleLabel(selectedRole)}.`}
              </Alert>
            </Box>

            <Divider />

            <Box display="grid" gap={2} gridTemplateColumns={{ xs: "1fr", xl: "repeat(2, 1fr)" }}>
              {groupedPermissions.map(([group, items]) => (
                <Paper key={group} variant="outlined" sx={{ p: 2, borderRadius: 2 }}>
                  <Stack spacing={1.5}>
                    <Typography fontWeight={700}>{group}</Typography>
                    {items.map((item) => (
                      <Box key={item.key}>
                        <FormControlLabel
                          control={
                            <Checkbox
                              checked={selectedPermissions.includes(item.key)}
                              onChange={() => togglePermission(item.key)}
                              disabled={selectedRoleIsAdministrator}
                            />
                          }
                          label={item.label}
                        />
                        <Typography variant="caption" color="text.secondary" display="block" pl={4.5}>
                          {item.description}
                        </Typography>
                      </Box>
                    ))}
                  </Stack>
                </Paper>
              ))}
            </Box>

            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} justifyContent="space-between" alignItems={{ xs: "stretch", sm: "center" }}>
              <Typography variant="body2" color="text.secondary">
                {selectedProfile ? `${selectedProfile.permissions.length} permissoes ativas neste perfil.` : "Selecione um perfil."}
              </Typography>
              <Button variant="contained" startIcon={<SaveIcon />} onClick={saveRolePermissions} disabled={selectedRoleIsAdministrator}>
                Salvar permissoes
              </Button>
            </Stack>
          </Stack>
        </Paper>
      ) : null}
    </Stack>
  );
}
