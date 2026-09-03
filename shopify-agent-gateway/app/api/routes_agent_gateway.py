from fastapi import APIRouter, Request, HTTPException, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from sqlmodel import Session, select
from datetime import datetime, timedelta
import json
import time

from app.core.database import get_sync_session
from app.models.db import Merchant, Product, Variant, MediaAsset, ShopifyConnection, Cart, RequestLog
from app.schemas.agent import AgentQueryRequest, CartCreateRequest, CartCreateResponse, ProductSummary, ProductDetail
from app.services.query_resolver import resolve_agent_query

router = APIRouter()


def log_request(endpoint: str, request_payload: dict, response_status: int, latency_ms: int, merchant_id: str = None):
    """Log a request to the database."""
    try:
        with get_sync_session() as session:
            log = RequestLog(
                merchant_id=merchant_id,
                endpoint=endpoint,
                request_payload=json.dumps(request_payload) if request_payload else None,
                response_status=response_status,
                latency_ms=latency_ms
            )
            session.add(log)
            session.commit()
    except Exception:
        pass  # Don't let logging errors crash the app


def get_merchant_by_slug(session: Session, store_slug: str) -> Merchant:
    """Get a merchant by slug."""
    merchant = session.exec(select(Merchant).where(Merchant.slug == store_slug)).first()
    if not merchant:
        raise HTTPException(status_code=404, detail="Merchant not found")
    return merchant


@router.get("/stores/{store_slug}/llms.txt", response_class=PlainTextResponse)
async def llms_txt(store_slug: str, request: Request):
    """Generate llms.txt for AI agents."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        
        content = f"""# Store: {merchant.name}

{merchant.name} sells products through Shopify.

Agent capabilities:
- product_search: true
- product_details: true
- inventory_check: true
- cart_create: true
- checkout_handoff: true

Endpoints:
- Manifest: /stores/{store_slug}/ai/manifest
- Products: /stores/{store_slug}/ai/products
- Product details: /stores/{store_slug}/ai/products/{{product_id}}
- Query: /stores/{store_slug}/ai/query
- Cart: /stores/{store_slug}/ai/cart
"""
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/llms.txt", {}, 200, latency_ms, merchant.id)
    
    return content


@router.get("/stores/{store_slug}/ai/manifest")
async def agent_manifest(store_slug: str, request: Request):
    """Generate AI agent manifest."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        
        manifest = {
            "merchant_id": merchant.id,
            "store_name": merchant.name,
            "channel": "shopify",
            "capabilities": {
                "catalog_read": True,
                "inventory_read": True,
                "pricing_read": True,
                "variant_resolution": True,
                "product_search": True,
                "cart_create": True,
                "checkout_handoff": True,
                "delegated_checkout": False,
                "order_status_read": False
            },
            "endpoints": {
                "products": f"/stores/{store_slug}/ai/products",
                "product": f"/stores/{store_slug}/ai/products/{{product_id}}",
                "query": f"/stores/{store_slug}/ai/query",
                "cart": f"/stores/{store_slug}/ai/cart"
            },
            "authentication": {
                "type": "none",
                "note": "Phase 1 development mode. API key enforcement will be added later."
            }
        }
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/ai/manifest", {}, 200, latency_ms, merchant.id)
    
    return manifest


