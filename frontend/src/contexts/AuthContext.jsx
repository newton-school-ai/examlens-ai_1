import { createContext, useContext, useEffect, useMemo, useState } from "react";

const AuthContext = createContext(null);
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const SESSION_STORAGE_KEY = "examlens.auth.session";

function readStoredSession() {
  try {
    const stored = window.localStorage.getItem(SESSION_STORAGE_KEY);
    return stored ? JSON.parse(stored) : null;
  } catch {
    return null;
  }
}

function writeStoredSession(nextSession) {
  try {
    window.localStorage.setItem(SESSION_STORAGE_KEY, JSON.stringify(nextSession));
  } catch {
    // Keep the in-memory session even if browser storage is unavailable.
  }
}

function clearStoredSession() {
  try {
    window.localStorage.removeItem(SESSION_STORAGE_KEY);
  } catch {
    // Storage may be blocked in private or restricted browser contexts.
  }
}

export function AuthProvider({ children }) {
  const [session, setSession] = useState(() => readStoredSession());
  const [isAuthLoading, setIsAuthLoading] = useState(() =>
    Boolean(session?.refresh_token),
  );

  function persistSession(nextSession) {
    setSession(nextSession);
    writeStoredSession(nextSession);
  }

  function clearSession() {
    setSession(null);
    clearStoredSession();
  }

  async function refreshStoredSession(refreshTokenValue) {
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshTokenValue }),
    });
    if (!response.ok) {
      clearSession();
      return null;
    }
    const nextSession = await response.json();
    persistSession(nextSession);
    return nextSession.access_token;
  }

  useEffect(() => {
    const storedSession = readStoredSession();
    if (!storedSession?.refresh_token) {
      setIsAuthLoading(false);
      return;
    }

    let isMounted = true;
    refreshStoredSession(storedSession.refresh_token)
      .catch(() => null)
      .finally(() => {
        if (isMounted) setIsAuthLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function login(code) {
    const response = await fetch(`${API_URL}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!response.ok) throw new Error("Google sign-in failed");
    const nextSession = await response.json();
    persistSession(nextSession);
    return nextSession;
  }

  async function refreshToken() {
    const refreshTokenValue =
      session?.refresh_token || readStoredSession()?.refresh_token;
    if (!refreshTokenValue) return null;
    return refreshStoredSession(refreshTokenValue);
  }

  const value = useMemo(() => ({
    accessToken: session?.access_token || null,
    isAuthLoading,
    isAuthenticated: Boolean(session?.access_token),
    login,
    logout: clearSession,
    refreshToken,
    user: session?.user || null,
  }), [isAuthLoading, session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
