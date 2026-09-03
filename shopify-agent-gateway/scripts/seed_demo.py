"""
Seed demo data for the Shopify Agent Readiness Gateway.

This script creates a demo merchant with sample products for testing.
"""
import json
from datetime import datetime
from sqlmodel import Session, select

from app.core.database import engine, create_db_and_tables
from app.models.db import Merchant, ShopifyConnection, Product, Variant, MediaAsset, ReadinessScore
from app.services.readiness import calculate_readiness_score


def create_demo_products_for_merchant(merchant: Merchant, session: Session) -> int:
    """Create or update demo products for a merchant."""
    
    shop_domain = "peak-outdoor-demo.myshopify.com"
    
    # Demo product data
    demo_products = [
        {
            "title": "TrailHound Waterproof Dog Collar",
            "handle": "trailhound-waterproof-dog-collar",
            "summary": "Durable waterproof dog collar for outdoor use.",
            "description": "A weatherproof dog collar made for hiking and training. Waterproof, durable, and available in multiple sizes.",
            "brand": "TrailHound",
            "product_type": "Dog Accessories",
            "tags": ["dog", "collar", "waterproof", "outdoor"],
            "status": "ACTIVE",
            "url": f"https://{shop_domain}/products/trailhound-waterproof-dog-collar",
            "variants": [
                {
                    "source_variant_id": "44556677889",
                    "sku": "TH-RED-S",
                    "price": 34.0,
                    "inventory_quantity": 18,
                    "options": {"color": "Red", "size": "Small"}
                },
                {
                    "source_variant_id": "44556677890",
                    "sku": "TH-RED-M",
                    "price": 34.0,
                    "inventory_quantity": 25,
                    "options": {"color": "Red", "size": "Medium"}
                },
                {
                    "source_variant_id": "44556677891",
                    "sku": "TH-BLK-L",
                    "price": 36.0,
                    "inventory_quantity": 0,
                    "options": {"color": "Black", "size": "Large"}
                }
            ],
            "media": [
                {
                    "url": "https://cdn.example.com/dog-collar-red.jpg",
                    "alt_text": "Red waterproof dog collar",
                    "position": 1
                }
            ]
        },
        {
            "title": "Summit 45L Hiking Backpack",
            "handle": "summit-45l-hiking-backpack",
            "summary": "Lightweight 45L hiking backpack for multi-day trails.",
            "description": "A comfortable 45L backpack with waterproof rain cover and multiple compartments.",
            "brand": "Peak Outdoor",
            "product_type": "Backpacks",
            "tags": ["hiking", "backpack", "45L", "waterproof"],
            "status": "ACTIVE",
            "url": f"https://{shop_domain}/products/summit-45l-hiking-backpack",
            "variants": [
                {
                    "source_variant_id": "55667788990",
                    "sku": "BP-45L-GRN",
                    "price": 129.0,
                    "inventory_quantity": 12,
                    "options": {"color": "Green", "size": "45L"}
                }
            ],
            "media": [
                {
                    "url": "https://cdn.example.com/backpack.jpg",
                    "alt_text": "Green 45L hiking backpack",
                    "position": 1
                }
            ]
        },
        {
            "title": "Alpine Insulated Water Bottle",
            "handle": "alpine-insulated-water-bottle",
            "summary": "Keeps drinks cold for 24 hours.",
            "description": "Insulated stainless steel bottle for hiking, camping, and travel.",
            "brand": "Alpine",
            "product_type": "Hydration",
            "tags": ["water bottle", "insulated", "camping"],
            "status": "ACTIVE",
            "url": f"https://{shop_domain}/products/alpine-insulated-water-bottle",
            "variants": [
                {
                    "source_variant_id": "66778899001",
                    "sku": "WB-750-BLU",
                    "price": 24.0,
                    "inventory_quantity": 50,
                    "options": {"color": "Blue", "size": "750ml"}
                }
            ],
            "media": [
                {
                    "url": "https://cdn.example.com/bottle.jpg",
                    "alt_text": "Blue insulated water bottle",
                    "position": 1
                }
            ]
        }
    ]
    
    created_count = 0
    
    for demo_product in demo_products:
        # Check if product already exists
        existing_product = session.exec(
            select(Product).where(
                Product.merchant_id == merchant.id,
                Product.source_product_id == demo_product["variants"][0]["source_variant_id"][:10]  # Use first variant ID as product ID proxy
            )
        ).first()
        
        # Generate a unique source_product_id from handle
        source_product_id = str(abs(hash(demo_product["handle"])))
        
        existing_product = session.exec(
            select(Product).where(
                Product.merchant_id == merchant.id,
                Product.handle == demo_product["handle"]
            )
        ).first()
        
        if existing_product:
            # Update existing product
            existing_product.title = demo_product["title"]
            existing_product.summary = demo_product["summary"]
            existing_product.description = demo_product["description"]
            existing_product.brand = demo_product["brand"]
            existing_product.product_type = demo_product["product_type"]
            existing_product.tags = json.dumps(demo_product["tags"])
            existing_product.status = demo_product["status"]
            existing_product.url = demo_product["url"]
            existing_product.updated_at = datetime.utcnow()
            product = existing_product
        else:
            # Create new product
            product = Product(
                merchant_id=merchant.id,
                channel="shopify",
                source_product_id=source_product_id,
                title=demo_product["title"],
                handle=demo_product["handle"],
                summary=demo_product["summary"],
                description=demo_product["description"],
                brand=demo_product["brand"],
                product_type=demo_product["product_type"],
                tags=json.dumps(demo_product["tags"]),
                status=demo_product["status"],
                url=demo_product["url"],
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            session.add(product)
            created_count += 1
        
        session.flush()
        
        # Upsert variants
        for variant_data in demo_product["variants"]:
            existing_variant = session.exec(
                select(Variant).where(
                    Variant.product_id == product.id,
                    Variant.source_variant_id == variant_data["source_variant_id"]
                )
            ).first()
            
            if existing_variant:
                existing_variant.sku = variant_data["sku"]
                existing_variant.price = variant_data["price"]
                existing_variant.inventory_quantity = variant_data["inventory_quantity"]
                existing_variant.options = json.dumps(variant_data["options"])
                existing_variant.available = variant_data["inventory_quantity"] > 0
                existing_variant.updated_at = datetime.utcnow()
            else:
                variant = Variant(
                    product_id=product.id,
                    source_variant_id=variant_data["source_variant_id"],
                    sku=variant_data["sku"],
                    price=variant_data["price"],
                    inventory_quantity=variant_data["inventory_quantity"],
                    options=json.dumps(variant_data["options"]),
                    available=variant_data["inventory_quantity"] > 0,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                session.add(variant)
        
        # Upsert media
        for media_data in demo_product["media"]:
            existing_media = session.exec(
                select(MediaAsset).where(
                    MediaAsset.product_id == product.id,
                    MediaAsset.url == media_data["url"]
                )
            ).first()
            
            if not existing_media:
                media = MediaAsset(
                    product_id=product.id,
                    url=media_data["url"],
                    alt_text=media_data["alt_text"],
                    position=media_data["position"]
                )
                session.add(media)
    
    session.commit()
    
    return created_count


def seed_demo():
    """Main seed function."""
    print("Creating database tables...")
    create_db_and_tables()
    
    with Session(engine) as session:
        # Create or get demo merchant
        demo_slug = "demo"
        merchant = session.exec(select(Merchant).where(Merchant.slug == demo_slug)).first()
        
        if not merchant:
            print("Creating demo merchant: Peak Outdoor Gear")
            merchant = Merchant(
                name="Peak Outdoor Gear",
                slug=demo_slug
            )
            session.add(merchant)
            session.flush()
        else:
            print("Demo merchant already exists")
        
        # Create or update Shopify connection
        connection = session.exec(
            select(ShopifyConnection).where(ShopifyConnection.shop_domain == "peak-outdoor-demo.myshopify.com")
        ).first()
        
        if not connection:
            print("Creating Shopify connection")
            connection = ShopifyConnection(
                merchant_id=merchant.id,
                shop_domain="peak-outdoor-demo.myshopify.com",
                access_token="demo-token",
                scopes="read_products",
                status="demo"
            )
            session.add(connection)
            session.flush()
        else:
            print("Shopify connection already exists")
        
        # Create demo products
        print("Creating demo products...")
        created_count = create_demo_products_for_merchant(merchant, session)
        print(f"Created {created_count} new products")
        
        # Calculate readiness score
        print("Calculating readiness score...")
        readiness = calculate_readiness_score(merchant.id, session)
        print(f"Readiness score: {readiness.score}")
        
        issues = json.loads(readiness.issues) if readiness.issues else []
        recommendations = json.loads(readiness.recommendations) if readiness.recommendations else []
        
        print(f"Issues: {issues}")
        print(f"Recommendations: {recommendations}")
    
    print("\nDemo seeding complete!")
    print(f"Merchant slug: {demo_slug}")
    print(f"Test endpoints at /stores/{demo_slug}/ai/manifest")


if __name__ == "__main__":
    seed_demo()
