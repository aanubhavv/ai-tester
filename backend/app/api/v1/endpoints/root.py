from fastapi import APIRouter

router = APIRouter()

@router.get("/")
def root():
    return {"message": "Welcome to the API v1"}
