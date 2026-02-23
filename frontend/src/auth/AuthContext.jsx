/* Module: AuthContext. */

import React, { createContext, useContext, useEffect, useMemo, useState } from "react";
import { api } from "../api/client";

const AuthContext = createContext(null);

// Provider component for auth state, login/logout, and registration actions.
export function AuthProvider({ children }) {
// Local UI/data state for this page.
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

// Initial/refresh data loading side-effect.
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

  async function registerOwner(payload) {
    const formData = new FormData();
    formData.append("email", payload.email);
    formData.append("password", payload.password);
    formData.append("full_name", payload.full_name);
    formData.append("phone", payload.phone || "");
    formData.append("pet_name", payload.pet_name);
    formData.append("pet_species", payload.pet_species);
    formData.append("pet_breed", payload.pet_breed || "");
    formData.append("pet_sex", payload.pet_sex || "");
    formData.append("pet_microchip_number", payload.pet_microchip_number || "");
    formData.append("pet_date_of_birth", payload.pet_date_of_birth || "");
    if (payload.pet_photo_file) {
      formData.append("photo", payload.pet_photo_file);
    }

    await api.post("/auth/register-owner", formData, {
      headers: { "Content-Type": "multipart/form-data" },
    });
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
    () => ({ user, token, isAuthed, login, registerOwner, logout, hasRole, setUser }),
    [user, token, isAuthed]
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  return useContext(AuthContext);
}

