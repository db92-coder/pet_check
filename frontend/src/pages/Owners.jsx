/* Module: Owners. */

import React from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

// Primary component for this view/module.
export default function Owners() {
  const { user } = useAuth();

  // Local UI/data state for this page.
  const [loading, setLoading] = React.useState(true);
  const [contextLoading, setContextLoading] = React.useState(false);
  const [error, setError] = React.useState("");
  const [search, setSearch] = React.useState("");
  const [owners, setOwners] = React.useState([]);
  const [selectedOwner, setSelectedOwner] = React.useState(null);
  const [ownerPets, setOwnerPets] = React.useState([]);
  const [ownerNotes, setOwnerNotes] = React.useState([]);
  const [ownerConcerns, setOwnerConcerns] = React.useState([]);
  const [noteForm, setNoteForm] = React.useState({
    pet_id: "",
    note_type: "FOLLOWUP",
    note_text: "",
  });
  const [concernForm, setConcernForm] = React.useState({
    pet_id: "",
    severity: "MEDIUM",
    category: "WELFARE",
    description: "",
  });
  const [savingNote, setSavingNote] = React.useState(false);
  const [savingConcern, setSavingConcern] = React.useState(false);

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

  const loadOwnerContext = React.useCallback(async (ownerId) => {
    if (!ownerId) {
      setOwnerPets([]);
      setOwnerNotes([]);
      setOwnerConcerns([]);
      return;
    }
    setContextLoading(true);
    try {
      const [petsRes, notesRes, concernsRes] = await Promise.all([
        api.get(`/owners/${ownerId}/pets`),
        api.get(`/owners/${ownerId}/notes`, { params: { limit: 100 } }),
        api.get(`/owners/${ownerId}/concerns`, { params: { status: "ALL", limit: 100 } }),
      ]);
      setOwnerPets(Array.isArray(petsRes.data) ? petsRes.data : []);
      setOwnerNotes(Array.isArray(notesRes.data) ? notesRes.data : []);
      setOwnerConcerns(Array.isArray(concernsRes.data) ? concernsRes.data : []);
    } catch (e) {
      console.error("Owner context load failed", e);
      setOwnerPets([]);
      setOwnerNotes([]);
      setOwnerConcerns([]);
      setError("Failed to load owner detail context.");
    } finally {
      setContextLoading(false);
    }
  }, []);

  // Initial/refresh data loading side-effect.
  React.useEffect(() => {
    loadOwners();
  }, [loadOwners]);

  React.useEffect(() => {
    loadOwnerContext(selectedOwner?.id || null);
  }, [selectedOwner?.id, loadOwnerContext]);

  const filteredOwners = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return owners;
    return owners.filter((o) =>
      [o.full_name, o.email, o.phone, o.address, o.clinic_name]
        .some((v) => String(v || "").toLowerCase().includes(q))
    );
  }, [owners, search]);

  async function createNote(e) {
    e.preventDefault();
    if (!selectedOwner?.id || !noteForm.note_text.trim()) return;
    setSavingNote(true);
    setError("");
    try {
      await api.post(`/owners/${selectedOwner.id}/notes`, {
        pet_id: noteForm.pet_id || null,
        author_user_id: user?.user_id || null,
        note_type: noteForm.note_type,
        note_text: noteForm.note_text.trim(),
      });
      setNoteForm((prev) => ({ ...prev, note_text: "" }));
      await loadOwnerContext(selectedOwner.id);
      await loadOwners();
    } catch (e1) {
      const detail = e1?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to add note.");
    } finally {
      setSavingNote(false);
    }
  }

  async function deleteNote(noteId) {
    if (!selectedOwner?.id || !noteId) return;
    setError("");
    try {
      await api.delete(`/owners/${selectedOwner.id}/notes/${noteId}`);
      await loadOwnerContext(selectedOwner.id);
      await loadOwners();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to delete note.");
    }
  }

  async function createConcern(e) {
    e.preventDefault();
    if (!selectedOwner?.id || !concernForm.description.trim()) return;
    setSavingConcern(true);
    setError("");
    try {
      await api.post(`/owners/${selectedOwner.id}/concerns`, {
        pet_id: concernForm.pet_id || null,
        raised_by_user_id: user?.user_id || null,
        severity: concernForm.severity,
        category: concernForm.category,
        description: concernForm.description.trim(),
      });
      setConcernForm((prev) => ({ ...prev, description: "" }));
      await loadOwnerContext(selectedOwner.id);
      await loadOwners();
    } catch (e1) {
      const detail = e1?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to add concern.");
    } finally {
      setSavingConcern(false);
    }
  }

  async function resolveConcern(flagId) {
    if (!selectedOwner?.id || !flagId) return;
    setError("");
    try {
      await api.patch(`/owners/${selectedOwner.id}/concerns/${flagId}`, {
        status: "RESOLVED",
        resolution_notes: "Resolved after owner follow-up and care-plan confirmation.",
        resolved_by_user_id: user?.user_id || null,
      });
      await loadOwnerContext(selectedOwner.id);
      await loadOwners();
    } catch (e) {
      const detail = e?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to resolve concern.");
    }
  }

  // Render UI layout and interactions.
  return (
    <Stack spacing={2}>
      <Typography variant="h5" fontWeight={800}>Owners</Typography>
      <Typography sx={{ opacity: 0.8 }}>
        Manage owner records, pets, clinical notes, and concern flags.
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
        <Grid size={{ xs: 12, md: 4 }}>
          <Paper sx={{ p: 2, minHeight: 520 }}>
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
                      mb: 0.25,
                      backgroundColor: selectedOwner?.id === o.id ? "rgba(25,118,210,0.08)" : "transparent",
                    }}
                    onClick={() => setSelectedOwner(o)}
                  >
                    <ListItemText
                      primary={o.full_name || o.email || o.id}
                      secondary={`${o.email || "-"} | Open concerns: ${o.open_concern_count ?? 0}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 8 }}>
          <Paper sx={{ p: 2 }}>
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
                <Typography><strong>Recent clinical note:</strong> {selectedOwner.recent_clinical_note || "-"}</Typography>
                <Typography><strong>Visits in year:</strong> {selectedOwner.visits_last_12m ?? 0}</Typography>

                <Box sx={{ pt: 1 }}>
                  <Typography variant="subtitle1" fontWeight={700}>Pets linked to owner</Typography>
                  {contextLoading ? (
                    <Typography sx={{ opacity: 0.75 }}>Loading owner details...</Typography>
                  ) : ownerPets.length === 0 ? (
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

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, lg: 7 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Clinical Notes</Typography>
            <Divider sx={{ my: 1.25 }} />

            <Box component="form" onSubmit={createNote} sx={{ display: "grid", gap: 1.25, mb: 2 }}>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                <TextField
                  select
                  size="small"
                  label="Pet"
                  value={noteForm.pet_id}
                  onChange={(e) => setNoteForm((prev) => ({ ...prev, pet_id: e.target.value }))}
                  sx={{ minWidth: 220 }}
                >
                  <MenuItem value="">Owner-level note</MenuItem>
                  {ownerPets.map((pet) => (
                    <MenuItem key={pet.id} value={pet.id}>{pet.name} ({pet.species})</MenuItem>
                  ))}
                </TextField>
                <TextField
                  select
                  size="small"
                  label="Type"
                  value={noteForm.note_type}
                  onChange={(e) => setNoteForm((prev) => ({ ...prev, note_type: e.target.value }))}
                  sx={{ minWidth: 180 }}
                >
                  <MenuItem value="CHECKUP">CHECKUP</MenuItem>
                  <MenuItem value="FOLLOWUP">FOLLOWUP</MenuItem>
                  <MenuItem value="MEDICATION">MEDICATION</MenuItem>
                  <MenuItem value="WELFARE">WELFARE</MenuItem>
                </TextField>
              </Stack>
              <TextField
                multiline
                minRows={3}
                label="Note text"
                placeholder="Example: BCS 6/9, otitis externa resolving, continue topical medication and review in 14 days."
                value={noteForm.note_text}
                onChange={(e) => setNoteForm((prev) => ({ ...prev, note_text: e.target.value }))}
              />
              <Stack direction="row" justifyContent="flex-end">
                <Button type="submit" variant="contained" disabled={savingNote || !selectedOwner}>
                  {savingNote ? "Saving..." : "Add Note"}
                </Button>
              </Stack>
            </Box>

            {ownerNotes.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No notes recorded.</Typography>
            ) : (
              <List dense>
                {ownerNotes.map((n) => (
                  <ListItem
                    key={n.id}
                    disableGutters
                    secondaryAction={
                      <Button color="error" size="small" onClick={() => deleteNote(n.id)}>
                        Delete
                      </Button>
                    }
                  >
                    <ListItemText
                      primary={`${n.note_type || "NOTE"}${n.pet_name ? ` - ${n.pet_name}` : ""}`}
                      secondary={`${formatDateTime(n.created_at)}${n.author_name ? ` | ${n.author_name}` : ""}\n${n.note_text || "-"}`}
                      secondaryTypographyProps={{ sx: { whiteSpace: "pre-line" } }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, lg: 5 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Concern Flags</Typography>
            <Divider sx={{ my: 1.25 }} />

            <Box component="form" onSubmit={createConcern} sx={{ display: "grid", gap: 1.25, mb: 2 }}>
              <TextField
                select
                size="small"
                label="Pet"
                value={concernForm.pet_id}
                onChange={(e) => setConcernForm((prev) => ({ ...prev, pet_id: e.target.value }))}
              >
                <MenuItem value="">Owner-level concern</MenuItem>
                {ownerPets.map((pet) => (
                  <MenuItem key={pet.id} value={pet.id}>{pet.name} ({pet.species})</MenuItem>
                ))}
              </TextField>
              <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                <TextField
                  select
                  size="small"
                  label="Severity"
                  value={concernForm.severity}
                  onChange={(e) => setConcernForm((prev) => ({ ...prev, severity: e.target.value }))}
                  fullWidth
                >
                  <MenuItem value="LOW">LOW</MenuItem>
                  <MenuItem value="MEDIUM">MEDIUM</MenuItem>
                  <MenuItem value="HIGH">HIGH</MenuItem>
                </TextField>
                <TextField
                  select
                  size="small"
                  label="Category"
                  value={concernForm.category}
                  onChange={(e) => setConcernForm((prev) => ({ ...prev, category: e.target.value }))}
                  fullWidth
                >
                  <MenuItem value="WELFARE">WELFARE</MenuItem>
                  <MenuItem value="FOLLOW_UP">FOLLOW_UP</MenuItem>
                  <MenuItem value="MEDICATION">MEDICATION</MenuItem>
                  <MenuItem value="COMPLIANCE">COMPLIANCE</MenuItem>
                </TextField>
              </Stack>
              <TextField
                multiline
                minRows={3}
                label="Concern"
                value={concernForm.description}
                onChange={(e) => setConcernForm((prev) => ({ ...prev, description: e.target.value }))}
              />
              <Stack direction="row" justifyContent="flex-end">
                <Button type="submit" variant="contained" color="warning" disabled={savingConcern || !selectedOwner}>
                  {savingConcern ? "Saving..." : "Raise Concern"}
                </Button>
              </Stack>
            </Box>

            {ownerConcerns.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No concerns raised.</Typography>
            ) : (
              <List dense>
                {ownerConcerns.map((c) => (
                  <ListItem
                    key={c.id}
                    disableGutters
                    secondaryAction={
                      c.status === "OPEN" || c.status === "UNDER_REVIEW" ? (
                        <Button size="small" onClick={() => resolveConcern(c.id)}>
                          Resolve
                        </Button>
                      ) : null
                    }
                  >
                    <ListItemText
                      primary={
                        <Stack direction="row" spacing={1} alignItems="center">
                          <Typography variant="body2" fontWeight={700}>
                            {c.category || "CONCERN"}{c.pet_name ? ` - ${c.pet_name}` : ""}
                          </Typography>
                          <Chip size="small" label={c.severity || "MEDIUM"} color={c.severity === "HIGH" ? "error" : "warning"} />
                          <Chip size="small" label={c.status || "OPEN"} variant="outlined" />
                        </Stack>
                      }
                      secondary={`${formatDateTime(c.created_at)}\n${c.description || "-"}${c.resolution_notes ? `\nResolution: ${c.resolution_notes}` : ""}`}
                      secondaryTypographyProps={{ sx: { whiteSpace: "pre-line" } }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
}
