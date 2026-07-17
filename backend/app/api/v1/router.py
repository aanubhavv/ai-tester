from fastapi import APIRouter
from app.api.v1.endpoints import health, info, scan, scans, comparison, projects, knowledge, ai, test_cases

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(info.router, tags=["info"])
api_router.include_router(scan.router, tags=["scan"])
api_router.include_router(scans.router, tags=["scans"])
api_router.include_router(comparison.router, tags=["comparison"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(knowledge.router, prefix="/projects", tags=["knowledge"])
api_router.include_router(test_cases.router, prefix="/projects", tags=["test_cases"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
