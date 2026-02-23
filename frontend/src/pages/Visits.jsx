/* Module: Visits. */

import React from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
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
import { ResponsiveLine } from "@nivo/line";

import { api } from "../api/client.js";

function monthBounds(monthValue) {
  if (!monthValue) return { start: "", end: "" };
  const [y, m] = monthValue.split("-").map(Number);
  const start = new Date(y, m - 1, 1);
  const end = new Date(y, m, 0);
  const fmt = (d) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleString();
}

// Primary component for this view/module.
export default function Visits() {
  const today = new Date();
  const defaultMonth = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}`;
  const defaultDay = `${defaultMonth}-${String(today.getDate()).padStart(2, "0")}`;

// Local UI/data state for this page.
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [month, setMonth] = React.useState(defaultMonth);
  const [selectedDay, setSelectedDay] = React.useState(defaultDay);

  const [visits, setVisits] = React.useState([]);
  const [calendar, setCalendar] = React.useState([]);
  const [pets, setPets] = React.useState([]);
  const [clinics, setClinics] = React.useState([]);

  const [createOpen, setCreateOpen] = React.useState(false);
  const [saving, setSaving] = React.useState(false);
  const [createForm, setCreateForm] = React.useState({
    pet_id: "",
    organisation_id: "",
    visit_datetime: "",
    reason: "",
    notes_visible_to_owner: "",
  });

  const [profilePetId, setProfilePetId] = React.useState("");
  const [profile, setProfile] = React.useState(null);

  const loadData = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const { start, end } = monthBounds(month);
      const [visitRes, calendarRes, petsRes, clinicsRes] = await Promise.all([
        api.get("/visits", { params: { limit: 1000, start_date: start, end_date: end } }),
        api.get("/visits/calendar-summary", { params: { month } }),
        api.get("/pets", { params: { limit: 1000 } }),
        api.get("/clinics", { params: { limit: 200 } }),
      ]);

      setVisits(Array.isArray(visitRes.data) ? visitRes.data : []);
      setCalendar(Array.isArray(calendarRes.data) ? calendarRes.data : []);
      const petsRows = Array.isArray(petsRes.data) ? petsRes.data : [];
      setPets(petsRows);
      setClinics(Array.isArray(clinicsRes.data) ? clinicsRes.data : []);

      if (!createForm.pet_id && petsRows.length > 0) {
        setCreateForm((f) => ({ ...f, pet_id: petsRows[0].id }));
      }
    } catch (e) {
      console.error("Visits page load failed", e);
      setError("Failed to load visits page data.");
    } finally {
      setLoading(false);
    }
  }, [month, createForm.pet_id]);

// Initial/refresh data loading side-effect.
  React.useEffect(() => {
    loadData();
  }, [loadData]);

  const dayVisits = React.useMemo(() => {
    if (!selectedDay) return [];
    return visits.filter((v) => String(v.visit_datetime || "").slice(0, 10) === selectedDay);
  }, [visits, selectedDay]);

  const calendarRows = React.useMemo(
    () =>
      calendar.map((r) => ({
        day: r.day,
        label: new Date(r.day).toLocaleDateString(),
        total: r.total_visits ?? 0,
        cancelled: r.cancelled_or_missed ?? 0,
      })),
    [calendar]
  );

  async function createVisit(e) {
    e.preventDefault();
    setSaving(true);
    try {
      await api.post("/visits", createForm);
      setCreateOpen(false);
      setCreateForm((f) => ({ ...f, visit_datetime: "", reason: "", notes_visible_to_owner: "" }));
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to create visit.");
    } finally {
      setSaving(false);
    }
  }

  async function cancelVisit(visitId) {
    try {
      await api.patch(`/visits/${visitId}/cancel`, { reason: "Cancelled by clinic team" });
      await loadData();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to cancel visit.");
    }
  }

  async function openPetProfile(petId) {
    setProfilePetId(petId);
    try {
      const [petRes, weightsRes, vaxRes, medsRes] = await Promise.all([
        api.get(`/pets/${petId}`),
        api.get(`/pets/${petId}/weights`, { params: { limit: 100 } }),
        api.get(`/pets/${petId}/vaccinations`, { params: { limit: 20 } }),
        api.get(`/pets/${petId}/medications`),
      ]);
      setProfile({
        pet: petRes.data,
        weights: Array.isArray(weightsRes.data) ? weightsRes.data : [],
        vaccinations: Array.isArray(vaxRes.data) ? vaxRes.data : [],
        medications: Array.isArray(medsRes.data) ? medsRes.data : [],
      });
    } catch (e) {
      console.error("Pet profile load failed", e);
      setError("Failed to load selected pet profile.");
    }
  }

  const weightSeries = React.useMemo(() => {
    const rows = [...(profile?.weights || [])].sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at));
    return [{ id: "Weight (kg)", data: rows.map((r) => ({ x: String(r.measured_at).slice(0, 10), y: Number(r.weight_kg || 0) })) }];
  }, [profile]);

// Render UI layout and interactions.
  return (
    <Stack spacing={2}>
      <Typography variant="h5" fontWeight={800}>Visits</Typography>
      <Typography sx={{ opacity: 0.8 }}>
        Create, track, and cancel appointments with monthly and daily clinic visibility.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={1.5} alignItems="center">
          <TextField label="Month" type="month" value={month} onChange={(e) => setMonth(e.target.value)} InputLabelProps={{ shrink: true }} />
          <TextField label="Day" type="date" value={selectedDay} onChange={(e) => setSelectedDay(e.target.value)} InputLabelProps={{ shrink: true }} />
          <Button variant="contained" onClick={() => setCreateOpen(true)}>Create Appointment</Button>
          {loading && <Typography variant="body2">Loading...</Typography>}
        </Stack>
      </Paper>

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 5 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Monthly Calendar Overview</Typography>
            <Divider sx={{ my: 1.25 }} />
            {calendarRows.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No visits for selected month.</Typography>
            ) : (
              <List dense>
                {calendarRows.map((r) => (
                  <ListItem key={r.day} disableGutters secondaryAction={<Button size="small" onClick={() => setSelectedDay(r.day)}>View Day</Button>}>
                    <ListItemText primary={r.label} secondary={`Visits: ${r.total} | Cancelled/Missed: ${r.cancelled}`} />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 7 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Appointments for {selectedDay || "selected day"}</Typography>
            <Divider sx={{ my: 1.25 }} />
            {dayVisits.length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No appointments for this day.</Typography>
            ) : (
              <List dense>
                {dayVisits.map((v) => (
                  <ListItem
                    key={v.id}
                    disableGutters
                    alignItems="flex-start"
                    sx={{ py: 0.75 }}
                    secondaryAction={
                      <Stack direction="row" spacing={1} sx={{ top: 12 }}>
                        <Button size="small" onClick={() => openPetProfile(v.pet_id)}>Pet Profile</Button>
                        <Button size="small" color="error" onClick={() => cancelVisit(v.id)}>Cancel</Button>
                      </Stack>
                    }
                  >
                    <ListItemText
                      sx={{ pr: 24 }}
                      primary={`${v.pet_name || "Unknown pet"} - ${v.reason || "General check"}`}
                      secondary={`${formatDateTime(v.visit_datetime)} | Clinic: ${v.clinic_name || "-"} | Owner: ${v.owner_full_name || "-"} (${v.owner_email || "-"})`}
                      slotProps={{
                        secondary: {
                          sx: {
                            whiteSpace: "normal",
                            wordBreak: "break-word",
                          },
                        },
                      }}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Dialog open={createOpen} onClose={() => setCreateOpen(false)} maxWidth="sm" fullWidth>
        <DialogTitle>Create Appointment</DialogTitle>
        <Box component="form" onSubmit={createVisit}>
          <DialogContent sx={{ display: "grid", gap: 2 }}>
            <TextField select label="Pet" value={createForm.pet_id} onChange={(e) => setCreateForm((f) => ({ ...f, pet_id: e.target.value }))} required>
              {pets.map((p) => (
                <MenuItem key={p.id} value={p.id}>{p.name} ({p.species})</MenuItem>
              ))}
            </TextField>
            <TextField select label="Clinic" value={createForm.organisation_id} onChange={(e) => setCreateForm((f) => ({ ...f, organisation_id: e.target.value }))}>
              <MenuItem value="">Unassigned</MenuItem>
              {clinics.map((c) => (
                <MenuItem key={c.id} value={c.id}>{c.name}</MenuItem>
              ))}
            </TextField>
            <TextField
              label="Appointment Date/Time"
              type="datetime-local"
              value={createForm.visit_datetime}
              onChange={(e) => setCreateForm((f) => ({ ...f, visit_datetime: e.target.value }))}
              InputLabelProps={{ shrink: true }}
              required
            />
            <TextField label="Reason" value={createForm.reason} onChange={(e) => setCreateForm((f) => ({ ...f, reason: e.target.value }))} required />
            <TextField
              label="Clinic requirements / notes"
              multiline
              minRows={3}
              value={createForm.notes_visible_to_owner}
              onChange={(e) => setCreateForm((f) => ({ ...f, notes_visible_to_owner: e.target.value }))}
            />
          </DialogContent>
          <DialogActions>
            <Button onClick={() => setCreateOpen(false)} disabled={saving}>Close</Button>
            <Button type="submit" variant="contained" disabled={saving}>{saving ? "Saving..." : "Create"}</Button>
          </DialogActions>
        </Box>
      </Dialog>

      <Dialog open={Boolean(profilePetId)} onClose={() => { setProfilePetId(""); setProfile(null); }} maxWidth="md" fullWidth>
        <DialogTitle>Pet Profile</DialogTitle>
        <DialogContent>
          {!profile ? (
            <Typography>Loading profile...</Typography>
          ) : (
            <Stack spacing={2}>
              <Typography variant="h6" fontWeight={700}>
                {profile.pet?.name || "Pet"} ({profile.pet?.species || "-"})
              </Typography>
              <Typography>
                Breed: {profile.pet?.breed || "-"} | Sex: {profile.pet?.sex || "-"} | Microchip: {profile.pet?.microchip_number || "-"}
              </Typography>
              <Typography>DOB: {profile.pet?.date_of_birth || "-"}</Typography>
              <Box sx={{ height: 260 }}>
                {weightSeries[0]?.data?.length ? (
                  <ResponsiveLine
                    data={weightSeries}
                    margin={{ top: 20, right: 20, bottom: 50, left: 55 }}
                    xScale={{ type: "point" }}
                    yScale={{ type: "linear", stacked: false }}
                    axisBottom={{ tickRotation: -25, legend: "Date", legendOffset: 40, legendPosition: "middle" }}
                    axisLeft={{ legend: "kg", legendOffset: -40, legendPosition: "middle" }}
                    useMesh
                    enablePoints
                    colors={{ scheme: "set2" }}
                  />
                ) : (
                  <Typography sx={{ opacity: 0.75 }}>No weight trend available.</Typography>
                )}
              </Box>
              <Typography variant="subtitle1" fontWeight={700}>Recent Vaccinations</Typography>
              <List dense>
                {(profile.vaccinations || []).slice(0, 5).map((v) => (
                  <ListItem key={v.id} disableGutters>
                    <ListItemText primary={v.vaccine_type || "Vaccine"} secondary={`Administered: ${String(v.administered_at || "-").slice(0, 10)} | Due: ${String(v.due_at || "-").slice(0, 10)}`} />
                  </ListItem>
                ))}
              </List>
              <Typography variant="subtitle1" fontWeight={700}>Current Medications</Typography>
              <List dense>
                {(profile.medications || []).slice(0, 5).map((m) => (
                  <ListItem key={m.id} disableGutters>
                    <ListItemText primary={m.name || "Medication"} secondary={`${m.dosage || "-"} | ${m.instructions || "-"}`} />
                  </ListItem>
                ))}
              </List>
            </Stack>
          )}
        </DialogContent>
        <DialogActions>
          <Button onClick={() => { setProfilePetId(""); setProfile(null); }}>Close</Button>
        </DialogActions>
      </Dialog>
    </Stack>
  );
}

