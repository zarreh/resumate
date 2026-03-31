"""ResuMate API — FastAPI application with CORS and router includes."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.analytics import router as analytics_router
from src.api.auth import router as auth_router
from src.api.career import router as career_router
from src.api.chat import router as chat_router
from src.api.health import router as health_router
from src.api.jobs import router as jobs_router
from src.api.resumes import router as resumes_router
from src.api.sessions import router as sessions_router
from src.api.websocket import router as ws_router
from src.core.config import settings

app = FastAPI(title="ResuMate API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix="/api/v1", tags=["health"])
app.include_router(auth_router, prefix="/api/v1/auth", tags=["auth"])
app.include_router(career_router, prefix="/api/v1/career", tags=["career"])
app.include_router(jobs_router, prefix="/api/v1/jobs", tags=["jobs"])
app.include_router(sessions_router, prefix="/api/v1/sessions", tags=["sessions"])
app.include_router(resumes_router, prefix="/api/v1/resumes", tags=["resumes"])
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])
app.include_router(analytics_router, prefix="/api/v1/analytics", tags=["analytics"])
app.include_router(ws_router, prefix="/api/v1", tags=["websocket"])
