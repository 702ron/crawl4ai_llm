"""
User management API routes for the Crawl4AI LLM API.

This module provides routes for user management, including creating,
updating, and deleting users. These routes are restricted to administrators.
"""

import logging
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from .auth import User, UserRole, USERS, get_current_user, has_role, register_user

# Setup logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(
    prefix="/users",
    tags=["Users"],
    dependencies=[Depends(has_role([UserRole.ADMIN]))],
    responses={
        401: {"description": "Unauthorized"},
        403: {"description": "Forbidden"},
    },
)


# Request and response models
class UserCreate(BaseModel):
    """Request model for creating a new user."""
    username: str
    roles: List[UserRole] = [UserRole.USER]
    rate_limit: int = Field(default=60, ge=1, le=1000)


class UserResponse(BaseModel):
    """Response model for user data."""
    username: str
    roles: List[UserRole]
    rate_limit: int
    disabled: bool


class UserWithKey(UserResponse):
    """Extended user response that includes the API key."""
    api_key: str


class UserUpdate(BaseModel):
    """Request model for updating a user."""
    roles: Optional[List[UserRole]] = None
    rate_limit: Optional[int] = Field(default=None, ge=1, le=1000)
    disabled: Optional[bool] = None


# Routes
@router.post("/", response_model=UserWithKey, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    admin: User = Depends(get_current_user),
) -> Dict:
    """Create a new user with API key."""
    # Check for duplicate username
    if any(u.username == user_data.username for u in USERS.values()):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"User with username '{user_data.username}' already exists",
        )

    # Register the user
    api_key = register_user(
        username=user_data.username,
        roles=user_data.roles,
        rate_limit=user_data.rate_limit,
    )

    # Get the created user
    user = USERS[api_key]
    
    logger.info(f"Admin '{admin.username}' created new user '{user.username}'")
    
    return {
        "username": user.username,
        "roles": user.roles,
        "rate_limit": user.rate_limit,
        "disabled": user.disabled,
        "api_key": api_key,
    }


@router.get("/", response_model=List[UserResponse])
async def list_users() -> List[Dict]:
    """List all users (without API keys)."""
    return [
        {
            "username": user.username,
            "roles": user.roles,
            "rate_limit": user.rate_limit,
            "disabled": user.disabled,
        }
        for user in USERS.values()
    ]


@router.get("/{username}", response_model=UserResponse)
async def get_user(username: str) -> Dict:
    """Get a user by username."""
    # Find the user
    user = next((u for u in USERS.values() if u.username == username), None)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    return {
        "username": user.username,
        "roles": user.roles,
        "rate_limit": user.rate_limit,
        "disabled": user.disabled,
    }


@router.put("/{username}", response_model=UserResponse)
async def update_user(
    username: str,
    user_data: UserUpdate,
    admin: User = Depends(get_current_user),
) -> Dict:
    """Update a user."""
    # Find the user
    user_api_key = None
    for api_key, user in USERS.items():
        if user.username == username:
            user_api_key = api_key
            break

    if not user_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    user = USERS[user_api_key]

    # Update the user
    if user_data.roles is not None:
        user.roles = user_data.roles
    if user_data.rate_limit is not None:
        user.rate_limit = user_data.rate_limit
    if user_data.disabled is not None:
        user.disabled = user_data.disabled

    logger.info(f"Admin '{admin.username}' updated user '{user.username}'")

    return {
        "username": user.username,
        "roles": user.roles,
        "rate_limit": user.rate_limit,
        "disabled": user.disabled,
    }


@router.delete("/{username}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    username: str,
    admin: User = Depends(get_current_user),
) -> None:
    """Delete a user."""
    # Find the user
    user_api_key = None
    for api_key, user in USERS.items():
        if user.username == username:
            user_api_key = api_key
            break

    if not user_api_key:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found",
        )

    # Don't allow deleting the current user
    if username == admin.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    # Delete the user
    del USERS[user_api_key]
    
    logger.info(f"Admin '{admin.username}' deleted user '{username}'")

    return None 