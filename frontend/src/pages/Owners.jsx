/* Module: Owners. */

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

function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

// Primary component for this view/module.
export default function Owners() {
// Local UI/data state for this page.
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [owners, setOwners] = React.useState([]);
  const [selectedOwner, setSelectedOwner] = React.useState(null);
  const [ownerPets, setOwnerPets] = React.useState([]);

  const loadOwners = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const res = await api.get("/owners", { params: { limit: 500 } });
      const rows = Array.isArray(res.data) ? res.data : [];
      setOwners(rows);
      if (rows.length > 0 && !selectedOwner) {
        setSelectedOwner(rows[0]);
      }
    } catch (e) {
      console.error("Owners load failed", e);
      setError("Failed to load owners.");
    } finally {
      setLoading(false);
    }
  }, [selectedOwner]);

// Initial/refresh data loading side-effect.
  React.useEffect(() => {
    loadOwners();
  }, [loadOwners]);

  React.useEffect(() => {
    let cancelled = false;
    async function loadOwnerPets() {
      if (!selectedOwner?.id) {
        setOwnerPets([]);
        return;
      }
      try {
        const res = await api.get(`/owners/${selectedOwner.id}/pets`);
        if (cancelled) return;
        setOwnerPets(Array.isArray(res.data) ? res.data : []);
      } catch {
        if (cancelled) return;
        setOwnerPets([]);
      }
    }
    loadOwnerPets();
    return () => {
      cancelled = true;
    };
  }, [selectedOwner?.id]);

  const filteredOwners = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return owners;
    return owners.filter((o) =>
      [o.full_name, o.email, o.phone, o.address, o.clinic_name]
        .some((v) => String(v || "").toLowerCase().includes(q))
    );
  }, [owners, search]);

// Render UI layout and interactions.
  return (
    <Stack spacing={2}>
      <Typography variant="h5" fontWeight={800}>Owners</Typography>
      <Typography sx={{ opacity: 0.8 }}>
        Track owner profile details, recent adoptions, clinic activity, and recent vet notes.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <TextField
          fullWidth
          size="small"
          label="Search owners"
          placeholder="Name, email, phone, address, clinic..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </Paper>

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 2, minHeight: 500 }}>
            <Typography variant="h6" fontWeight={700}>Owner List</Typography>
            <Divider sx={{ my: 1.25 }} />
            {loading ? (
              <Typography>Loading owners...</Typography>
            ) : filteredOwners.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No matching owners.</Typography>
            ) : (
              <List dense>
                {filteredOwners.map((o) => (
                  <ListItem
                    key={o.id}
                    disableGutters
                    sx={{
                      cursor: "pointer",
                      borderRadius: 1,
                      px: 1,
                      backgroundColor: selectedOwner?.id === o.id ? "rgba(25,118,210,0.08)" : "transparent",
                    }}
                    onClick={() => setSelectedOwner(o)}
                  >
                    <ListItemText
                      primary={o.full_name || o.email || o.id}
                      secondary={`${o.email || "-"} | Visits(12m): ${o.visits_last_12m ?? 0} | New pets(90d): ${o.new_pets_last_90d ?? 0}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 2, minHeight: 500 }}>
            <Typography variant="h6" fontWeight={700}>Owner Details</Typography>
            <Divider sx={{ my: 1.25 }} />
            {!selectedOwner ? (
              <Typography sx={{ opacity: 0.75 }}>Select an owner.</Typography>
            ) : (
              <Stack spacing={1.1}>
                <Typography><strong>Name:</strong> {selectedOwner.full_name || "-"}</Typography>
                <Typography><strong>Email:</strong> {selectedOwner.email || "-"}</Typography>
                <Typography><strong>Phone:</strong> {selectedOwner.phone || "-"}</Typography>
                <Typography><strong>Address:</strong> {selectedOwner.address || "-"}</Typography>
                <Typography><strong>Clinic:</strong> {selectedOwner.clinic_name || "-"}</Typography>
                <Typography><strong>Recent visit:</strong> {formatDateTime(selectedOwner.recent_visit_at)}</Typography>
                <Typography><strong>Recent reason:</strong> {selectedOwner.recent_visit_reason || "-"}</Typography>
                <Typography><strong>Recent notes:</strong> {selectedOwner.recent_visit_notes || "-"}</Typography>
                <Typography><strong>Visits in year:</strong> {selectedOwner.visits_last_12m ?? 0}</Typography>
                <Typography><strong>New pets in 90d:</strong> {selectedOwner.new_pets_last_90d ?? 0}</Typography>

                <Box sx={{ pt: 1 }}>
                  <Typography variant="subtitle1" fontWeight={700}>Pets linked to owner</Typography>
                  {(ownerPets || []).length === 0 ? (
                    <Typography sx={{ opacity: 0.75 }}>No pets linked.</Typography>
                  ) : (
                    <List dense>
                      {ownerPets.map((p) => (
                        <ListItem key={p.id} disableGutters>
                          <ListItemText
                            primary={`${p.name || "Unnamed"} (${p.species || "-"})`}
                            secondary={`Breed: ${p.breed || "-"} | Sex: ${p.sex || "-"} | Microchip: ${p.microchip_number || "-"}`}
                          />
                        </ListItem>
                      ))}
                    </List>
                  )}
                </Box>
              </Stack>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
}

