"""
Return broker connection details for remote execution.
"""

from fastapi import APIRouter, HTTPException, Request

from api.services import rexec_services

router = APIRouter()


@router.get(
    "/broker-config",
    summary="Get Rexec Broker Configuration",
    description="Retrieve broker connection details for the caller's remote execution environment.",
)
def get_rexec_broker_config(request: Request):
    """
    Return broker address/port plus the Rexec API URL.
    """
    try:
        return rexec_services.get_rexec_broker_config()
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve Rexec broker configuration: {exc}",
        )
