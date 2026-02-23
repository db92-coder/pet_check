/* Module: OwnerResources. */

import React from "react";
import {
  Alert,
  Box,
  Button,
  Divider,
  Grid,
  MenuItem,
  Paper,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

import { api } from "../api/client.js";
import { useAuth } from "../auth/AuthContext.jsx";

const pageSx = {
  p: { xs: 1.5, sm: 2.5 },
  borderRadius: 3,
  backgroundColor: "#e9f0f8",
};

const cardSx = {
  p: 2,
  borderRadius: 3,
  backgroundColor: "#ffffff",
  border: "1px solid #d9e2ef",
  boxShadow: "0 8px 20px rgba(16, 24, 40, 0.06)",
};

// Primary component for this view/module.
export default function OwnerResources() {
  const { user } = useAuth();

  // Local UI/data state for this page.
  const [loading, setLoading] = React.useState(true);
  const [error, setError] = React.useState("");
  const [selectedSpecies, setSelectedSpecies] = React.useState("ALL");
  const [payload, setPayload] = React.useState(null);

  // Initial/refresh data loading side-effect.
  React.useEffect(() => {
    let cancelled = false;

    async function loadResources() {
      const role = (user?.role || "").toUpperCase();
      if (role !== "OWNER" || !user?.user_id) {
        setPayload(null);
        setLoading(false);
        return;
      }

      setLoading(true);
      setError("");
      try {
        const res = await api.get("/dashboard/owner-faq", {
          params: {
            user_id: user.user_id,
            species: selectedSpecies !== "ALL" ? selectedSpecies : undefined,
          },
        });
        if (cancelled) return;
        setPayload(res?.data || null);
      } catch (e) {
        if (cancelled) return;
        console.error("Owner resources load failed", e);
        setError("Failed to load pet care resources.");
        setPayload(null);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    loadResources();
    return () => {
      cancelled = true;
    };
  }, [user?.role, user?.user_id, selectedSpecies]);

  const availableSpecies = Array.isArray(payload?.available_species) ? payload.available_species : ["ALL"];
  const commonSections = Array.isArray(payload?.common_sections) ? payload.common_sections : [];
  const sections = Array.isArray(payload?.species_sections) ? payload.species_sections : [];

  // Render UI layout and interactions.
  return (
    <Stack spacing={2} sx={pageSx}>
      <Box>
        <Typography variant="h4" fontWeight={800}>
          Pet Care Resources
        </Typography>
        <Typography sx={{ opacity: 0.8 }}>
          One-stop companion animal guidance from RSPCA categories based on your pets.
        </Typography>
      </Box>

      {error && <Alert severity="error">{error}</Alert>}

      <Paper sx={cardSx}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5} alignItems="center" justifyContent="space-between">
          <TextField
            select
            size="small"
            label="Animal Category"
            value={selectedSpecies}
            onChange={(e) => setSelectedSpecies(e.target.value)}
            sx={{ minWidth: 220 }}
          >
            {availableSpecies.map((sp) => (
              <MenuItem key={sp} value={sp}>
                {sp.replaceAll("_", " ")}
              </MenuItem>
            ))}
          </TextField>
          <Button
            variant="outlined"
            href={payload?.source_url}
            target="_blank"
            rel="noopener noreferrer"
          >
            Open RSPCA Companion Animals Hub
          </Button>
        </Stack>
      </Paper>

      <Paper sx={cardSx}>
        <Typography variant="h6" fontWeight={700}>
          Companion Animal Essentials
        </Typography>
        <Typography sx={{ opacity: 0.78, mb: 1 }}>
          Core guidance recommended for all companion animal owners.
        </Typography>
        <Divider sx={{ my: 1.5 }} />
        <Grid container spacing={1}>
          {commonSections.map((item) => (
            <Grid key={item.url} size={{ xs: 12, md: 6 }}>
              <Button
                fullWidth
                variant="outlined"
                href={item.url}
                target="_blank"
                rel="noopener noreferrer"
                sx={{ justifyContent: "flex-start" }}
              >
                {item.title}
              </Button>
            </Grid>
          ))}
        </Grid>
      </Paper>

      {loading ? (
        <Paper sx={cardSx}>
          <Typography>Loading resources...</Typography>
        </Paper>
      ) : sections.length === 0 ? (
        <Paper sx={cardSx}>
          <Typography sx={{ opacity: 0.75 }}>No resources available for the selected category.</Typography>
        </Paper>
      ) : (
        <Grid container spacing={2}>
          {sections.map((section) => (
            <Grid key={section.species} size={{ xs: 12, md: 6 }}>
              <Paper sx={cardSx}>
                <Typography variant="h6" fontWeight={700}>
                  {section.title}
                </Typography>
                <Typography sx={{ opacity: 0.78, mb: 1 }}>{section.summary}</Typography>
                <Button
                  size="small"
                  variant="text"
                  href={section.category_url}
                  target="_blank"
                  rel="noopener noreferrer"
                  sx={{ px: 0 }}
                >
                  Open Category Page
                </Button>
                <Divider sx={{ my: 1.5 }} />
                <Stack spacing={1}>
                  {(section.subcategories || []).map((sub) => (
                    <Button
                      key={sub.url}
                      variant="outlined"
                      size="small"
                      href={sub.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      sx={{ justifyContent: "flex-start" }}
                    >
                      {sub.title}
                    </Button>
                  ))}
                </Stack>
              </Paper>
            </Grid>
          ))}
        </Grid>
      )}

      <Typography variant="caption" sx={{ opacity: 0.75 }}>
        {payload?.disclaimer ||
          "Resources are external links and may change over time. Always refer to the source page for latest information."}
      </Typography>
    </Stack>
  );
}
