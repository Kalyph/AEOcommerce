from fastapi import APIRouter, Request, Query, HTTPException
from fastapi.responses import JSONResponse, RedirectResponse
from sqlmodel import Session, select
import secrets

from app.core.database import get_sync_session
from app.core.config import settings
from app.models.db import Merchant, ShopifyConnection, SyncJob
from app.core.security import encrypt_token
from app.services.shopify_oauth import build_shopify_install_url, verify_shopify_hmac, exchange_code_for_token
from app.services.canonical import slugify
from app.services.shopify_sync import sync_shopify_products

router = APIRouter()


@router.get("/auth/shopify/install")
async def shopify_install(
    shop: str = Query(..., description="Shop domain (e.g., my-store.myshopify.com)")
):
    """Initiate Shopify OAuth installation."""
    
    if not settings.shopify_api_key:
        return JSONResponse(
            status_code=200,
            content={
                "status": "configuration_required",
                "message": "Set SHOPIFY_API_KEY, SHOPIFY_API_SECRET, and SHOPIFY_REDIRECT_URI to enable Shopify OAuth."
            }
        )
    
    state = secrets.token_urlsafe(32)
    install_url = build_shopify_install_url(shop, state)
    
    return RedirectResponse(url=install_url)


@router.get("/auth/shopify/callback")
async def shopify_callback(
    request: Request,
    shop: str = Query(None),
    code: str = Query(None),
    hmac: str = Query(None),
    timestamp: str = Query(None),
):
    """Handle Shopify OAuth callback."""
    
    # Get all query params
    params = dict(request.query_params)
    
    # Verify HMAC if secret is configured
    if settings.shopify_api_secret:
        if not verify_shopify_hmac(params):
            raise HTTPException(status_code=400, detail="Invalid HMAC signature")
    
    # Exchange code for token
    try:
        token_response = exchange_code_for_token(shop, code)
        access_token = token_response.get("access_token", "")
        scopes = token_response.get("scope", "")
    except Exception as e:
        return JSONResponse(
            status_code=400,
            content={
                "error": "token_exchange_failed",
                "message": f"Failed to exchange code for token: {str(e)}"
            }
        )
    
    with get_sync_session() as session:
        # Create or get merchant using shop subdomain as slug
        shop_subdomain = shop.replace(".myshopify.com", "").replace(".", "-")
        slug = slugify(shop_subdomain)
        
        merchant = session.exec(select(Merchant).where(Merchant.slug == slug)).first()
        
        if not merchant:
            merchant = Merchant(
                name=shop_subdomain,
                slug=slug
            )
            session.add(merchant)
            session.flush()
        
        # Create or update ShopifyConnection
        connection = session.exec(
            select(ShopifyConnection).where(ShopifyConnection.shop_domain == shop)
        ).first()
        
        if connection:
            connection.access_token = encrypt_token(access_token)
            connection.scopes = scopes
            connection.status = "active"
        else:
            connection = ShopifyConnection(
                merchant_id=merchant.id,
                shop_domain=shop,
                access_token=encrypt_token(access_token),
                scopes=scopes,
                status="active"
            )
            session.add(connection)
        
        session.flush()
        session.refresh(connection)
        
        # Trigger sync synchronously
        sync_job = sync_shopify_products(connection, merchant.id, session)
        
        return JSONResponse(
            content={
                "merchant_id": merchant.id,
                "shop_domain": shop,
                "sync_status": sync_job.status,
                "sync_error": sync_job.error
            }
        )
