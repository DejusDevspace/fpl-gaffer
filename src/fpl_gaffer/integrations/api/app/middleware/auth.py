from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from fpl_gaffer.integrations.api.app.services.supabase import supabase_client

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[dict]:
    """
    Dependency to get current user from JWT token.
    Verifies JWT using asymmetric JWKS verification.
    """
    if not credentials:
        return None

    token = credentials.credentials

    # Verify JWT using JWKS
    claims = await supabase_client.verify_jwt(token)

    if not claims:
        return None

    return claims


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Dependency that requires authentication."""
    if not credentials:
        raise HTTPException(
            status_code=401,
            detail="Missing authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    claims = await supabase_client.verify_jwt(token)

    if not claims:
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return claims


async def require_admin(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> dict:
    """Dependency that requires admin role."""
    claims = await require_auth(credentials)

    role = claims.get("role", "")

    # Check if user has admin privileges
    # TODO: customize this based on role structure
    # Also add custom admin role check
    if role not in ["service_role", "authenticated"]:
        raise HTTPException(
            status_code=403,
            detail="Insufficient permissions"
        )

    return claims
