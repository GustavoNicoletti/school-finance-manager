import MenuIcon from "@mui/icons-material/Menu";
import { AppBar, Box, Chip, Drawer, IconButton, Stack, Toolbar, Typography } from "@mui/material";
import { useEffect, useState } from "react";
import { Outlet } from "react-router-dom";

import { useAuth } from "../auth/AuthContext";
import { warmCommonLookups } from "../api/lookups";
import { Sidebar } from "../components/Sidebar";
import { warmPrimaryRoutes } from "../routes/prefetch";

const drawerWidth = 264;

export function DashboardLayout() {
  const [mobileOpen, setMobileOpen] = useState(false);
  const { user } = useAuth();

  useEffect(() => {
    const runWarmup = () => {
      warmPrimaryRoutes();
      warmCommonLookups();
    };

    const windowWithIdleCallback = window as Window & {
      requestIdleCallback?: (callback: () => void) => number;
    };

    if (windowWithIdleCallback.requestIdleCallback) {
      windowWithIdleCallback.requestIdleCallback(runWarmup);
      return;
    }

    const timer = window.setTimeout(runWarmup, 300);
    return () => window.clearTimeout(timer);
  }, []);

  return (
    <Box sx={{ display: "flex", minHeight: "100vh" }}>
      <AppBar
        position="fixed"
        color="inherit"
        elevation={0}
        sx={{
          borderBottom: "1px solid",
          borderColor: "divider",
          width: { md: `calc(100% - ${drawerWidth}px)` },
          ml: { md: `${drawerWidth}px` },
        }}
      >
        <Toolbar>
          <IconButton edge="start" onClick={() => setMobileOpen(true)} sx={{ mr: 2, display: { md: "none" } }}>
            <MenuIcon />
          </IconButton>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "flex-start", sm: "center" }}
            spacing={1}
            sx={{ width: "100%" }}
          >
            <Typography variant="h6" fontWeight={700}>
              Gestao Escolar
            </Typography>
            {user ? (
              <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap" useFlexGap>
                <Typography variant="body2" color="text.secondary">
                  {user.full_name}
                </Typography>
                <Chip size="small" label={user.role} variant="outlined" />
              </Stack>
            ) : null}
          </Stack>
        </Toolbar>
      </AppBar>
      <Box component="nav" sx={{ width: { md: drawerWidth }, flexShrink: { md: 0 } }}>
        <Drawer
          variant="temporary"
          open={mobileOpen}
          onClose={() => setMobileOpen(false)}
          ModalProps={{ keepMounted: true }}
          sx={{
            display: { xs: "block", md: "none" },
            "& .MuiDrawer-paper": { width: drawerWidth },
          }}
        >
          <Sidebar />
        </Drawer>
        <Drawer
          variant="permanent"
          sx={{
            display: { xs: "none", md: "block" },
            "& .MuiDrawer-paper": { width: drawerWidth, boxSizing: "border-box" },
          }}
          open
        >
          <Sidebar />
        </Drawer>
      </Box>
      <Box component="main" sx={{ flexGrow: 1, width: { md: `calc(100% - ${drawerWidth}px)` }, p: { xs: 2, md: 3 } }}>
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
