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

export default function Dashboard() {
  const { user } = useAuth();

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
  const [selectedPetId, setSelectedPetId] = useState("");
  const [weightKg, setWeightKg] = useState("");
  const [weightDate, setWeightDate] = useState("");
  const [savingWeight, setSavingWeight] = useState(false);

  const [petDialogOpen, setPetDialogOpen] = useState(false);
  const [editingPetId, setEditingPetId] = useState(null);
  const [petForm, setPetForm] = useState(emptyPetForm);

  const loadDashboard = useCallback(async () => {
    setLoading(true);
    setError("");

    try {
      const [petsRes, visitsRes] = await Promise.all([
        api.get("/pets", { params: { user_id: user?.user_id, limit: 1000 } }),
        api.get("/visits", { params: { limit: 5000 } }),
      ]);

      const currentPets = Array.isArray(petsRes.data) ? petsRes.data : [];
      const allVisits = Array.isArray(visitsRes.data) ? visitsRes.data : [];

      const resolvedOwnerId = currentPets.length > 0 ? currentPets[0].owner_id : null;
      setOwnerNotResolved(user?.role === "OWNER" && Boolean(user?.user_id) && !resolvedOwnerId);
      setPets(currentPets);

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
      setLoading(false);
    }
  }, [user?.role, user?.user_id]);

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

  return (
    <Stack spacing={2} sx={dashboardPageSx}>
      <Box>
        <Typography variant="h4" fontWeight={800}>
          Dashboard
        </Typography>
        <Typography sx={{ opacity: 0.8 }}>
          Overview of your pets, appointments, and upcoming vaccine due dates.
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
                </Stack>
              </Paper>
            </Grid>
          </Grid>

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
