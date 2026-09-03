"""Tests for the Shopify Agent Readiness Gateway API."""
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine
from sqlmodel.pool import StaticPool

from app.main import app
from app.core.database import create_db_and_tables, get_session
from app.models.db import Merchant, Product, Variant, MediaAsset, ShopifyConnection


def override_get_session():
    """Override session dependency for tests."""
    with Session(engine) as session:
        yield session


# Create test engine
engine = create_engine(
    "sqlite:///./test_phase1.db",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)


def setup_module(module):
    """Setup test database before running tests."""
    create_db_and_tables()
    
    # Seed demo data
    from scripts.seed_demo import seed_demo
    seed_demo()


def teardown_module(module):
    """Cleanup after tests."""
    pass


@pytest.fixture(scope="module")
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


class TestHealthEndpoint:
    """Test health check endpoint."""
    
    def test_health_check(self, client):
        """Test /health returns 200."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert data["app"] == "Shopify Agent Readiness Gateway"
        assert data["phase"] == 1


class TestLlmsTxt:
    """Test llms.txt endpoint."""
    
    def test_llms_txt(self, client):
        """Test /stores/demo/llms.txt returns 200."""
        response = client.get("/stores/demo/llms.txt")
        assert response.status_code == 200
        assert "Peak Outdoor Gear" in response.text
        assert "product_search: true" in response.text


class TestAgentManifest:
    """Test agent manifest endpoint."""
    
    def test_agent_manifest(self, client):
        """Test /stores/demo/ai/manifest returns 200."""
        response = client.get("/stores/demo/ai/manifest")
        assert response.status_code == 200
        data = response.json()
        assert data["store_name"] == "Peak Outdoor Gear"
        assert data["channel"] == "shopify"
        assert data["capabilities"]["catalog_read"] is True
        assert data["capabilities"]["cart_create"] is True


class TestProductsEndpoint:
    """Test products listing endpoint."""
    
    def test_list_products(self, client):
        """Test /stores/demo/ai/products returns products."""
        response = client.get("/stores/demo/ai/products")
        assert response.status_code == 200
        data = response.json()
        assert "products" in data
        assert len(data["products"]) > 0
    
    def test_list_products_with_query(self, client):
        """Test /stores/demo/ai/products with query filter."""
        response = client.get("/stores/demo/ai/products?query=backpack")
        assert response.status_code == 200
        data = response.json()
        assert len(data["products"]) > 0


class TestProductDetail:
    """Test product detail endpoint."""
    
    def test_get_product(self, client):
        """Test /stores/demo/ai/products/{product_id} returns 200."""
        # First get a product ID
        products_response = client.get("/stores/demo/ai/products")
        products = products_response.json()["products"]
        
        if products:
            product_id = products[0]["product_id"]
            response = client.get(f"/stores/demo/ai/products/{product_id}")
            assert response.status_code == 200
            data = response.json()
            assert "title" in data
            assert "variants" in data
            assert data["capabilities"]["cart_eligible"] is True


class TestAgentQuery:
    """Test agent query endpoint."""
    
    def test_agent_query(self, client):
        """Test POST /stores/demo/ai/query returns matching products."""
        response = client.post(
            "/stores/demo/ai/query",
            json={"query": "waterproof dog collar"}
        )
        assert response.status_code == 200
        data = response.json()
        assert "answer" in data
        assert "products" in data
        assert "next_actions" in data
        assert "confidence" in data
        assert len(data["products"]) >= 1


class TestCartCreation:
    """Test cart creation endpoint."""
    
    def test_create_cart(self, client):
        """Test POST /stores/demo/ai/cart creates cart URL."""
        # Use known variant ID from demo data
        response = client.post(
            "/stores/demo/ai/cart",
            json={
                "items": [
                    {
                        "variant_id": "44556677889",
                        "quantity": 1
                    }
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "cart_url" in data
        assert "/cart/44556677889:1" in data["cart_url"]
        assert data["mode"] == "checkout_handoff"
    
    def test_create_cart_multiple_items(self, client):
        """Test creating cart with multiple items."""
        response = client.post(
            "/stores/demo/ai/cart",
            json={
                "items": [
                    {"variant_id": "44556677889", "quantity": 2},
                    {"variant_id": "55667788990", "quantity": 1}
                ]
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert "cart_url" in data
        assert "44556677889:2" in data["cart_url"]
        assert "55667788990:1" in data["cart_url"]
    
    def test_create_cart_invalid_variant(self, client):
        """Test cart creation with invalid variant returns 400."""
        response = client.post(
            "/stores/demo/ai/cart",
            json={
                "items": [
                    {"variant_id": "invalid_variant_id", "quantity": 1}
                ]
            }
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
