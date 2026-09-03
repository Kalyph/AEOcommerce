from sqlmodel import SQLModel, Field, Relationship
from typing import Optional, List
from datetime import datetime
import uuid


def generate_uuid() -> str:
    return str(uuid.uuid4())


class Merchant(SQLModel, table=True):
    __tablename__ = "merchants"
    
    id: str = Field(default_factory=generate_uuid, primary_key=True)
    name: str
    slug: str = Field(unique=True, index=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    shopify_connections: List["ShopifyConnection"] = Relationship(back_populates="merchant")
    products: List["Product"] = Relationship(back_populates="merchant")
    collections: List["Collection"] = Relationship(back_populates="merchant")
    sync_jobs: List["SyncJob"] = Relationship(back_populates="merchant")
    agent_api_keys: List["AgentApiKey"] = Relationship(back_populates="merchant")
    request_logs: List["RequestLog"] = Relationship(back_populates="merchant")
    carts: List["Cart"] = Relationship(back_populates="merchant")
    readiness_scores: List["ReadinessScore"] = Relationship(back_populates="merchant")


class ShopifyConnection(SQLModel, table=True):
    __tablename__ = "shopify_connections"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    shop_domain: str = Field(unique=True, index=True)
    access_token: str
    scopes: str = ""
    status: str = "active"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="shopify_connections")
    sync_jobs: List["SyncJob"] = Relationship(back_populates="connection")


class Product(SQLModel, table=True):
    __tablename__ = "products"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    channel: str = "shopify"
    source_product_id: str
    title: str
    handle: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    tags: Optional[str] = None  # JSON string
    status: Optional[str] = None
    url: Optional[str] = None
    raw_payload: Optional[str] = None  # JSON string
    canonical_attributes: Optional[str] = None  # JSON string
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="products")
    variants: List["Variant"] = Relationship(back_populates="product")
    media_assets: List["MediaAsset"] = Relationship(back_populates="product")
    product_collections: List["ProductCollection"] = Relationship(back_populates="product")
    
    __table_args__ = (
        # Unique constraint on merchant_id + channel + source_product_id
        {"sqlite_autoincrement": True} if True else {}
    )


class Variant(SQLModel, table=True):
    __tablename__ = "variants"
    
    id: int = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    source_variant_id: str
    sku: Optional[str] = None
    price: Optional[float] = None
    compare_at_price: Optional[float] = None
    currency: str = "USD"
    inventory_quantity: int = 0
    options: Optional[str] = None  # JSON string
    available: bool = True
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    product: Product = Relationship(back_populates="variants")


class MediaAsset(SQLModel, table=True):
    __tablename__ = "media_assets"
    
    id: int = Field(default=None, primary_key=True)
    product_id: int = Field(foreign_key="products.id", index=True)
    url: str
    alt_text: Optional[str] = None
    position: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    product: Product = Relationship(back_populates="media_assets")


class Collection(SQLModel, table=True):
    __tablename__ = "collections"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    source_collection_id: str
    title: str
    handle: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="collections")
    product_collections: List["ProductCollection"] = Relationship(back_populates="collection")
    
    __table_args__ = (
        # Unique constraint on merchant_id + source_collection_id
        {"sqlite_autoincrement": True} if True else {}
    )


class ProductCollection(SQLModel, table=True):
    __tablename__ = "product_collections"
    
    product_id: int = Field(foreign_key="products.id", primary_key=True)
    collection_id: int = Field(foreign_key="collections.id", primary_key=True)
    
    product: Product = Relationship(back_populates="product_collections")
    collection: Collection = Relationship(back_populates="product_collections")


class SyncJob(SQLModel, table=True):
    __tablename__ = "sync_jobs"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    connection_id: Optional[int] = Field(default=None, foreign_key="shopify_connections.id")
    status: str
    started_at: datetime = Field(default_factory=datetime.utcnow)
    finished_at: Optional[datetime] = None
    error: Optional[str] = None
    
    merchant: Merchant = Relationship(back_populates="sync_jobs")
    connection: Optional[ShopifyConnection] = Relationship(back_populates="sync_jobs")


class AgentApiKey(SQLModel, table=True):
    __tablename__ = "agent_api_keys"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    name: str
    key_hash: str
    scopes: Optional[str] = None  # JSON string
    rate_limit: int = 60
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="agent_api_keys")


class RequestLog(SQLModel, table=True):
    __tablename__ = "request_logs"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: Optional[str] = Field(default=None, foreign_key="merchants.id")
    endpoint: str
    request_payload: Optional[str] = None  # JSON string
    response_status: int
    latency_ms: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Optional[Merchant] = Relationship(back_populates="request_logs")


class Cart(SQLModel, table=True):
    __tablename__ = "carts"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    items: str  # JSON string
    cart_url: Optional[str] = None
    status: str = "created"
    expires_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="carts")


class ReadinessScore(SQLModel, table=True):
    __tablename__ = "readiness_scores"
    
    id: int = Field(default=None, primary_key=True)
    merchant_id: str = Field(foreign_key="merchants.id", index=True)
    score: int
    issues: Optional[str] = None  # JSON string
    recommendations: Optional[str] = None  # JSON string
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    merchant: Merchant = Relationship(back_populates="readiness_scores")
