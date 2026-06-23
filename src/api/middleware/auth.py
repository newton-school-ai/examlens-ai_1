"""JWT verification middleware and role-based access control."""

# verify_token() - Decode and validate JWT from Authorization header
# get_current_user() - FastAPI dependency that returns authenticated user
# require_role(role) - Dependency factory for role-based access
# (student/contributor)
# Public routes (question bank, analytics) skip auth
# Protected routes (upload, mock, study plan) require valid JWT
