from fastapi import APIRouter
from app.schemas.info import InfoResponse
from app.core.config import settings
from fastapi import Request

router = APIRouter()

@router.get("/info", response_model=InfoResponse)
def info(request: Request):
    return InfoResponse(
        app_name=settings.app_name,
        version=request.app.version,
        environment=settings.app_env
    )
