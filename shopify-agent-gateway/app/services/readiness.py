import json
from datetime import datetime
from typing import List, Dict, Any
from sqlmodel import Session, select

from app.models.db import ReadinessScore, Product, Variant, Collection, Merchant


def calculate_readiness_score(merchant_id: str, session: Session) -> ReadinessScore:
    """
    Calculate the Agent Readiness Score for a merchant.
    
    Args:
        merchant_id: The merchant's ID
        session: The database session
    
    Returns:
        A ReadinessScore record
    """
    issues = []
    recommendations = []
    score = 100
    
    # Get all products for this merchant
    products = session.exec(select(Product).where(Product.merchant_id == merchant_id)).all()
    
    # Check if merchant has zero products
    if len(products) == 0:
        score = 20
        issues.append("No products synced")
        recommendations.append("Connect Shopify store to sync live catalog")
        recommendations.append("Add clear product descriptions")
        recommendations.append("Add alt text and images to products")
        recommendations.append("Add SKUs to all variants")
        recommendations.append("Add inventory quantities")
    else:
        # Check products missing description
        products_missing_description = sum(
            1 for p in products if not p.description or len(p.description.strip()) == 0
        )
        pct_missing_desc = products_missing_description / len(products)
        if pct_missing_desc > 0.2:
            score -= 15
            issues.append(f"{int(pct_missing_desc * 100)}% of products missing description")
            recommendations.append("Add clear product descriptions")
        
        # Check products missing images
        products_missing_images = 0
        for product in products:
            media_count = len(session.exec(select(MediaAsset).where(MediaAsset.product_id == product.id)).all())
            if media_count == 0:
                products_missing_images += 1
        
        pct_missing_images = products_missing_images / len(products)
        if pct_missing_images > 0.2:
            score -= 15
            issues.append(f"{int(pct_missing_images * 100)}% of products missing images")
            recommendations.append("Add alt text and images to products")
        
        # Check variants missing SKU
        all_variants = []
        for product in products:
            variants = session.exec(select(Variant).where(Variant.product_id == product.id)).all()
            all_variants.extend(variants)
        
        if len(all_variants) > 0:
            variants_missing_sku = sum(1 for v in all_variants if not v.sku or len(v.sku.strip()) == 0)
            pct_missing_sku = variants_missing_sku / len(all_variants)
            if pct_missing_sku > 0.3:
                score -= 15
                issues.append(f"{int(pct_missing_sku * 100)}% of variants missing SKU")
                recommendations.append("Add SKUs to all variants")
            
            # Check variants with zero inventory
            variants_zero_inventory = sum(1 for v in all_variants if v.inventory_quantity <= 0)
            pct_zero_inventory = variants_zero_inventory / len(all_variants)
            if pct_zero_inventory > 0.2:
                score -= 10
                issues.append(f"{int(pct_zero_inventory * 100)}% of variants have no inventory")
                recommendations.append("Add inventory quantities")
    
    # Check if no collections exist
    collections = session.exec(select(Collection).where(Collection.merchant_id == merchant_id)).all()
    if len(collections) == 0:
        score -= 5
        issues.append("No collections defined")
        # Don't add recommendation for collections as it's optional
    
    # Ensure score doesn't go below 0
    score = max(0, score)
    
    # If no recommendations yet, add generic ones
    if not recommendations:
        recommendations.append("Your store is well configured for agent access")
    
    # Create or update ReadinessScore
    existing_score = session.exec(
        select(ReadinessScore).where(ReadinessScore.merchant_id == merchant_id)
    ).first()
    
    if existing_score:
        existing_score.score = score
        existing_score.issues = json.dumps(issues)
        existing_score.recommendations = json.dumps(recommendations)
        existing_score.updated_at = datetime.utcnow()
        readiness_score = existing_score
    else:
        readiness_score = ReadinessScore(
            merchant_id=merchant_id,
            score=score,
            issues=json.dumps(issues),
            recommendations=json.dumps(recommendations),
            updated_at=datetime.utcnow()
        )
        session.add(readiness_score)
    
    session.commit()
    session.refresh(readiness_score)
    
    return readiness_score


# Import MediaAsset here to avoid circular dependency
from app.models.db import MediaAsset
