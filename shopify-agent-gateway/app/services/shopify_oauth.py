import hmac
import hashlib
from urllib.parse import urlencode, quote
from typing import Dict
from app.core.config import settings


def build_shopify_install_url(shop_domain: str, state: str) -> str:
    """
    Build the Shopify OAuth installation URL.
    
    Args:
        shop_domain: The shop's domain (e.g., 'my-store.myshopify.com')
        state: A random state string for CSRF protection
    
    Returns:
        The full authorization URL
    """
    base_url = f"https://{shop_domain}/admin/oauth/authorize"
    
    params = {
        'client_id': settings.shopify_api_key or '',
        'scope': 'read_products,read_product_listings,read_inventory,read_content',
        'redirect_uri': settings.shopify_redirect_uri,
        'state': state
    }
    
    query_string = urlencode(params, quote_via=quote)
    return f"{base_url}?{query_string}"


def verify_shopify_hmac(params: Dict[str, str]) -> bool:
    """
    Verify the HMAC signature from Shopify's OAuth callback.
    
    Args:
        params: The query parameters from Shopify's callback
    
    Returns:
        True if the HMAC is valid, False otherwise
    """
    if not settings.shopify_api_secret:
        return False
    
    hmac_param = params.get('hmac', '')
    if not hmac_param:
        return False
    
    # Remove hmac and signature from params
    params_to_verify = {k: v for k, v in params.items() if k not in ('hmac', 'signature')}
    
    # Sort keys and URL encode as query string
    sorted_params = sorted(params_to_verify.items())
    query_string = '&'.join(f"{k}={v}" for k, v in sorted_params)
    
    # Compute HMAC-SHA256
    computed_hmac = hmac.new(
        settings.shopify_api_secret.encode(),
        query_string.encode(),
        hashlib.sha256
    ).hexdigest()
    
    # Compare using constant-time comparison
    return hmac.compare_digest(computed_hmac, hmac_param)


def exchange_code_for_token(shop_domain: str, code: str) -> Dict:
    """
    Exchange the OAuth authorization code for an access token.
    
    Args:
        shop_domain: The shop's domain
        code: The authorization code from Shopify
    
    Returns:
        The response JSON containing the access token
    """
    import httpx
    
    url = f"https://{shop_domain}/admin/oauth/access_token"
    
    payload = {
        'client_id': settings.shopify_api_key,
        'client_secret': settings.shopify_api_secret,
        'code': code
    }
    
    response = httpx.post(url, json=payload)
    response.raise_for_status()
    
    return response.json()
