from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import api.routes as routes
from .config import swagger_settings

# Create a FastAPI app instance with custom Swagger UI settings
app = FastAPI(
    title=swagger_settings.swagger_title,
    description=swagger_settings.swagger_description,
    version=swagger_settings.swagger_version,
)

# Add CORS middleware to allow cross-origin requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes.default_router, include_in_schema=False)
app.include_router(routes.rexec_router, tags=["Remote Execution"])