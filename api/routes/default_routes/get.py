from fastapi import APIRouter, Request
from api.services import default_services

router = APIRouter()

@router.get("/")
async def index(request: Request):
    return default_services.index(request)

@router.get("/health")
async def health_check():
    """Health check endpoint for container orchestration"""
    return {"status": "healthy", "service": "rexec-deployment-api"}