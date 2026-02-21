import React, { useMemo, useState } from "react";
import { Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Box,
  Drawer,
  List,
  ListItemButton,
  ListItemIcon,
  ListItemText,
  Toolbar,
  AppBar,
  Typography,
  IconButton,
  Divider,
  Tooltip,
} from "@mui/material";

import MenuIcon from "@mui/icons-material/Menu";
import LogoutIcon from "@mui/icons-material/Logout";
import DashboardIcon from "@mui/icons-material/Dashboard";
import PetsIcon from "@mui/icons-material/Pets";
import PeopleIcon from "@mui/icons-material/People";
import EventNoteIcon from "@mui/icons-material/EventNote";
import LocalHospitalIcon from "@mui/icons-material/LocalHospital";
import BadgeIcon from "@mui/icons-material/Badge";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import InsightsIcon from "@mui/icons-material/Insights";

import { useTheme } from "@mui/material/styles";

import { useAuth } from "../auth/AuthContext.jsx";

const drawerWidth = 260;

export default function AdminLayout() {
  const { user, logout } = useAuth();
  const role = user?.role || "OWNER";
  const name = user?.full_name || user?.name || user?.username || "User";

  const [mobileOpen, setMobileOpen] = useState(false);
  const location = useLocation();
  const nav = useNavigate();
  const theme = useTheme();

  const navItems = useMemo(
    () => [
      { label: "Dashboard", path: "/dashboard", icon: <DashboardIcon />, roles: ["ADMIN", "VET", "OWNER"] },
      { label: "Pets", path: "/pets", icon: <PetsIcon />, roles: ["ADMIN", "VET"] },
      { label: "Visits", path: "/visits", icon: <EventNoteIcon />, roles: ["ADMIN", "VET"] },
      { label: "Owners", path: "/owners", icon: <PeopleIcon />, roles: ["ADMIN", "VET"] },
      { label: "Clinics", path: "/clinics", icon: <LocalHospitalIcon />, roles: ["ADMIN", "VET"] },
      { label: "Staff", path: "/staff", icon: <BadgeIcon />, roles: ["ADMIN", "VET"] },
      { label: "Users", path: "/users", icon: <AdminPanelSettingsIcon />, roles: ["ADMIN", "VET"] },
      { label: "Analytics", path: "/admin/analytics", icon: <InsightsIcon />, roles: ["ADMIN"] },
    ],
    []
  );

  const allowed = navItems.filter((i) => i.roles.includes(role));

  const drawerContent = (
    <Box sx={{ height: "100%", color: "#fff" }}>
      <Box sx={theme.mixins.toolbar} />

      <Box sx={{ px: 2.5, pb: 2.5 }}>
        <Typography variant="h6" fontWeight={800}>
          Pet Protect
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.82 }}>
          {name} - {role}
        </Typography>
      </Box>

      <Divider sx={{ borderColor: "rgba(255,255,255,0.14)" }} />

      <List sx={{ px: 1, pt: 1 }}>
        {allowed.map((item) => {
          const selected = location.pathname === item.path;
          return (
            <ListItemButton
              key={item.path}
              selected={selected}
              onClick={() => {
                nav(item.path);
                setMobileOpen(false);
              }}
              sx={{
                borderRadius: 2.5,
                mx: 1,
                mb: 0.5,
                color: "rgba(255,255,255,0.88)",
                "& .MuiListItemIcon-root": {
                  color: "inherit",
                  minWidth: 36,
                },
                "&.Mui-selected": {
                  background: "linear-gradient(195deg, #49a3f1, #1A73E8)",
                  boxShadow: "0 6px 14px rgba(0, 0, 0, 0.22)",
                  color: "#fff",
                },
                "&.Mui-selected:hover": {
                  background: "linear-gradient(195deg, #49a3f1, #1A73E8)",
                },
                "&:hover": {
                  backgroundColor: "rgba(255,255,255,0.08)",
                },
              }}
            >
              <ListItemIcon>{item.icon}</ListItemIcon>
              <ListItemText primary={item.label} />
            </ListItemButton>
          );
        })}
      </List>
    </Box>
  );

  return (
    <Box
      sx={{
        display: "flex",
        minHeight: "100vh",
        background: "transparent",
      }}
    >
      <AppBar
        position="fixed"
        elevation={0}
        sx={{
          zIndex: (t) => t.zIndex.drawer + 1,
          backgroundColor: "rgba(255, 255, 255, 0.85)",
          backdropFilter: "blur(8px)",
          color: "text.primary",
          borderBottom: "1px solid rgba(0,0,0,0.06)",
        }}
      >
        <Toolbar>
          <IconButton
            color="default"
            edge="start"
            onClick={() => setMobileOpen((v) => !v)}
            sx={{ mr: 2, display: { sm: "none" } }}
          >
            <MenuIcon />
          </IconButton>

          <Typography variant="h6" sx={{ flexGrow: 1 }}>
            {allowed.find((x) => x.path === location.pathname)?.label || "Pet Protect"}
          </Typography>

          <Tooltip title="Logout">
            <IconButton
              color="default"
              onClick={() => {
                logout();
                nav("/login");
              }}
            >
              <LogoutIcon />
            </IconButton>
          </Tooltip>
        </Toolbar>
      </AppBar>

      <Drawer
        variant="permanent"
        sx={{
          width: drawerWidth,
          flexShrink: 0,
          display: { xs: "none", sm: "block" },
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            border: "none",
            margin: 2,
            height: "calc(100% - 32px)",
            borderRadius: 4,
            background: "linear-gradient(195deg, #42424a, #191919)",
            boxShadow: "0 16px 30px rgba(0, 0, 0, 0.22)",
            overflow: "hidden",
          },
        }}
        open
      >
        {drawerContent}
      </Drawer>

      <Drawer
        variant="temporary"
        open={mobileOpen}
        onClose={() => setMobileOpen(false)}
        sx={{
          display: { xs: "block", sm: "none" },
          [`& .MuiDrawer-paper`]: {
            width: drawerWidth,
            boxSizing: "border-box",
            background: "linear-gradient(195deg, #42424a, #191919)",
            color: "#fff",
          },
        }}
      >
        {drawerContent}
      </Drawer>

      <Box
        component="main"
        sx={{
          flexGrow: 1,
          p: { xs: 2, sm: 3 },
          mt: 1,
          minHeight: "100vh",
        }}
      >
        <Toolbar />
        <Outlet />
      </Box>
    </Box>
  );
}
