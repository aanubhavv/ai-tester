from fastapi import APIRouter
from app.api.v1.endpoints import health, info

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(info.router, tags=["info"])
