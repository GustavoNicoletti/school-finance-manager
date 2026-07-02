import { Card, CardContent, Stack, Typography } from "@mui/material";
import { ReactNode } from "react";

interface StatCardProps {
  title: string;
  value: string | number;
  helper?: string;
  icon?: ReactNode;
  trend?: string;
  trendColor?: string;
}

export function StatCard({ title, value, helper, icon, trend, trendColor = "text.secondary" }: StatCardProps) {
  return (
    <Card variant="outlined" sx={{ height: "100%", borderRadius: 2 }}>
      <CardContent>
        <Stack direction="row" spacing={2} alignItems="center" justifyContent="space-between">
          <Stack spacing={0.5}>
            <Typography variant="body2" color="text.secondary">
              {title}
            </Typography>
            <Typography variant="h5" fontWeight={700}>
              {value}
            </Typography>
            {helper ? (
              <Typography variant="caption" color="text.secondary">
                {helper}
              </Typography>
            ) : null}
            {trend ? (
              <Typography variant="caption" sx={{ color: trendColor, fontWeight: 600 }}>
                {trend}
              </Typography>
            ) : null}
          </Stack>
          {icon}
        </Stack>
      </CardContent>
    </Card>
  );
}
