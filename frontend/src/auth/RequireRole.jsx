/* Module: RequireRole. */

import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Primary component for this view/module.
export default function RequireRole({ roles }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  return roles.includes(user.role) ? <Outlet /> : <Navigate to="/dashboard" replace />;
}

