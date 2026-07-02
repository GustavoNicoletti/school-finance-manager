import AccountBalanceWalletIcon from "@mui/icons-material/AccountBalanceWallet";
import DashboardIcon from "@mui/icons-material/Dashboard";
import HistoryIcon from "@mui/icons-material/History";
import GroupIcon from "@mui/icons-material/Group";
import LogoutIcon from "@mui/icons-material/Logout";
import PaidIcon from "@mui/icons-material/Paid";
import PeopleIcon from "@mui/icons-material/People";
import PersonIcon from "@mui/icons-material/Person";
import SummarizeIcon from "@mui/icons-material/Summarize";
import ReceiptLongIcon from "@mui/icons-material/ReceiptLong";
import SchoolIcon from "@mui/icons-material/School";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import { Box, Divider, List, ListItemButton, ListItemIcon, ListItemText, Toolbar } from "@mui/material";
import { NavLink } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { canAccess } from "../auth/permissions";
import { prefetchRoute } from "../routes/prefetch";
import { PermissionKey, UserRole } from "../types";

interface NavItem {
  label: string;
  path: string;
  icon: JSX.Element;
  prefetch: Parameters<typeof prefetchRoute>[0];
  roles?: UserRole[];
  permissions?: PermissionKey[];
  mode?: "all" | "any";
}

const navItems: NavItem[] = [
  { label: "Dashboard", path: "/dashboard", icon: <DashboardIcon />, prefetch: "dashboard", permissions: ["dashboard_view"] },
  { label: "Alunos", path: "/students", icon: <SchoolIcon />, prefetch: "students", permissions: ["students_view"] },
  { label: "Responsaveis", path: "/guardians", icon: <PeopleIcon />, prefetch: "guardians", permissions: ["guardians_view"] },
  { label: "Contas a receber", path: "/receivables", icon: <PaidIcon />, prefetch: "receivables", permissions: ["receivables_view"] },
  { label: "Contas a pagar", path: "/payables", icon: <ReceiptLongIcon />, prefetch: "payables", permissions: ["payables_view"] },
  { label: "Inadimplencia", path: "/delinquency", icon: <WarningAmberIcon />, prefetch: "delinquency", permissions: ["delinquency_view"] },
  { label: "Fluxo de caixa", path: "/cash-flow", icon: <AccountBalanceWalletIcon />, prefetch: "cashFlow", permissions: ["cash_flow_view"] },
  {
    label: "Relatorios",
    path: "/reports",
    icon: <SummarizeIcon />,
    prefetch: "reports",
    permissions: ["students_view", "guardians_view", "receivables_view", "payables_view", "delinquency_view", "cash_flow_view"],
    mode: "any",
  },
  { label: "Usuarios", path: "/users", icon: <GroupIcon />, prefetch: "users", permissions: ["users_view", "role_permissions_manage"], mode: "any" },
  { label: "Auditoria", path: "/audit", icon: <HistoryIcon />, prefetch: "audit", permissions: ["audit_view"] },
];

export function Sidebar() {
  const { logout, user } = useAuth();
  const visibleItems = navItems.filter((item) => canAccess(user, { roles: item.roles, permissions: item.permissions, mode: item.mode }));

  return (
    <Box sx={{ width: 264, height: "100%", display: "flex", flexDirection: "column" }}>
      <Toolbar sx={{ gap: 1 }}>
        <PersonIcon color="primary" />
        <Box sx={{ fontWeight: 700 }}>Gestao Escolar</Box>
      </Toolbar>
      <Divider />
      <List sx={{ flex: 1, px: 1 }}>
        {visibleItems.map((item) => (
          <ListItemButton
            key={item.path}
            component={NavLink}
            to={item.path}
            onMouseEnter={() => prefetchRoute(item.prefetch)}
            onFocus={() => prefetchRoute(item.prefetch)}
            sx={{
              borderRadius: 2,
              mb: 0.5,
              "&.active": { bgcolor: "primary.main", color: "primary.contrastText" },
              "&.active .MuiListItemIcon-root": { color: "inherit" },
            }}
          >
            <ListItemIcon>{item.icon}</ListItemIcon>
            <ListItemText primary={item.label} />
          </ListItemButton>
        ))}
      </List>
      <Divider />
      <Box sx={{ p: 1 }}>
        <ListItemButton onClick={() => void logout()} sx={{ borderRadius: 2 }}>
          <ListItemIcon>
            <LogoutIcon />
          </ListItemIcon>
          <ListItemText primary="Sair" secondary={user?.full_name} />
        </ListItemButton>
      </Box>
    </Box>
  );
}
