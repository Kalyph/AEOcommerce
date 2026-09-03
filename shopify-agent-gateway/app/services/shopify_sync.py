import httpx
import json
from datetime import datetime
from typing import Optional
from sqlmodel import Session, select

from app.models.db import ShopifyConnection, Product, Variant, MediaAsset, SyncJob, Merchant
from app.core.config import settings
from app.core.security import decrypt_token
from app.services.canonical import transform_shopify_product_to_canonical


def sync_shopify_products(connection: ShopifyConnection, merchant_id: str, session: Session) -> SyncJob:
    """
    Sync products from Shopify to the local database.
    
    Args:
        connection: The ShopifyConnection record
        merchant_id: The merchant's ID
        session: The database session
    
    Returns:
        A SyncJob record with the result
    """
    # Create sync job record
    sync_job = SyncJob(
        merchant_id=merchant_id,
        connection_id=connection.id,
        status="running",
        started_at=datetime.utcnow()
    )
    session.add(sync_job)
    session.commit()
    session.refresh(sync_job)
    
    try:
        shop_domain = connection.shop_domain
        access_token = decrypt_token(connection.access_token)
        
        graphql_url = f"https://{shop_domain}/admin/api/{settings.shopify_api_version}/graphql.json"
        
        headers = {
            "X-Shopify-Access-Token": access_token,
            "Content-Type": "application/json"
        }
        
        query = """
        query getProducts($first: Int!, $after: String) {
          products(first: $first, after: $after) {
            pageInfo {
              hasNextPage
              endCursor
            }
            edges {
              node {
                id
                title
                handle
                descriptionHtml
                vendor
                productType
                tags
                status
                variants(first: 100) {
                  edges {
                    node {
                      id
                      title
                      sku
                      price
                      compareAtPrice
                      inventoryQuantity
                      selectedOptions {
                        name
                        value
                      }
                    }
                  }
                }
                images(first: 20) {
                  edges {
                    node {
                      url
                      altText
                    }
                  }
                }
              }
            }
          }
        }
        """
        
        all_products = []
        has_next_page = True
        cursor = None
        
        while has_next_page:
            variables = {"first": 100}
            if cursor:
                variables["after"] = cursor
            
            response = httpx.post(
                graphql_url,
                headers=headers,
                json={"query": query, "variables": variables}
            )
            response.raise_for_status()
            
            data = response.json()
            
            if "errors" in data:
                raise Exception(f"GraphQL errors: {data['errors']}")
            
            products_data = data.get("data", {}).get("products", {})
            page_info = products_data.get("pageInfo", {})
            edges = products_data.get("edges", [])
            
            for edge in edges:
                node = edge.get("node", {})
                all_products.append(node)
            
            has_next_page = page_info.get("hasNextPage", False)
            cursor = page_info.get("endCursor")
        
        # Process each product
        for product_node in all_products:
            canonical = transform_shopify_product_to_canonical(
                merchant_id=merchant_id,
                product_node=product_node,
                shop_domain=shop_domain
            )
            
            # Upsert Product
            existing_product = session.exec(
                select(Product).where(
                    Product.merchant_id == merchant_id,
                    Product.channel == canonical["channel"],
                    Product.source_product_id == canonical["source_product_id"]
                )
            ).first()
            
            if existing_product:
                # Update existing product
                existing_product.title = canonical["title"]
                existing_product.handle = canonical["handle"]
                existing_product.summary = canonical["summary"]
                existing_product.description = canonical["description"]
                existing_product.brand = canonical["brand"]
                existing_product.product_type = canonical["product_type"]
                existing_product.tags = json.dumps(canonical["tags"])
                existing_product.status = canonical["status"]
                existing_product.url = canonical["url"]
                existing_product.raw_payload = json.dumps(canonical["raw_payload"])
                existing_product.canonical_attributes = json.dumps(canonical["canonical_attributes"])
                existing_product.updated_at = datetime.utcnow()
                product = existing_product
            else:
                # Create new product
                product = Product(
                    merchant_id=merchant_id,
                    channel=canonical["channel"],
                    source_product_id=canonical["source_product_id"],
                    title=canonical["title"],
                    handle=canonical["handle"],
                    summary=canonical["summary"],
                    description=canonical["description"],
                    brand=canonical["brand"],
                    product_type=canonical["product_type"],
                    tags=json.dumps(canonical["tags"]),
                    status=canonical["status"],
                    url=canonical["url"],
                    raw_payload=json.dumps(canonical["raw_payload"]),
                    canonical_attributes=json.dumps(canonical["canonical_attributes"]),
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(product)
            
            session.flush()  # Get product ID
            
            # Upsert Variants
            existing_variant_ids = set()
            for variant in session.exec(select(Variant).where(Variant.product_id == product.id)).all():
                existing_variant_ids.add(variant.source_variant_id)
            
            processed_variant_ids = set()
            
            for variant_data in canonical.get("variants", []):
                source_variant_id = variant_data["source_variant_id"]
                processed_variant_ids.add(source_variant_id)
                
                existing_variant = session.exec(
                    select(Variant).where(
                        Variant.product_id == product.id,
                        Variant.source_variant_id == source_variant_id
                    )
                ).first()
                
                if existing_variant:
                    existing_variant.sku = variant_data.get("sku")
                    existing_variant.price = variant_data.get("price")
                    existing_variant.compare_at_price = variant_data.get("compare_at_price")
                    existing_variant.inventory_quantity = variant_data.get("inventory_quantity", 0)
                    existing_variant.options = json.dumps(variant_data.get("options", {}))
                    existing_variant.available = variant_data.get("available", True)
                    existing_variant.updated_at = datetime.utcnow()
                else:
                    variant = Variant(
                        product_id=product.id,
                        source_variant_id=source_variant_id,
                        sku=variant_data.get("sku"),
                        price=variant_data.get("price"),
                        compare_at_price=variant_data.get("compare_at_price"),
                        currency=variant_data.get("currency", "USD"),
                        inventory_quantity=variant_data.get("inventory_quantity", 0),
                        options=json.dumps(variant_data.get("options", {})),
                        available=variant_data.get("available", True),
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    session.add(variant)
            
            # Delete removed variants
            for variant_id in existing_variant_ids - processed_variant_ids:
                variant_to_delete = session.exec(
                    select(Variant).where(
                        Variant.product_id == product.id,
                        Variant.source_variant_id == variant_id
                    )
                ).first()
                if variant_to_delete:
                    session.delete(variant_to_delete)
            
            # Replace MediaAssets
            session.exec(
                select(MediaAsset).where(MediaAsset.product_id == product.id)
            ).all()
            for media in session.exec(select(MediaAsset).where(MediaAsset.product_id == product.id)).all():
                session.delete(media)
            
            for media_data in canonical.get("media", []):
                media = MediaAsset(
                    product_id=product.id,
                    url=media_data["url"],
                    alt_text=media_data.get("alt_text"),
                    position=media_data.get("position")
                )
                session.add(media)
        
        session.commit()
        
        # Update sync job
        sync_job.status = "completed"
        sync_job.finished_at = datetime.utcnow()
        session.add(sync_job)
        session.commit()
        
    except Exception as e:
        session.rollback()
        sync_job.status = "failed"
        sync_job.finished_at = datetime.utcnow()
        sync_job.error = str(e)
        session.add(sync_job)
        session.commit()
    
    return sync_job
