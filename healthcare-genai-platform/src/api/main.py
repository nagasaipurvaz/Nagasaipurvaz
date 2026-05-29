"""FastAPI application entry point."""

import logging
import os

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.routes import care_management, clinical
from src.config.settings import get_settings

structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.stdlib.add_log_level,
        structlog.processors.JSONRenderer(),
    ]
)

settings = get_settings()

app = FastAPI(
    title="Enterprise Healthcare GenAI Platform",
    description=(
        "HIPAA-compliant AI-powered clinical co-pilots and agentic care management. "
        "Built with LangGraph, CrewAI, GPT-4, and FHIR R4."
    ),
    version="1.0.0",
    docs_url="/docs" if settings.app_env != "production" else None,
    redoc_url="/redoc" if settings.app_env != "production" else None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

app.include_router(clinical.router, prefix="/api/v1")
app.include_router(care_management.router, prefix="/api/v1")


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "version": "1.0.0", "env": settings.app_env}


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Enterprise Healthcare GenAI Platform",
        "docs": "/docs",
        "health": "/health",
    }


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger = structlog.get_logger()
    logger.error("unhandled_exception", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=500,
        content={"detail": "An internal error occurred. This incident has been logged."},
    )
