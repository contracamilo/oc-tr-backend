# Architecture — Hogar BFF

> Documento completo de arquitectura: estilo, capas, patrones, flujos, y decisiones técnicas.

---

## 1. Architectural Style: BFF Hexagonal de 3 Capas

```
┌─────────────────────────────────────────────────────────────────────┐
│                        BFF (FastAPI)                                │
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐  │
│  │   Routers     │    │   Services   │    │    Repositories      │  │
│  │  (HTTP)       │───▶│  (Business)  │───▶│     (Persistence)    │  │
│  │               │    │              │    │                      │  │
│  │  • Validation │    │  • Pure func │    │  • SQLAlchemy async  │  │
│  │  • Response   │    │  • No HTTP   │    │  • Queries           │  │
│  │  • Shape      │    │  • No DB     │    │  • Transactions      │  │
│  └──────────────┘    └──────────────┘    └───────────┬──────────┘  │
│                                                       │             │
│  ┌───────────────────────────────────────────────────┐│             │
│  │  Cross-Cutting Layer                              ││             │
│  │  • Rate Limiting (slowapi)                        ││             │
│  │  • Global Exception Handlers                      ││             │
│  │  • Structured Logging (structlog)                 ││             │
│  │  • Health Checks (/api/health, .../ready, .../live) ││           │
│  │  • CORS                                           ││             │
│  └───────────────────────────────────────────────────┘│             │
└───────────────────────────────────────────────────────┼─────────────┘
                                                        │
                                                        ▼
                                              ┌──────────────────┐
                                              │   PostgreSQL 16+  │
                                              │                  │
                                              │  • ACID           │
                                              │  • Joins nativos  │
                                              │  • JSONB          │
                                              │  • asyncpg driver │
                                              └──────────────────┘
```

### Por qué BFF y no API genérica

El frontend es una SPA mobile-first con necesidades específicas:

| Necesidad del frontend | Solución BFF |
|------------------------|-------------|
| Payloads ligeros (poca batería/datos móviles) | Response shaping: solo campos necesarios |
| Pocos viajes red | Endpoints batch (roulette, batch-purchase) |
| Paginación para infinite scroll | `limit`/`offset` consistentes en todos los list |
| Errores legibles para el usuario | Mensajes en español, códigos de error |
| Sin autenticación (LAN) | Rate limiting como protección básica |

Si en el futuro la SPA necesita un endpoint compuesto (ej: "dashboard" con tareas + checklist + compras), la BFF lo orquesta sin exponer esa complejidad al frontend.

---

## 2. Layer Responsibilities

### 2.1 Router Layer (`app/routers/`)

**Responsabilidad**: Recibir HTTP, validar input, llamar a service/repo, devolver respuesta.

```python
@router.get("", response_model=PaginatedResponse[TaskOut])
async def list_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    repo: TaskRepository = Depends(get_task_repo),
) -> PaginatedResponse[TaskOut]:
    items, total = await repo.list(
        status=status, assigned_to=assigned_to,
        limit=limit, offset=offset,
    )
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
```

**Reglas**:
- No importar SQLAlchemy ni models directamente
- No contener lógica de negocio
- Obtener dependencias via FastAPI `Depends()`
- `async def` siempre

### 2.2 Service Layer (`app/services/`)

**Responsabilidad**: Lógica de negocio pura, sin dependencias de HTTP ni DB.

```python
# app/services/roulette.py
import random
from typing import Optional

def assign_tasks(
    task_ids: list[int],
    user_ids: list[int],
    seed: Optional[int] = None,
) -> tuple[list[tuple[int, int]], list[int]]:
    rng = random.Random(seed)
    users = user_ids.copy()
    rng.shuffle(users)
    assignments, unassigned = [], []
    for i, tid in enumerate(task_ids):
        if users:
            assignments.append((tid, users[i % len(users)]))
        else:
            unassigned.append(tid)
    return assignments, unassigned
```

**Reglas**:
- Funciones puras: mismas entradas → mismas salidas
- No importar FastAPI, SQLAlchemy, HTTP
- 100% testeable sin fixtures ni mocks
- Si una función necesita DB → está en el lugar equivocado

### 2.3 Repository Layer (`app/repositories/`)

**Responsabilidad**: Persistencia, consultas, transacciones. Única capa que conoce SQLAlchemy.

