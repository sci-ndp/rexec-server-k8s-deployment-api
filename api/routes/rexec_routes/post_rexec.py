"""
Register route for provisioning user Rexec server.
"""

from typing import Annotated

from fastapi import APIRouter, HTTPException, Form, status

from api.services import rexec_services
from api.services.auth import require_group_membership, validate_token

router = APIRouter()


@router.post("/rexec/spawn", status_code=200)
def create_rexec_server(
    requirments: Annotated[list[str],
        Form(
            title="Requirements",
            description="User-specified package list provided by requirements.txt",
        )
    ],
    token: Annotated[str,
        Form(
            title="User token",
            description="Bearer token for validating group membership"
        )
    ],
):
    """
    Create a new rexec server for a user in a unique namespace.
    """
    user_info = validate_token(token)
    matched_group = require_group_membership(user_info)

    resolved_user_id = str(user_info.get("sub") or "").strip()
    if not resolved_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User id could not be resolved from token.",
        )

    group_id = matched_group
    username = str(user_info.get('username')).strip()
    try:
        msg = rexec_services.create_rexec_server_resources(group_id, resolved_user_id, requirments)
        return {
            "Status": msg,
            "Username": username,
            "NDP_Endpoint_membership": group_id,
        }
    except Exception as e:
        print(type(e), e)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")
