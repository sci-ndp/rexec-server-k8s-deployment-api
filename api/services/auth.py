"""
Helper utilities for validating tokens and enforcing group membership.
"""

from typing import Any, Dict, List, Optional

import requests
from fastapi import HTTPException, status

from api.config.swagger import settings as swagger_settings


def get_allowed_groups() -> List[str]:
    """Return configured allowed groups in lowercase without leading slashes."""
    print(f"Configured allowed groups: {swagger_settings.group_names}")
    allowed: List[str] = []
    for group in swagger_settings.group_names.split(","):
        cleaned = group.strip().lower().lstrip("/")
        if cleaned:
            allowed.append(cleaned)
    return allowed


def validate_token(token: str) -> Dict[str, Any]:
    """Validate the provided token via the configured auth service."""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token is required.",
        )
    print(f"Received token: {token}")
    try:
        response = requests.post(
            swagger_settings.auth_api_url,
            json={"token": token},
            timeout=10,
        )
    except requests.exceptions.RequestException as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Auth service unavailable: {exc}",
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )
    if response.status_code == 403:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Token does not have sufficient permissions",
        )
    if response.status_code == 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Authentication service error",
        )
    if response.status_code != 200:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=(
                f"Authentication service returned unexpected response "
                f"(HTTP {response.status_code})."
            ),
        )

    data = response.json()
    print(f"Token validation response data: {data}")
    if "error" in data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token validation failed: {data['error']}",
        )
    if "sub" not in data:
        data["sub"] = "unknown"
    return data


def require_group_membership(user_info: Dict[str, Any]) -> Optional[str]:
    """
    Enforce allowed group membership when the feature is enabled.

    Returns the matched group name (lowercase) or None when group-based
    access control is disabled.
    """
    if not swagger_settings.enable_group_based_access:
        return None

    allowed_groups = get_allowed_groups()
    if not allowed_groups:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Group-based access is enabled but no groups are configured.",
        )

    user_groups = user_info.get("groups", [])
    print(f"User {user_info.get('sub', 'unknown')} groups membership: {user_groups}")
    for group in user_groups:
        if isinstance(group, str):
            group_value = group.lower().lstrip("/")
        elif isinstance(group, dict):
            group_value = str(
                group.get("path")
                or group.get("name")
                or ""
            ).lower().lstrip("/")
        else:
            continue

        if group_value and group_value in allowed_groups:
            return group_value

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Access forbidden: user is not a member of an allowed group.",
    )
