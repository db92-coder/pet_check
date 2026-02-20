import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../src/api/client.js";

import {
  Box,
  Paper,
  Stack,
  Typography,
  TextField,
  Button,
  Divider,
} from "@mui/material";

import { ResponsiveLine } from "@nivo/line";
import { ResponsiveBar } from "@nivo/bar";

const MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

function monthLabelFromYYYYMM(yyyymm) {
  if (typeof yyyymm !== "string") return "Unknown";
  const m = yyyymm.match(/^(\d{4})-(\d{2})$/);
  if (!m) return yyyymm;
  const monthNum = Number(m[2]);
  if (!Number.isFinite(monthNum) || monthNum < 1 || monthNum > 12) return yyyymm;
  return `${MONTH_LABELS[monthNum - 1]} ${m[1]}`;
}

function toFiniteNumber(value, fallback = 0) {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export default function AdminAnalytics() {
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [organisationId, setOrganisationId] = useState("");

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [careEventsByMonth, setCareEventsByMonth] = useState([]);
  const [vaccinationsByType, setVaccinationsByType] = useState([]);
  const [topOrgsByVisits, setTopOrgsByVisits] = useState([]);
  const [visitsByReason, setVisitsByReason] = useState([]);

  useEffect(() => {
    let cancelled = false;

    async function fetchAnalytics() {
      setLoading(true);
      setError("");

      const params = {};
      if (start) params.start = start;
      if (end) params.end = end;
      if (organisationId) params.organisation_id = organisationId;

      try {
        const [careRes, vaxRes, topRes, reasonsRes] = await Promise.all([
          api.get("/analytics/care-events-by-month", { params }),
          api.get("/analytics/vaccinations-by-type", { params }),
          api.get("/analytics/top-organisations-by-visits", { params: { ...params, limit: 10 } }),
          api.get("/analytics/visits-by-reason", { params: { ...params, limit: 10 } }),
        ]);

        if (cancelled) return;

        setCareEventsByMonth(Array.isArray(careRes.data) ? careRes.data : []);
        setVaccinationsByType(Array.isArray(vaxRes.data) ? vaxRes.data : []);
        setTopOrgsByVisits(Array.isArray(topRes.data) ? topRes.data : []);
        setVisitsByReason(Array.isArray(reasonsRes.data) ? reasonsRes.data : []);
      } catch (e) {
        if (cancelled) return;
        console.error("Analytics fetch failed:", e);
        setError("Failed to load analytics (check backend logs).");
      } finally {
        if (!cancelled) setLoading(false);
      }
    }

    fetchAnalytics();
    return () => {
      cancelled = true;
    };
  }, [start, end, organisationId]);

  const careLineData = useMemo(() => {
    const rows = Array.isArray(careEventsByMonth) ? careEventsByMonth : [];

    const visits = [];
    const vaccinations = [];
    const weights = [];
    const total = [];

    for (const r of rows) {
      const x = monthLabelFromYYYYMM(r.month);
      total.push({ x, y: toFiniteNumber(r.total) });
      visits.push({ x, y: toFiniteNumber(r.visits) });
      vaccinations.push({ x, y: toFiniteNumber(r.vaccinations) });
      weights.push({ x, y: toFiniteNumber(r.weights) });
    }

    return [
      { id: "Total", data: total },
      { id: "Visits", data: visits },
      { id: "Vaccinations", data: vaccinations },
      { id: "Weights", data: weights },
    ];
  }, [careEventsByMonth]);

  const vaccinationsBarData = useMemo(() => {
    const rows = Array.isArray(vaccinationsByType) ? vaccinationsByType : [];
    return rows.map((r) => ({
      type: r.type ?? "Unknown",
      count: toFiniteNumber(r.count),
    }));
  }, [vaccinationsByType]);

  const topOrgsBarData = useMemo(() => {
    const rows = Array.isArray(topOrgsByVisits) ? topOrgsByVisits : [];
    return rows.map((r) => ({
      organisation: r.organisation_name ?? r.organisation_id ?? "Unknown",
      visits: toFiniteNumber(r.visits),
    }));
  }, [topOrgsByVisits]);

  const reasonsBarData = useMemo(() => {
    const rows = Array.isArray(visitsByReason) ? visitsByReason : [];
    return rows.map((r) => ({
      reason: r.reason ?? "Unknown",
      count: toFiniteNumber(r.count),
    }));
  }, [visitsByReason]);

  const hasCareLineData = careLineData.some((s) => Array.isArray(s.data) && s.data.length > 0);

  return (
    <Box sx={{ p: 3 }}>
      <Stack spacing={2}>
        <Typography variant="h4">Admin Analytics</Typography>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Filters
          </Typography>

          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center">
            <TextField
              label="Start date"
              type="date"
              value={start}
              onChange={(e) => setStart(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 220 }}
            />

            <TextField
              label="End date"
              type="date"
              value={end}
              onChange={(e) => setEnd(e.target.value)}
              InputLabelProps={{ shrink: true }}
              sx={{ minWidth: 220 }}
            />

            <TextField
              label="Organisation ID (optional)"
              value={organisationId}
              onChange={(e) => setOrganisationId(e.target.value)}
              placeholder="e.g. UUID or text id"
              sx={{ minWidth: 260 }}
            />

            <Button
              variant="outlined"
              onClick={() => {
                setStart("");
                setEnd("");
                setOrganisationId("");
              }}
              disabled={loading}
            >
              Clear
            </Button>

            {loading && <Typography variant="body2">Loading...</Typography>}
            {error && <Typography variant="body2" color="error">{error}</Typography>}
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Care events by month
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Box sx={{ height: 360 }}>
            {hasCareLineData ? (
              <ResponsiveLine
                data={careLineData}
                margin={{ top: 20, right: 20, bottom: 60, left: 60 }}
                xScale={{ type: "point" }}
                yScale={{ type: "linear", stacked: false }}
                colors={{ scheme: "set2" }}
                axisBottom={{
                  tickRotation: -35,
                  legend: "Month",
                  legendOffset: 48,
                  legendPosition: "middle",
                }}
                axisLeft={{
                  legend: "Count",
                  legendOffset: -45,
                  legendPosition: "middle",
                }}
                enablePoints
                useMesh
                legends={[
                  {
                    anchor: "bottom",
                    direction: "row",
                    justify: false,
                    translateX: 0,
                    translateY: 56,
                    itemsSpacing: 12,
                    itemDirection: "left-to-right",
                    itemWidth: 100,
                    itemHeight: 20,
                    itemOpacity: 0.85,
                    symbolSize: 12,
                    symbolShape: "circle",
                    effects: [
                      {
                        on: "hover",
                        style: {
                          itemOpacity: 1,
                        },
                      },
                    ],
                  },
                ]}
              />
            ) : (
              <Typography variant="body2" sx={{ opacity: 0.7 }}>
                No care event data for the current filters.
              </Typography>
            )}
          </Box>
        </Paper>

        <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
          <Paper sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Vaccinations by type
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ height: 360 }}>
              <ResponsiveBar
                data={vaccinationsBarData}
                keys={["count"]}
                indexBy="type"
                margin={{ top: 20, right: 20, bottom: 80, left: 60 }}
                axisBottom={{ tickRotation: -35 }}
                axisLeft={{ legend: "Count", legendOffset: -45, legendPosition: "middle" }}
                padding={0.3}
              />
            </Box>
          </Paper>

          <Paper sx={{ p: 2, flex: 1 }}>
            <Typography variant="h6" sx={{ mb: 1 }}>
              Top organisations by visits
            </Typography>
            <Divider sx={{ mb: 2 }} />

            <Box sx={{ height: 360 }}>
              <ResponsiveBar
                data={topOrgsBarData}
                keys={["visits"]}
                indexBy="organisation"
                margin={{ top: 20, right: 20, bottom: 120, left: 60 }}
                axisBottom={{ tickRotation: -45 }}
                axisLeft={{ legend: "Visits", legendOffset: -45, legendPosition: "middle" }}
                padding={0.3}
              />
            </Box>
          </Paper>
        </Stack>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Visits by reason
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Box sx={{ height: 360 }}>
            <ResponsiveBar
              data={reasonsBarData}
              keys={["count"]}
              indexBy="reason"
              margin={{ top: 20, right: 20, bottom: 140, left: 60 }}
              axisBottom={{ tickRotation: -45 }}
              axisLeft={{ legend: "Count", legendOffset: -45, legendPosition: "middle" }}
              padding={0.3}
            />
          </Box>
        </Paper>
      </Stack>
    </Box>
  );
}
