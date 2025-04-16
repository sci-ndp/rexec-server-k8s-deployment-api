from fastapi import APIRouter, HTTPException, Depends, Form
from typing import Annotated, Optional, Dict

from api.services import rexec_services
# from api.services.keycloak_services.get_current_user import get_current_user

router = APIRouter()


@router.post("/rexec", status_code=200)
def create_rexec_server(requirments: Annotated[list[str],
        Form(
            title="Requirements",
            description="User-specified package list provided by requirements.txt",
        )
    ]):
    """
    Create a new dspaces instance for a user in a unique namespace.
    """
    # try:
    #     user_id = current_user["id"]
    # except KeyError:
    #     raise HTTPException(status_code=400, detail="User ID not found in the current user information")
    user_id = '0'

    try:
        rexec_services.create_rexec_server_resources(user_id, requirments)
        return {"message": f"dspaces instance created for user"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")