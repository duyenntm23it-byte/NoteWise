"use client";

import { createContext, useContext, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import type { ReactNode } from "react";

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
const TOKEN_STORAGE_KEY = "notewise_access_token";

export interface AuthUser {
  id: string;
  email: string;
}

interface TokenResponse {
  access_token: string;
  token_type: "bearer";
  user?: AuthUser;
}

interface AuthContextValue {
  user: AuthUser | null;
  isLoading: boolean;
  sessionError: string | null;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextValue | null>(null);

function isAuthUser(value: unknown): value is AuthUser {
  return (
    typeof value === "object" &&
    value !== null &&
    "id" in value &&
    typeof value.id === "string" &&
    "email" in value &&
    typeof value.email === "string"
  );
}

function isTokenResponse(value: unknown): value is TokenResponse {
  return (
    typeof value === "object" &&
    value !== null &&
    "access_token" in value &&
    typeof value.access_token === "string" &&
    "token_type" in value &&
    value.token_type === "bearer"
  );
}

function responseError(payload: unknown): string {
  if (
    typeof payload === "object" &&
    payload !== null &&
    "detail" in payload &&
    typeof payload.detail === "string"
  ) {
    return payload.detail;
  }
  return "The request could not be completed. Please try again.";
}

async function readJson(response: Response): Promise<unknown> {
  return response.json();
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [sessionError, setSessionError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;

    async function restoreSession() {
      const token = window.sessionStorage.getItem(TOKEN_STORAGE_KEY);
      if (!token) {
        setIsLoading(false);
        return;
      }

      try {
        const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (response.status === 401) {
          window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
          return;
        }
        const payload = await readJson(response);
        if (!response.ok) {
          throw new Error(responseError(payload));
        }
        if (!isAuthUser(payload)) {
          throw new Error("The API returned an unexpected profile response.");
        }
        if (!cancelled) {
          setUser(payload);
          setSessionError(null);
        }
      } catch (error) {
        if (!cancelled) {
          setSessionError(
            error instanceof Error ? error.message : "Unable to restore your session.",
          );
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    }

    void restoreSession();
    return () => {
      cancelled = true;
    };
  }, []);

  async function establishSession(
    endpoint: "register" | "token",
    email: string,
    password: string,
  ) {
    const isRegistration = endpoint === "register";
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": isRegistration
          ? "application/json"
          : "application/x-www-form-urlencoded",
      },
      body: isRegistration
        ? JSON.stringify({ email, password })
        : new URLSearchParams({ username: email, password }).toString(),
    });
    const payload = await readJson(response);
    if (!response.ok) {
      throw new Error(responseError(payload));
    }
    if (!isTokenResponse(payload)) {
      throw new Error("The API returned an unexpected authentication response.");
    }

    let authenticatedUser = payload.user;
    if (!isAuthUser(authenticatedUser)) {
      const profileResponse = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
        headers: { Authorization: `Bearer ${payload.access_token}` },
      });
      const profilePayload = await readJson(profileResponse);
      if (!profileResponse.ok) {
        throw new Error(responseError(profilePayload));
      }
      if (!isAuthUser(profilePayload)) {
        throw new Error("The API returned an unexpected profile response.");
      }
      authenticatedUser = profilePayload;
    }

    window.sessionStorage.setItem(TOKEN_STORAGE_KEY, payload.access_token);
    setUser(authenticatedUser);
    setSessionError(null);
  }

  async function login(email: string, password: string) {
    await establishSession("token", email, password);
  }

  async function register(email: string, password: string) {
    await establishSession("register", email, password);
  }

  function logout() {
    window.sessionStorage.removeItem(TOKEN_STORAGE_KEY);
    setUser(null);
    setSessionError(null);
    router.replace("/login");
  }

  const value = useMemo(
    () => ({ user, isLoading, sessionError, login, register, logout }),
    [user, isLoading, sessionError],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
