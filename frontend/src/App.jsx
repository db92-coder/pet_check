/* Module: App. */

import React from "react";
import { Routes, Route, Navigate } from "react-router-dom";

import RequireAuth from "./auth/RequireAuth.jsx";
import RequireRole from "./auth/RequireRole.jsx";

import AdminLayout from "./layouts/AdminLayout.jsx";
import Login from "./pages/Login.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Placeholder from "./pages/Placeholder.jsx";
import Pets from "./pages/Pets.jsx";
import AdminAnalytics from "./pages/AdminAnalytics.jsx";
import Visits from "./pages/Visits.jsx";
import Owners from "./pages/Owners.jsx";
import Clinics from "./pages/Clinics.jsx";
import Staff from "./pages/Staff.jsx";

// Primary component for this view/module.
export default function App() {
// Render UI layout and interactions.
  return (
    <Routes>
      <Route path="/login" element={<Login />} />

      <Route element={<RequireAuth />}>
        <Route element={<AdminLayout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/dashboard" element={<Dashboard />} />

          <Route element={<RequireRole roles={["ADMIN", "VET"]} />}>
            <Route path="/pets" element={<Pets />} />
            <Route path="/visits" element={<Visits />} />
            <Route path="/owners" element={<Owners />} />
            <Route path="/clinics" element={<Clinics />} />
            <Route path="/staff" element={<Staff />} />
            <Route path="/users" element={<Placeholder title="Users" />} />
          </Route>

          <Route element={<RequireRole roles={["ADMIN"]} />}>
            <Route path="/admin/analytics" element={<AdminAnalytics />} />
          </Route>
        </Route>
      </Route>

      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}

