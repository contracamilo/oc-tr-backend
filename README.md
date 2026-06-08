# Hogar — Backend API

FastAPI + PostgreSQL (async) · BFF para la app de gestión doméstica.

## Requisitos

- [Docker](https://docs.docker.com/get-docker/) y Docker Compose

Para desarrollo local sin Docker: Python 3.11+ y PostgreSQL 16+.

---

## Levantar con Docker (recomendado)

```bash
# 1. Copiar variables de entorno
cp .env.example .env

# 2. Construir y levantar
docker compose up --build
```

La API queda disponible en:

| URL | Descripción |
|-----|-------------|
| `http://localhost:8000/api/health` | Estado del servidor y DB |
| `http://localhost:8000/docs` | Swagger UI |
| `http://localhost:8000/redoc` | ReDoc |

Para correr en segundo plano:

```bash
docker compose up -d --build
docker compose logs -f api   # ver logs
```

Para detener y eliminar volúmenes:

```bash
docker compose down          # detiene, conserva datos
docker compose down -v       # detiene y borra el volumen de PostgreSQL
```

---

## Desarrollo local (sin Docker)

### 1. PostgreSQL

Tener una instancia de PostgreSQL 16 corriendo. Con Docker solo la DB:

```bash
docker compose up db
```

### 2. Entorno Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 3. Variables de entorno

```bash
cp .env.example .env
# Editar .env si la URL de DB es distinta
```

### 4. Arrancar

```bash
uvicorn app.main:app --reload --port 8000
```

---

## Variables de entorno

| Variable | Default | Descripción |
|----------|---------|-------------|
| `APP_ENV` | `development` | Entorno (`development` / `production`) |
| `DATABASE_URL` | `postgresql+asyncpg://hogar:hogar@localhost:5432/hogar` | Conexión a PostgreSQL |
| `CORS_ORIGINS` | `http://localhost:5500` | Orígenes permitidos (separados por coma) |
| `RATE_LIMIT_READ` | `30/minute` | Límite para endpoints GET |
| `RATE_LIMIT_WRITE` | `10/minute` | Límite para POST/PATCH/DELETE |
| `LOG_LEVEL` | `INFO` | Nivel de logging |
| `SECRET_KEY` | `change-me-in-production` | Clave para firmar JWT (cambiar en prod) |
| `ALGORITHM` | `HS256` | Algoritmo JWT |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Expiración del access token |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `30` | Expiración del refresh token |

---

## Estructura

```
app/
├── main.py            # App factory, CORS, rate limiter, health checks
├── config.py          # Settings desde .env
├── database.py        # Engine async, sesión, init_db
├── models.py          # Modelos SQLAlchemy (ORM)
├── schemas.py         # Schemas Pydantic + PaginatedResponse[T]
├── errors.py          # Handlers globales de errores
├── logging_conf.py    # structlog (JSON en prod, consola en dev)
├── security.py        # JWT + hashing (iter 2)
├── routers/           # Endpoints HTTP por dominio
├── services/          # Lógica de negocio pura
└── repositories/      # Acceso a DB (BaseRepository + concretos)
```

## Endpoints disponibles

| Método | Ruta | Descripción |
|--------|------|-------------|
| `GET` | `/api/health` | Estado + ping a DB |
| `GET` | `/api/health/live` | Liveness probe |
| `GET` | `/api/health/ready` | Readiness probe |

El resto de endpoints se implementan en iteraciones 2–8.
