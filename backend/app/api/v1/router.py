from fastapi import APIRouter
from app.api.v1.endpoints import health, info, scan, scans

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(info.router, tags=["info"])
api_router.include_router(scan.router, tags=["scan"])
api_router.include_router(scans.router, tags=["scans"])
