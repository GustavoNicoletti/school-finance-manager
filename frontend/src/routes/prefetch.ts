const routeImporters = {
  dashboard: () => import("../pages/Dashboard"),
  students: () => import("../pages/Students"),
  guardians: () => import("../pages/Guardians"),
  receivables: () => import("../pages/Receivables"),
  payables: () => import("../pages/Payables"),
  delinquency: () => import("../pages/Delinquency"),
  cashFlow: () => import("../pages/CashFlow"),
  reports: () => import("../pages/Reports"),
  users: () => import("../pages/Users"),
  audit: () => import("../pages/Audit"),
};

type RoutePrefetchKey = keyof typeof routeImporters;

const prefetchedRoutes = new Set<RoutePrefetchKey>();

export function prefetchRoute(key: RoutePrefetchKey) {
  if (prefetchedRoutes.has(key)) {
    return;
  }
  prefetchedRoutes.add(key);
  void routeImporters[key]();
}

export function warmPrimaryRoutes() {
  const primaryRoutes: RoutePrefetchKey[] = ["dashboard", "students", "guardians", "receivables", "payables", "users"];
  primaryRoutes.forEach(prefetchRoute);
}
