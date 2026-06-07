# AGENTS.md — `oc-tr-backend`

> Documento de orientación para agentes IA y contribuidores humanos.
> Repo independiente. Su gemelo de UI vive en [`oc-tr-frontend`](https://github.com/contracamilo/oc-tr-frontend).
> La documentación de producto/arquitectura compartida está en `docs/` dentro del directorio padre `oc-tr/` (no en este repo).

---

## 1. Project overview

**Hogar** es una app web ligera para gestionar la convivencia doméstica (tareas, compras, presupuesto, asignación de responsabilidades) entre 2-5 personas que se conocen y comparten red. Este repo es la **API REST** en FastAPI + SQLAlchemy + SQLite, sin autenticación, pensada para correr en una Raspberry Pi o un portátil en LAN.

> Iteración actual: **1 — Estructura y plan**. Ver [`SPEC.md`](./SPEC.md) para el plan SDD completo y la spec-driven development por iteraciones.

## 2. Stack

| Capa | Tecnología | Versión pineada | Por qué |
|---|---|---|---|
| Lenguaje | Python | 3.11+ | Pedido por el usuario |
| Framework | FastAPI | `0.115.0` | Async-ready, validación Pydantic integrada, docs auto en `/docs` |
| ORM | SQLAlchemy | `2.0.35` (sync) | Maduro, simple, suficiente para SQLite |
| Validación | Pydantic | `2.9.2` (v2) | Ya viene con FastAPI |
| Servidor | Uvicorn | `0.30.6` | Estándar para FastAPI |
| Config | `python-dotenv` | `1.0.1` | `.env` para entorno dev |
| DB | SQLite | — | File-based, cero-config, perfecto para uso doméstico. WAL mode activado implícitamente. |
| Tests | `pytest` + `httpx.AsyncClient` | (iter 7) | Smoke tests por router |

Para el detalle arquitectónico completo (capas, DI, patrones), ver `../oc-tr/docs/ARCHITECTURE.md` (en el repo raíz, no en este).

## 3. Estructura del repo

```
oc-tr-backend/
├── AGENTS.md                  ← este archivo
├── SPEC.md                    ← plan SDD (mapa de iteraciones, modelos, endpoints)
├── README.md                  ← (no existe todavía, se crea en iter 7)
├── requirements.txt           ← deps fijadas
├── .env.example               ← variables documentadas (APP_ENV, DATABASE_URL, CORS_ORIGINS)
├── .gitignore                 ← __pycache__, .venv, .env, data/*.db
└── app/
    ├── __init__.py
    ├── main.py                ← create_app(), CORS, init_db() en startup, GET /api/health
    ├── config.py              ← Settings (APP_ENV, DATABASE_URL, CORS_ORIGINS) cargadas de .env
    ├── database.py            ← engine, SessionLocal, Base, get_db (DI), init_db
    ├── models.py              ← Base + TimestampMixin (esqueleto en iter 1; 5 modelos en iter 2+)
    ├── schemas.py             ← Pydantic in/out (esqueleto en iter 1)
    ├── routers/
    │   ├── __init__.py
    │   ├── users.py           ← CRUD (iter 2)
    │   ├── tasks.py           ← CRUD + filtros (iter 2)
    │   ├── checklist.py       ← CRUD + query por semana (iter 4)
    │   ├── shopping.py        ← CRUD + filtros (iter 5)
    │   ├── budget.py          ← CRUD + summary (iter 6)
    │   └── roulette.py        ← POST /api/roulette (iter 3)
    └── services/
        ├── __init__.py
        └── roulette.py        ← assign_tasks() pura, sin DB (iter 3)
```

**Archivo de DB**: `data/hogar.db`, relativo a la raíz del repo padre `oc-tr/`. Está gitignored.

## 4. Setup y dev commands

### Setup (una vez)

```bash
cd oc-tr-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

> El `.env` por defecto apunta a `sqlite:///../data/hogar.db` (la DB vive en el directorio padre `oc-tr/data/`).

### Levantar el server

```bash
uvicorn app.main:app --reload --port 8000
```

- API: <http://localhost:8000/api/health>
- Swagger: <http://localhost:8000/docs>
- ReDoc: <http://localhost:8000/redoc>

### Tests (a partir de iter 7)

```bash
pytest -q
```

Stack objetivo: `pytest` + `httpx.AsyncClient` contra `TestClient` de FastAPI, con SQLite en memoria o archivo temporal por test. La lógica pura en `services/roulette.py` es lo primero testeable (sin DB).

## 5. Convenciones

### Código

- **Python**: PEP 8, **snakecase**, type hints en funciones públicas, docstrings en módulos y funciones públicas. Sin comentarios innecesarios (solo donde el código no se explique solo).
- **Routers**: `def`, **no `async def`**. Sync, porque SQLAlchemy sync + SQLite + baja concurrencia = código 30% más simple, mismo throughput percibido en LAN.
- **Schemas Pydantic**: separados `XxxCreate` / `XxxUpdate` (campos `Optional`) / `XxxOut`. En PATCH, usar `model_dump(exclude_unset=True)` para no blankar campos no enviados.
- **Códigos HTTP**: 200 / 201 (crear) / 204 (DELETE) / 400 (validación, FK inválida) / 404 (no existe) / 409 (conflicto de unicidad). Mensajes en `{"detail": "..."}` (default FastAPI; en iter 7 se amplía a `{"detail", "code"}`).
- **API**: prefijo `/api` en todos los routers; nombres en kebab-case en URLs son aceptables pero los routers usan nombres simples (`/users`, `/tasks`).
- **Timestamps**: `created_at` lo pone la DB con `default=datetime.utcnow`. `completed_at` / `purchased_at` se setean explícitamente en el router cuando el estado cambia a "hecho".
- **Validación FK**: explícita en el router, devuelve 400 si el `assigned_to` / `completed_by` no existe.
- **Soft deletes**: NO. Se hace `DELETE` real. Si se necesita auditoría, añadir `archived_at` (decisión pendiente, no en MVP).
- **Errores en español** en los mensajes de `detail`.

### Commits

[Conventional Commits](https://www.conventionalcommits.org/) en español o inglés (el repo mezcla ambos, sigue el idioma del último commit).

- `feat:` nueva funcionalidad
- `fix:` corrección de bug
- `docs:` solo documentación
- `refactor:` cambio interno sin nueva feature
- `test:` añadir/ajustar tests
- `chore:` tooling, dependencias, config
- `style:` formato, sin cambio de lógica

Scopes usados: `api`, `db`, `models`, `schemas`, `tests`, `deps`. Ej: `feat(api): implement Task model and CRUD`.

### UI y copy

- **No emojis en código fuente** (salvo iconos UI acordados en `frontend/`).
- Mensajes de error de la API en español.

## 6. Mapa de iteraciones

Resumen del [`SPEC.md` §6](./SPEC.md). Los issues viven en GitHub con label `iter-N`.

| Iter | Estado | Issues | Entregable |
|---|---|---|---|
| **1** | ✅ hecho | — | Scaffold, `requirements.txt`, `init_db`, `GET /api/health` |
| **2** | 🟡 parcial | [#1](https://github.com/contracamilo/oc-tr-backend/issues/1) (Users), [#2](https://github.com/contracamilo/oc-tr-backend/issues/2) (Tasks) | CRUD de Users + Tasks |
| **3** | ⬜ | [#3](https://github.com/contracamilo/oc-tr-backend/issues/3) | Ruleta: `services/roulette.assign_tasks()` + `POST /api/roulette` |
| **4** | ⬜ | [#4](https://github.com/contracamilo/oc-tr-backend/issues/4) | Checklist semanal (CRUD + `?week_start=`) |
| **5** | ⬜ | [#5](https://github.com/contracamilo/oc-tr-backend/issues/5) | Lista de mercado (CRUD + filtros) |
| **6** | ⬜ | [#6](https://github.com/contracamilo/oc-tr-backend/issues/6) (Budget CRUD), [#7](https://github.com/contracamilo/oc-tr-backend/issues/7) (Summary) | Presupuesto mensual + endpoint `/budget/summary` |
| **7** | ⬜ | [#8](https://github.com/contracamilo/oc-tr-backend/issues/8) (static), [#9](https://github.com/contracamilo/oc-tr-backend/issues/9) (tests), [#11](https://github.com/contracamilo/oc-tr-backend/issues/11) (README) | Montar frontend como static + pytest + quickstart |

> ✅ **Resuelto**: el cuerpo de los issues se realineó con `gh issue edit --body-file`. `#1` describe User, `#2` describe Task, `#10` quedó cerrado como duplicado histórico de `#1`, y `#11` cubre el README. La spec apunta a `#1/#2` correctamente.

## 7. Decisiones arquitectónicas

- **Sync, no async** en routers: SQLAlchemy sync + SQLite + 2-5 usuarios en LAN no justifican la complejidad de async. Reversible capa a capa.
- **SQLite** con `check_same_thread=False`: file-based, cero-config. WAL mode se puede activar con `PRAGMA` si hace falta. Migrar a Postgres = cambiar `DATABASE_URL` y revisar tipos.
- **Sin auth**: los convivientes se fían entre sí y comparten LAN. Si se expone fuera, añadir middleware. Bind a `127.0.0.1` por defecto.
- **`Base.metadata.create_all` en startup** (iter 1-6). Migrar a Alembic en iter 7 cuando haya DBs en uso y se cambie un modelo.
- **`Pydantic v2`** con schemas in/out separados: evita el bug clásico de PUT con campos nulos.
- **Lógica pura en `services/`** (no toca DB), persistencia en routers. La ruleta es el primer ejemplo: `assign_tasks()` testable sin DB.
- **`datetime.utcnow` en columnas** (no `func.now()`) para que el timestamp sea portable entre SQLite y Postgres sin sorpresas.
- **Frontend servido desde FastAPI** (decisión de iter 7, `app.mount("/", StaticFiles(...))`). Hasta entonces, dev con servidor estático aparte.

## 8. Reglas de oro

### ✅ Do

- Lee `SPEC.md` antes de tocar código de una iteración. El modelo de datos, endpoints y acceptance criteria están ahí.
- Sigue el patrón **router → schema → service → model**. No metas SQL en los routers (salvo el caso del router de la ruleta en iter 3, que delega en `services/`).
- En PATCH, usa `model_dump(exclude_unset=True)` para updates parciales.
- En `completed_at` / `purchased_at`: setea explícitamente cuando el estado cambia a "hecho", limpia explícitamente cuando vuelve a "no hecho".
- Si introduces un cambio que rompe un contrato con el frontend (path, payload, status code), actualiza también la spec del frontend o coordina con su issue.
- Si un error 500 viene de una FK inválida, captura `IntegrityError` y devuelve 400 con mensaje claro.

### ❌ Don't

- **No** añadas `async def` en routers sin discutirlo antes. Sync es la decisión de arquitectura.
- **No** uses soft deletes (`is_deleted`, `archived_at`) salvo que se apruebe explícitamente — no está en MVP.
- **No** crees un framework de "utils" / "helpers" genérico. Si una función se usa en 2+ sitios, muévela a `services/` con un nombre que describa el dominio.
- **No** añadas dependencias a `requirements.txt` sin justificación en el commit (`sqlalchemy-utils`, `alembic` se aprueban en su iter).
- **No** metas `print()` para debug. Usa `logging` o elimina el código.
- **No** crees migraciones manuales (Alembic) hasta iter 7. `create_all` es suficiente mientras no haya DBs en uso en producción.
- **No** subas `.env`, `data/*.db`, `__pycache__/` ni `.venv/` — el `.gitignore` ya los cubre.
- **No** uses caracteres no-ASCII en mensajes de commit o nombres de archivo (acentos, ñ) — causar problemas en cross-platform.
- **No** inventes endpoints que no estén en `SPEC.md` §7 sin actualizar la spec primero.

### Pendiente de decidir

- Formato de errores en iter 7: ¿`{"detail"}` simple o `{"detail", "code"}` estructurado? (SPEC §3 lo deja abierto.)
- ¿Activar `PRAGMA journal_mode=WAL` en `init_db()`? Recomendado para concurrencia, pero no se ha hecho.
- ¿Migrar `datetime.utcnow` a `datetime.now(timezone.utc)` cuando se toque el modelo? `utcnow` está deprecado en Python 3.12+.
- Política de FK: capturar `IntegrityError` y devolver 400 está dicho en SPEC §2/iter 2 acceptance criteria, pero la implementación exacta se decide en su issue.