@router.get("/stores/{store_slug}/ai/products")
async def list_products(
    store_slug: str,
    request: Request,
    query: str = Query(None),
    min_price: float = Query(None),
    max_price: float = Query(None),
    in_stock: bool = Query(None),
    limit: int = Query(20, ge=1, le=100)
):
    """List products for a store."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        
        # Base query
        products = session.exec(select(Product).where(Product.merchant_id == merchant.id)).all()
        
        # Apply filters
        filtered_products = []
        
        for product in products:
            variants = session.exec(select(Variant).where(Variant.product_id == product.id)).all()
            
            # Price filter
            prices = [v.price for v in variants if v.price is not None]
            if prices:
                min_product_price = min(prices)
                max_product_price = max(prices)
                
                if min_price is not None and max_product_price < min_price:
                    continue
                if max_price is not None and min_product_price > max_price:
                    continue
            
            # In-stock filter
            if in_stock:
                if not any(v.inventory_quantity > 0 for v in variants):
                    continue
            
            # Query filter (simple text search)
            if query:
                query_lower = query.lower()
                searchable = f"{product.title} {product.summary or ''} {product.description or ''}".lower()
                if query_lower not in searchable:
                    continue
            
            filtered_products.append(product)
        
        # Limit results
        filtered_products = filtered_products[:limit]
        
        # Build response
        response_products = []
        
        for product in filtered_products:
            variants = session.exec(select(Variant).where(Variant.product_id == product.id)).all()
            
            prices = [v.price for v in variants if v.price is not None]
            price_from = min(prices) if prices else None
            
            in_stock_bool = any(v.inventory_quantity > 0 for v in variants)
            
            response_products.append({
                "product_id": product.source_product_id,
                "title": product.title,
                "summary": product.summary,
                "price_from": price_from,
                "currency": "USD",
                "in_stock": in_stock_bool,
                "url": product.url,
                "variants_available": len(variants)
            })
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/ai/products", {"query": query}, 200, latency_ms, merchant.id)
    
    return {"products": response_products}


@router.get("/stores/{store_slug}/ai/products/{product_id}")
async def get_product(store_slug: str, product_id: str, request: Request):
    """Get product details."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        
        product = session.exec(
            select(Product).where(
                Product.merchant_id == merchant.id,
                Product.source_product_id == product_id
            )
        ).first()
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        variants = session.exec(select(Variant).where(Variant.product_id == product.id)).all()
        media = session.exec(select(MediaAsset).where(MediaAsset.product_id == product.id)).all()
        
        prices = [v.price for v in variants if v.price is not None]
        price_from = min(prices) if prices else None
        
        in_stock_bool = any(v.inventory_quantity > 0 for v in variants)
        
        # Parse tags
        tags = None
        if product.tags:
            try:
                tags = json.loads(product.tags)
            except:
                pass
        
        # Build variants list
        variants_list = []
        for v in variants:
            options = None
            if v.options:
                try:
                    options = json.loads(v.options)
                except:
                    pass
            
            variants_list.append({
                "variant_id": v.source_variant_id,
                "sku": v.sku,
                "price": v.price,
                "compare_at_price": v.compare_at_price,
                "currency": v.currency,
                "inventory_quantity": v.inventory_quantity,
                "available": v.available,
                "options": options
            })
        
        # Build media list
        media_list = []
        for m in media:
            media_list.append({
                "url": m.url,
                "alt_text": m.alt_text,
                "position": m.position
            })
        
        response = {
            "product_id": product.source_product_id,
            "title": product.title,
            "handle": product.handle,
            "summary": product.summary,
            "description": product.description,
            "brand": product.brand,
            "product_type": product.product_type,
            "tags": tags,
            "price_from": price_from,
            "currency": "USD",
            "in_stock": in_stock_bool,
            "url": product.url,
            "variants": variants_list,
            "media": media_list,
            "capabilities": {
                "cart_eligible": True,
                "checkout_eligible": True
            }
        }
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/ai/products/{product_id}", {}, 200, latency_ms, merchant.id)
    
    return response


@router.post("/stores/{store_slug}/ai/query")
async def agent_query(store_slug: str, request_body: AgentQueryRequest, request: Request):
    """Resolve an agent query."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        
        response = resolve_agent_query(
            merchant_id=merchant.id,
            query=request_body.query,
            context=request_body.context,
            limit=request_body.limit,
            session=session
        )
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/ai/query", {"query": request_body.query}, 200, latency_ms, merchant.id)
    
    return response


@router.post("/stores/{store_slug}/ai/cart")
async def create_cart(store_slug: str, request_body: CartCreateRequest, request: Request):
    """Create a cart and generate checkout URL."""
    start_time = time.time()
    
    with get_sync_session() as session:
        merchant = get_merchant_by_slug(session, store_slug)
        merchant_id = merchant.id
        merchant_slug = merchant.slug
        
        # Validate items and build cart line items
        cart_items = []
        
        for item in request_body.items:
            # Look up variant by source_variant_id
            variant = session.exec(
                select(Variant).where(Variant.source_variant_id == item.variant_id)
            ).first()
            
            if not variant:
                raise HTTPException(status_code=400, detail=f"Variant not found: {item.variant_id}")
            
            # Ensure variant belongs to this merchant's products
            product = session.get(Product, variant.product_id)
            if not product or product.merchant_id != merchant_id:
                raise HTTPException(status_code=400, detail=f"Variant does not belong to this merchant: {item.variant_id}")
            
            cart_items.append({
                "variant_id": item.variant_id,
                "quantity": item.quantity
            })
        
        # Get shop domain
        connection = session.exec(
            select(ShopifyConnection).where(ShopifyConnection.merchant_id == merchant_id)
        ).first()
        
        if connection:
            shop_domain = connection.shop_domain
        else:
            shop_domain = f"{merchant_slug}.myshopify.com"
        
        # Build cart URL
        line_items = ",".join(f"{item['variant_id']}:{item['quantity']}" for item in cart_items)
        cart_url = f"https://{shop_domain}/cart/{line_items}"
        
        # Save cart record
        cart = Cart(
            merchant_id=merchant_id,
            items=json.dumps(cart_items),
            cart_url=cart_url,
            status="created",
            expires_at=datetime.utcnow() + timedelta(hours=1)
        )
        session.add(cart)
        session.commit()
        session.refresh(cart)
        
        result_cart_url = cart.cart_url
        result_expires_at = cart.expires_at
    
    latency_ms = int((time.time() - start_time) * 1000)
    log_request(f"/stores/{store_slug}/ai/cart", {"items": [dict(i) for i in request_body.items]}, 200, latency_ms, merchant_id)
    
    return CartCreateResponse(
        cart_url=result_cart_url,
        mode="checkout_handoff",
        expires_at=result_expires_at
    )
