import React, { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Chip,
  CircularProgress,
  Divider,
  Grid,
  List,
  ListItem,
  ListItemText,
  Paper,
  Stack,
  Typography,
} from "@mui/material";

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

export default function Dashboard() {
  const { user } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  const [pets, setPets] = useState([]);
  const [appointments, setAppointments] = useState([]);
  const [vaccinationDue, setVaccinationDue] = useState([]);
  const [ownerNotResolved, setOwnerNotResolved] = useState(false);

  useEffect(() => {
    let cancelled = false;

    async function loadDashboard() {
      setLoading(true);
      setError("");

      try {
        const [petsRes, visitsRes] = await Promise.all([
          api.get("/pets", { params: { user_id: user?.user_id, limit: 1000 } }),
          api.get("/visits", { params: { limit: 5000 } }),
        ]);

        if (cancelled) return;

        const currentPets = Array.isArray(petsRes.data) ? petsRes.data : [];
        const allVisits = Array.isArray(visitsRes.data) ? visitsRes.data : [];

        const resolvedOwnerId = currentPets.length > 0 ? currentPets[0].owner_id : null;
        setOwnerNotResolved(Boolean(user?.user_id) && !resolvedOwnerId);
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

        const due = vaccinationRows
          .filter((v) => v.due_at)
          .filter((v) => {
            const dueAt = new Date(v.due_at);
            return !Number.isNaN(dueAt.getTime()) && dueAt >= now;
          })
          .sort((a, b) => new Date(a.due_at) - new Date(b.due_at))
          .slice(0, 20);

        if (cancelled) return;
        setVaccinationDue(due);
      } catch (e) {
        if (cancelled) return;
        console.error("Dashboard load failed", e);
        setError("Failed to load dashboard data.");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadDashboard();
    return () => {
      cancelled = true;
    };
  }, [user?.user_id]);

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

  return (
    <Stack spacing={2}>
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
        <Paper sx={{ p: 3 }}>
          <Stack direction="row" spacing={1.5} alignItems="center">
            <CircularProgress size={20} />
            <Typography>Loading dashboard...</Typography>
          </Stack>
        </Paper>
      ) : (
        <>
          <Grid container spacing={2}>
            <Grid size={{ xs: 12, md: 6 }}>
              <Paper sx={{ p: 2 }}>
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
              <Paper sx={{ p: 2 }}>
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

          <Grid container spacing={2}>
            <Grid size={{ xs: 12, lg: 5 }}>
              <Paper sx={{ p: 2, height: "100%" }}>
                <Typography variant="h6" fontWeight={700}>Current Pets</Typography>
                <Divider sx={{ my: 1.5 }} />
                {pets.length === 0 ? (
                  <Typography sx={{ opacity: 0.75 }}>No pets found.</Typography>
                ) : (
                  <List dense>
                    {pets.map((pet) => (
                      <ListItem key={pet.id} disableGutters>
                        <ListItemText
                          primary={`${pet.name || "Unnamed"} (${pet.species || "Unknown"})`}
                          secondary={`Breed: ${pet.breed || "-"} | Sex: ${pet.sex || "-"} | DOB: ${formatDate(pet.date_of_birth)}`}
                        />
                      </ListItem>
                    ))}
                  </List>
                )}
              </Paper>
            </Grid>

            <Grid size={{ xs: 12, lg: 7 }}>
              <Paper sx={{ p: 2, mb: 2 }}>
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

              <Paper sx={{ p: 2 }}>
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
            </Grid>
          </Grid>
        </>
      )}
    </Stack>
  );
}
