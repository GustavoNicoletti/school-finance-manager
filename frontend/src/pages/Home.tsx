import { Alert, Stack } from "@mui/material";
import { Navigate } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { canAccess } from "../auth/permissions";

export function Home() {
  const { user } = useAuth();

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (canAccess(user, { permissions: ["dashboard_view"] })) {
    return <Navigate to="/dashboard" replace />;
  }

  if (canAccess(user, { permissions: ["students_view"] })) {
    return <Navigate to="/students" replace />;
  }

  if (canAccess(user, { permissions: ["guardians_view"] })) {
    return <Navigate to="/guardians" replace />;
  }

  if (canAccess(user, { permissions: ["receivables_view"] })) {
    return <Navigate to="/receivables" replace />;
  }

  if (canAccess(user, { permissions: ["payables_view"] })) {
    return <Navigate to="/payables" replace />;
  }

  if (canAccess(user, { permissions: ["delinquency_view"] })) {
    return <Navigate to="/delinquency" replace />;
  }

  if (canAccess(user, { permissions: ["cash_flow_view"] })) {
    return <Navigate to="/cash-flow" replace />;
  }

  if (canAccess(user, { permissions: ["users_view", "role_permissions_manage"], mode: "any" })) {
    return <Navigate to="/users" replace />;
  }

  if (canAccess(user, { permissions: ["audit_view"] })) {
    return <Navigate to="/audit" replace />;
  }

  return (
    <Stack py={4}>
      <Alert severity="warning">Seu perfil nao possui nenhum modulo liberado no momento.</Alert>
    </Stack>
  );
}
