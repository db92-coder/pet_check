import React from "react";
import { Box, Paper, Typography, Stack, TextField, MenuItem, CircularProgress } from "@mui/material";
import { ResponsiveLine } from "@nivo/line";
import { ResponsivePie } from "@nivo/pie";
import { ResponsiveBar } from "@nivo/bar";
import { api } from "../api/client";

function toISODate(d) {
  return d ? new Date(d).toISOString().slice(0, 10) : "";
}

export default function AdminAnalytics() {
  const [start, setStart] = React.useState(""); // YYYY-MM-DD
  const [end, setEnd] = React.useState("");     // YYYY-MM-DD
  const [organisationId, setOrganisationId] = React.useState("");
  const [orgs, setOrgs] = React.useState([]);

  const [kpis, setKpis] = React.useState(null);
  const [careByMonth, setCareByMonth] = React.useState([]);
  const [vaxByType, setVaxByType] = React.useState([]);
  const [topOrgs, setTopOrgs] = React.useState([]);
  const [visitsByReason, setVisitsByReason] = React.useState([]);

  const [loading, setLoading] = React.useState(true);

  const params = React.useMemo(() => {
    const p = {};
    if (start) p.start = start;
    if (end) p.end = end;
    if (organisationId) p.organisation_id = organisationId;
    return p;
  }, [start, end, organisationId]);

  React.useEffect(() => {
    // optional: load organisations list for the filter dropdown
    (async () => {
      try {
        const res = await api.get("/integrations/vet/ping"); // placeholder to prove backend up
        // If you have /organisations endpoint later, swap this to real org list.
      } catch {}
    })();
  }, []);

  React.useEffect(() => {
    let mounted = true;
    (async () => {
      try {
        setLoading(true);

        const [k, care, vax, orgsTop, reasons] = await Promise.all([
          api.get("/analytics/kpis", { params }),
          api.get("/analytics/care-events-by-month", { params }),
          api.get("/analytics/vaccinations-by-type", { params }),
          api.get("/analytics/top-organisations-by-visits", { params: { ...params, limit: 10 } }),
          api.get("/analytics/visits-by-reason", { params: { ...params, limit: 10 } }),
        ]);

        if (!mounted) return;

        setKpis(k.data);
        setCareByMonth(care.data);
        setVaxByType(vax.data);
        setTopOrgs(orgsTop.data);
        setVisitsByReason(reasons.data);
      } finally {
        if (mounted) setLoading(false);
      }
    })();

    return () => {
      mounted = false;
    };
  }, [params]);

  const lineData = React.useMemo(() => {
    // const months = careByMonth.map((r) => ({ x: r.month, y: r.total }));
    const n = (v) => (Number.isFinite(Number(v)) ? Number(v) : 0);

    const lineData = React.useMemo(() => {
    const total = careByMonth.map((r) => ({ x: r.month ?? "Unknown", y: n(r.total) }));
    const visits = careByMonth.map((r) => ({ x: r.month ?? "Unknown", y: n(r.visits) }));
    const vax = careByMonth.map((r) => ({ x: r.month ?? "Unknown", y: n(r.vaccinations) }));
    const weights = careByMonth.map((r) => ({ x: r.month ?? "Unknown", y: n(r.weights) }));

    return [
        { id: "Total", data: total },
        { id: "Visits", data: visits },
        { id: "Vaccinations", data: vax },
        { id: "Weights", data: weights },
    ];
    }, [careByMonth]);

    const visits = careByMonth.map((r) => ({ x: r.month, y: r.visits }));
    const vax = careByMonth.map((r) => ({ x: r.month, y: r.vaccinations }));
    const weights = careByMonth.map((r) => ({ x: r.month, y: r.weights }));

    return [
      { id: "Total", data: months },
      { id: "Visits", data: visits },
      { id: "Vaccinations", data: vax },
      { id: "Weights", data: weights },
    ];
  }, [careByMonth]);

  const pieData = React.useMemo(
    () => vaxByType.map((r) => ({ id: r.type, label: r.type, value: r.count })),
    [vaxByType]
  );

  const barTopOrgs = React.useMemo(
    () => topOrgs.map((r) => ({ org: r.organisation_name, visits: r.visits })),
    [topOrgs]
  );

  const barReasons = React.useMemo(
    () => visitsByReason.map((r) => ({ reason: r.reason, count: r.count })),
    [visitsByReason]
  );

  return (
    <Box>
      <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>
        Admin Analytics
      </Typography>

      <Paper sx={{ p: 2, mb: 2 }}>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
          <TextField
            label="Start date"
            type="date"
            value={start}
            onChange={(e) => setStart(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 200 }}
          />
          <TextField
            label="End date"
            type="date"
            value={end}
            onChange={(e) => setEnd(e.target.value)}
            InputLabelProps={{ shrink: true }}
            sx={{ minWidth: 200 }}
          />
          <TextField
            label="Organisation (optional)"
            value={organisationId}
            onChange={(e) => setOrganisationId(e.target.value)}
            placeholder="Paste organisation UUID"
            sx={{ minWidth: 320 }}
          />
        </Stack>
      </Paper>

      {loading && (
        <Paper sx={{ p: 3, display: "flex", alignItems: "center", gap: 2 }}>
          <CircularProgress size={22} />
          <Typography>Loading analytics…</Typography>
        </Paper>
      )}

      {!loading && kpis && (
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} sx={{ mb: 2 }}>
          {[
            ["Pets", kpis.pets],
            ["Owners", kpis.owners],
            ["Visits", kpis.visits],
            ["Vaccinations", kpis.vaccinations],
            ["Weights", kpis.weights],
            ["Organisations", kpis.organisations],
          ].map(([label, value]) => (
            <Paper key={label} sx={{ p: 2, flex: 1 }}>
              <Typography variant="body2" sx={{ opacity: 0.7 }}>
                {label}
              </Typography>
              <Typography variant="h5" fontWeight={900}>
                {value}
              </Typography>
            </Paper>
          ))}
        </Stack>
      )}

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2} sx={{ mb: 2 }}>
        <Paper sx={{ p: 2, height: 420, flex: 2 }}>
          <Typography fontWeight={800} sx={{ mb: 1 }}>
            Care events over time
          </Typography>
          <Box sx={{ height: 360 }}>
            <ResponsiveLine
              data={lineData}
              margin={{ top: 20, right: 20, bottom: 50, left: 50 }}
              xScale={{ type: "point" }}
              yScale={{ type: "linear", min: "auto", max: "auto" }}
              axisBottom={{ tickRotation: -35 }}
              pointSize={6}
              useMesh
            />
          </Box>
        </Paper>

        <Paper sx={{ p: 2, height: 420, flex: 1 }}>
          <Typography fontWeight={800} sx={{ mb: 1 }}>
            Vaccinations by type
          </Typography>
          <Box sx={{ height: 360 }}>
            <ResponsivePie
              data={pieData}
              margin={{ top: 20, right: 20, bottom: 20, left: 20 }}
              innerRadius={0.6}
              padAngle={1}
              cornerRadius={3}
            />
          </Box>
        </Paper>
      </Stack>

      <Stack direction={{ xs: "column", lg: "row" }} spacing={2}>
        <Paper sx={{ p: 2, height: 420, flex: 1 }}>
          <Typography fontWeight={800} sx={{ mb: 1 }}>
            Top organisations by visits
          </Typography>
          <Box sx={{ height: 360 }}>
            <ResponsiveBar
              data={barTopOrgs}
              keys={["visits"]}
              indexBy="org"
              margin={{ top: 20, right: 20, bottom: 90, left: 60 }}
              axisBottom={{ tickRotation: -35 }}
              labelSkipWidth={12}
              labelSkipHeight={12}
            />
          </Box>
        </Paper>

        <Paper sx={{ p: 2, height: 420, flex: 1 }}>
          <Typography fontWeight={800} sx={{ mb: 1 }}>
            Visits by reason
          </Typography>
          <Box sx={{ height: 360 }}>
            <ResponsiveBar
              data={barReasons}
              keys={["count"]}
              indexBy="reason"
              margin={{ top: 20, right: 20, bottom: 90, left: 60 }}
              axisBottom={{ tickRotation: -35 }}
              labelSkipWidth={12}
              labelSkipHeight={12}
            />
          </Box>
        </Paper>
      </Stack>
    </Box>
  );
}
