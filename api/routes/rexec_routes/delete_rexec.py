"""
Register route for tearing down a user's Rexec server.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Form, status

from api.services import rexec_services
from api.services.auth import require_group_membership, validate_token

router = APIRouter()


@router.delete("/terminate", status_code=200)
def delete_rexec_server(
    token: Annotated[str,
        Form(
            title="User token",
            description="Bearer token for validating group membership"
        )
    ],
):
    """
    Delete the caller's rexec server and its namespace.
    """
    user_info = validate_token(token)
    matched_group = require_group_membership(user_info)

    resolved_user_id = str(user_info.get("sub") or "").strip()
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User id could not be resolved from token.",
        )

    username = str(user_info.get('username')).strip()
    try:
        msg = rexec_services.delete_rexec_server_resources(resolved_user_id)
        return {
            "Status": msg,
            "Username": username,
            "NDP_Endpoint_membership": matched_group,
        }
    except Exception as e:
        print(type(e), e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
