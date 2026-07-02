import { API_ROOT_URL } from "./api";

export type HealthState = "checking" | "ok" | "warning" | "error";

export interface SystemStatusResult {
  apiStatus: HealthState;
  databaseStatus: HealthState;
}

const STATUS_TTL_MS = 30 * 1000;

let cachedStatus: SystemStatusResult | null = null;
let cachedAt = 0;
let pendingPromise: Promise<SystemStatusResult> | null = null;

async function fetchHealth(path: string) {
  const primaryUrl = `${API_ROOT_URL}${path}`;
  const fallbackUrl = primaryUrl.replace("://localhost", "://127.0.0.1");

  try {
    return await fetch(primaryUrl);
  } catch (error) {
    if (fallbackUrl === primaryUrl) {
      throw error;
    }

    return fetch(fallbackUrl);
  }
}

export async function getSystemStatus(force = false): Promise<SystemStatusResult> {
  const now = Date.now();

  if (!force && cachedStatus && now - cachedAt < STATUS_TTL_MS) {
    return cachedStatus;
  }

  if (pendingPromise) {
    return pendingPromise;
  }

  pendingPromise = (async () => {
    let apiStatus: HealthState = "error";
    let databaseStatus: HealthState = "error";

    try {
      const apiResponse = await fetchHealth("/health");
      apiStatus = apiResponse.ok ? "ok" : "error";
    } catch {
      apiStatus = "error";
    }

    try {
      const databaseResponse = await fetchHealth("/health/db");
      const databaseData = await databaseResponse.json();
      databaseStatus = databaseData.database === "available" ? "ok" : "warning";
    } catch {
      databaseStatus = "error";
    }

    const value = { apiStatus, databaseStatus };
    cachedStatus = value;
    cachedAt = Date.now();
    pendingPromise = null;
    return value;
  })();

  return pendingPromise;
}
