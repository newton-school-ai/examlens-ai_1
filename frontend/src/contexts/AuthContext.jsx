// Auth context for React app
// Stores: user object, JWT token, isAuthenticated flag
// Provides: login(), logout(), refreshToken()
// Token stored in memory (not localStorage) for security
// Auto-refresh before expiry using refresh token
export default function AuthProvider({ children }) {
  return children; // TODO: implement
}
