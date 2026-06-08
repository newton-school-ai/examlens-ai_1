"""Google OAuth authentication routes."""

# POST /api/auth/google - Exchange Google auth code for JWT
# GET /api/auth/google/callback - OAuth redirect handler
# POST /api/auth/refresh - Refresh expired JWT using refresh token
# POST /api/auth/logout - Invalidate refresh token
