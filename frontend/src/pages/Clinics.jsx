/* Module: Clinics. */

import React from "react";
import {
  Alert,
  Box,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "../api/client.js";

function toNum(v) {
  const n = Number(v);
  return Number.isFinite(n) ? n : null;
}

function haversineKm(a, b) {
  const lat1 = toNum(a.latitude);
  const lon1 = toNum(a.longitude);
  const lat2 = toNum(b.latitude);
  const lon2 = toNum(b.longitude);
  if ([lat1, lon1, lat2, lon2].some((x) => x === null)) return null;
  const R = 6371;
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const p1 = (lat1 * Math.PI) / 180;
  const p2 = (lat2 * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(p1) * Math.cos(p2) * Math.sin(dLon / 2) ** 2;
  const c = 2 * Math.atan2(Math.sqrt(h), Math.sqrt(1 - h));
  return R * c;
}

export default function Clinics() {
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [clinics, setClinics] = React.useState([]);
  const [selectedClinic, setSelectedClinic] = React.useState(null);

  React.useEffect(() => {
    let cancelled = false;
    async function load() {
      setLoading(true);
      setError("");
      try {
        const res = await api.get("/clinics", { params: { limit: 300 } });
        if (cancelled) return;
        const rows = Array.isArray(res.data) ? res.data : [];
        setClinics(rows);
        if (rows.length > 0) setSelectedClinic(rows[0]);
      } catch (e) {
        if (cancelled) return;
        console.error("Clinics load failed", e);
        setError("Failed to load clinics.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    load();
    return () => {
      cancelled = true;
    };
  }, []);

  const filtered = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return clinics;
    return clinics.filter((c) =>
      [c.name, c.phone, c.email, c.address, c.suburb, c.state, c.postcode]
        .some((v) => String(v || "").toLowerCase().includes(q))
    );
  }, [clinics, search]);

  const nearby = React.useMemo(() => {
    if (!selectedClinic) return [];
    return clinics
      .filter((c) => c.id !== selectedClinic.id)
      .map((c) => ({ ...c, distance_km: haversineKm(selectedClinic, c) }))
      .filter((c) => c.distance_km !== null)
      .sort((a, b) => a.distance_km - b.distance_km)
      .slice(0, 8);
  }, [clinics, selectedClinic]);

  return (
    <Stack spacing={2}>
      <Typography variant="h5" fontWeight={800}>Clinics</Typography>
      <Typography sx={{ opacity: 0.8 }}>
        Contact details, demand/cancellations, and nearby clinic distances.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <TextField
          fullWidth
          size="small"
          label="Search clinics"
          placeholder="Name, phone, email, suburb..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </Paper>

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 2, minHeight: 500 }}>
            <Typography variant="h6" fontWeight={700}>Clinic Directory</Typography>
            <Divider sx={{ my: 1.25 }} />
            {loading ? (
              <Typography>Loading clinics...</Typography>
            ) : filtered.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No matching clinics.</Typography>
            ) : (
              <List dense>
                {filtered.map((c) => (
                  <ListItem
                    key={c.id}
                    disableGutters
                    sx={{
                      cursor: "pointer",
                      px: 1,
                      borderRadius: 1,
                      backgroundColor: selectedClinic?.id === c.id ? "rgba(25,118,210,0.08)" : "transparent",
                    }}
                    onClick={() => setSelectedClinic(c)}
                  >
                    <ListItemText
                      primary={c.name || "Clinic"}
                      secondary={`Upcoming(7d): ${c.upcoming_visits_next_7d ?? 0} | Cancellations(30d): ${c.cancellations_last_30d ?? 0}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 2, minHeight: 500 }}>
            <Typography variant="h6" fontWeight={700}>Clinic Details</Typography>
            <Divider sx={{ my: 1.25 }} />
            {!selectedClinic ? (
              <Typography sx={{ opacity: 0.75 }}>Select a clinic.</Typography>
            ) : (
              <Stack spacing={1.1}>
                <Typography><strong>Name:</strong> {selectedClinic.name || "-"}</Typography>
                <Typography><strong>Phone:</strong> {selectedClinic.phone || "-"}</Typography>
                <Typography><strong>Email:</strong> {selectedClinic.email || "-"}</Typography>
                <Typography>
                  <strong>Address:</strong>{" "}
                  {[selectedClinic.address, selectedClinic.suburb, selectedClinic.state, selectedClinic.postcode].filter(Boolean).join(", ") || "-"}
                </Typography>
                <Typography><strong>Staff count:</strong> {selectedClinic.staff_count ?? 0}</Typography>
                <Typography><strong>Visits (30d):</strong> {selectedClinic.visits_last_30d ?? 0}</Typography>
                <Typography><strong>Cancellations (30d):</strong> {selectedClinic.cancellations_last_30d ?? 0}</Typography>
                <Typography><strong>Upcoming visits (7d):</strong> {selectedClinic.upcoming_visits_next_7d ?? 0}</Typography>

                <Box />
                <Typography variant="subtitle1" fontWeight={700}>Nearest Clinics</Typography>
                {nearby.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>Distance unavailable (missing geolocation).</Typography>
                ) : (
                  <List dense>
                    {nearby.map((c) => (
                      <ListItem key={c.id} disableGutters>
                        <ListItemText
                          primary={c.name}
                          secondary={`${c.distance_km.toFixed(1)} km | Upcoming(7d): ${c.upcoming_visits_next_7d ?? 0}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Stack>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
}

