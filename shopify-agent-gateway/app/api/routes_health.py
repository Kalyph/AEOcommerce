from fastapi import APIRouter
from app.core.database import engine

router = APIRouter()


@router.get("/health")
async def health_check():
    """Health check endpoint."""
    # Check database connection
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "status": "ok",
        "app": "Shopify Agent Readiness Gateway",
        "phase": 1,
        "database": db_status
    }
