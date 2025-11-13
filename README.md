
# Product Importer — Enterprise CSV Import System

High-performance, scalable FastAPI application for bulk product management with real-time CSV import capabilities. Designed to efficiently process very large CSV files (500k+ records) using Celery workers, PostgreSQL, and Redis.

## Table of Contents
- Features
- Technology Stack
- Architecture
- Installation & Setup
- API Overview
- CSV Format
- Deployment
- Development Guide
- Testing
- Troubleshooting
- Contributing
- Support

## Features
- Large file processing: Streamed, chunked CSV imports (500,000+ records)
- Real-time progress tracking via task status endpoints
- SKU-based deduplication (case-insensitive)
- Batch processing for memory-efficient imports
- Full CRUD for products, filtering, pagination, and bulk delete
- Webhook system for event notifications
- Asynchronous background processing (Celery)
- Lightweight responsive frontend for monitoring and upload

## Technology Stack
- Backend: FastAPI, Uvicorn/Gunicorn
- ORM/Validation: SQLAlchemy, Pydantic
- Task Queue: Celery
- Database: PostgreSQL
- Broker/Cache: Redis
- Frontend: HTML5, CSS3, Vanilla JavaScript
- Deployment examples: Render.com / Docker

## Architecture (high level)
Client Browser → FastAPI Application → PostgreSQL
                     ↓
                Celery Worker (Redis)
                     ↓
               Background Task Processing

Design patterns: Repository (CRUD), Factory (DB sessions), Observer (webhooks), Strategy (file processing).

## Installation & Setup (Windows)
Prerequisites:
- Python 3.11+
- PostgreSQL 13+
- Redis 6+
- (Optional) Docker

1. Clone repository
```bash
git clone https://github.com/adharsh555/Product-Importer.git
cd Product-Importer
```

2. Create & activate virtualenv
```powershell
python -m venv venv
# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1
# Or CMD
venv\Scripts\activate
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Create `.env` in project root:
```
DATABASE_URL=postgresql://username:password@localhost:5432/product_importer
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=your-secure-secret-key
ENVIRONMENT=development
```

5. Start services
- Option A: Docker (recommended for local dev)
```bash
docker run --name postgres -e POSTGRES_PASSWORD=password -d -p 5432:5432 postgres:13
docker run --name redis -d -p 6379:6379 redis:alpine
```
- Option B: Local installations — ensure PostgreSQL and Redis are running and DB `product_importer` exists.

6. Start workers & app (two terminals)
Terminal 1 — Celery worker:
```bash
celery -A app.celery_app worker --loglevel=info
```
Terminal 2 — FastAPI server:
```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Open: http://localhost:8000

## API Overview (base: /api/)
- GET /api/products/ — list with skip, limit, sku, name, active, description filters
- POST /api/products/ — create product
- PUT /api/products/{id} — update product
- DELETE /api/products/{id} — delete product
- DELETE /api/products/ — bulk delete (returns deleted_count)
- POST /api/upload/ — multipart/form-data CSV upload (returns job_id & task_id)
- GET /api/tasks/{task_id} — get import progress/status
- GET /api/webhooks/ — list webhooks
- POST /api/webhooks/ — create webhook
- DELETE /api/webhooks/{id} — delete webhook

Example response snippets and shapes are implemented in the API docs (Swagger/OpenAPI available at runtime).

## CSV File Format
Expected header and fields:
```
sku,name,description
ABC123,Product One,Description...
```
Required:
- sku (unique, case-insensitive) — duplicates update existing product
- name

Optional:
- description

Processing: streamed by chunks with SKU dedupe and batch inserts/updates.

## Deployment (Render.com)
- Use render.yaml for automated provisioning (web + worker + DB + Redis).
- Build command: pip install -r requirements.txt
- Start command (web): gunicorn app.main:app --workers 1 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
- Worker: celery -A app.celery_app worker --loglevel=info
- Configure DATABASE_URL, REDIS_URL, SECRET_KEY in environment vars.

Production considerations:
- HTTPS, CORS config, rate limiting, DB pooling, Redis persistence, logging & monitoring, and proper worker scaling.

## Development Guide
Project layout (key files)
- app/main.py — FastAPI app & routes
- app/config.py — config loader
- app/database.py — DB session / engine
- app/models.py — SQLAlchemy models (Product, Webhook, ImportJob)
- app/schemas.py — Pydantic schemas
- app/crud.py — DB operations
- app/tasks.py — Celery tasks
- app/celery_app.py — Celery config
- app/static/ — frontend (index.html, style.css, app.js)
- tests/ — unit & integration tests

Adding new features: update models, add migrations, expose API route, add tasks/tests.

## Testing
Run tests:
```bash
pytest
pytest --cov=app tests/
pytest tests/test_products.py
```
Recommended: use fixtures in tests/conftest.py to provision test DB and Redis mocks.

## Troubleshooting (common)
- DB connection: verify service running, correct DATABASE_URL, psql check
- Redis: redis-cli ping → PONG; celery inspect ping
- File uploads failing: check size limits, CSV format, disk space
- Bulk delete: confirm transaction commit & permissions
- Slow imports: increase batch size, add DB indexes, scale workers, stream processing

Enable SQL logging in development:
```python
import logging
logging.basicConfig()
logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)
```

## Contributing
- Fork → branch (feature/...) → tests → PR
- Follow PEP8, type hints, docstrings
- Include DB migrations for model changes
- Add unit + integration tests for new features

## Support
- Check Issues and Discussions in repo
- When reporting bugs include: app version, env, steps to reproduce, logs, expected vs actual


