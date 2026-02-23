/* Module: Placeholder. */

import React from "react";
import { Paper, Typography } from "@mui/material";

// Primary component for this view/module.
export default function Placeholder({ title }) {
// Render UI layout and interactions.
  return (
    <Paper sx={{ p: 3 }}>
      <Typography variant="h5" fontWeight={800}>{title}</Typography>
      <Typography sx={{ mt: 1, opacity: 0.8 }}>
        Page stub — next we’ll wire this to the API.
      </Typography>
    </Paper>
  );
}

