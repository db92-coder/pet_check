/* Module: Dashboard. */

import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Avatar,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemAvatar,
  ListItemText,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { ResponsiveLine } from "@nivo/line";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

function formatDateTime(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString();
}

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleDateString();
}

function toIsoDate(value) {
  if (!value) return "";
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return "";
  return d.toISOString().slice(0, 10);
}

const emptyPetForm = {
  name: "",
  species: "",
  breed: "",
  sex: "",
  microchip_number: "",
  date_of_birth: "",
  photo: null,
};

const dashboardPageSx = {
  p: { xs: 1.5, sm: 2.5 },
  borderRadius: 3,
  backgroundColor: "#e9f0f8",
};

const dashboardCardSx = {
  p: 2,
  minHeight: 210,
  borderRadius: 3,
  backgroundColor: "#ffffff",
  border: "1px solid #d9e2ef",
  boxShadow: "0 8px 20px rgba(16, 24, 40, 0.06)",
};

function dashboardSubtitleForRole(role) {
  const roleKey = String(role || "").toUpperCase();
  if (roleKey === "ADMIN") {
    return "Monitor clinic KPIs, operational performance, and unresolved concerns across the network.";
  }
  if (roleKey === "VET") {
    return "Track your clinic's appointments, action items, medication demand, and stock-related alerts.";
  }
  return "Overview of your pets, appointments, and upcoming vaccine due dates.";
}

