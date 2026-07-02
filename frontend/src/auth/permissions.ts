import { PermissionKey, User, UserRole } from "../types";

interface AccessOptions {
  permissions?: PermissionKey[];
  roles?: UserRole[];
  mode?: "all" | "any";
}

export function hasRole(userRole: UserRole | undefined, roles?: UserRole[]) {
  if (!roles || roles.length === 0) {
    return true;
  }
  return Boolean(userRole && roles.includes(userRole));
}

export function hasPermission(user: Pick<User, "permissions"> | null | undefined, permission?: PermissionKey) {
  if (!permission) {
    return true;
  }
  return Boolean(user?.permissions.includes(permission));
}

export function hasPermissions(
  user: Pick<User, "permissions" | "role"> | null | undefined,
  permissions?: PermissionKey[],
  mode: "all" | "any" = "all",
) {
  if (!permissions || permissions.length === 0) {
    return true;
  }
  if (!user) {
    return false;
  }
  return mode === "all"
    ? permissions.every((permission) => user.permissions.includes(permission))
    : permissions.some((permission) => user.permissions.includes(permission));
}

export function canAccess(user: Pick<User, "permissions" | "role"> | null | undefined, options: AccessOptions) {
  return hasRole(user?.role, options.roles) && hasPermissions(user, options.permissions, options.mode ?? "all");
}
