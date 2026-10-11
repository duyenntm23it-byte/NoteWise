"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  ACCESS_TOKEN_KEY,
  API_BASE_URL,
  clearAccessToken,
  SESSION_CHANGED_EVENT,
  type AuthenticatedUser,
} from "../lib/api";

interface SessionContextValue {
  isLoading: boolean;
  user: AuthenticatedUser | null;
  error: string | null;
  logout: () => void;
  retryVerification: () => void;
}

interface SessionChangedDetail {
  token: string | null;
  user: AuthenticatedUser | null;
}

const SessionContext = createContext<SessionContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<AuthenticatedUser | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [verificationKey, setVerificationKey] = useState(0);

  useEffect(() => {
    let active = true;
    const handleSessionChange = (event: Event) => {
      active = false;
      const detail = (event as CustomEvent<SessionChangedDetail>).detail;
      setUser(detail.user);
      setError(null);
      setIsLoading(false);
    };

    window.addEventListener(SESSION_CHANGED_EVENT, handleSessionChange);
    const token = localStorage.getItem(ACCESS_TOKEN_KEY);
    if (!token) {
      setUser(null);
      setError(null);
      setIsLoading(false);
      return () => {
        active = false;
        window.removeEventListener(SESSION_CHANGED_EVENT, handleSessionChange);
      };
    }

    setIsLoading(true);
    setError(null);
    fetch(`${API_BASE_URL}/api/v1/me`, {
      headers: { Authorization: `Bearer ${token}` },
    })
      .then(async (response) => {
        if (response.status === 401) {
          clearAccessToken();
          return null;
        }
        if (!response.ok) {
          throw new Error("Unable to verify your session.");
        }
        return (await response.json()) as AuthenticatedUser;
      })
      .then((verifiedUser) => {
        if (active) {
          setUser(verifiedUser);
          setIsLoading(false);
        }
      })
      .catch(() => {
        if (active) {
          setError("Unable to verify your session. Please try again.");
          setIsLoading(false);
        }
      });

    return () => {
      active = false;
      window.removeEventListener(SESSION_CHANGED_EVENT, handleSessionChange);
    };
  }, [verificationKey]);

  const logout = useCallback(() => {
    clearAccessToken();
  }, []);
  const retryVerification = useCallback(() => {
    setVerificationKey((key) => key + 1);
  }, []);

  const value = useMemo(
    () => ({ isLoading, user, error, logout, retryVerification }),
    [isLoading, user, error, logout, retryVerification],
  );

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  );
}

export function useAuth(): SessionContextValue {
  const context = useContext(SessionContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider.");
  }
  return context;
}
