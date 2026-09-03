# Shopify Agent Readiness Gateway

Phase 1 of the Agentic Commerce Middleware platform - a FastAPI backend that enables AI agents to interact with Shopify store data.

## Overview

This gateway provides:
- Merchant and Shopify connection management
- Normalized commerce data storage
- Agent-readable endpoints for product search and details
- `llms.txt` and `/ai/manifest` generation for AI agent discovery
- Cart handoff URL generation for Shopify checkout
- Agent Readiness Score calculation

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Environment Variables (Optional)

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=sqlite:///./phase1.db
SHOPIFY_API_KEY=your_api_key
SHOPIFY_API_SECRET=your_api_secret
SHOPIFY_REDIRECT_URI=http://localhost:8000/auth/shopify/callback
APP_URL=http://localhost:8000
SHOPIFY_API_VERSION=2025-10
ENCRYPTION_KEY=your_fernet_key
```

**Note:** The app will run without setting Shopify credentials. Demo data can be seeded for local testing.

### 3. Seed Demo Data

```bash
python -m scripts.seed_demo
```

This creates a demo merchant "Peak Outdoor Gear" with sample products.

### 4. Run the Server

```bash
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The API docs will be available at: http://localhost:8000/docs

## Endpoints

### Public Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | App info |
| `/health` | GET | Health check |
| `/stores/{slug}/llms.txt` | GET | AI agent manifest (plain text) |
| `/stores/{slug}/ai/manifest` | GET | Agent capabilities manifest |
| `/stores/{slug}/ai/products` | GET | List products with filters |
| `/stores/{slug}/ai/products/{id}` | GET | Product details |
| `/stores/{slug}/ai/query` | POST | Natural language product search |
| `/stores/{slug}/ai/cart` | POST | Create cart handoff URL |

### Admin Endpoints (Phase 1: No Auth)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/admin/merchants` | GET | List merchants |
| `/admin/merchants` | POST | Create merchant |
| `/admin/merchants/{id}/readiness` | GET | Get readiness score |
| `/admin/merchants/{id}/seed-demo-products` | POST | Seed demo products |

### Shopify OAuth Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/auth/shopify/install` | GET | Initiate OAuth flow |
| `/auth/shopify/callback` | GET | OAuth callback handler |

## Testing

Run tests with pytest:

```bash
pytest tests/test_api.py -v
```

## Project Structure

```
shopify-agent-gateway/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── core/
│   │   ├── config.py        # Pydantic settings
│   │   ├── database.py      # SQLModel engine & session
│   │   └── security.py      # Token encryption/hashing
│   ├── models/
│   │   └── db.py            # SQLModel database tables
│   ├── schemas/
│   │   └── agent.py         # Pydantic request/response schemas
│   ├── services/
│   │   ├── canonical.py     # Product transformation logic
│   │   ├── shopify_oauth.py # OAuth helpers
│   │   ├── shopify_sync.py  # Product sync from Shopify
│   │   ├── readiness.py     # Readiness score calculation
│   │   └── query_resolver.py # Keyword-based search
│   └── api/
│       ├── routes_health.py
│       ├── routes_auth_shopify.py
│       ├── routes_agent_gateway.py
│       └── routes_admin.py
├── scripts/
│   └── seed_demo.py         # Demo data seeder
├── tests/
│   └── test_api.py          # API tests
├── requirements.txt
├── .env.example
└── README.md
```

## Shopify OAuth Notes

To enable real Shopify integration:

1. Create a custom app in your Shopify Partner dashboard
2. Get API key and secret
3. Set `SHOPIFY_API_KEY`, `SHOPIFY_API_SECRET`, and `SHOPIFY_REDIRECT_URI`
4. Visit `/auth/shopify/install?shop=your-store.myshopify.com`

Without credentials, the app runs in demo mode with seeded data.

## Next Steps (Future Phases)

- [ ] API key authentication for agent endpoints
- [ ] Real-time Shopify webhook sync
- [ ] LLM-based query resolution
- [ ] Order status reading
- [ ] Delegated checkout support
- [ ] Multi-channel support (beyond Shopify)
- [ ] PostgreSQL deployment support
- [ ] Rate limiting and quota management