```python
class TaskRepository(BaseRepository[Task]):
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list(
        self,
        status: str | None = None,
        assigned_to: int | None = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[list[Task], int]:
        query = select(Task).order_by(Task.status, Task.due_date, Task.id)
        if status:
            query = query.where(Task.status == status)
        if assigned_to is not None:
            query = query.where(Task.assigned_to == assigned_to)
        return await paginate(self.db, query, limit, offset)
```

**Reglas**:
- Solo queries SQLAlchemy (o SQL raw si es necesario)
- No contener lógica de negocio
- Métodos retornan modelos ORM (los routers/schemas los serializan)
- `async` siempre

### 2.4 Cross-Cutting Layer

- **Rate Limiting**: slowapi middleware, configurable por ruta
- **Exception Handlers**: `app/errors.py` — handlers globales registrados en `create_app()`
- **Logging**: structlog middleware que loggea cada request
- **Health Checks**: `/api/health` (status general + DB), `/api/health/ready` (readiness), `/api/health/live` (liveness). Ver `api.md` §1.
- **CORS**: configuración vía `CORSMiddleware`

---

## 3. Request Lifecycle

```
1. Request llega a Uvicorn
2. structlog middleware: loggea method + path
3. slowapi: verifica rate limit → 429 si excede
4. CORS middleware: headers de origen
5. FastAPI routea al router correspondiente
6. Router valida path/query/body params (Pydantic)
7. Router llama a Repository (o Service → Repository)
8. Repository ejecuta query en PostgreSQL
9. (Opcional) Service procesa lógica de negocio
10. Router serializa respuesta (Pydantic Out schema)
11. structlog middleware: loggea status_code + duration_ms
12. Response enviada al cliente
```

---

## 4. Exception Handling Strategy

| Excepción | Código HTTP | Response Body |
|-----------|-------------|---------------|
| `IntegrityError` (FK violada en POST/PATCH) | 409 | `{"detail": "El usuario 5 no existe", "code": "FK_VIOLATION"}` |
| `IntegrityError` (unique violation) | 409 | `{"detail": "El nombre 'Juan' ya existe", "code": "UNIQUE_VIOLATION"}` |
| `NoResultFound` | 404 | `{"detail": "Tarea no encontrada", "code": "NOT_FOUND"}` |
| `RequestValidationError` (Pydantic) | 422 | `{"detail": "month debe tener formato YYYY-MM", "code": "VALIDATION_ERROR"}` |
| `RateLimitExceeded` | 429 | `{"detail": "Demasiadas solicitudes. Intenta en 30 segundos.", "code": "RATE_LIMITED"}` |
| `Exception` (no capturada) | 500 | `{"detail": "Error interno del servidor", "code": "INTERNAL_ERROR"}` |

```python
# app/errors.py
from fastapi import Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, NoResultFound

async def integrity_error_handler(request: Request, exc: IntegrityError) -> JSONResponse:
    return JSONResponse(
        status_code=409,
        content={
            "detail": "Error de integridad en la base de datos",
            "code": "INTEGRITY_ERROR",
        },
    )

def register_handlers(app: FastAPI) -> None:
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(NoResultFound, lambda r, e: JSONResponse(404, {"detail": "Recurso no encontrado", "code": "NOT_FOUND"}))
```

---

## 5. Logging Strategy

### Configuración (structlog)

```python
# app/logging_conf.py
import structlog

def setup_logging(env: str) -> None:
    processors = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
    ]
    if env == "production":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(processors=processors)
```

### Middleware de request logging

```python
# En main.py
import time
import structlog

@app.middleware("http")
async def log_requests(request: Request, call_next) -> Response:
    start = time.time()
    response = await call_next(request)
    duration_ms = int((time.time() - start) * 1000)
    log = structlog.get_logger()
    log.info("request", method=request.method, path=request.url.path,
             status=response.status_code, duration_ms=duration_ms)
    return response
```

---

## 6. Testing Strategy

### Pirámide de tests

```
        ╱╲
       ╱  ╲          Smoke tests (1 por router → 6 tests)
      ╱    ╲
     ╱──────╲        Integration tests (repositorios con PostgreSQL real)
    ╱        ╲
   ╱──────────╲      Unit tests (services/roulette, helpers)
  ╱            ╲
 ╱──────────────╲    Repository tests con testcontainers-postgres
```

### Stack de testing

- **Framework**: `pytest` + `pytest-asyncio`
- **HTTP client**: `httpx.AsyncClient` via `AsyncClient` de FastAPI
- **DB en tests**: `testcontainers-postgres` (PostgreSQL real en Docker)
- **DB en unit tests**: SQLite en memoria (para repos simples) o mocking

