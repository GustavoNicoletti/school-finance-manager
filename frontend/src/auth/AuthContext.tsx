import { createContext, ReactNode, useContext, useEffect, useMemo, useState } from "react";

import { api, clearStoredAccessToken, setStoredAccessToken } from "../api/api";
import { User } from "../types";

interface AuthContextValue {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  async function fetchCurrentUser() {
    const { data } = await api.get<User>("/auth/me");
    setUser(data);
    return data;
  }

  async function refreshUser() {
    try {
      await fetchCurrentUser();
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    let active = true;

    async function loadUser() {
      if (!active) {
        return;
      }
      await refreshUser();
    }

    loadUser();
    return () => {
      active = false;
    };
  }, []);

  useEffect(() => {
    function handleUnauthorized() {
      setUser(null);
    }

    window.addEventListener("auth:unauthorized", handleUnauthorized);
    return () => window.removeEventListener("auth:unauthorized", handleUnauthorized);
  }, []);

  async function login(email: string, password: string) {
    const { data } = await api.post<{ access_token: string; user: User }>("/auth/login", { email, password });
    setStoredAccessToken(data.access_token);
    setUser(data.user);
    setLoading(false);
  }

  async function logout() {
    try {
      await api.post("/auth/logout");
    } finally {
      clearStoredAccessToken();
      setUser(null);
    }
  }

  const value = useMemo(() => ({ user, loading, login, logout, refreshUser }), [user, loading]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth deve ser usado dentro de AuthProvider.");
  }
  return context;
}
