from fastapi import APIRouter, HTTPException, Body
from sqlmodel import Session, select
from typing import List
import json

from app.core.database import get_sync_session
from app.models.db import Merchant, Product, ReadinessScore
from app.services.canonical import slugify
from app.services.readiness import calculate_readiness_score
from scripts.seed_demo import create_demo_products_for_merchant

router = APIRouter()


@router.get("/admin/merchants")
async def list_merchants():
    """List all merchants with product counts."""
    # TODO: Add authentication before production use
    
    with get_sync_session() as session:
        merchants = session.exec(select(Merchant)).all()
        
        result = []
        for merchant in merchants:
            product_count = len(session.exec(select(Product).where(Product.merchant_id == merchant.id)).all())
            result.append({
                "id": merchant.id,
                "name": merchant.name,
                "slug": merchant.slug,
                "product_count": product_count,
                "created_at": merchant.created_at.isoformat() if merchant.created_at else None
            })
        
        return {"merchants": result}


@router.post("/admin/merchants")
async def create_merchant(name: str = Body(..., embed=True)):
    """Create a new merchant."""
    # TODO: Add authentication before production use
    
    with get_sync_session() as session:
        slug = slugify(name)
        
        # Check if slug already exists
        existing = session.exec(select(Merchant).where(Merchant.slug == slug)).first()
        if existing:
            raise HTTPException(status_code=400, detail="Merchant with this name already exists")
        
        merchant = Merchant(name=name, slug=slug)
        session.add(merchant)
        session.commit()
        session.refresh(merchant)
        
        return {
            "id": merchant.id,
            "name": merchant.name,
            "slug": merchant.slug,
            "created_at": merchant.created_at.isoformat() if merchant.created_at else None
        }


@router.get("/admin/merchants/{merchant_id}/readiness")
async def get_readiness(merchant_id: str):
    """Calculate and return readiness score for a merchant."""
    # TODO: Add authentication before production use
    
    with get_sync_session() as session:
        merchant = session.get(Merchant, merchant_id)
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
        
        readiness = calculate_readiness_score(merchant_id, session)
        
        issues = json.loads(readiness.issues) if readiness.issues else []
        recommendations = json.loads(readiness.recommendations) if readiness.recommendations else []
        
        return {
            "merchant_id": readiness.merchant_id,
            "score": readiness.score,
            "issues": issues,
            "recommendations": recommendations,
            "updated_at": readiness.updated_at.isoformat() if readiness.updated_at else None
        }


@router.post("/admin/merchants/{merchant_id}/seed-demo-products")
async def seed_demo_products(merchant_id: str):
    """Seed demo products for a merchant."""
    # TODO: Add authentication before production use
    
    with get_sync_session() as session:
        merchant = session.get(Merchant, merchant_id)
        if not merchant:
            raise HTTPException(status_code=404, detail="Merchant not found")
        
        # Create demo products
        created_count = create_demo_products_for_merchant(merchant, session)
        
        return {
            "merchant_id": merchant_id,
            "products_created": created_count
        }
