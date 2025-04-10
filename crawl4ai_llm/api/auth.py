"""
Authentication and authorization for the Crawl4AI LLM API.

This module implements API key authentication and role-based access control
for the API endpoints. It also provides rate limiting functionality.
"""

import os
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from fastapi import Depends, HTTPException, Request, Security, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field

# API Key header
API_KEY_HEADER = APIKeyHeader(name="X-API-Key", auto_error=False)

# Rate limiting settings (configurable via environment variables)
RATE_LIMIT_WINDOW = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))
DEFAULT_RATE_LIMIT = int(os.getenv("DEFAULT_RATE_LIMIT", "60"))  # 60 requests per minute


class UserRole(str, Enum):
    """User roles for access control."""
    ADMIN = "admin"
    USER = "user"
    READONLY = "readonly"


class User(BaseModel):
    """User model with API key and roles."""
    username: str
    api_key: str
    roles: List[UserRole] = [UserRole.USER]
    rate_limit: int = DEFAULT_RATE_LIMIT
    disabled: bool = False


# In-memory user store (in production, this would be a database)
# Format: {"api_key": User}
USERS: Dict[str, User] = {}

# Initialize with admin user from environment if available
ADMIN_API_KEY = os.getenv("ADMIN_API_KEY")
if ADMIN_API_KEY:
    USERS[ADMIN_API_KEY] = User(
        username="admin",
        api_key=ADMIN_API_KEY,
        roles=[UserRole.ADMIN],
        rate_limit=int(os.getenv("ADMIN_RATE_LIMIT", "120")),
    )

# In-memory rate limiting store
# Format: {"api_key": [(timestamp, endpoint), ...]}
RATE_LIMIT_STORE: Dict[str, List[tuple]] = {}


async def get_current_user(
    api_key: str = Security(API_KEY_HEADER),
) -> User:
    """Get the current user from the API key."""
    if not api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Please provide a valid API key.",
            headers={"WWW-Authenticate": "APIKey"},
        )

    user = USERS.get(api_key)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
            headers={"WWW-Authenticate": "APIKey"},
        )

    if user.disabled:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is disabled",
        )

    return user


def has_role(required_roles: List[UserRole]) -> bool:
    """Check if user has any of the required roles."""
    def role_checker(user: User = Depends(get_current_user)) -> User:
        for role in required_roles:
            if role in user.roles:
                return user
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Insufficient permissions. Required roles: {', '.join(r.value for r in required_roles)}",
        )
    return role_checker


async def check_rate_limit(request: Request, user: User = Depends(get_current_user)) -> User:
    """Check rate limit for the current user and endpoint."""
    # Get the current endpoint from the request
    endpoint = request.url.path

    # Get the current time
    current_time = time.time()

    # Initialize the rate limit store for this user if it doesn't exist
    if user.api_key not in RATE_LIMIT_STORE:
        RATE_LIMIT_STORE[user.api_key] = []

    # Clean up old requests (outside the window)
    RATE_LIMIT_STORE[user.api_key] = [
        (ts, ep) for ts, ep in RATE_LIMIT_STORE[user.api_key]
        if current_time - ts < RATE_LIMIT_WINDOW
    ]

    # Check if the user has exceeded their rate limit
    if len(RATE_LIMIT_STORE[user.api_key]) >= user.rate_limit:
        retry_after = RATE_LIMIT_WINDOW - (current_time - RATE_LIMIT_STORE[user.api_key][0][0])
        retry_after = max(1, int(retry_after))
        
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    # Add the current request to the store
    RATE_LIMIT_STORE[user.api_key].append((current_time, endpoint))

    return user


# User management functions
def register_user(username: str, roles: List[UserRole] = [UserRole.USER], rate_limit: int = DEFAULT_RATE_LIMIT) -> str:
    """Register a new user and return the API key."""
    # Generate a new API key (in production, use a more secure method)
    import secrets
    api_key = secrets.token_hex(16)
    
    # Create the user
    USERS[api_key] = User(
        username=username,
        api_key=api_key,
        roles=roles,
        rate_limit=rate_limit,
    )
    
    return api_key 