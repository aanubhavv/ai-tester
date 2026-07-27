from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging

from app.core.config import settings
from app.core.logging import setup_logging
from app.core.exceptions import global_exception_handler
from app.api.v1.router import api_router
from app.api.v1.endpoints.root import router as root_router
from app.api.v1.endpoints.browser_stream import router as browser_stream_router
from app.services.execution.queue import execution_queue
from app.db.mongodb import connect_to_mongo, close_mongo_connection
from app.db.imagekit_config import setup_imagekit

logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    logger.info(f"Starting {settings.app_name} in {settings.app_env} environment...")
    
    # Initialize DB and ImageKit
    setup_imagekit()
    await connect_to_mongo()
    
    await execution_queue.start()
    yield
    logger.info(f"Shutting down {settings.app_name}...")
    await execution_queue.stop()
    await close_mongo_connection()

app = FastAPI(
    title=settings.app_name,
    description="Clean Architecture Refactor for FastAPI",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs" if settings.debug else None,
    redoc_url="/redoc" if settings.debug else None,
)

# CORS configuration
origins = [origin.strip() for origin in settings.cors_origins.split(",")]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
app.add_exception_handler(Exception, global_exception_handler)

# Include root endpoint
app.include_router(root_router)

# Include WebSocket browser streaming endpoint (no API prefix — WS path is /ws/browser/{job_id})
app.include_router(browser_stream_router)

# Include API v1 endpoints
app.include_router(api_router, prefix=settings.api_prefix)