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

function ClinicMapPanel({ centerClinic, nearbyClinics }) {
  const mapRef = React.useRef(null);
  const mapInstanceRef = React.useRef(null);
  const markersLayerRef = React.useRef(null);
  const [leafletReady, setLeafletReady] = React.useState(Boolean(window.L));

  const points = React.useMemo(() => {
    if (!centerClinic) return [];
    return [
      { ...centerClinic, _isCenter: true },
      ...nearbyClinics.map((c) => ({ ...c, _isCenter: false })),
    ].filter((p) => Number.isFinite(toNum(p.latitude)) && Number.isFinite(toNum(p.longitude)));
  }, [centerClinic, nearbyClinics]);

  React.useEffect(() => {
    if (window.L) {
      setLeafletReady(true);
      return;
    }

    const cssId = "leaflet-css-cdn";
    const jsId = "leaflet-js-cdn";

    if (!document.getElementById(cssId)) {
      const link = document.createElement("link");
      link.id = cssId;
      link.rel = "stylesheet";
      link.href = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css";
      document.head.appendChild(link);
    }

    if (!document.getElementById(jsId)) {
      const script = document.createElement("script");
      script.id = jsId;
      script.src = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js";
      script.async = true;
      script.onload = () => setLeafletReady(true);
      document.body.appendChild(script);
    }
  }, []);

  React.useEffect(() => {
    if (!leafletReady || !mapRef.current || points.length === 0) return;
    const L = window.L;
    if (!L) return;

    if (!mapInstanceRef.current) {
      mapInstanceRef.current = L.map(mapRef.current, {
        zoomControl: true,
        attributionControl: true,
      });
      L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 18,
        attribution: "&copy; OpenStreetMap contributors",
      }).addTo(mapInstanceRef.current);
    }

    if (markersLayerRef.current) {
      markersLayerRef.current.remove();
    }
    markersLayerRef.current = L.layerGroup().addTo(mapInstanceRef.current);

    const latLngs = [];
    points.forEach((point) => {
      const lat = toNum(point.latitude);
      const lon = toNum(point.longitude);
      const color = point._isCenter ? "#1565c0" : "#2e7d32";
      latLngs.push([lat, lon]);
      L.circleMarker([lat, lon], {
        radius: point._isCenter ? 9 : 6,
        color: "#ffffff",
        weight: 2,
        fillColor: color,
        fillOpacity: 0.95,
      })
        .addTo(markersLayerRef.current)
        .bindTooltip(point.name || "Clinic", { direction: "top", offset: [0, -8] });
    });

    const bounds = L.latLngBounds(latLngs);
    if (latLngs.length === 1) {
      mapInstanceRef.current.setView(latLngs[0], 10);
    } else {
      mapInstanceRef.current.fitBounds(bounds, { padding: [20, 20] });
    }
  }, [leafletReady, points]);

  React.useEffect(() => {
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, []);

  if (!centerClinic || points.length === 0) {
    return <Typography sx={{ opacity: 0.75 }}>Map unavailable.</Typography>;
  }

  return (
    <Box sx={{ border: "1px solid", borderColor: "divider", borderRadius: 1.5, overflow: "hidden" }}>
      <Box
        sx={{
          px: 1.5,
          py: 1,
          background:
            "linear-gradient(90deg, rgba(13,71,161,0.06) 0%, rgba(46,125,50,0.06) 100%)",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          Surrounding Clinics Map (OpenStreetMap)
        </Typography>
      </Box>
      <Box sx={{ p: 1, backgroundColor: "#f8fafc" }}>
        <Box
          ref={mapRef}
          sx={{
            width: "100%",
            height: 340,
            borderRadius: 1,
            overflow: "hidden",
            border: "1px solid",
            borderColor: "divider",
          }}
        />
        <Stack direction="row" spacing={2} sx={{ pt: 1 }}>
          <Typography variant="caption"><strong style={{ color: "#1565c0" }}>Blue</strong>: selected clinic</Typography>
          <Typography variant="caption"><strong style={{ color: "#2e7d32" }}>Green</strong>: nearby clinics</Typography>
        </Stack>
      </Box>
    </Box>
  );
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

  const mappedNearby = React.useMemo(() => nearby.slice(0, 12), [nearby]);

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
                {selectedClinic.metrics_simulated && (
                  <Typography variant="caption" sx={{ opacity: 0.75 }}>
                    Upcoming/cancellation metrics are currently simulated for planning views.
                  </Typography>
                )}
                {selectedClinic.geo_simulated && (
                  <Typography variant="caption" sx={{ opacity: 0.75 }}>
                    Geolocation is currently simulated where source coordinates are unavailable.
                  </Typography>
                )}

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

                <Box sx={{ pt: 1 }}>
                  <ClinicMapPanel centerClinic={selectedClinic} nearbyClinics={mappedNearby} />
                </Box>
              </Stack>
            )}
          </Paper>
        </Grid>
      </Grid>
    </Stack>
  );
}

