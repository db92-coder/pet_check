import React from "react";
import { Box, Button, TextField, Typography, Alert, Paper } from "@mui/material";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login } = useAuth();
  const nav = useNavigate();
  const [error, setError] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  async function onSubmit(e) {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const data = new FormData(e.currentTarget);
    const email = data.get("email");
    const password = data.get("password");

    try {
      await login({ email, password });
      nav("/dashboard");
    } catch (err) {
      setError("Login failed. Check your details.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper sx={{ p: 4, width: "100%", maxWidth: 420 }}>
        <Typography variant="h4" fontWeight={800} gutterBottom>
          Pet Check
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8, mb: 2 }}>
          Sign in to manage pets, visits and clinic records.
        </Typography>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}

        <Box component="form" onSubmit={onSubmit} sx={{ display: "grid", gap: 2 }}>
          <TextField name="email" label="Email" autoComplete="email" required />
          <TextField name="password" label="Password" type="password" autoComplete="current-password" required />
          <Button type="submit" variant="contained" disabled={loading}>
            {loading ? "Signing in…" : "Sign in"}
          </Button>
        </Box>
      </Paper>
    </Box>
  );
}
