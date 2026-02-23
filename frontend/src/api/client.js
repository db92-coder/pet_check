/* Module: client. */

import axios from "axios";

// Central axios instance used by all frontend API calls.
export const api = axios.create({
  baseURL: (import.meta.env.VITE_API_BASE_URL || "http://localhost:8000") + "/api/v1",
});

// Attach bearer token automatically when user is authenticated.
api.interceptors.request.use((config) => {
  const token = localStorage.getItem("access_token");
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

