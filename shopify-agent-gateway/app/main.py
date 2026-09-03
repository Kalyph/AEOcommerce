from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.database import create_db_and_tables
from app.api.routes_health import router as health_router
from app.api.routes_auth_shopify import router as auth_shopify_router
from app.api.routes_agent_gateway import router as agent_gateway_router
from app.api.routes_admin import router as admin_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    create_db_and_tables()
    yield
    # Shutdown (cleanup if needed)


app = FastAPI(
    title="Shopify Agent Readiness Gateway",
    description="Phase 1: Agent-ready commerce middleware for Shopify stores",
    version="1.0.0",
    lifespan=lifespan
)

# Enable CORS for development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    """Root endpoint with basic info."""
    return {
        "app": "Shopify Agent Readiness Gateway",
        "phase": 1,
        "docs": "/docs",
        "health": "/health",
        "demo_store": "/stores/demo/ai/manifest"
    }


# Include routers
app.include_router(health_router)
app.include_router(auth_shopify_router)
app.include_router(agent_gateway_router)
app.include_router(admin_router)
