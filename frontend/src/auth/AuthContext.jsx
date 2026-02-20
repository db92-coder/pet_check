import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    try {
      const raw = localStorage.getItem("auth_user");
      return raw ? JSON.parse(raw) : null;
    } catch {
      return null;
    }
  });
  const [token, setToken] = useState(localStorage.getItem("access_token"));

  const isAuthed = !!token;

  useEffect(() => {
    let cancelled = false;

    async function hydrateUser() {
      if (!token || user) return;
      try {
        const res = await api.get("/auth/me");
        if (cancelled) return;
        const me = res.data;
        localStorage.setItem("auth_user", JSON.stringify(me));
        setUser(me);
      } catch {
        if (cancelled) return;
        localStorage.removeItem("access_token");
        localStorage.removeItem("auth_user");
        setToken(null);
        setUser(null);
      }
    }

    hydrateUser();
    return () => {
      cancelled = true;
    };
  }, [token, user]);

  async function login({ email, password }) {
    const res = await api.post("/auth/login", { email, password });
    const { access_token, user: me } = res.data;

    localStorage.setItem("access_token", access_token);
    localStorage.setItem("auth_user", JSON.stringify(me));
    setToken(access_token);
    setUser(me);
  }

  function logout() {
    localStorage.removeItem("access_token");
    localStorage.removeItem("auth_user");
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
