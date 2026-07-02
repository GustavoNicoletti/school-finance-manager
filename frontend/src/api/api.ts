import axios from "axios";

const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const ACCESS_TOKEN_STORAGE_KEY = "gestao_escolar_access_token";

function resolveApiBaseUrl() {
  if (configuredApiUrl && configuredApiUrl.length > 0) {
    return configuredApiUrl;
  }
  return "/api";
}

export const API_BASE_URL = resolveApiBaseUrl();
export const API_ROOT_URL = API_BASE_URL.startsWith("http") ? API_BASE_URL.replace(/\/api\/?$/, "") : "";

export const api = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
  headers: {
    "Content-Type": "application/json",
  },
});

export function getStoredAccessToken() {
  return window.sessionStorage.getItem(ACCESS_TOKEN_STORAGE_KEY) ?? "";
}

export function setStoredAccessToken(token: string) {
  if (!token) {
    return;
  }
  window.sessionStorage.setItem(ACCESS_TOKEN_STORAGE_KEY, token);
}

export function clearStoredAccessToken() {
  window.sessionStorage.removeItem(ACCESS_TOKEN_STORAGE_KEY);
}

api.interceptors.request.use((config) => {
  const token = getStoredAccessToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

function formatValidationDetail(detail: unknown) {
  if (!Array.isArray(detail)) {
    return null;
  }

  const messages = detail
    .map((item) => {
      if (!item || typeof item !== "object") {
        return null;
      }
      const loc = Array.isArray((item as { loc?: unknown }).loc) ? (item as { loc: unknown[] }).loc.slice(1).join(" > ") : "";
      const msg = typeof (item as { msg?: unknown }).msg === "string" ? (item as { msg: string }).msg : "";
      if (!msg) {
        return null;
      }
      return loc ? `${loc}: ${msg}` : msg;
    })
    .filter((message): message is string => Boolean(message));

  return messages.length > 0 ? messages.join(" | ") : null;
}

async function extractErrorMessage(detail: unknown) {
  if (detail instanceof Blob) {
    try {
      const text = await detail.text();
      const parsed = JSON.parse(text) as { detail?: unknown };
      const blobDetail = parsed?.detail;
      if (typeof blobDetail === "string" && blobDetail.trim().length > 0) {
        return blobDetail;
      }
      const validationMessage = formatValidationDetail(blobDetail);
      if (validationMessage) {
        return validationMessage;
      }
    } catch {
      return null;
    }
  }

  const validationMessage = formatValidationDetail(detail);
  if (validationMessage) {
    return validationMessage;
  }

  return typeof detail === "string" ? detail : null;
}

api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      clearStoredAccessToken();
      window.dispatchEvent(new Event("auth:unauthorized"));
    }

    const detail = error.response?.data?.detail;
    const message = (await extractErrorMessage(detail ?? error.response?.data)) ?? "Nao foi possivel concluir a operacao.";
    return Promise.reject(new Error(typeof message === "string" ? message : "Nao foi possivel concluir a operacao."));
  },
);

export async function downloadFile(path: string, filename: string, params?: Record<string, unknown>) {
  const response = await api.get<Blob>(path, {
    params,
    responseType: "blob",
  });
  const contentDisposition = response.headers["content-disposition"];
  const matchedFilename = typeof contentDisposition === "string" ? contentDisposition.match(/filename="([^"]+)"/i) : null;
  const resolvedFilename = matchedFilename?.[1] || filename;
  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = resolvedFilename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export const downloadCsv = downloadFile;
