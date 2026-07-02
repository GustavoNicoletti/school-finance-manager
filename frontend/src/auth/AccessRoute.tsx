import { Alert, Stack } from "@mui/material";
import { Outlet } from "react-router-dom";

import { PermissionKey, UserRole } from "../types";
import { useAuth } from "./AuthContext";
import { canAccess } from "./permissions";

interface AccessRouteProps {
  permissions?: PermissionKey[];
  roles?: UserRole[];
  mode?: "all" | "any";
}

export function AccessRoute({ permissions, roles, mode = "all" }: AccessRouteProps) {
  const { user } = useAuth();

  if (!canAccess(user, { permissions, roles, mode })) {
    return (
      <Stack py={4}>
        <Alert severity="warning">Voce nao possui permissao para acessar esta pagina.</Alert>
      </Stack>
    );
  }

  return <Outlet />;
}
