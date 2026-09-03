from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime


class AgentQueryRequest(BaseModel):
    query: str
    context: Dict[str, Any] = {}
    limit: int = 20


class AgentQueryResponse(BaseModel):
    answer: str
    products: List[Dict[str, Any]]
    next_actions: List[str]
    confidence: float


class CartItem(BaseModel):
    variant_id: str
    quantity: int = 1


class CartCreateRequest(BaseModel):
    items: List[CartItem]


class CartCreateResponse(BaseModel):
    cart_url: str
    mode: str = "checkout_handoff"
    expires_at: Optional[datetime] = None


class ProductSummary(BaseModel):
    product_id: str
    title: str
    summary: Optional[str] = None
    price_from: Optional[float] = None
    currency: str = "USD"
    in_stock: bool
    url: Optional[str] = None
    variants_available: int = 0


class ProductDetail(BaseModel):
    product_id: str
    title: str
    handle: Optional[str] = None
    summary: Optional[str] = None
    description: Optional[str] = None
    brand: Optional[str] = None
    product_type: Optional[str] = None
    tags: Optional[List[str]] = None
    price_from: Optional[float] = None
    currency: str = "USD"
    in_stock: bool
    url: Optional[str] = None
    variants: List[Dict[str, Any]] = []
    media: List[Dict[str, Any]] = []
    capabilities: Dict[str, bool] = {
        "cart_eligible": True,
        "checkout_eligible": True
    }


class MerchantReadiness(BaseModel):
    merchant_id: str
    score: int
    issues: List[str]
    recommendations: List[str]
    updated_at: datetime
