/* Module: RequireAuth. */

import React from "react";
import { Navigate, Outlet } from "react-router-dom";
import { useAuth } from "./AuthContext";

// Primary component for this view/module.
export default function RequireAuth() {
  const { isAuthed } = useAuth();
  return isAuthed ? <Outlet /> : <Navigate to="/login" replace />;
}

