/* Module: Staff. */

import React from "react";
import {
  Alert,
  Box,
  Button,
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

export default function Staff() {
  const { user } = useAuth();

  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [payload, setPayload] = React.useState(null);
  const [selectedClinicId, setSelectedClinicId] = React.useState("");
  const [savingLeave, setSavingLeave] = React.useState(false);
  const [leaveForm, setLeaveForm] = React.useState({
    start_date: "",
    end_date: "",
    reason: "",
  });

  const loadPayload = React.useCallback(async () => {
    setLoading(true);
    setError("");
    try {
      const params = { user_id: user?.user_id };
      if (selectedClinicId) params.organisation_id = selectedClinicId;
      const res = await api.get("/staff", { params });
      const data = res.data || {};
      setPayload(data);
      if (!selectedClinicId && Array.isArray(data.clinics) && data.clinics.length > 0) {
        setSelectedClinicId(data.clinics[0].id);
      }
    } catch (e) {
      console.error("Staff page load failed", e);
      setError("Failed to load staff dashboard data.");
    } finally {
      setLoading(false);
    }
  }, [user?.user_id, selectedClinicId]);

  React.useEffect(() => {
    if (!user?.user_id) return;
    loadPayload();
  }, [loadPayload, user?.user_id]);

  async function applyLeave(e) {
    e.preventDefault();
    if (!selectedClinicId) {
      setError("Select a clinic first.");
      return;
    }
    setSavingLeave(true);
    setError("");
    try {
      await api.post("/staff/leave", {
        user_id: user.user_id,
        organisation_id: selectedClinicId,
        start_date: leaveForm.start_date,
        end_date: leaveForm.end_date,
        reason: leaveForm.reason,
      });
      setLeaveForm({ start_date: "", end_date: "", reason: "" });
      await loadPayload();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to apply for leave.");
    } finally {
      setSavingLeave(false);
    }
  }

  return (
    <Stack spacing={2}>
      <Typography variant="h5" fontWeight={800}>Staff</Typography>
      <Typography sx={{ opacity: 0.8 }}>
        Track team leave, submit leave requests, view roles, and access policy documents for your clinic.
      </Typography>
      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={{ p: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center">
          <TextField
            select
            size="small"
            label="Clinic"
            value={selectedClinicId}
            onChange={(e) => setSelectedClinicId(e.target.value)}
            sx={{ minWidth: 280 }}
          >
            {(payload?.clinics || []).map((clinic) => (
              <MenuItem key={clinic.id} value={clinic.id}>{clinic.name}</MenuItem>
            ))}
          </TextField>
          {loading && <Typography variant="body2">Loading...</Typography>}
        </Stack>
      </Paper>

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, minHeight: 460 }}>
            <Typography variant="h6" fontWeight={700}>Team Directory</Typography>
            <Divider sx={{ my: 1.25 }} />
            {(payload?.staff || []).length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No team members found.</Typography>
            ) : (
              <List dense>
                {(payload?.staff || []).map((s) => (
                  <ListItem key={`${s.organisation_id}-${s.user_id}`} disableGutters>
                    <ListItemText
                      primary={`${s.full_name || "Staff"} (${s.member_role || s.role || "-"})`}
                      secondary={`${s.email || "-"} | ${s.phone || "-"}`}
                    />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2, minHeight: 460 }}>
            <Typography variant="h6" fontWeight={700}>Leave Management</Typography>
            <Divider sx={{ my: 1.25 }} />
            <Typography variant="subtitle2" sx={{ mb: 0.5 }}>Currently on leave</Typography>
            {(payload?.leave_now || []).length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No staff currently on leave.</Typography>
            ) : (
              <List dense>
                {(payload?.leave_now || []).map((l) => (
                  <ListItem key={l.leave_id} disableGutters>
                    <ListItemText primary={l.staff_name || l.user_id} secondary={`${l.start_date} to ${l.end_date} (${l.status})`} />
                  </ListItem>
                ))}
              </List>
            )}

            <Typography variant="subtitle2" sx={{ mt: 1.25, mb: 0.5 }}>Upcoming / pending leave</Typography>
            {(payload?.leave_upcoming || []).length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No upcoming leave entries.</Typography>
            ) : (
              <List dense>
                {(payload?.leave_upcoming || []).slice(0, 6).map((l) => (
                  <ListItem key={l.leave_id} disableGutters>
                    <ListItemText primary={l.staff_name || l.user_id} secondary={`${l.start_date} to ${l.end_date} (${l.status})`} />
                  </ListItem>
                ))}
              </List>
            )}
          </Paper>
        </Grid>
      </Grid>

      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Apply For Leave</Typography>
            <Divider sx={{ my: 1.25 }} />
            <Box component="form" onSubmit={applyLeave} sx={{ display: "grid", gap: 1.5 }}>
              <TextField
                label="Start Date"
                type="date"
                value={leaveForm.start_date}
                onChange={(e) => setLeaveForm((f) => ({ ...f, start_date: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                required
              />
              <TextField
                label="End Date"
                type="date"
                value={leaveForm.end_date}
                onChange={(e) => setLeaveForm((f) => ({ ...f, end_date: e.target.value }))}
                InputLabelProps={{ shrink: true }}
                required
              />
              <TextField
                label="Reason"
                value={leaveForm.reason}
                onChange={(e) => setLeaveForm((f) => ({ ...f, reason: e.target.value }))}
                multiline
                minRows={2}
              />
              <Button type="submit" variant="contained" disabled={savingLeave}>
                {savingLeave ? "Submitting..." : "Submit Leave Request"}
              </Button>
            </Box>
          </Paper>
        </Grid>

        <Grid size={{ xs: 12, md: 6 }}>
          <Paper sx={{ p: 2 }}>
            <Typography variant="h6" fontWeight={700}>Documents & Policies</Typography>
            <Divider sx={{ my: 1.25 }} />
            {(payload?.policies || []).length === 0 ? (
              <Typography sx={{ opacity: 0.75 }}>No policy documents available.</Typography>
            ) : (
              <List dense>
                {(payload?.policies || []).map((p) => (
                  <ListItem key={p.id} disableGutters>
                    <ListItemText primary={p.title} secondary={p.category} />
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

