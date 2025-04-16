from fastapi import APIRouter

from .post_rexec_route import router as post_rexec_router

router = APIRouter()

router.include_router(post_rexec_router)