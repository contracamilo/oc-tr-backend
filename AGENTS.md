# AGENTS.md — `oc-tr-backend`

> Documento de orientación para agentes IA y contribuidores humanos.
> Repo independiente. Su gemelo de UI vive en [`oc-tr-frontend`](https://github.com/contracamilo/oc-tr-frontend).
> La documentación de producto/arquitectura compartida está en `docs/` dentro del directorio padre `oc-tr/` (no en este repo).
> La especificación técnica detallada está en `.sdd/`.

---

## 1. Project overview

**Hogar** es una app web ligera para gestionar la convivencia doméstica (tareas, compras, presupuesto, asignación de responsabilidades) entre 2-5 personas. Este repo es la **API BFF** en FastAPI + PostgreSQL que sirve la API REST para el frontend SPA (Vue 3 + Vite + Pinia + TanStack Query) y en producción sirve sus estáticos compilados.

> Iteración actual: **1 — Estructura y plan**. Ver [`SPEC.md`](./SPEC.md) para el plan SDD completo.

## 2. Stack

| Capa | Tecnología | Versión | Por qué |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | Pedido por el usuario |
| Framework | FastAPI | `0.115.0` | Async-ready, validación Pydantic, docs auto en `/docs` |
| ORM | SQLAlchemy | `2.0.35` (asyncio) | Async con PostgreSQL para conexiones eficientes |
| DB Driver | asyncpg | latest | Driver PostgreSQL asíncrono más rápido |
| Validación | Pydantic | `2.9.2` (v2) | Viene con FastAPI |
| Servidor | Uvicorn | `0.30.6` | Estándar para FastAPI |
| Config | `python-dotenv` | `1.0.1` | `.env` para entorno dev |
| DB | PostgreSQL | 16+ | ACID, joins, agregaciones, escalabilidad |
| Rate limiting | slowapi | latest | Middleware de rate limiting para FastAPI |
| Logging | structlog | latest | Logging estructurado listo para producción |
| Tests | `pytest` + `httpx.AsyncClient` | latest | Tests asíncronos contra la BFF |
| DB en tests | testcontainers-postgres | latest | PostgreSQL real en tests (no mock) |

**Evaluación NoSQL**: MongoDB, DynamoDB y Firestore fueron evaluados. Se descartan porque el dominio es relacional: las consultas requieren joins (task→user, shopping→user), agregaciones (budget summary con GROUP BY), y transacciones atómicas multi-fila (roulette, batch-purchase). PostgreSQL maneja esto de forma nativa, con mejor performance y sin la complejidad operativa de NoSQL para este volumen de datos (<1000 registros/hogar). Si el día de mañana se necesitara un campo flexible por entidad, PostgreSQL tiene `JSONB`.

## 3. Arquitectura

**Estilo**: BFF (Backend For Frontend) hexagonal de 3 capas.

```
┌──────────────┐     ┌──────────────────────────────────────────┐     ┌──────────────┐
│  Mobile SPA  │────▶│              BFF (FastAPI)               │────▶│  PostgreSQL  │
│  (frontend)  │     │                                          │     │              │
└──────────────┘     │  ┌──────────┐  ┌──────────┐  ┌────────┐ │     └──────────────┘
                     │  │  Router  │──▶│ Service  │──▶│  Repo  │ │
                     │  │  (HTTP)  │  │ (biz)    │  │ (DB)   │ │
                     │  └──────────┘  └──────────┘  └────────┘ │
                     │                                          │
                     │  Cross-cutting:                          │
                     │  • Rate limiting (slowapi)               │
                     │  • Global exception handlers             │
                     │  • Structured logging (structlog)        │
                     │  • Health check (/api/health + DB ping)  │
                     │  • CORS configurable                     │
                     └──────────────────────────────────────────┘
```

**Responsabilidades de la BFF**:
- Orquestar respuestas específicas para el frontend SPA mobile-first
- Response shaping (devolver solo los campos que necesita la SPA)
- Rate limiting por endpoint
- Manejo de errores uniforme (códigos + mensajes en español)
- Health checks con verificación de DB

**Flujo típico**:
```
Request → Rate Limiter → Router → Service → Repository → DB
                                      ↓
                                Pure logic (roulette, etc.)
```

## 4. Patrones

| Patrón | Problema que resuelve | Dónde se aplica |
|--------|----------------------|-----------------|
| **BFF** | El frontend mobile-first necesita respuestas ligeras y orquestadas, no una API genérica | `app/routers/*` — cada endpoint da forma a la respuesta para la SPA |
| **Repository** | Aísla la lógica de persistencia; los servicios no conocen SQLAlchemy | `app/repositories/*` — toda consulta DB vive aquí, no en routers |
| **Service Layer** | Separa lógica de negocio de HTTP y DB | `app/services/*` — `assign_tasks()`, lógica de negocio pura |
| **Generic Paginated DTO** | Un schema paginado reusable, no N copias | `app/schemas.py` — `PaginatedResponse[T]` con Pydantic generics |
| **Transaction per batch** | Operaciones atómicas multi-fila | Roulette y batch-purchase envueltos en una transacción |
| **Global Exception Handler** | Errores uniformes en toda la API | `app/errors.py` — captura `IntegrityError`, `NotFound`, `ValidationError` |
| **Middleware de rate limiting** | Protege la BFF de abusos | `app/main.py` — slowapi montado globalmente |

## 5. Estructura del repo

```
oc-tr-backend/
├── AGENTS.md
├── SPEC.md
├── README.md                  ← (iter 7)
├── requirements.txt
├── .env.example
├── .gitignore
├── .sdd/
│   ├── architecture.md        ← Arquitectura completa (capas, patrones, ADRs, testing)
│   ├── api-pagination.md      ← Paginación y batch (issue #12)
│   ├── api.md                 ← Contratos de todos los endpoints
│   ├── data-model.md          ← Modelo de datos, relaciones, evaluación NoSQL
│   └── setup.md               ← Setup local con PostgreSQL y Docker
└── app/
    ├── __init__.py
    ├── main.py                ← create_app(), CORS, rate limiter, startup, health, exception handlers
    ├── config.py              ← Settings desde .env (DB, CORS, rate limit, logging)
    ├── database.py            ← async engine, async session, get_db, init_db
    ├── models.py              ← SQLAlchemy models (User, Task, ChecklistItem, ShoppingItem, BudgetItem)
    ├── schemas.py             ← Pydantic schemas: Create/Update/Out + PaginatedResponse[T]
    ├── errors.py              ← Global exception handlers (IntegrityError, NotFound, ValidationError)
    ├── logging_conf.py        ← structlog configuration
    ├── routers/
    │   ├── __init__.py
    │   ├── users.py           ← CRUD Users
    │   ├── tasks.py           ← CRUD Tasks + paginación
    │   ├── checklist.py       ← CRUD Checklist + paginación
    │   ├── shopping.py        ← CRUD Shopping + paginación + batch-purchase
    │   ├── budget.py          ← CRUD Budget + paginación + summary
    │   ├── dashboard.py       ← GET /api/dashboard (KPIs agregados)
    │   └── roulette.py        ← POST /api/roulette (batch assignment)
    ├── services/
    │   ├── __init__.py
    │   ├── roulette.py        ← assign_tasks() pure function
    │   └── pagination.py      ← paginate(query, limit, offset) helper for repositories
    └── repositories/
        ├── __init__.py
        ├── base.py            ← BaseRepository with common CRUD (get, list, create, update, delete)
        ├── user_repo.py       ← UserRepository extends BaseRepository
        ├── task_repo.py       ← TaskRepository (adds filtering by status, assigned_to)
        ├── checklist_repo.py  ← ChecklistItemRepository (adds filtering by week_start)
        ├── shopping_repo.py   ← ShoppingItemRepository (adds filtering by purchased, category)
        └── budget_repo.py     ← BudgetItemRepository (adds summary aggregation query)
```

## 6. Convenciones

### Código
- **Python**: PEP 8, snake_case, type hints en funciones públicas, docstrings en módulos y funciones públicas. Sin comentarios innecesarios.
- **Routers**: `async def`. FastAPI async + async SQLAlchemy + asyncpg = mejor throughput con PostgreSQL.
- **Schemas Pydantic**: separados `XxxCreate` / `XxxUpdate` (campos `Optional`) / `XxxOut`. PATCH usa `model_dump(exclude_unset=True)`.
- **Códigos HTTP**: 200 / 201 (crear) / 204 (DELETE) / 400 (validación) / 404 (no existe) / 409 (conflicto) / 429 (rate limit).
- **API**: prefijo `/api`, respuestas JSON.
- **Timestamps**: `created_at` con `default=func.now()` (PostgreSQL nativo). `completed_at` / `purchased_at` se setean explícitamente.
- **No soft deletes**: DELETE real.
- **Errores en español** en los mensajes de `detail`.

### Capas

```
Router (HTTP) → Service (business logic, pure) → Repository (DB access)
```

- Los **routers** solo: validan input, llaman al service/repo, devuelven respuesta.
- Los **services** solo: lógica de negocio pura, no conocen HTTP ni DB.
- Los **repositories** solo: queries a DB, no tienen lógica de negocio.
- Excepción: CRUD simple puede ir router → repo directo (sin service).

### Paginación (transversal)
- Todos los GET list aceptan `limit` y `offset`.
- Respuesta: `{"items": [...], "total": int, "limit": int, "offset": int}`.
- Usar `services/pagination.paginate(query, limit, offset)` en cada repository.
- `limit` máximo: Tasks=100, Checklist=200, Shopping=200, Budget=100.

### Batch operations
- `POST /api/shopping/batch-purchase`: atómico en una transacción.
- `POST /api/roulette`: atómico en una transacción.
- Validar todos los IDs antes de aplicar cambios.

### Manejo de errores (global)
- `app/errors.py` registra handlers globales con `@app.exception_handler`:
  - `IntegrityError` → 409 (conflicto de unicidad o FK)
  - `NoResultFound` → 404
  - `ValidationError` (Pydantic) → 422
  - `Exception` genérica → 500 con `{"detail": "Error interno del servidor", "code": "INTERNAL_ERROR"}`
  - `RateLimitExceeded` → 429

### Logging
- `structlog` configurado en `app/logging_conf.py`.
- Formato: JSON en producción, consola coloreada en dev.
- Cada request loggea: method, path, status_code, duration_ms, error_code (si hay).
- No loggear `detail` de errores 500 en producción (solo `error_code`).

### Health checks
- `GET /api/health` → `{"status": "ok", "db": "connected", "env": "development", "uptime": 3600}`
- Verifica conectividad con PostgreSQL (SELECT 1).
- `GET /api/health/ready` → readiness (DB conectada, migrations aplicadas).
- `GET /api/health/live` → liveness (servidor responde).

### Rate limiting
- `slowapi` middleware con límites por defecto:
  - Endpoints de lista (GET): 30 requests/minuto
  - Endpoints de escritura (POST/PATCH/DELETE): 10 requests/minuto
  - `/api/health`: sin límite
- Configurable vía `RATE_LIMIT_*` en `.env`.

### Pruebas
- `pytest` + `httpx.AsyncClient` contra `TestClient` de FastAPI.
- DB: PostgreSQL via `testcontainers-postgres` (o SQLite en memoria para tests unitarios de repos).
- Tests de integración: levantan PostgreSQL en contenedor Docker, corren migraciones, ejecutan tests.
- Tests unitarios: lógica pura en `services/` (no requieren DB).
- Smoke tests: un test por router que verifica 200/404 en endpoints clave.
- `pytest -q` debe pasar antes de cada commit.

### Commits
[Conventional Commits](https://www.conventionalcommits.org/) en español o inglés.

- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` solo documentación
- `refactor:` cambio interno sin nueva feature
- `test:` añadir/ajustar tests
- `chore:` tooling, dependencias, config
- `style:` formato, sin cambio de lógica

Scopes: `api`, `bff`, `db`, `models`, `schemas`, `repos`, `tests`, `deps`.

## 7. Decisiones arquitectónicas

| Decisión | Opción elegida | Alternativa | Por qué |
|----------|---------------|-------------|---------|
| **DB** | PostgreSQL 16+ | SQLite, MongoDB | Escala, ACID, joins nativos, agregaciones, JSONB para flexibilidad futura |
| **Async** | async routers + async SQLAlchemy | sync | PostgreSQL con pool de conexiones se beneficia de async; sync servía para SQLite |
| **BFF vs API pura** | BFF | API REST genérica | La BFF da forma a respuestas para la SPA mobile-first, reduciendo payload y viajes red |
| **Repository** | Capa explícita de repos | Queries en routers | Testabilidad, separación de concerns, facilita cambiar ORM o DB después |
| **Rate limiting** | slowapi | Middleware custom | Librería madura, configurable por ruta, headers estándar (X-RateLimit-Remaining) |
| **Logging** | structlog | logging estándar | Logging estructurado nativo, fácil de enviar a sistemas externos (Datadog, ELK) |
| **Exception handling** | Global handlers | Try/except en cada router | Código más limpio, errores consistentes, un solo punto de cambio |
| **Health checks** | /health, /ready, /live | Solo /health | Patrón estándar para orquestadores (K8s, Docker Compose healthcheck) |
| **Tests** | testcontainers-postgres | SQLite en memoria | Tests contra la misma DB que producción evita falsos positivos |
| **Migrations** | create_all en startup | Alembic | El equipo decidió no usar Alembic; create_all es suficiente para el volumen actual |
| **NoSQL** | No se usa | MongoDB, DynamoDB | El dominio es relacional; NoSQL añade complejidad sin beneficio tangible |

## 8. Dependencias nuevas (requirements.txt)

```
# Actuales
fastapi==0.115.0
uvicorn[standard]==0.30.6
sqlalchemy==2.0.35
pydantic==2.9.2
python-dotenv==1.0.1

# Nuevas — PostgreSQL
asyncpg
psycopg2-binary          # sync fallback para scripts

# Nuevas — infra
slowapi                  # rate limiting
structlog                # logging estructurado
testcontainers-postgres  # tests con PostgreSQL real
pytest-asyncio           # tests asíncronos
```

## 9. Mapa de iteraciones

Resumen del [`SPEC.md` §6](./SPEC.md). Los issues viven en GitHub con label `iter-N`.

| Iter | Estado | Issues | Entregable |
|---|---|---|---|
| **1** | ✅ hecho | — | Scaffold, `requirements.txt`, `init_db`, `GET /api/health` |
| **2** | 🟡 parcial | [#1](https://github.com/contracamilo/oc-tr-backend/issues/1) (Users), [#2](https://github.com/contracamilo/oc-tr-backend/issues/2) (Tasks) | CRUD de Users + Tasks |
| **3** | ⬜ | [#3](https://github.com/contracamilo/oc-tr-backend/issues/3) | Ruleta: `services/roulette.assign_tasks()` + `POST /api/roulette` |
| **4** | ⬜ | [#4](https://github.com/contracamilo/oc-tr-backend/issues/4) | Checklist semanal (CRUD + `?week_start=`) |
| **5** | ⬜ | [#5](https://github.com/contracamilo/oc-tr-backend/issues/5) | Lista de mercado (CRUD + filtros) |
| **6** | ⬜ | [#6](https://github.com/contracamilo/oc-tr-backend/issues/6) (Budget CRUD), [#7](https://github.com/contracamilo/oc-tr-backend/issues/7) (Summary) | Presupuesto mensual + endpoint `/budget/summary` |
| **7** | ⬜ | [#8](https://github.com/contracamilo/oc-tr-backend/issues/8) (static), [#9](https://github.com/contracamilo/oc-tr-backend/issues/9) (tests), [#11](https://github.com/contracamilo/oc-tr-backend/issues/11) (README) | Static files + pytest + dashboard API + quickstart |
| **#12** | ⬜ | [#12](https://github.com/contracamilo/oc-tr-backend/issues/12) | Paginación transversal + batch operations |
| **Infra** | ⬜ | — | Migrar a PostgreSQL, async, BFF, repos, rate limiting, logging, errors |

## 10. Plan de implementación — Infraestructura profesional

Antes de tocar features, hay que migrar la base del proyecto a la arquitectura profesional.

### Fase 0: Fundación profesional

**Objetivo**: Migrar de SQLite sync a PostgreSQL async con toda la infraestructura BFF.

**Dependencias**: Ninguna (es requisito para todo lo demás)

**Componentes a crear/modificar**:
- `app/config.py` — añadir `DATABASE_URL` postgres, `RATE_LIMIT_*`, `LOG_LEVEL`
- `app/database.py` — engine asyncio con asyncpg, `AsyncSession`, `get_db` async generator
- `app/logging_conf.py` — structlog config (nuevo)
- `app/errors.py` — global exception handlers (nuevo)
- `app/main.py` — montar rate limiter, exception handlers, health checks, structlog middleware
- `app/repositories/base.py` — `BaseRepository` con CRUD genérico (nuevo)

**Pasos**:
1. Cambiar `DATABASE_URL` a PostgreSQL y configurar async engine
2. Migrar modelos de sync a async SQLAlchemy
3. Configurar structlog con middleware de request logging
4. Implementar global exception handlers en `errors.py`
5. Montar slowapi con límites por defecto
6. Implementar health checks (`/health`, `/ready`, `/live`)
7. Crear `BaseRepository` con métodos genéricos `get`, `list`, `create`, `update`, `delete`
8. Mover queries existentes de routers a repositorios concretos
9. Configurar `testcontainers-postgres` para tests de integración
10. Actualizar `.env.example` con nuevas variables

**Definition of done**: `pytest -q` pasa, `/api/health` responde con DB conectada, rate limiting activo, errores devuelven formato uniforme.

### Fase A-G (Issue #12)

Ver `.sdd/api-pagination.md` para el detalle. Estas fases se implementan sobre la Fase 0.

| Fase | Issues | Depende de | Entregable |
|---|---|---|---|
| A | #12 (infra) | Fase 0 | `PaginatedResponse[T]`, `paginate()`, schemas |
| B | #12 (tasks) | A | Task list con paginación |
| C | #3, #12 (roulette) | A | Roulette endpoint + lógica `assign_tasks()` |
| D | #4, #12 (checklist) | A | Checklist list con paginación |
| E | #5, #12 (shopping) | A | Shopping list + `POST /batch-purchase` |
| F | #6, #12 (budget) | A | Budget list con paginación |
| G | #8, #9, #11 | A-F | Static files, pytest smoke, dashboard endpoint, README |

## 11. Para agents

- Leer `SPEC.md` y `.sdd/*.md` antes de implementar cualquier cambio.
- La **Fase 0** (migración a PostgreSQL async + BFF) debe completarse antes de tocar features.
- Todos los GET list DEBEN usar `paginate()` — no hacer `.all()` directo.
- Todas las batch operations DEBEN ser atómicas (una transacción).
- No importar SQLAlchemy en routers — usar repositories.
- Los routers son `async def` — no olvidar `await` en llamadas a repo.
- Ver con `pytest -q` que no se rompe nada existente.
- Los mensajes de error van en español.