// Primary component for this view/module.
export default function Dashboard() {
  const { user } = useAuth();

// Local UI/data state for this page.
  const [loading, setLoading] = useState(true);
  const [savingPet, setSavingPet] = useState(false);
  const [error, setError] = useState("");

  const [pets, setPets] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [vaccinationDue, setVaccinationDue] = useState([]);
  const [vaccinations, setVaccinations] = useState([]);
  const [medications, setMedications] = useState([]);
  const [petWeights, setPetWeights] = useState([]);
  const [ownerNotResolved, setOwnerNotResolved] = useState(false);
  const [eligibility, setEligibility] = useState(null);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);
  const [roleKpis, setRoleKpis] = useState(null);
  const [roleKpisLoading, setRoleKpisLoading] = useState(false);
  const [selectedPetId, setSelectedPetId] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [weightDate, setWeightDate] = useState("");
  const [savingWeight, setSavingWeight] = useState(false);
  const [calendarMonth, setCalendarMonth] = useState(new Date().toISOString().slice(0, 7));
  const [selectedCalendarDate, setSelectedCalendarDate] = useState("");
  const [reminders, setReminders] = useState([]);
  const [reminderLoading, setReminderLoading] = useState(false);
  const [savingReminder, setSavingReminder] = useState(false);
  const [reminderPetOptions, setReminderPetOptions] = useState([]);
  const [reminderForm, setReminderForm] = useState({
    title: "",
    details: "",
    due_at: "",
    reminder_type: "REMINDER",
    pet_id: "",
  });

  const [petDialogOpen, setPetDialogOpen] = useState(false);
  const [editingPetId, setEditingPetId] = useState(null);
  const [petForm, setPetForm] = useState(emptyPetForm);

  const loadReminders = useCallback(async () => {
    const role = (user?.role || "").toUpperCase();
    if (!["ADMIN", "VET", "OWNER"].includes(role)) {
      setReminders([]);
      return;
    }
    setReminderLoading(true);
    try {
      const res = await api.get("/dashboard/reminders", {
        params: {
          role,
          user_id: user?.user_id,
          month: calendarMonth,
          limit: 400,
        },
      });
      setReminders(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      console.error("Reminder load failed", err);
      setReminders([]);
    } finally {
      setReminderLoading(false);
    }
  }, [calendarMonth, user?.role, user?.user_id]);

  const loadReminderPetOptions = useCallback(async () => {
    const role = String(user?.role || "").toUpperCase();
    try {
      if (role === "OWNER") {
        // Owners only see their own pets in the reminder link dropdown.
        setReminderPetOptions(
          pets.map((p) => ({
            id: p.id,
            name: p.name,
            species: p.species,
            owner_name: p.owner_full_name,
          }))
        );
        return;
      }
      // Admin/Vet can link reminders to pets across the network for coordination tasks.
      const res = await api.get("/pets", { params: { limit: 500 } });
      const rows = Array.isArray(res.data) ? res.data : [];
      setReminderPetOptions(
        rows.map((p) => ({
          id: p.id,
          name: p.name,
          species: p.species,
          owner_name: p.owner_full_name,
        }))
      );
    } catch (err) {
      console.error("Reminder pet options load failed", err);
      setReminderPetOptions([]);
    }
  }, [pets, user?.role]);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const role = (user?.role || "").toUpperCase();

      if (role === "ADMIN" || role === "VET") {
        setRoleKpisLoading(true);
        const kpiRes = await api.get("/dashboard/kpis", {
          params: {
            role,
            user_id: role === "VET" ? user?.user_id : undefined,
          },
        });
        setRoleKpis(kpiRes?.data || null);
        setPets([]);
        setAppointments([]);
        setVaccinationDue([]);
        setVaccinations([]);
        setMedications([]);
        setPetWeights([]);
        setEligibility(null);
        setOwnerNotResolved(false);
        setRoleKpisLoading(false);
        return;
      }

      const [petsRes, visitsRes] = await Promise.all([
        api.get("/pets", { params: { user_id: user?.user_id, limit: 1000 } }),
        api.get("/visits", { params: { limit: 5000 } }),
      ]);

      const currentPets = Array.isArray(petsRes.data) ? petsRes.data : [];
      const allVisits = Array.isArray(visitsRes.data) ? visitsRes.data : [];

      const resolvedOwnerId = currentPets.length > 0 ? currentPets[0].owner_id : null;
      setOwnerNotResolved(user?.role === "OWNER" && Boolean(user?.user_id) && !resolvedOwnerId);
      setPets(currentPets);
      setRoleKpis(null);
      setEligibility(null);

      if (resolvedOwnerId && (user?.role || "").toUpperCase() === "OWNER") {
        setEligibilityLoading(true);
        try {
          const eligRes = await api.get(`/eligibility/owner/${resolvedOwnerId}`);
          setEligibility(eligRes?.data || null);
        } catch (eligErr) {
          console.error("Eligibility load failed", eligErr);
          setEligibility(null);
        } finally {
          setEligibilityLoading(false);
        }
      } else {
        setEligibilityLoading(false);
      }

      const petIdSet = new Set(currentPets.map((p) => String(p.id)));
      const now = new Date();

      const upcoming = allVisits
        .filter((v) => petIdSet.has(String(v.pet_id)))
        .filter((v) => {
          const dt = new Date(v.visit_datetime);
          return !Number.isNaN(dt.getTime()) && dt >= now;
        })
        .sort((a, b) => new Date(a.visit_datetime) - new Date(b.visit_datetime))
        .slice(0, 12);

      setAppointments(upcoming);

      const vaccinationRows = (
        await Promise.all(
          currentPets.map(async (pet) => {
            try {
              const res = await api.get(`/pets/${pet.id}/vaccinations`, { params: { limit: 200 } });
              const rows = Array.isArray(res.data) ? res.data : [];
              return rows.map((row) => ({ ...row, pet_name: pet.name, pet_id: pet.id }));
            } catch {
              return [];
            }
          })
        )
      ).flat();
      setVaccinations(vaccinationRows);

      const medicationRows = (
        await Promise.all(
          currentPets.map(async (pet) => {
            try {
              const res = await api.get(`/pets/${pet.id}/medications`);
              const rows = Array.isArray(res.data) ? res.data : [];
              return rows.map((row) => ({ ...row, pet_name: pet.name, pet_id: pet.id }));
            } catch {
              return [];
            }
          })
        )
      ).flat();
      setMedications(medicationRows);

      const due = vaccinationRows
        .filter((v) => v.due_at)
        .filter((v) => {
          const dueAt = new Date(v.due_at);
          return !Number.isNaN(dueAt.getTime()) && dueAt >= now;
        })
        .sort((a, b) => new Date(a.due_at) - new Date(b.due_at))
        .slice(0, 20);

      setVaccinationDue(due);
    } catch (e) {
      console.error("Dashboard load failed", e);
      setError("Failed to load dashboard data.");
    } finally {
      setRoleKpisLoading(false);
      setLoading(false);
    }
  }, [user?.role, user?.user_id]);

