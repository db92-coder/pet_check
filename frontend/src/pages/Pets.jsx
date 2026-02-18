import React from "react";
import { Box, Paper, Typography } from "@mui/material";
import { DataGrid } from "@mui/x-data-grid";
import { api } from "../api/client.js";

export default function Pets() {
  const [rows, setRows] = React.useState([]);
  const [loading, setLoading] = React.useState(true);

  React.useEffect(() => {
    let mounted = true;

    async function load() {
      try {
        setLoading(true);
        // Adjust endpoint to match your backend
        const res = await api.get("/pets", { params: { limit: 200 } });
        if (!mounted) return;

        // Expect: [{ id, name, species, breed, owner_name, suburb, clinic_name, created_at }, ...]
        setRows(res.data);
      } finally {
        if (mounted) setLoading(false);
      }
    }

    load();
    return () => {
      mounted = false;
    };
  }, []);

  const columns = [
    { field: "id", headerName: "ID", width: 90 },
    { field: "name", headerName: "Name", flex: 1, minWidth: 140 },
    { field: "species", headerName: "Species", width: 130 },
    { field: "breed", headerName: "Breed", flex: 1, minWidth: 160 },
    { field: "owner_name", headerName: "Owner", flex: 1, minWidth: 180 },
    { field: "suburb", headerName: "Suburb", width: 140 },
    { field: "clinic_name", headerName: "Clinic", flex: 1, minWidth: 180 },
  ];

  return (
    <Box>
      <Typography variant="h5" fontWeight={800} sx={{ mb: 2 }}>
        Pets
      </Typography>

      <Paper sx={{ height: 620 }}>
        <DataGrid
          rows={rows}
          columns={columns}
          loading={loading}
          pageSizeOptions={[25, 50, 100]}
          initialState={{
            pagination: { paginationModel: { pageSize: 25, page: 0 } },
          }}
          disableRowSelectionOnClick
          getRowId={(r) => r.id}
        />
      </Paper>
    </Box>
  );
}
