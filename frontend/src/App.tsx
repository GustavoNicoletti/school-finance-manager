import { CircularProgress, CssBaseline, Stack, ThemeProvider, createTheme } from "@mui/material";
import { Suspense, lazy } from "react";
import { Navigate, Route, Routes } from "react-router-dom";

import { AccessRoute } from "./auth/AccessRoute";
import { ProtectedRoute } from "./auth/ProtectedRoute";
import { DashboardLayout } from "./layouts/DashboardLayout";

const Audit = lazy(() => import("./pages/Audit").then((module) => ({ default: module.Audit })));
const CashFlow = lazy(() => import("./pages/CashFlow").then((module) => ({ default: module.CashFlow })));
const Dashboard = lazy(() => import("./pages/Dashboard").then((module) => ({ default: module.Dashboard })));
const Delinquency = lazy(() => import("./pages/Delinquency").then((module) => ({ default: module.Delinquency })));
const Guardians = lazy(() => import("./pages/Guardians").then((module) => ({ default: module.Guardians })));
const Home = lazy(() => import("./pages/Home").then((module) => ({ default: module.Home })));
const Login = lazy(() => import("./pages/Login").then((module) => ({ default: module.Login })));
const Payables = lazy(() => import("./pages/Payables").then((module) => ({ default: module.Payables })));
const Receivables = lazy(() => import("./pages/Receivables").then((module) => ({ default: module.Receivables })));
const Reports = lazy(() => import("./pages/Reports").then((module) => ({ default: module.Reports })));
const Students = lazy(() => import("./pages/Students").then((module) => ({ default: module.Students })));
const Users = lazy(() => import("./pages/Users").then((module) => ({ default: module.Users })));

const theme = createTheme({
  palette: {
    primary: { main: "#1d4f91" },
    secondary: { main: "#2f855a" },
    background: { default: "#f6f8fb" },
  },
  shape: {
    borderRadius: 8,
  },
});

export default function App() {
  return (
    <ThemeProvider theme={theme}>
      <CssBaseline />
      <Suspense
        fallback={
          <Stack minHeight="100vh" alignItems="center" justifyContent="center">
            <CircularProgress />
          </Stack>
        }
      >
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route element={<ProtectedRoute />}>
            <Route element={<DashboardLayout />}>
              <Route index element={<Home />} />
              <Route element={<AccessRoute permissions={["dashboard_view"]} />}>
                <Route path="/dashboard" element={<Dashboard />} />
              </Route>
              <Route element={<AccessRoute permissions={["students_view"]} />}>
                <Route path="/students" element={<Students />} />
              </Route>
              <Route element={<AccessRoute permissions={["guardians_view"]} />}>
                <Route path="/guardians" element={<Guardians />} />
              </Route>
              <Route element={<AccessRoute permissions={["receivables_view"]} />}>
                <Route path="/receivables" element={<Receivables />} />
              </Route>
              <Route element={<AccessRoute permissions={["payables_view"]} />}>
                <Route path="/payables" element={<Payables />} />
              </Route>
              <Route element={<AccessRoute permissions={["delinquency_view"]} />}>
                <Route path="/delinquency" element={<Delinquency />} />
              </Route>
              <Route element={<AccessRoute permissions={["cash_flow_view"]} />}>
                <Route path="/cash-flow" element={<CashFlow />} />
              </Route>
              <Route
                element={
                  <AccessRoute
                    permissions={["students_view", "guardians_view", "receivables_view", "payables_view", "delinquency_view", "cash_flow_view"]}
                    mode="any"
                  />
                }
              >
                <Route path="/reports" element={<Reports />} />
              </Route>
              <Route element={<AccessRoute permissions={["users_view", "role_permissions_manage"]} mode="any" />}>
                <Route path="/users" element={<Users />} />
              </Route>
              <Route element={<AccessRoute permissions={["audit_view"]} />}>
                <Route path="/audit" element={<Audit />} />
              </Route>
            </Route>
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </ThemeProvider>
  );
}
