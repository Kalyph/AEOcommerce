import re
from typing import Dict, Any, List, Optional


def slugify(text: str) -> str:
    """Convert text to a URL-friendly slug."""
    # Convert to lowercase
    text = text.lower()
    # Replace spaces and underscores with hyphens
    text = re.sub(r'[\s_]+', '-', text)
    # Remove non-alphanumeric characters except hyphens
    text = re.sub(r'[^a-z0-9-]', '', text)
    # Remove leading/trailing hyphens
    text = text.strip('-')
    # Collapse multiple hyphens
    text = re.sub(r'-+', '-', text)
    return text


def _extract_numeric_id(gid: str) -> str:
    """Extract numeric ID from a Shopify GID like 'gid://shopify/Product/123456'."""
    if not gid:
        return ""
    
    # Try to extract the last part after the last slash
    parts = gid.split('/')
    if len(parts) > 1:
        return parts[-1]
    
    return gid


def _html_to_text(html: str) -> str:
    """Convert HTML to plain text by stripping tags."""
    if not html:
        return ""
    
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', html)
    # Decode common HTML entities
    text = text.replace('&nbsp;', ' ')
    text = text.replace('&amp;', '&')
    text = text.replace('&lt;', '<')
    text = text.replace('&gt;', '>')
    text = text.replace('&quot;', '"')
    text = text.replace('&#39;', "'")
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def transform_shopify_product_to_canonical(merchant_id: str, product_node: Dict[str, Any], shop_domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Transform a Shopify GraphQL product node into canonical structure.
    
    Args:
        merchant_id: The merchant's ID
        product_node: The Shopify GraphQL product node
        shop_domain: Optional shop domain for constructing URLs
    
    Returns:
        Dictionary containing product fields, variants, and media
    """
    # Extract basic fields
    title = product_node.get('title', '')
    handle = product_node.get('handle', '')
    description_html = product_node.get('descriptionHtml', '')
    vendor = product_node.get('vendor', '')
    product_type = product_node.get('productType', '')
    tags = product_node.get('tags', [])
    status = product_node.get('status', '')
    
    # Extract source_product_id from GID
    raw_id = product_node.get('id', '')
    source_product_id = _extract_numeric_id(raw_id)
    
    # Create summary from first 200 characters of description
    description_text = _html_to_text(description_html)
    summary = description_text[:200] + '...' if len(description_text) > 200 else description_text
    
    # Build URL
    url = None
    if shop_domain and handle:
        url = f"https://{shop_domain}/products/{handle}"
    
    # Process variants
    variants_data = []
    variants_edges = product_node.get('variants', {}).get('edges', [])
    
    for edge in variants_edges:
        variant_node = edge.get('node', {})
        
        # Extract options
        selected_options = variant_node.get('selectedOptions', [])
        options_dict = {}
        for opt in selected_options:
            opt_name = opt.get('name', '')
            opt_value = opt.get('value', '')
            if opt_name:
                options_dict[opt_name.lower()] = opt_value
        
        variant_data = {
            'source_variant_id': _extract_numeric_id(variant_node.get('id', '')),
            'sku': variant_node.get('sku'),
            'price': float(variant_node.get('price', 0) or 0),
            'compare_at_price': float(variant_node.get('compareAtPrice', 0) or 0) if variant_node.get('compareAtPrice') else None,
            'currency': 'USD',  # Default, could be extracted from context
            'inventory_quantity': int(variant_node.get('inventoryQuantity', 0) or 0),
            'options': options_dict,
            'available': int(variant_node.get('inventoryQuantity', 0) or 0) > 0
        }
        variants_data.append(variant_data)
    
    # Process images/media
    media_data = []
    images_edges = product_node.get('images', {}).get('edges', [])
    
    for idx, edge in enumerate(images_edges):
        image_node = edge.get('node', {})
        media_data.append({
            'url': image_node.get('url', ''),
            'alt_text': image_node.get('altText'),
            'position': idx + 1
        })
    
    # Build canonical attributes
    canonical_attributes = {
        'options': list(set(opt.lower() for v in variants_data for opt in (v.get('options', {}) or {}).keys())),
        'tags': tags if isinstance(tags, list) else []
    }
    
    # Build the canonical product structure
    canonical_product = {
        'merchant_id': merchant_id,
        'channel': 'shopify',
        'source_product_id': source_product_id,
        'title': title,
        'handle': handle,
        'summary': summary,
        'description': description_text,
        'brand': vendor,
        'product_type': product_type,
        'tags': tags if isinstance(tags, list) else [],
        'status': status,
        'url': url,
        'raw_payload': product_node,
        'canonical_attributes': canonical_attributes,
        'variants': variants_data,
        'media': media_data
    }
    
    return canonical_product
