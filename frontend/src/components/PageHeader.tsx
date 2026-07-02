import { Box, Stack, Typography } from "@mui/material";
import { ReactNode } from "react";

interface PageHeaderProps {
  title: string;
  subtitle?: string;
  actions?: ReactNode;
}

export function PageHeader({ title, subtitle, actions }: PageHeaderProps) {
  return (
    <Stack direction={{ xs: "column", md: "row" }} justifyContent="space-between" alignItems={{ xs: "stretch", md: "center" }} spacing={2}>
      <Box>
        <Typography variant="h5" fontWeight={700}>
          {title}
        </Typography>
        {subtitle ? <Typography color="text.secondary">{subtitle}</Typography> : null}
      </Box>
      {actions ? <Box>{actions}</Box> : null}
    </Stack>
  );
}
