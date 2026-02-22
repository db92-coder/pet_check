/* Module: Pets. */

import React from "react";
import { Box, Paper, Typography, Stack, TextField, InputAdornment, IconButton } from "@mui/material";
import { DataGrid, GridToolbar } from "@mui/x-data-grid";
import SearchIcon from "@mui/icons-material/Search";
import ClearIcon from "@mui/icons-material/Clear";
import { api } from "../api/client.js";

function formatDate(value) {
  if (!value) return "-";
  const d = new Date(value);
  return Number.isNaN(d.getTime()) ? String(value) : d.toLocaleDateString();
}

export default function Pets() {
  const [rows, setRows] = React.useState([]);
  const [loading, setLoading] = React.useState(true);
  const [search, setSearch] = React.useState("");

  React.useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);
        const res = await api.get("/pets", { params: { limit: 200 } });
        if (!mounted) return;
        const mapped = (Array.isArray(res.data) ? res.data : []).map((r) => ({
          ...r,
          id_short: r?.id ? String(r.id).slice(0, 8) : "-",
          date_of_birth_display: formatDate(r?.date_of_birth),
          created_at_display: formatDate(r?.created_at),
          clinic_name_display: r?.clinic_name || "-",
          owner_email_display: r?.owner_email || "-",
          owner_id_display: r?.owner_id || "-",
          verified_display: r?.verified_identity_level ?? "-",
        }));
        setRows(mapped);
      } catch (e) {
        console.error("Pets load failed:", e);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const filteredRows = React.useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return rows;

    return rows.filter((row) => {
      const values = [
        row.id,
        row.id_short,
        row.name,
        row.species,
        row.breed,
        row.sex,
        row.date_of_birth_display,
        row.created_at_display,
        row.clinic_name_display,
        row.owner_email_display,
        row.owner_id_display,
        row.verified_display,
      ];
      return values.some((v) => String(v ?? "").toLowerCase().includes(q));
    });
  }, [rows, search]);

  const columns = [
    {
      field: "id_short",
      headerName: "ID",
      width: 120,
      renderCell: (params) => <span title={params.row?.id || ""}>{params.value}</span>,
    },
    { field: "name", headerName: "Name", width: 150 },
    { field: "species", headerName: "Species", width: 120 },
    { field: "breed", headerName: "Breed", width: 150 },
    { field: "sex", headerName: "Sex", width: 90 },
    { field: "date_of_birth_display", headerName: "DOB", width: 120 },
    { field: "created_at_display", headerName: "Created", width: 120 },
    { field: "clinic_name_display", headerName: "Clinic", width: 180 },
    { field: "owner_email_display", headerName: "Owner Email", width: 220 },
    { field: "owner_id_display", headerName: "Owner ID", width: 260 },
    { field: "verified_display", headerName: "Verified", width: 100 },
  ];

  return (
    <Box>
      <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>
        Pets
      </Typography>
      <Stack direction={{ xs: "column", sm: "row" }} sx={{ mb: 1.5 }}>
        <TextField
          fullWidth
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search pets, owners, clinics, IDs..."
          size="small"
          InputProps={{
            startAdornment: (
              <InputAdornment position="start">
                <SearchIcon fontSize="small" />
              </InputAdornment>
            ),
            endAdornment: search ? (
              <InputAdornment position="end">
                <IconButton aria-label="clear search" edge="end" size="small" onClick={() => setSearch("")}>
                  <ClearIcon fontSize="small" />
                </IconButton>
              </InputAdornment>
            ) : null,
          }}
        />
      </Stack>

      <Paper
        sx={{
          width: 1400,
          height: 617.778,
          maxWidth: "100%",
          overflowX: "auto",
        }}
      >
        <DataGrid
          rows={filteredRows}
          columns={columns}
          loading={loading}
          density="compact"
          pageSizeOptions={[25, 50, 100]}
          slots={{ toolbar: GridToolbar }}
          slotProps={{
            toolbar: {
              showQuickFilter: false,
              csvOptions: { disableToolbarButton: true },
              printOptions: { disableToolbarButton: true },
            },
          }}
          initialState={{
            pagination: { paginationModel: { pageSize: 25, page: 0 } },
            sorting: { sortModel: [{ field: "created_at", sort: "desc" }] },
          }}
          disableRowSelectionOnClick
          getRowId={(r) => r.id}
        />
      </Paper>
    </Box>
  );
}

