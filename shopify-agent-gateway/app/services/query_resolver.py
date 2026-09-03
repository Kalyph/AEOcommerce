import re
from typing import List, Dict, Any, Optional
from sqlmodel import Session, select

from app.models.db import Product, Variant
from app.schemas.agent import AgentQueryResponse


def normalize_query(query: str) -> str:
    """Normalize a query string for matching."""
    return query.lower().strip()


def extract_price_filter(query: str) -> Optional[float]:
    """Extract price filter from query like 'under $50' or 'below 100'."""
    patterns = [
        r'under\s*\$?\s*(\d+(?:\.\d+)?)',
        r'below\s*\$?\s*(\d+(?:\.\d+)?)',
        r'less than\s*\$?\s*(\d+(?:\.\d+)?)',
        r'max\s*\$?\s*(\d+(?:\.\d+)?)',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, query, re.IGNORECASE)
        if match:
            return float(match.group(1))
    
    return None


def has_in_stock_preference(query: str) -> bool:
    """Check if query indicates preference for in-stock items."""
    phrases = ['in stock', 'available', 'in-stock', 'instock']
    query_lower = query.lower()
    return any(phrase in query_lower for phrase in phrases)


def score_product_match(product: Product, variants: List[Variant], normalized_query: str) -> float:
    """
    Score a product based on keyword matches.
    
    Weights:
    - title: 5
    - summary: 3
    - description: 2
    - product_type: 3
    - tags: 2
    - variant options: 2
    """
    score = 0.0
    query_terms = normalized_query.split()
    
    # Title (weight 5)
    if product.title:
        title_lower = product.title.lower()
        for term in query_terms:
            if term in title_lower:
                score += 5
    
    # Summary (weight 3)
    if product.summary:
        summary_lower = product.summary.lower()
        for term in query_terms:
            if term in summary_lower:
                score += 3
    
    # Description (weight 2)
    if product.description:
        desc_lower = product.description.lower()
        for term in query_terms:
            if term in desc_lower:
                score += 2
    
    # Product type (weight 3)
    if product.product_type:
        type_lower = product.product_type.lower()
        for term in query_terms:
            if term in type_lower:
                score += 3
    
    # Tags (weight 2)
    if product.tags:
        try:
            import json
            tags = json.loads(product.tags)
            if isinstance(tags, list):
                tags_str = ' '.join(tags).lower()
                for term in query_terms:
                    if term in tags_str:
                        score += 2
        except:
            pass
    
    # Variant options (weight 2)
    for variant in variants:
        if variant.options:
            try:
                import json
                options = json.loads(variant.options)
                if isinstance(options, dict):
                    options_str = ' '.join(options.values()).lower()
                    for term in query_terms:
                        if term in options_str:
                            score += 2
            except:
                pass
    
    return score


def resolve_agent_query(merchant_id: str, query: str, context: Dict[str, Any], limit: int, session: Session) -> AgentQueryResponse:
    """
    Resolve an agent query using keyword search.
    
    Args:
        merchant_id: The merchant's ID
        query: The user's query string
        context: Additional context (not used in simple implementation)
        limit: Maximum number of products to return
        session: The database session
    
    Returns:
        An AgentQueryResponse with matching products
    """
    normalized = normalize_query(query)
    max_price = extract_price_filter(query)
    prefer_in_stock = has_in_stock_preference(query)
    
    # Fetch all products for this merchant
    products = session.exec(select(Product).where(Product.merchant_id == merchant_id)).all()
    
    # Score each product
    scored_products = []
    
    for product in products:
        variants = session.exec(select(Variant).where(Variant.product_id == product.id)).all()
        
        # Apply filters
        if variants:
            min_price = min(v.price for v in variants if v.price is not None)
            max_inventory = max(v.inventory_quantity for v in variants)
        else:
            min_price = None
            max_inventory = 0
        
        # Price filter
        if max_price is not None and min_price is not None and min_price > max_price:
            continue
        
        # In-stock filter (soft preference, not hard filter)
        if prefer_in_stock and max_inventory <= 0:
            continue
        
        # Calculate match score
        score = score_product_match(product, variants, normalized)
        
        if score > 0:
            scored_products.append((score, product, variants))
    
    # Sort by score descending
    scored_products.sort(key=lambda x: x[0], reverse=True)
    
    # Take top results
    top_score = scored_products[0][0] if scored_products else 0
    results = scored_products[:limit]
    
    # Build response products
    response_products = []
    
    for score, product, variants in results:
        # Calculate price_from
        prices = [v.price for v in variants if v.price is not None]
        price_from = min(prices) if prices else None
        
        # Check if any variant is in stock
        in_stock = any(v.inventory_quantity > 0 for v in variants)
        
        response_products.append({
            "product_id": product.source_product_id,
            "title": product.title,
            "price_from": price_from,
            "currency": "USD",
            "in_stock": in_stock,
            "url": product.url,
            "summary": product.summary,
            "variants_available": len(variants)
        })
    
    # Generate answer
    if response_products:
        count = len(response_products)
        answer = f"Found {count} product(s) matching your query."
    else:
        answer = "No products found matching your query."
    
    # Next actions
    next_actions = ["select_variant", "create_cart"]
    
    # Confidence
    confidence = min(1.0, top_score / 10) if top_score > 0 else 0.0
    
    return AgentQueryResponse(
        answer=answer,
        products=response_products,
        next_actions=next_actions,
        confidence=confidence
    )
