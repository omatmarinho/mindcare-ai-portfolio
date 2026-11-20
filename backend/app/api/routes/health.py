
from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health_check():
    return {
        "application": "MindCare AI",
        "status": "healthy",
        "version": "0.1.0"
    }
