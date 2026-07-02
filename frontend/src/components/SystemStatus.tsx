import { Chip, Stack, Tooltip } from "@mui/material";
import { useEffect, useState } from "react";

import { getSystemStatus, type HealthState } from "../api/systemStatus";

export function SystemStatus() {
  const [apiStatus, setApiStatus] = useState<HealthState>("checking");
  const [databaseStatus, setDatabaseStatus] = useState<HealthState>("checking");

  useEffect(() => {
    let active = true;

    async function checkStatus() {
      const result = await getSystemStatus();
      if (!active) {
        return;
      }
      setApiStatus(result.apiStatus);
      setDatabaseStatus(result.databaseStatus);
    }

    void checkStatus();

    return () => {
      active = false;
    };
  }, []);

  return (
    <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
      <Tooltip title="Conexao com a API FastAPI">
        <Chip
          size="small"
          label={apiStatus === "checking" ? "API verificando" : apiStatus === "ok" ? "API online" : "API offline"}
          color={apiStatus === "ok" ? "success" : apiStatus === "checking" ? "default" : "error"}
          variant="outlined"
        />
      </Tooltip>
      <Tooltip title="Conexao com o PostgreSQL">
        <Chip
          size="small"
          label={
            databaseStatus === "checking"
              ? "Banco verificando"
              : databaseStatus === "ok"
                ? "Banco online"
                : databaseStatus === "warning"
                  ? "Banco indisponivel"
                  : "Banco offline"
          }
          color={databaseStatus === "ok" ? "success" : databaseStatus === "checking" ? "default" : databaseStatus === "warning" ? "warning" : "error"}
          variant="outlined"
        />
      </Tooltip>
    </Stack>
  );
}
