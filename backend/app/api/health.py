from fastapi import APIRouter

from app.core.config import get_settings

router = APIRouter(prefix="/health", tags=["health"])


@router.get("/live")
async def live() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
async def ready() -> dict[str, str]:
    settings = get_settings()

    return {
        "status": "ok",
        "database_url": settings.database_url,
        "redis_url": settings.redis_url,
        "rabbitmq_url": settings.rabbitmq_url,
    }
