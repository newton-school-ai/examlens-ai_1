import { createContext, useContext, useMemo, useState } from "react";

const AuthContext = createContext(null);
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export function AuthProvider({ children }) {
  const [session, setSession] = useState(null);

  async function login(code) {
    const response = await fetch(`${API_URL}/api/auth/google`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code }),
    });
    if (!response.ok) throw new Error("Google sign-in failed");
    const nextSession = await response.json();
    setSession(nextSession);
    return nextSession;
  }

  async function refreshToken() {
    if (!session?.refresh_token) return null;
    const response = await fetch(`${API_URL}/api/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: session.refresh_token }),
    });
    if (!response.ok) {
      setSession(null);
      return null;
    }
    const nextSession = await response.json();
    setSession(nextSession);
    return nextSession.access_token;
  }

  const value = useMemo(() => ({
    accessToken: session?.access_token || null,
    isAuthenticated: Boolean(session?.access_token),
    login,
    logout: () => setSession(null),
    refreshToken,
    user: session?.user || null,
  }), [session]);

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}
