import React, { useEffect, useMemo, useState } from "react";
import { api } from "../../src/api/client.js";

import {
  Box,
  Paper,
  Stack,
  Typography,
  TextField,
  MenuItem,
  Button,
  Divider,
  Chip,
} from "@mui/material";

import { ResponsiveLine } from "@nivo/line";
import { ResponsiveBar } from "@nivo/bar";
import { ResponsivePie } from "@nivo/pie";

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
  const [month, setMonth] = useState("");
  const [organisationId, setOrganisationId] = useState("");
  const [vaccineType, setVaccineType] = useState("");
  const [visitReason, setVisitReason] = useState("");

  const [loading, setLoading] = useState(false);
  const [exporting, setExporting] = useState(false);
  const [error, setError] = useState("");

  const [filterOptions, setFilterOptions] = useState({
    organisations: [],
    months: [],
    vaccine_types: [],
    visit_reasons: [],
  });

  const [careEventsByMonth, setCareEventsByMonth] = useState([]);
  const [vaccinationsByType, setVaccinationsByType] = useState([]);
  const [topOrgsByVisits, setTopOrgsByVisits] = useState([]);
  const [visitsByReason, setVisitsByReason] = useState([]);
  const [eligibilityOwners, setEligibilityOwners] = useState([]);
  const [selectedEligibilityOwnerId, setSelectedEligibilityOwnerId] = useState("");
  const [eligibilityDetail, setEligibilityDetail] = useState(null);
  const [eligibilityLoading, setEligibilityLoading] = useState(false);

  const buildParams = () => {
    const params = {};
    if (start) params.start = start;
    if (end) params.end = end;
    if (month) params.month = month;
    if (organisationId) params.organisation_id = organisationId;
    if (vaccineType) params.vaccine_type = vaccineType;
    if (visitReason) params.visit_reason = visitReason;
    return params;
  };

  useEffect(() => {
    let cancelled = false;

    async function loadFilterOptions() {
      try {
        const params = {};
        if (start) params.start = start;
        if (end) params.end = end;
        if (month) params.month = month;
        if (organisationId) params.organisation_id = organisationId;

        const res = await api.get("/analytics/filter-options", { params });
        if (cancelled) return;

        const options = {
          organisations: Array.isArray(res.data?.organisations) ? res.data.organisations : [],
          months: Array.isArray(res.data?.months) ? res.data.months : [],
          vaccine_types: Array.isArray(res.data?.vaccine_types) ? res.data.vaccine_types : [],
          visit_reasons: Array.isArray(res.data?.visit_reasons) ? res.data.visit_reasons : [],
        };
        setFilterOptions(options);
      } catch (e) {
        if (cancelled) return;
        console.error("Analytics filter options fetch failed:", e);
      }
    }

    loadFilterOptions();
    return () => {
      cancelled = true;
    };
  }, [start, end, month, organisationId]);

  useEffect(() => {
    let cancelled = false;
    async function loadEligibilityOwners() {
      try {
        const res = await api.get("/eligibility/owners", { params: { limit: 100 } });
        if (cancelled) return;
        const rows = Array.isArray(res.data) ? res.data : [];
        setEligibilityOwners(rows);
        if (rows.length > 0 && !selectedEligibilityOwnerId) {
          setSelectedEligibilityOwnerId(rows[0].owner_id);
        }
      } catch (e) {
        if (cancelled) return;
        console.error("Eligibility owners load failed:", e);
      }
    }
    loadEligibilityOwners();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;
    async function loadEligibilityDetail() {
      if (!selectedEligibilityOwnerId) {
        setEligibilityDetail(null);
        return;
      }
      setEligibilityLoading(true);
      try {
        const res = await api.get(`/eligibility/owner/${selectedEligibilityOwnerId}`);
        if (cancelled) return;
        setEligibilityDetail(res.data || null);
      } catch (e) {
        if (cancelled) return;
        console.error("Eligibility detail load failed:", e);
        setEligibilityDetail(null);
      } finally {
        if (!cancelled) setEligibilityLoading(false);
      }
    }
    loadEligibilityDetail();
    return () => {
      cancelled = true;
    };
  }, [selectedEligibilityOwnerId]);

  useEffect(() => {
    let cancelled = false;

    async function fetchAnalytics() {
      setLoading(true);
      setError("");

      const params = buildParams();

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
  }, [start, end, month, organisationId, vaccineType, visitReason]);

  async function handleExport() {
    setExporting(true);
    setError("");
    try {
      const res = await api.get("/analytics/export", {
        params: buildParams(),
        responseType: "blob",
      });
      const disposition = res.headers?.["content-disposition"] || "";
      const match = disposition.match(/filename="?([^"]+)"?/i);
      const filename = match?.[1] || "analytics_export.csv";

      const blob = new Blob([res.data], { type: "text/csv" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e) {
      console.error("Analytics export failed:", e);
      setError("Failed to export analytics data.");
    } finally {
      setExporting(false);
    }
  }

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

  const scoreMixPieData = useMemo(() => {
    if (!eligibilityDetail) return [];
    const vetContribution = toFiniteNumber(eligibilityDetail.vet_score) * 0.45;
    const govContribution = toFiniteNumber(eligibilityDetail.gov_score) * 0.55;
    return [
      { id: "Vet contribution", label: "Vet contribution", value: Number(vetContribution.toFixed(2)) },
      { id: "Govt contribution", label: "Govt contribution", value: Number(govContribution.toFixed(2)) },
    ];
  }, [eligibilityDetail]);

  const annualCostBySpeciesPieData = useMemo(() => {
    const pets = Array.isArray(eligibilityDetail?.pets) ? eligibilityDetail.pets : [];
    const totals = new Map();
    for (const p of pets) {
      const key = p?.species || "Unknown";
      const v = toFiniteNumber(p?.annual_min_cost);
      totals.set(key, (totals.get(key) || 0) + v);
    }
    return Array.from(totals.entries()).map(([species, value]) => ({
      id: species,
      label: species,
      value: Number(value.toFixed(2)),
    }));
  }, [eligibilityDetail]);

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
              select
              label="Month"
              value={month}
              onChange={(e) => setMonth(e.target.value)}
              sx={{ minWidth: 180 }}
            >
              <MenuItem value="">All months</MenuItem>
              {filterOptions.months.map((m) => (
                <MenuItem key={m} value={m}>
                  {monthLabelFromYYYYMM(m)}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Clinic"
              value={organisationId}
              onChange={(e) => setOrganisationId(e.target.value)}
              sx={{ minWidth: 260 }}
            >
              <MenuItem value="">All clinics</MenuItem>
              {filterOptions.organisations.map((o) => (
                <MenuItem key={o.organisation_id} value={o.organisation_id}>
                  {o.name}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Vaccination Type"
              value={vaccineType}
              onChange={(e) => setVaccineType(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              <MenuItem value="">All vaccination types</MenuItem>
              {filterOptions.vaccine_types.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>

            <TextField
              select
              label="Visit Reason"
              value={visitReason}
              onChange={(e) => setVisitReason(e.target.value)}
              sx={{ minWidth: 220 }}
            >
              <MenuItem value="">All visit reasons</MenuItem>
              {filterOptions.visit_reasons.map((value) => (
                <MenuItem key={value} value={value}>
                  {value}
                </MenuItem>
              ))}
            </TextField>

            <Button variant="contained" onClick={handleExport} disabled={loading || exporting}>
              {exporting ? "Exporting..." : "Export CSV"}
            </Button>

            <Button
              variant="outlined"
              onClick={() => {
                setStart("");
                setEnd("");
                setMonth("");
                setOrganisationId("");
                setVaccineType("");
                setVisitReason("");
              }}
              disabled={loading || exporting}
            >
              Clear
            </Button>

            {loading && <Typography variant="body2">Loading...</Typography>}
            {error && <Typography variant="body2" color="error">{error}</Typography>}
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Eligibility Overview (Vet + Govt)
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems="center" sx={{ mb: 2 }}>
            <TextField
              select
              label="Owner"
              value={selectedEligibilityOwnerId}
              onChange={(e) => setSelectedEligibilityOwnerId(e.target.value)}
              sx={{ minWidth: 360 }}
            >
              {eligibilityOwners.length === 0 && (
                <MenuItem value="" disabled>
                  No owners available
                </MenuItem>
              )}
              {eligibilityOwners.map((o) => (
                <MenuItem key={o.owner_id} value={o.owner_id}>
                  {(o.owner_name || o.owner_email || o.owner_id) + ` (${o.owner_email || "no-email"})`}
                </MenuItem>
              ))}
            </TextField>
            {eligibilityDetail && (
              <>
                <Chip label={`Overall: ${toFiniteNumber(eligibilityDetail.overall_eligibility_score).toFixed(2)}`} color="primary" />
                <Chip label={`Risk: ${eligibilityDetail.risk_level || "-"}`} color={eligibilityDetail.risk_level === "HIGH" ? "error" : eligibilityDetail.risk_level === "MEDIUM" ? "warning" : "success"} />
                <Chip label={`Pets: ${eligibilityDetail.pet_count || 0}`} variant="outlined" />
              </>
            )}
            {eligibilityLoading && <Typography variant="body2">Loading eligibility...</Typography>}
          </Stack>

          <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Score Composition (Weighted)
              </Typography>
              <Box sx={{ height: 320 }}>
                {scoreMixPieData.length > 0 ? (
                  <ResponsivePie
                    data={scoreMixPieData}
                    margin={{ top: 20, right: 20, bottom: 80, left: 20 }}
                    innerRadius={0.55}
                    padAngle={1}
                    cornerRadius={4}
                    activeOuterRadiusOffset={8}
                    arcLabelsSkipAngle={10}
                    arcLabelsTextColor="#fff"
                    legends={[
                      {
                        anchor: "bottom",
                        direction: "row",
                        justify: false,
                        translateY: 52,
                        itemWidth: 150,
                        itemHeight: 18,
                        symbolSize: 12,
                        symbolShape: "circle",
                      },
                    ]}
                  />
                ) : (
                  <Typography variant="body2" sx={{ opacity: 0.7 }}>
                    Select an owner to view score composition.
                  </Typography>
                )}
              </Box>
            </Box>

            <Box sx={{ flex: 1 }}>
              <Typography variant="subtitle1" sx={{ mb: 1 }}>
                Annual Min Care Cost by Species
              </Typography>
              <Box sx={{ height: 320 }}>
                {annualCostBySpeciesPieData.length > 0 ? (
                  <ResponsivePie
                    data={annualCostBySpeciesPieData}
                    margin={{ top: 20, right: 20, bottom: 80, left: 20 }}
                    innerRadius={0.45}
                    padAngle={1}
                    cornerRadius={4}
                    activeOuterRadiusOffset={8}
                    arcLabelsSkipAngle={10}
                    arcLabelsTextColor="#fff"
                    valueFormat=">-.2f"
                    legends={[
                      {
                        anchor: "bottom",
                        direction: "row",
                        justify: false,
                        translateY: 52,
                        itemWidth: 120,
                        itemHeight: 18,
                        symbolSize: 12,
                        symbolShape: "circle",
                      },
                    ]}
                  />
                ) : (
                  <Typography variant="body2" sx={{ opacity: 0.7 }}>
                    No species cost data for selected owner.
                  </Typography>
                )}
              </Box>
            </Box>
          </Stack>
        </Paper>

        <Paper sx={{ p: 2 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Care events by month
          </Typography>
          <Divider sx={{ mb: 2 }} />

          <Box sx={{ height: 380 }}>
            {hasCareLineData ? (
              <ResponsiveLine
                data={careLineData}
                margin={{ top: 85, right: 20, bottom: 70, left: 60 }}
                xScale={{ type: "point" }}
                yScale={{ type: "linear", stacked: false }}
                colors={{ scheme: "set2" }}
                axisBottom={{
                  tickRotation: -30,
                  legend: "Month",
                  legendOffset: 56,
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
                    anchor: "top-left",
                    direction: "column",
                    justify: false,
                    translateX: 0,
                    translateY: -72,
                    itemsSpacing: 6,
                    itemDirection: "left-to-right",
                    itemWidth: 130,
                    itemHeight: 18,
                    itemOpacity: 0.9,
                    symbolSize: 11,
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
