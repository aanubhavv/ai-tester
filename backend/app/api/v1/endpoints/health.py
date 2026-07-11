from fastapi import APIRouter
from app.schemas.health import HealthResponse
from app.core.config import settings
from fastapi import Request

router = APIRouter()

@router.get("/health", response_model=HealthResponse)
def health(request: Request):
    return HealthResponse(
        status="healthy",
        version=request.app.version,
        environment=settings.app_env
    )
