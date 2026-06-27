from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from loguru import logger

from backend.config import BackendConfig
from backend.api.routes import chat
from backend.services.agent_service import get_agent_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("starting bid intelligence system...")
    try:
        BackendConfig.validate()
        logger.info("config validated")
    except ValueError as e:
        logger.error(f"config validation failed: {e}")
        raise
    try:
        service = get_agent_service()
        await service.initialize()
        logger.info("agent service initialized")
    except Exception as e:
        logger.error(f"agent service init failed: {e}")
        raise
    logger.info("system ready")
    yield
    logger.info("system shutting down...")


app = FastAPI(
    title="bid intelligence multi-agent system",
    description="gateway + crawler + document + presentation agents with loop architecture and skill evolution",
    version="2.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=BackendConfig.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)


@app.get("/")
async def root():
    return {
        "service": "bid intelligence multi-agent system",
        "version": "2.0.0",
        "agents": ["crawler", "document", "presentation"],
        "architecture": "gateway + agent + loop + skill evolution",
        "docs": "/docs",
        "health": "/api/health"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "backend.main:app",
        host=BackendConfig.API_HOST,
        port=BackendConfig.API_PORT,
        reload=BackendConfig.API_RELOAD,
        log_level=BackendConfig.LOG_LEVEL.lower()
    )