import React, { createContext, useContext, useMemo, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(localStorage.getItem("access_token"));

  const isAuthed = !!token;

  async function login({ email, password }) {
  const access_token = "dev-token";
  const me = { username: email || "daniel", role: "ADMIN" };

  localStorage.setItem("access_token", access_token);
  setToken(access_token);
  setUser(me);
}


  function logout() {
    localStorage.removeItem("access_token");
    setToken(null);
    setUser(null);
  }

  function hasRole(roles) {
    return !!user?.role && roles.includes(user.role);
  }

  const value = useMemo(
    () => ({ user, token, isAuthed, login, logout, hasRole, setUser }),
    [user, token, isAuthed]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}
