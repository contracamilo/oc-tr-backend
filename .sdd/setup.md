# Setup — Hogar BFF

> Guía de setup local para desarrollo con PostgreSQL + FastAPI async.

---

## 1. Requisitos

- Python 3.11+
- Docker Desktop (para PostgreSQL local y tests con testcontainers)
- Git

## 2. Clonar e instalar

```bash
git clone https://github.com/contracamilo/oc-tr-backend.git
cd oc-tr-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

## 3. Base de datos

### Opción A: PostgreSQL con Docker (recomendada)

```bash
docker run --name hogar-db \
  -e POSTGRES_USER=hogar \
  -e POSTGRES_PASSWORD=hogar \
  -e POSTGRES_DB=hogar \
  -p 5432:5432 \
  -d postgres:16
```

### Opción B: PostgreSQL nativo (si lo tienes instalado)

```bash
createdb hogar
psql hogar -c "CREATE USER hogar WITH PASSWORD 'hogar';"
psql hogar -c "GRANT ALL ON DATABASE hogar TO hogar;"
```

### Configurar .env

```env
APP_ENV=development
DATABASE_URL=postgresql+asyncpg://hogar:hogar@localhost:5432/hogar
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
RATE_LIMIT_LIST=30/minute
RATE_LIMIT_WRITE=10/minute
LOG_LEVEL=DEBUG
```

**Nota**: `DATABASE_URL` usa `postgresql+asyncpg://` para el driver asíncrono.

## 4. Levantar el servidor

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

## 5. Tests

### Requisito

Los tests de integración requieren Docker corriendo (usan `testcontainers-postgres`).

### Ejecutar todos los tests

```bash
pytest -q
```

### Estructura de tests

```
tests/
├── conftest.py              ← Fixtures (app, postgres_container, client)
├── test_users.py            ← Smoke + CRUD Users
├── test_tasks.py            ← Smoke + CRUD Tasks + paginación
├── test_roulette.py         ← Unit (pure function) + Integration (endpoint)
├── test_checklist.py        ← Smoke + CRUD Checklist
├── test_shopping.py         ← Smoke + CRUD Shopping + batch-purchase
├── test_budget.py           ← Smoke + CRUD Budget + summary
└── test_health.py           ← Health check endpoints
```

### Fixtures principales

```python
# tests/conftest.py
import pytest
from testcontainers.postgres import PostgresContainer
from app.main import create_app

@pytest.fixture(scope="session")
def postgres_container():
    with PostgresContainer("postgres:16") as pg:
        yield pg

@pytest.fixture
def app(postgres_container):
    app = create_app()
    app.state.testing = True
    app.state.database_url = postgres_container.get_connection_url()
    return app

@pytest.fixture
async def client(app):
    from httpx import AsyncClient, ASGITransport
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

## 6. Comandos útiles

```bash
# Ver logs de PostgreSQL
docker logs hogar-db

# Conectarse a PostgreSQL
docker exec -it hogar-db psql -U hogar -d hogar

# Resetear base de datos (borrar y recrear)
docker stop hogar-db && docker rm hogar-db
docker run --name hogar-db ... (mismo comando de arriba)

# Ver endpoints disponibles
curl http://localhost:8000/openapi.json | python -m json.tool

# Rate limiting: probar límite
for i in $(seq 1 35); do curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/tasks; done
```

## 7. Troubleshooting

| Problema | Causa | Solución |
|----------|-------|----------|
| `conn refused` al conectar DB | PostgreSQL no corriendo | `docker start hogar-db` |
| `asyncpg.exceptions.InvalidPasswordError` | .env incorrecto | Verificar credenciales en .env |
| `tests fail with Docker not found` | Docker no instalado o no corriendo | `docker ps` para verificar |
| `pytest-asyncio` no reconoce async tests | Falta marcador | Añadir `@pytest.mark.asyncio` o configurar `asyncio_mode = auto` en pytest.ini |
| Rate limit alcanzado en dev | Límite muy bajo | Aumentar en .env: `RATE_LIMIT_LIST=100/minute` |
