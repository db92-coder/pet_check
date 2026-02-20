import React from "react";
import { Box, Button, TextField, Typography, Alert, Paper, Stack, ToggleButton, ToggleButtonGroup } from "@mui/material";
import { useAuth } from "../auth/AuthContext";
import { useNavigate } from "react-router-dom";

export default function Login() {
  const { login, registerOwner } = useAuth();
  const nav = useNavigate();
  const [mode, setMode] = React.useState("login");
  const [error, setError] = React.useState(null);
  const [success, setSuccess] = React.useState(null);
  const [loading, setLoading] = React.useState(false);

  async function onLoginSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    const data = new FormData(e.currentTarget);
    const email = data.get("email");
    const password = data.get("password");

    try {
      await login({ email, password });
      nav("/dashboard");
    } catch {
      setError("Login failed. Check your details.");
    } finally {
      setLoading(false);
    }
  }

  async function onRegisterSubmit(e) {
    e.preventDefault();
    setError(null);
    setSuccess(null);
    setLoading(true);

    const data = new FormData(e.currentTarget);
    const payload = {
      email: data.get("email"),
      password: data.get("password"),
      full_name: data.get("full_name"),
      phone: data.get("phone"),
      pet_name: data.get("pet_name"),
      pet_species: data.get("pet_species"),
      pet_breed: data.get("pet_breed"),
      pet_sex: data.get("pet_sex"),
      pet_date_of_birth: data.get("pet_date_of_birth"),
      pet_photo_file: data.get("pet_photo_file"),
    };

    try {
      await registerOwner(payload);
      await login({ email: payload.email, password: payload.password });
      nav("/dashboard");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Registration failed.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Box sx={{ minHeight: "100vh", display: "grid", placeItems: "center", p: 2 }}>
      <Paper sx={{ p: 4, width: "100%", maxWidth: 520 }}>
        <Typography variant="h4" fontWeight={800} gutterBottom>
          Pet Check
        </Typography>
        <Typography variant="body2" sx={{ opacity: 0.8, mb: 2 }}>
          Sign in with your user credentials, or create a new owner account.
        </Typography>

        <ToggleButtonGroup
          color="primary"
          exclusive
          value={mode}
          onChange={(_, value) => value && setMode(value)}
          sx={{ mb: 2 }}
        >
          <ToggleButton value="login">Login</ToggleButton>
          <ToggleButton value="register">Create User</ToggleButton>
        </ToggleButtonGroup>

        {error && <Alert severity="error" sx={{ mb: 2 }}>{error}</Alert>}
        {success && <Alert severity="success" sx={{ mb: 2 }}>{success}</Alert>}

        {mode === "login" ? (
          <Box component="form" onSubmit={onLoginSubmit} sx={{ display: "grid", gap: 2 }}>
            <TextField name="email" label="Email" autoComplete="email" required />
            <TextField name="password" label="Password" type="password" autoComplete="current-password" required />
            <Button type="submit" variant="contained" disabled={loading}>
              {loading ? "Signing in..." : "Sign in"}
            </Button>
          </Box>
        ) : (
          <Box component="form" onSubmit={onRegisterSubmit} sx={{ display: "grid", gap: 2 }}>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField name="full_name" label="Full Name" required fullWidth />
              <TextField name="phone" label="Phone" fullWidth />
            </Stack>
            <TextField name="email" label="Email" autoComplete="email" required />
            <TextField name="password" label="Password" type="password" required />

            <Typography variant="subtitle2" sx={{ mt: 1 }}>Initial Pet</Typography>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField name="pet_name" label="Pet Name" required fullWidth />
              <TextField name="pet_species" label="Species" required fullWidth />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
              <TextField name="pet_breed" label="Breed" fullWidth />
              <TextField name="pet_sex" label="Sex" fullWidth />
            </Stack>
            <TextField
              name="pet_date_of_birth"
              label="Pet DOB"
              type="date"
              InputLabelProps={{ shrink: true }}
              fullWidth
            />
            <Button variant="outlined" component="label">
              Upload Pet Photo (JPEG/PNG)
              <input hidden type="file" name="pet_photo_file" accept="image/png,image/jpeg" />
            </Button>

            <Button type="submit" variant="contained" disabled={loading}>
              {loading ? "Creating account..." : "Create User"}
            </Button>
          </Box>
        )}
      </Paper>
    </Box>
  );
}
