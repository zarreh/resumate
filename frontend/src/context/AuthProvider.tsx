"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import type { User } from "@/types/auth";
import { apiClient, clearTokens, setTokens, ApiError } from "@/lib/api";

interface AuthContextType {
  user: User | null;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string) => Promise<void>;
  logout: () => void;
  isLoading: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

function hasStoredToken() {
  if (typeof window === "undefined") return false;
  return !!localStorage.getItem("access_token");
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  // Start as loading only if there's a token to check
  const [isLoading, setIsLoading] = useState(hasStoredToken);
  const initialized = useRef(false);

  useEffect(() => {
    if (initialized.current) return;
    initialized.current = true;

    if (!isLoading) return; // no token, already not loading

    let cancelled = false;
    apiClient<User>("/api/v1/auth/me").then(
      (u) => {
        if (cancelled) return;
        setUser(u);
        setIsLoading(false);
      },
      () => {
        if (cancelled) return;
        clearTokens();
        setIsLoading(false);
      },
    );
    return () => {
      cancelled = true;
    };
  }, [isLoading]);

  const login = useCallback(async (email: string, password: string) => {
    const data = await apiClient<{
      access_token: string;
      refresh_token: string;
    }>("/api/v1/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    });
    setTokens(data.access_token, data.refresh_token);
    const u = await apiClient<User>("/api/v1/auth/me");
    setUser(u);
  }, []);

  const register = useCallback(
    async (name: string, email: string, password: string) => {
      const data = await apiClient<{
        access_token: string;
        refresh_token: string;
      }>("/api/v1/auth/register", {
        method: "POST",
        body: JSON.stringify({ name, email, password }),
      });
      setTokens(data.access_token, data.refresh_token);
      const u = await apiClient<User>("/api/v1/auth/me");
      setUser(u);
    },
    [],
  );

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({ user, login, register, logout, isLoading }),
    [user, login, register, logout, isLoading],
  );

  return <AuthContext value={value}>{children}</AuthContext>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}

export { ApiError };