### Ejemplo: test de integración

```python
# tests/test_tasks.py
import pytest
from httpx import AsyncClient, ASGITransport

@pytest.mark.asyncio
async def test_list_tasks_paginated(postgres_container, app):
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        resp = await client.get("/api/tasks?limit=5&offset=0")
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data
        assert data["limit"] == 5
        assert data["offset"] == 0
```

---

## 7. Decisiones Arquitectónicas (ADRs)

### ADR-001: PostgreSQL sobre SQLite

- **Contexto**: El proyecto original usaba SQLite. Necesitamos escalar y tener capacidades relacionales completas.
- **Decisión**: Migrar a PostgreSQL 16+.
- **Consecuencias**: Requiere Docker para dev, conexiones async con asyncpg, pool de conexiones.
- **Alternativas**: SQLite (no escala), MySQL (menos features que PostgreSQL).

### ADR-002: Async sobre Sync

- **Contexto**: El código original era sync porque SQLite no se beneficia de async. Con PostgreSQL, un pool de conexiones async mejora el throughput.
- **Decisión**: Routers `async def`, SQLAlchemy async, asyncpg.
- **Consecuencias**: Mayor complejidad (async/await en toda la cadena), pero mejor concurrencia.
- **Alternativas**: Mantener sync con `psycopg2` (pool bloqueante, menor throughput).

### ADR-003: BFF sobre API Genérica

- **Contexto**: El frontend es mobile-first y necesita respuestas optimizadas.
- **Decisión**: La FastAPI actúa como BFF, dando forma a respuestas específicas para la SPA.
- **Consecuencias**: Los endpoints no son genéricos reutilizables — están acoplados al frontend actual.
- **Alternativas**: API REST genérica + GraphQL (más complejo para este alcance).

### ADR-004: Repository Pattern

- **Contexto**: El código actual tenía queries SQLAlchemy mezcladas en los routers.
- **Decisión**: Introducir `app/repositories/` con `BaseRepository` genérico.
- **Consecuencias**: Más código boilerplate, pero mejor testabilidad y separación.
- **Alternativas**: Queries en routers (código más corto pero menos mantenible).

### ADR-005: Rate Limiting con slowapi

- **Contexto**: Sin autenticación, la API necesita protección básica contra abusos.
- **Decisión**: slowapi con límites por endpoint tipo (GET vs POST/PATCH/DELETE).
- **Consecuencias**: Dependencia adicional, pero evita implementar rate limiting custom.
- **Alternativas**: Middleware custom (más control, más código).

### ADR-006: testcontainers-postgres en tests

- **Contexto**: Tests con SQLite en memoria daban falsos positivos por diferencias con PostgreSQL.
- **Decisión**: Usar `testcontainers-postgres` para tests de integración.
- **Consecuencias**: Tests más lentos (requieren Docker), pero más fiables.
- **Alternativas**: SQLite en memoria (rápido pero inexacto), mocking (frágil).

### ADR-007: ON DELETE SET NULL en FK hacia User

- **Contexto**: Cuando se elimina un conviviente, debe decidirse qué pasa con sus tareas asignadas, items que añadió/completó y movimientos de presupuesto. Bloquear el borrado (RESTRICT) crea fricción ("primero reasigna sus tareas"); borrar en cascada destruye históricos útiles.
- **Decisión**: Todas las FK hacia `users.id` (`tasks.assigned_to`, `checklist_items.completed_by`, `shopping_items.added_by`, `shopping_items.purchased_by`, `budget_items.user_id`) usan `ON DELETE SET NULL`.
- **Consecuencias**: `DELETE /api/users/{id}` siempre devuelve 204. Las tareas asignadas al usuario eliminado quedan "sin asignar" y deben mostrarse así en el frontend. Los históricos de checklist/shopping/budget mantienen su integridad referencial pero pierden el "por quién" (mostrar como "—").
- **Alternativas**: RESTRICT (más seguro pero más fricción), CASCADE (destruye históricos), aplicación manual (más código, menos atómico).

---

## 8. Seguridad

- **Rate limiting**: Protección contra abusos a nivel de BFF
- **Bind a localhost**: Por defecto, la BFF solo escucha en `127.0.0.1` (LAN)
- **CORS**: Lista blanca de orígenes permitidos vía variable de entorno
- **Sin auth**: Decisión deliberada para el caso de uso (convivientes en LAN)
- **HTTP**: Sin HTTPS en LAN (se puede añadir proxy reverso si se expone)
