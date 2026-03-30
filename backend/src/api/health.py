"""Health check endpoint."""

from fastapi import APIRouter
from sqlalchemy import text

from src.core.database import engine

router = APIRouter()


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Health check with database connectivity verification."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
