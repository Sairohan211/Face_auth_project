"""
Authentication and Authorization Dependencies for FastAPI.
"""

import logging
from typing import Any, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase import supabase
from supabase_auth.errors import AuthApiError

logger = logging.getLogger(__name__)

# Standard Bearer token authentication scheme
bearer_scheme = HTTPBearer(auto_error=True)

async def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)) -> Any:
    """
    Validates the Supabase JWT access token from the Authorization header
    and returns the authenticated user object.
    """
    if credentials is None or not credentials.credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication credentials.",
            headers={"WWW-Authenticate": "Bearer"}
        )

    token = credentials.credentials

    try:
        user_response = supabase.auth.get_user(jwt=token)
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"}
            )
        return user_response.user

    except AuthApiError as auth_err:
        logger.warning("Supabase JWT validation failed: %s", auth_err)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Unexpected error validating token: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed. Please sign in again.",
            headers={"WWW-Authenticate": "Bearer"}
        )
