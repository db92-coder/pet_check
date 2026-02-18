import React from "react";
import { Paper, Typography } from "@mui/material";

export default function Dashboard() {
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={800}>Dashboard</Typography>
      <Typography sx={{ mt: 1, opacity: 0.8 }}>
        Welcome to Pet Check. We’ll show visit stats and alerts here.
      </Typography>
    </Paper>
  );
}