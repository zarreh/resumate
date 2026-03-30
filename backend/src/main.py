"""ResuMate API — minimal entrypoint for Docker health check.

This file will be expanded in Phase 1.4 with CORS, auth routers, etc.
"""

from fastapi import FastAPI
from sqlalchemy import text

from src.core.database import engine

app = FastAPI(title="ResuMate API", version="0.1.0")


@app.get("/api/v1/health")
async def health_check() -> dict[str, str]:
    """Health check with database connectivity verification."""
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        return {"status": "degraded", "database": str(e)}
