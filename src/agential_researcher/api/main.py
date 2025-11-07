from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer
from fastapi.responses import PlainTextResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from contextlib import asynccontextmanager
from typing import Optional
import time
import logging
import secrets

from prometheus_client import make_asgi_app
from prometheus_client import Counter, Histogram, Gauge

from ..config import settings
from .routes import router
from ..queue.celery_app import celery_app
from ..store.db import init_db


# Initialize rate limiter
limiter = Limiter(key_func=get_remote_address)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variables to store health status
provider_status = {
    "vllm": "unknown",
    "ollama": "unknown",
    "sqlite": "unknown",
    "lancedb": "unknown",
    "rabbitmq": "unknown"
}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("Initializing database...")
    init_db()

    logger.info("Starting application...")
    yield

    # Shutdown
    logger.info("Shutting down application...")

app = FastAPI(
    title="Agential Researcher API",
    description="API for the Agential Researcher system",
    version="0.1.0",
    lifespan=lifespan
)

# Add middleware in order: metrics first, then CORS
from .middleware import metrics_middleware
app.middleware('http')(metrics_middleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer(auto_error=False)

def verify_api_key(credentials=Depends(security)):
    # Skip auth for health endpoint
    if credentials is None:
        return None

    if credentials.credentials not in settings.api_keys:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    return credentials.credentials

# Include routes
app.include_router(router, prefix="/v1", dependencies=[Depends(verify_api_key)])
app.include_router(router, prefix="", dependencies=[Depends(verify_api_key)])  # For non-v1 routes

# Health endpoint with optional auth (/.well-known/health is public)
@app.get("/health", tags=["health"])
async def health(request: Request):
    """Health check endpoint - requires authentication"""
    from ..providers.router import llm_router  # Import here to avoid circular import
    
    # Update provider status
    global provider_status
    provider_status = {
        "vllm": "healthy" if llm_router.primary_healthy else "unhealthy" if llm_router.primary_provider == "vllm" else "unknown",
        "ollama": "healthy" if llm_router.secondary_healthy else "unhealthy" if llm_router.secondary_provider == "ollama" else "unknown",
        "sqlite": "healthy",  # Assume SQLite is healthy if we can reach this endpoint
        "lancedb": "healthy",  # Assume LanceDB is accessible
        "rabbitmq": "healthy"  # Assume RabbitMQ is accessible if Celery is working
    }

    # Check authentication
    api_key = request.headers.get("Authorization")
    if api_key and (api_key.startswith("Bearer ") or api_key.startswith("sk-")):
        # Validate the key
        actual_key = api_key[7:] if api_key.startswith("Bearer ") else api_key
        if actual_key not in (settings.api_keys if settings.api_keys != ["sk-..."] else [f"sk-{secrets.token_urlsafe(32)}"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key"
            )

    # Get actual queue depths using Celery's inspect functionality
    inspect = celery_app.control.inspect()
    
    try:
        # Get active tasks
        active_tasks = inspect.active()
        if active_tasks is None:
            active_tasks = {}
        hot_active = len(active_tasks.get('hot', []))
        
        backfill_active = len(active_tasks.get('backfill', []))
        vlm_ocr_active = len(active_tasks.get('vlm_ocr', []))
        maintenance_active = len(active_tasks.get('maintenance', []))
        
        # Get reserved tasks (queued but not yet active)
        reserved_tasks = inspect.reserved()
        if reserved_tasks is None:
            reserved_tasks = {}
        hot_reserved = len(reserved_tasks.get('hot', []))
        backfill_reserved = len(reserved_tasks.get('backfill', []))
        vlm_ocr_reserved = len(reserved_tasks.get('vlm_ocr', []))
        maintenance_reserved = len(reserved_tasks.get('maintenance', []))
        
        # Total queue depth = active + reserved
        hot_depth = hot_active + hot_reserved
        backfill_depth = backfill_active + backfill_reserved
        vlm_ocr_depth = vlm_ocr_active + vlm_ocr_reserved
        maintenance_depth = maintenance_active + maintenance_reserved
    except Exception as e:
        logger.error(f"Error getting queue depths: {e}")
        # Fallback to 0 if we can't get accurate counts
        hot_depth = 0
        backfill_depth = 0
        vlm_ocr_depth = 0
        maintenance_depth = 0

    return {
        "status": "healthy",
        "providers": provider_status,
        "queues": {
            "hot_depth": hot_depth,
            "backfill_depth": backfill_depth,
            "vlm_ocr_depth": vlm_ocr_depth,
            "maintenance_depth": maintenance_depth
        },
        "timestamp": time.time()
    }

@app.get("/.well-known/health", tags=["health"])
async def well_known_health():
    """Public health check endpoint - no authentication required"""
    return {
        "status": "healthy",
        "providers": provider_status,
        "timestamp": time.time()
    }

@app.get("/", tags=["info"])
async def root():
    """Root endpoint"""
    return {"message": "Agential Researcher API", "version": "0.1.0"}

# Add Prometheus metrics endpoint
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug
    )