// Initial/refresh data loading side-effect.
  useEffect(() => {
    let cancelled = false;
    async function run() {
      if (cancelled) return;
      await loadDashboard();
    }
    run();
    return () => {
      cancelled = true;
    };
  }, [loadDashboard]);

  useEffect(() => {
    loadReminders();
  }, [loadReminders]);

  useEffect(() => {
    loadReminderPetOptions();
  }, [loadReminderPetOptions]);

  const personalInfo = useMemo(() => {
    const firstPet = pets[0] || {};
    return {
      email: firstPet.owner_email || user?.email || "-",
      fullName: firstPet.owner_full_name || user?.full_name || "-",
      phone: firstPet.owner_phone || "-",
      role: user?.role || "-",
    };
  }, [pets, user]);

  const petsById = useMemo(() => {
    const map = new Map();
    for (const p of pets) {
      map.set(String(p.id), p);
    }
    return map;
  }, [pets]);

  useEffect(() => {
    if (!pets.length) {
      setSelectedPetId("");
      return;
    }
    if (!selectedPetId || !pets.some((p) => String(p.id) === String(selectedPetId))) {
      setSelectedPetId(String(pets[0].id));
    }
  }, [pets, selectedPetId]);

  useEffect(() => {
    let cancelled = false;
    async function loadWeights() {
      if (!selectedPetId) {
        setPetWeights([]);
        return;
      }
      try {
        const res = await api.get(`/pets/${selectedPetId}/weights`, { params: { limit: 500 } });
        if (cancelled) return;
        setPetWeights(Array.isArray(res.data) ? res.data : []);
      } catch {
        if (cancelled) return;
        setPetWeights([]);
      }
    }
    loadWeights();
    return () => {
      cancelled = true;
    };
  }, [selectedPetId]);

  const weightSeries = useMemo(() => {
    const rows = [...petWeights].sort((a, b) => new Date(a.measured_at) - new Date(b.measured_at));
    return [
      {
        id: "Weight (kg)",
        data: rows.map((r) => ({
          x: formatDate(r.measured_at),
          y: Number(r.weight_kg ?? 0),
        })),
      },
    ];
  }, [petWeights]);

  const hasWeightData = weightSeries[0]?.data?.length > 0;

  async function addWeightRecord(e) {
    e.preventDefault();
    if (!selectedPetId || !weightKg) return;
    setSavingWeight(true);
    try {
      await api.post(`/pets/${selectedPetId}/weights`, {
        weight_kg: Number(weightKg),
        measured_at: weightDate ? `${weightDate}T12:00:00` : undefined,
      });
      setWeightKg("");
      setWeightDate("");
      const res = await api.get(`/pets/${selectedPetId}/weights`, { params: { limit: 500 } });
      setPetWeights(Array.isArray(res.data) ? res.data : []);
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to add weight record.");
    } finally {
      setSavingWeight(false);
    }
  }

  const vaccinationsByPet = useMemo(() => {
    const map = new Map();
    for (const row of vaccinations) {
      const key = String(row.pet_id);
      const list = map.get(key) || [];
      list.push(row);
      map.set(key, list);
    }
    return map;
  }, [vaccinations]);

  const medicationsByPet = useMemo(() => {
    const map = new Map();
    for (const row of medications) {
      const key = String(row.pet_id);
      const list = map.get(key) || [];
      list.push(row);
      map.set(key, list);
    }
    return map;
  }, [medications]);

  const remindersByDate = useMemo(() => {
    const map = new Map();
    for (const reminder of reminders) {
      const key = toIsoDate(reminder.due_at);
      if (!key) continue;
      const list = map.get(key) || [];
      list.push(reminder);
      map.set(key, list);
    }
    return map;
  }, [reminders]);

  const calendarCells = useMemo(() => {
    const [yearStr, monthStr] = String(calendarMonth || "").split("-");
    const year = Number(yearStr);
    const month = Number(monthStr);
    if (!year || !month) return [];
    const first = new Date(year, month - 1, 1);
    const daysInMonth = new Date(year, month, 0).getDate();
    const offset = first.getDay();
    const cells = [];
    for (let i = 0; i < offset; i += 1) {
      cells.push({ empty: true, key: `e-${i}` });
    }
    for (let day = 1; day <= daysInMonth; day += 1) {
      const date = new Date(year, month - 1, day);
      const iso = toIsoDate(date);
      const count = (remindersByDate.get(iso) || []).length;
      cells.push({ empty: false, key: iso, iso, day, count });
    }
    return cells;
  }, [calendarMonth, remindersByDate]);

  const selectedDateReminders = useMemo(() => {
    if (selectedCalendarDate) {
      return [...(remindersByDate.get(selectedCalendarDate) || [])].sort(
        (a, b) => new Date(a.due_at) - new Date(b.due_at)
      );
    }
    return [...reminders].sort((a, b) => new Date(a.due_at) - new Date(b.due_at));
  }, [reminders, remindersByDate, selectedCalendarDate]);

  async function createReminder(e) {
    e.preventDefault();
    if (!reminderForm.title.trim() || !reminderForm.due_at) return;
    setSavingReminder(true);
    try {
      const role = String(user?.role || "OWNER").toUpperCase();
      const ownerId = role === "OWNER" ? pets[0]?.owner_id || null : null;
      await api.post("/dashboard/reminders", {
        role_scope: role,
        user_id: role === "VET" ? user?.user_id : null,
        owner_id: ownerId,
        pet_id: reminderForm.pet_id || null,
        title: reminderForm.title.trim(),
        details: reminderForm.details.trim() || null,
        reminder_type: reminderForm.reminder_type,
        due_at: new Date(reminderForm.due_at).toISOString(),
        created_by_user_id: user?.user_id || null,
      });
      setReminderForm({ title: "", details: "", due_at: "", reminder_type: "REMINDER", pet_id: "" });
      await loadReminders();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to create reminder.");
    } finally {
      setSavingReminder(false);
    }
  }

  async function markReminderDone(reminderId) {
    try {
      await api.patch(`/dashboard/reminders/${reminderId}`, { status: "DONE" });
      await loadReminders();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to update reminder.");
    }
  }

  async function deleteReminder(reminderId) {
    try {
      await api.delete(`/dashboard/reminders/${reminderId}`);
      await loadReminders();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to delete reminder.");
    }
  }

  function openAddPetDialog() {
    setEditingPetId(null);
    setPetForm(emptyPetForm);
    setPetDialogOpen(true);
  }

  function openEditPetDialog(pet) {
    setEditingPetId(pet.id);
    setPetForm({
      name: pet.name || "",
      species: pet.species || "",
      breed: pet.breed || "",
      sex: pet.sex || "",
      microchip_number: pet.microchip_number || "",
      date_of_birth: pet.date_of_birth ? String(pet.date_of_birth).slice(0, 10) : "",
      photo: null,
    });
    setPetDialogOpen(true);
  }

  function closePetDialog() {
    if (savingPet) return;
    setPetDialogOpen(false);
  }

  async function submitPetForm(e) {
    e.preventDefault();
    setSavingPet(true);
    setError("");

    try {
      const fd = new FormData();
      fd.append("name", petForm.name);
      fd.append("species", petForm.species);
      fd.append("breed", petForm.breed || "");
      fd.append("sex", petForm.sex || "");
      fd.append("microchip_number", petForm.microchip_number || "");
      fd.append("date_of_birth", petForm.date_of_birth || "");
      if (petForm.photo) {
        fd.append("photo", petForm.photo);
      }

      if (editingPetId) {
        await api.put(`/pets/${editingPetId}`, fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      } else {
        fd.append("user_id", user.user_id);
        await api.post("/pets", fd, {
          headers: { "Content-Type": "multipart/form-data" },
        });
      }

      setPetDialogOpen(false);
      setPetForm(emptyPetForm);
      await loadDashboard();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to save pet.");
    } finally {
      setSavingPet(false);
    }
  }

// Render UI layout and interactions.
  return (
    <Stack spacing={2} sx={dashboardPageSx}>
      <Box>
        <Typography variant="h4" fontWeight={800}>
          Dashboard
        </Typography>
        <Typography sx={{ opacity: 0.8 }}>
          {dashboardSubtitleForRole(user?.role)}
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}
      {ownerNotResolved && <Alert severity="warning">Owner profile could not be resolved for this login.</Alert>}

      {loading ? (
        <Paper sx={dashboardCardSx}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <CircularProgress size={20} />
            <Typography>Loading dashboard...</Typography>
          </Stack>
        </Paper>
      ) : (
        <>
          {(user?.role || "").toUpperCase() === "ADMIN" && (
            <>
              <Grid container spacing={2} alignItems="flex-start">
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Visits Today</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.visits_today ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Visits This Week</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.visits_week ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Visits This Month</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.visits_month ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Concerns Unfollowed</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.concerns_unfollowed ?? 0}</Typography>
                  </Paper>
                </Grid>
              </Grid>

              <Grid container spacing={2} alignItems="flex-start">
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Clinic Operations</Typography>
                    <Divider sx={{ my: 1.5 }} />
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip label={`Clinics: ${roleKpis?.summary?.clinic_count ?? 0}`} color="primary" />
                      <Chip label={`Staff registered: ${roleKpis?.summary?.staff_registered ?? 0}`} color="secondary" />
                      <Chip label={`Missed appts (month): ${roleKpis?.summary?.missed_appointments_month ?? 0}`} color="warning" />
                      <Chip label={`Injury visits (month): ${roleKpis?.summary?.injury_related_visits_month ?? 0}`} color="error" />
                    </Stack>
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Top Clinics By Visits</Typography>
                    <Divider sx={{ my: 1.5 }} />
                    {roleKpisLoading ? (
                      <Typography sx={{ opacity: 0.75 }}>Loading KPI data...</Typography>
                    ) : (roleKpis?.visits_by_clinic || []).length === 0 ? (
                      <Typography sx={{ opacity: 0.75 }}>No clinic visit data.</Typography>
                    ) : (
                      <List dense>
                        {(roleKpis?.visits_by_clinic || []).map((r) => (
                          <ListItem key={r.organisation_id} disableGutters>
                            <ListItemText primary={r.clinic_name || "Unknown clinic"} secondary={`Visits: ${r.visits ?? 0}`} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Paper>
                </Grid>
              </Grid>
            </>
          )}

          {(user?.role || "").toUpperCase() === "VET" && (
            <>
              <Grid container spacing={2} alignItems="flex-start">
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Appointments Today</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.appointments_today ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>This Week</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.appointments_week ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Concerns To Action</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.concerns_to_action ?? 0}</Typography>
                  </Paper>
                </Grid>
                <Grid size={{ xs: 12, md: 6, lg: 3 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Stock Low Alerts</Typography>
                    <Typography variant="h3" fontWeight={800}>{roleKpis?.summary?.stock_low_alerts ?? 0}</Typography>
                  </Paper>
                </Grid>
              </Grid>

              <Grid container spacing={2} alignItems="flex-start">
                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Action Queue</Typography>
                    <Divider sx={{ my: 1.5 }} />
                    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                      <Chip label={`Cancellations (month): ${roleKpis?.summary?.cancellations_month ?? 0}`} color="warning" />
                      <Chip label={`Injury cases (month): ${roleKpis?.summary?.injury_cases_month ?? 0}`} color="error" />
                      <Chip label={`Medications due review: ${roleKpis?.summary?.medications_due_review ?? 0}`} color="secondary" />
                    </Stack>
                    <Divider sx={{ my: 1.5 }} />
                    <Typography variant="body2" sx={{ opacity: 0.8, mb: 0.75 }}>
                      Linked clinics
                    </Typography>
                    {(roleKpis?.clinics || []).length === 0 ? (
                      <Typography sx={{ opacity: 0.75 }}>No clinic membership found for this vet account.</Typography>
                    ) : (
                      <List dense>
                        {(roleKpis?.clinics || []).map((clinic) => (
                          <ListItem key={clinic.organisation_id} disableGutters>
                            <ListItemText primary={clinic.clinic_name || "Unknown clinic"} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Paper>
                </Grid>

                <Grid size={{ xs: 12, md: 6 }}>
                  <Paper sx={dashboardCardSx}>
                    <Typography variant="h6" fontWeight={700}>Medication Demand (30d)</Typography>
                    <Divider sx={{ my: 1.5 }} />
                    {roleKpisLoading ? (
                      <Typography sx={{ opacity: 0.75 }}>Loading KPI data...</Typography>
                    ) : (roleKpis?.medication_demand || []).length === 0 ? (
                      <Typography sx={{ opacity: 0.75 }}>No medication demand records.</Typography>
                    ) : (
                      <List dense>
                        {(roleKpis?.medication_demand || []).map((row) => (
                          <ListItem key={row.medication_name} disableGutters>
                            <ListItemText primary={row.medication_name || "Unknown"} secondary={`Prescribed (30d): ${row.prescribed_count_30d ?? 0}`} />
                          </ListItem>
                        ))}
                      </List>
                    )}
                  </Paper>
                </Grid>
              </Grid>
            </>
          )}

          {(user?.role || "").toUpperCase() === "OWNER" && (
          <Grid container spacing={2} alignItems="flex-start">
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper sx={dashboardCardSx}>
                <Typography variant="h6" fontWeight={700}>Personal Information</Typography>
                <Divider sx={{ my: 1.5 }} />
                <Stack spacing={1}>
                  <Typography><strong>Name:</strong> {personalInfo.fullName}</Typography>
                  <Typography><strong>Email:</strong> {personalInfo.email}</Typography>
                  <Typography><strong>Phone:</strong> {personalInfo.phone}</Typography>
                  <Typography><strong>Role:</strong> {personalInfo.role}</Typography>
                </Stack>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, md: 6 }}>
              <Paper sx={dashboardCardSx}>
                <Typography variant="h6" fontWeight={700}>Summary</Typography>
                <Divider sx={{ my: 1.5 }} />
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip label={`Current pets: ${pets.length}`} color="primary" />
                  <Chip label={`Upcoming appointments: ${appointments.length}`} color="secondary" />
                  <Chip label={`Vaccines due: ${vaccinationDue.length}`} color="warning" />
                  {(user?.role || "").toUpperCase() === "OWNER" && eligibilityLoading && (
                    <Chip label="Eligibility: loading..." variant="outlined" />
                  )}
                  {(user?.role || "").toUpperCase() === "OWNER" && eligibility && (
                    <>
                      <Chip label={`Eligibility score: ${Number(eligibility.overall_eligibility_score || 0).toFixed(2)}`} color="success" />
                      <Chip
                        label={`Risk: ${eligibility.risk_level || "-"}`}
                        color={
                          eligibility.risk_level === "HIGH"
                            ? "error"
                            : eligibility.risk_level === "MEDIUM"
                              ? "warning"
                              : "success"
                        }
                        variant="outlined"
                      />
                      <Chip label={`Vet score: ${Number(eligibility.vet_score || 0).toFixed(2)}`} variant="outlined" />
                      <Chip label={`Govt score: ${Number(eligibility.gov_score || 0).toFixed(2)}`} variant="outlined" />
                    </>
                  )}
                </Stack>
                {(user?.role || "").toUpperCase() === "OWNER" && eligibility && (
                  <Typography sx={{ mt: 1.5, opacity: 0.8 }}>
                    Estimated annual minimum care cost: ${Number(eligibility.annual_required_cost_min || 0).toLocaleString()}
                  </Typography>
                )}
              </Paper>
            </Grid>
          </Grid>
          )}

          {(user?.role || "").toUpperCase() === "OWNER" && (
          <Grid container spacing={2} alignItems="flex-start">
            <Grid size={{ xs: 12, md: 6, lg: 6 }}>
              <Paper sx={dashboardCardSx}>
                <Stack direction="row" justifyContent="space-between" alignItems="center">
                  <Typography variant="h6" fontWeight={700}>Current Pets</Typography>
                  {user?.role === "OWNER" && (
                    <Button variant="contained" size="small" onClick={openAddPetDialog}>Add Pet</Button>
                  )}
                </Stack>
                <Divider sx={{ my: 1.5 }} />
                {pets.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>No pets found.</Typography>
                ) : (
                  <List dense>
                    {pets.map((pet) => {
                      const photoSrc = pet.has_photo ? `${api.defaults.baseURL}/pets/${pet.id}/photo` : null;
                      const petVaccinations = vaccinationsByPet.get(String(pet.id)) || [];
                      const petMedications = medicationsByPet.get(String(pet.id)) || [];
                      const vaccineSummary = petVaccinations.length
                        ? petVaccinations
                            .slice(0, 3)
                            .map((v) => v.vaccine_type || "Vaccine")
                            .join(", ")
                        : "None recorded";
                      const medicationSummary = petMedications.length
                        ? petMedications
                            .slice(0, 3)
                            .map((m) => m.name || "Medication")
                            .join(", ")
                        : "None prescribed";
                      return (
                        <ListItem key={pet.id} disableGutters secondaryAction={
                          user?.role === "OWNER" ? (
                            <Button size="small" onClick={() => openEditPetDialog(pet)}>Edit</Button>
                          ) : null
                        }>
                          <ListItemAvatar>
                            <Avatar src={photoSrc || undefined} alt={pet.name || "Pet"} />
                          </ListItemAvatar>
                          <ListItemText
                            primary={`${pet.name || "Unnamed"} (${pet.species || "Unknown"})`}
                            secondary={
                              `Breed: ${pet.breed || "-"} | Sex: ${pet.sex || "-"} | DOB: ${formatDate(pet.date_of_birth)} | Microchip: ${pet.microchip_number || "Not recorded"}\n` +
                              `Vaccinations: ${vaccineSummary}\n` +
                              `Medications: ${medicationSummary}`
                            }
                            secondaryTypographyProps={{ sx: { whiteSpace: "pre-line" } }}
                          />
                        </ListItem>
                      );
                    })}
                  </List>
                )}
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, md: 6, lg: 6 }}>
              <Paper sx={{ ...dashboardCardSx, mb: 2 }}>
                <Typography variant="h6" fontWeight={700}>Upcoming Appointments</Typography>
                <Divider sx={{ my: 1.5 }} />
                {appointments.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>No upcoming appointments.</Typography>
                ) : (
                  <List dense>
                    {appointments.map((v) => {
                      const pet = petsById.get(String(v.pet_id));
                      return (
                        <ListItem key={v.id} disableGutters>
                          <ListItemText
                            primary={`${pet?.name || "Unknown pet"} - ${v.reason || "General check"}`}
                            secondary={formatDateTime(v.visit_datetime)}
                          />
                        </ListItem>
                      );
                    })}
                  </List>
                )}
              </Paper>

              <Paper sx={dashboardCardSx}>
                <Typography variant="h6" fontWeight={700}>Vaccination Due Dates</Typography>
                <Divider sx={{ my: 1.5 }} />
                {vaccinationDue.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>No upcoming vaccine due dates.</Typography>
                ) : (
                  <List dense>
                    {vaccinationDue.map((v) => (
                      <ListItem key={`${v.id}-${v.due_at}`} disableGutters>
                        <ListItemText
                          primary={`${v.pet_name || "Unknown pet"} - ${v.vaccine_type || "Vaccine"}`}
                          secondary={`Due: ${formatDate(v.due_at)}${v.administered_at ? ` | Last administered: ${formatDate(v.administered_at)}` : ""}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>

              <Paper sx={{ ...dashboardCardSx, mt: 2 }}>
                <Typography variant="h6" fontWeight={700}>Weight Trend</Typography>
                <Divider sx={{ my: 1.5 }} />

                <Box component="form" onSubmit={addWeightRecord} sx={{ display: "grid", gap: 1.5, mb: 2 }}>
                  <TextField
                    select
                    label="Select Pet"
                    value={selectedPetId}
                    onChange={(e) => setSelectedPetId(e.target.value)}
                  >
                    {pets.map((pet) => (
                      <MenuItem key={pet.id} value={pet.id}>
                        {pet.name} ({pet.species})
                      </MenuItem>
                    ))}
                  </TextField>
                  <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                    <TextField
                      label="Date"
                      type="date"
                      value={weightDate}
                      onChange={(e) => setWeightDate(e.target.value)}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                    />
                    <TextField
                      label="Weight (kg)"
                      type="number"
                      value={weightKg}
                      onChange={(e) => setWeightKg(e.target.value)}
                      inputProps={{ step: "0.01", min: "0.1" }}
                      fullWidth
                    />
                    <Button type="submit" variant="contained" disabled={savingWeight || !selectedPetId}>
                      {savingWeight ? "Saving..." : "Add Weight"}
                    </Button>
                  </Stack>
                </Box>

                <Box sx={{ height: 280 }}>
                  {hasWeightData ? (
                    <ResponsiveLine
                      data={weightSeries}
                      margin={{ top: 20, right: 20, bottom: 60, left: 60 }}
                      xScale={{ type: "point" }}
                      yScale={{ type: "linear", stacked: false }}
                      axisBottom={{
                        tickRotation: -30,
                        legend: "Date",
                        legendOffset: 48,
                        legendPosition: "middle",
                      }}
                      axisLeft={{
                        legend: "kg",
                        legendOffset: -45,
                        legendPosition: "middle",
                      }}
                      enablePoints
                      useMesh
                      colors={{ scheme: "set2" }}
                    />
                  ) : (
                    <Typography sx={{ opacity: 0.75 }}>
                      No weight records yet for the selected pet.
                    </Typography>
                  )}
                </Box>
              </Paper>
            </Grid>
          </Grid>
          )}

          <Grid container spacing={2} alignItems="flex-start">
            <Grid size={{ xs: 12, lg: 4 }}>
              <Paper sx={dashboardCardSx}>
                <Typography variant="h6" fontWeight={700}>Calendar</Typography>
                <Divider sx={{ my: 1.5 }} />
                <Stack spacing={1.25}>
                  <TextField
                    label="Month"
                    type="month"
                    value={calendarMonth}
                    onChange={(e) => {
                      setCalendarMonth(e.target.value);
                      setSelectedCalendarDate("");
                    }}
                    InputLabelProps={{ shrink: true }}
                    size="small"
                  />
                  <Box
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "repeat(7, minmax(0, 1fr))",
                      gap: 0.75,
                    }}
                  >
                    {["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"].map((day) => (
                      <Typography key={day} variant="caption" sx={{ textAlign: "center", opacity: 0.75 }}>
                        {day}
                      </Typography>
                    ))}
                    {calendarCells.map((cell) => (
                      <Box
                        key={cell.key}
                        onClick={() => {
                          if (cell.empty) return;
                          setSelectedCalendarDate((prev) => (prev === cell.iso ? "" : cell.iso));
                        }}
                        sx={{
                          minHeight: 46,
                          borderRadius: 1.25,
                          border: "1px solid #d9e2ef",
                          backgroundColor: cell.empty
                            ? "transparent"
                            : selectedCalendarDate === cell.iso
                              ? "rgba(25,118,210,0.12)"
                              : "#fff",
                          cursor: cell.empty ? "default" : "pointer",
                          p: 0.6,
                          display: "flex",
                          flexDirection: "column",
                          justifyContent: "space-between",
                        }}
                      >
                        {!cell.empty && (
                          <>
                            <Typography variant="caption">{cell.day}</Typography>
                            {cell.count > 0 && (
                              <Chip size="small" label={cell.count} color="primary" sx={{ height: 18, alignSelf: "flex-start" }} />
                            )}
                          </>
                        )}
                      </Box>
                    ))}
                  </Box>
                </Stack>
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 8 }}>
              <Paper sx={dashboardCardSx}>
                <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" spacing={1.5}>
                  <Typography variant="h6" fontWeight={700}>
                    Reminders / Follow-ups / Concerns
                  </Typography>
                  <Typography variant="body2" sx={{ opacity: 0.75 }}>
                    {selectedCalendarDate ? `Showing ${selectedCalendarDate}` : "Showing all dates in selected month"}
                  </Typography>
                </Stack>
                <Divider sx={{ my: 1.5 }} />

                <Box component="form" onSubmit={createReminder} sx={{ display: "grid", gap: 1.25, mb: 2 }}>
                  <TextField
                    size="small"
                    label="Title"
                    value={reminderForm.title}
                    onChange={(e) => setReminderForm((prev) => ({ ...prev, title: e.target.value }))}
                    required
                  />
                  <TextField
                    size="small"
                    label="Details"
                    value={reminderForm.details}
                    onChange={(e) => setReminderForm((prev) => ({ ...prev, details: e.target.value }))}
                  />
                  <TextField
                    select
                    size="small"
                    label="Link to pet (optional)"
                    value={reminderForm.pet_id}
                    onChange={(e) => setReminderForm((prev) => ({ ...prev, pet_id: e.target.value }))}
                    helperText={reminderPetOptions.length === 0 ? "No pets available to link." : ""}
                  >
                    <MenuItem value="">No pet link</MenuItem>
                    {reminderPetOptions.map((pet) => (
                      <MenuItem key={pet.id} value={pet.id}>
                        {pet.name} ({pet.species}){pet.owner_name ? ` - ${pet.owner_name}` : ""}
                      </MenuItem>
                    ))}
                  </TextField>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={1.25}>
                    <TextField
                      select
                      size="small"
                      label="Type"
                      value={reminderForm.reminder_type}
                      onChange={(e) => setReminderForm((prev) => ({ ...prev, reminder_type: e.target.value }))}
                      fullWidth
                    >
                      <MenuItem value="REMINDER">REMINDER</MenuItem>
                      <MenuItem value="FOLLOWUP">FOLLOWUP</MenuItem>
                      <MenuItem value="CONCERN">CONCERN</MenuItem>
                    </TextField>
                    <TextField
                      size="small"
                      label="Due"
                      type="datetime-local"
                      value={reminderForm.due_at}
                      onChange={(e) => setReminderForm((prev) => ({ ...prev, due_at: e.target.value }))}
                      InputLabelProps={{ shrink: true }}
                      fullWidth
                      required
                    />
                    <Button type="submit" variant="contained" disabled={savingReminder}>
                      {savingReminder ? "Saving..." : "Add"}
                    </Button>
                  </Stack>
                </Box>

                {reminderLoading ? (
                  <Typography sx={{ opacity: 0.75 }}>Loading calendar items...</Typography>
                ) : selectedDateReminders.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>No reminders for the selected period.</Typography>
                ) : (
                  <List dense>
                    {selectedDateReminders.map((r) => (
                      <ListItem
                        key={r.id}
                        disableGutters
                        secondaryAction={
                          <Stack direction="row" spacing={1}>
                            {r.status !== "DONE" && (
                              <Button size="small" onClick={() => markReminderDone(r.id)}>Done</Button>
                            )}
                            <Button size="small" color="error" onClick={() => deleteReminder(r.id)}>Delete</Button>
                          </Stack>
                        }
                      >
                        <ListItemText
                          primary={`${r.title || "Reminder"}${r.pet_name ? ` - ${r.pet_name}` : ""}${r.clinic_name ? ` (${r.clinic_name})` : ""}`}
                          secondary={`${formatDateTime(r.due_at)} | ${r.reminder_type || "REMINDER"} | ${r.status || "OPEN"}${r.details ? `\n${r.details}` : ""}`}
                          secondaryTypographyProps={{ sx: { whiteSpace: "pre-line" } }}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>
            </Grid>
          </Grid>
        </>
      )}

      <Dialog open={petDialogOpen} onClose={closePetDialog} maxWidth="sm" fullWidth>
        <DialogTitle>{editingPetId ? "Edit Pet" : "Add Pet"}</DialogTitle>
        <Box component="form" onSubmit={submitPetForm}>
          <DialogContent sx={{ display: "grid", gap: 2 }}>
            <TextField
              label="Pet Name"
              value={petForm.name}
              onChange={(e) => setPetForm((p) => ({ ...p, name: e.target.value }))}
              required
            />
            <TextField
              label="Species"
              value={petForm.species}
              onChange={(e) => setPetForm((p) => ({ ...p, species: e.target.value }))}
              required
            />
            <TextField
              label="Breed"
              value={petForm.breed}
              onChange={(e) => setPetForm((p) => ({ ...p, breed: e.target.value }))}
            />
            <TextField
              label="Sex"
              value={petForm.sex}
              onChange={(e) => setPetForm((p) => ({ ...p, sex: e.target.value }))}
            />
            <TextField
              label="Microchip Number"
              value={petForm.microchip_number}
              onChange={(e) => setPetForm((p) => ({ ...p, microchip_number: e.target.value }))}
            />
            <TextField
              label="DOB"
              type="date"
              value={petForm.date_of_birth}
              onChange={(e) => setPetForm((p) => ({ ...p, date_of_birth: e.target.value }))}
              InputLabelProps={{ shrink: true }}
            />
            <Button variant="outlined" component="label">
              {petForm.photo ? `Selected: ${petForm.photo.name}` : "Upload Photo (JPEG/PNG)"}
              <input
                hidden
                type="file"
                accept="image/png,image/jpeg"
                onChange={(e) => setPetForm((p) => ({ ...p, photo: e.target.files?.[0] || null }))}
              />
            </Button>
          </DialogContent>
          <DialogActions>
            <Button onClick={closePetDialog} disabled={savingPet}>Cancel</Button>
            <Button type="submit" variant="contained" disabled={savingPet}>
              {savingPet ? "Saving..." : "Save"}
            </Button>
          </DialogActions>
        </Box>
      </Dialog>
    </Stack>
  );
}

