# Data Model — Hogar

> Modelo de datos, relaciones y evaluación NoSQL vs PostgreSQL para Hogar.

---

## 1. Evaluación NoSQL vs PostgreSQL

### Candidatos evaluados

| Sistema | Tipo | Evaluación |
|---------|------|------------|
| **PostgreSQL 16+** | Relacional | ✅ Recomendado |
| MongoDB | Document-based | ❌ Descartado |
| DynamoDB | Key-value + Document | ❌ Descartado |
| Firestore | Document-based (real-time) | ❌ Descartado |

### Criterios de evaluación

| Criterio | Peso | PostgreSQL | MongoDB | DynamoDB | Firestore |
|----------|------|-----------|---------|----------|-----------|
| Joins / relaciones | Alto | ⭐⭐⭐ nativo | ⭐⭐ $lookup | ⭐ manual | ⭐ manual |
| Transacciones multi-fila | Alto | ⭐⭐⭐ ACID | ⭐⭐ (v4.0+) | ⭐⭐ (transact) | ⭐ limitado |
| Agregaciones (GROUP BY, SUM) | Alto | ⭐⭐⭐ nativo | ⭐⭐⭐ aggregation pipeline | ⭐⭐⭐ (si cabe en query) | ⭐⭐⭐ (si cabe) |
| FK constraints | Medio | ⭐⭐⭐ nativo | ❌ no tiene | ❌ no tiene | ❌ no tiene |
| Flexibilidad de esquema | Bajo | ⭐⭐⭐ JSONB | ⭐⭐⭐ nativo | ⭐⭐⭐ nativo | ⭐⭐⭐ nativo |
| Escalamiento horizontal | Bajo* | ⭐⭐ réplicas | ⭐⭐⭐ nativo | ⭐⭐⭐ nativo | ⭐⭐⭐ nativo |
| Operación local (dev) | Alto | ⭐⭐⭐ Docker | ⭐⭐⭐ Docker | ⭐ local binary | ⭐ emulator |
| Costo operativo | Medio | ⭐⭐⭐ autogestionado | ⭐⭐⭐ Atlas | ⭐⭐⭐ serverless | ⭐⭐⭐ serverless |

*\* El volumen esperado es <1000 registros por hogar con <10 hogares. El escalamiento horizontal no es relevante.*

### Conclusión

**PostgreSQL es la opción correcta** para este dominio porque:

1. **El modelo de datos es relacional por naturaleza**: Tasks tienen FK a Users, ShoppingItems tienen FK a Users, BudgetItems tienen FK a Users. En NoSQL tendrías que desnormalizar o hacer joins manuales en aplicación.
2. **Las transacciones atómicas multi-fila son críticas**: Roulette asigna N tareas a M usuarios en una sola transacción. Batch-purchase marca K items como comprados. PostgreSQL garantiza ACID; en MongoDB las transacciones multi-documento son posibles pero con restricciones y menor rendimiento.
3. **Las agregaciones son constantes**: Budget summary requiere `GROUP BY category, type` con `SUM(amount)`. En PostgreSQL es una línea de SQL; en MongoDB es un pipeline de agregación de 5+ etapas.
4. **El volumen no justifica NoSQL**: Con <1000 registros, las ventajas de NoSQL (esquema flexible, escalamiento horizontal) no se aprovechan. PostgreSQL con JSONB ofrece la misma flexibilidad cuando se necesita.
5. **Operación local simple**: PostgreSQL corre en Docker con una línea (`docker run postgres:16`), o incluso en Raspberry Pi para el caso de uso original.

---

## 2. Entidades y relaciones

### Diagrama (ASCII)

```
┌──────────┐       ┌──────────────────┐
│   User   │       │      Task        │
│──────────│       │──────────────────│
│ id (PK)  │──┐    │ id (PK)          │
│ name     │  │    │ title            │
│ color    │  └───<│ description?     │
│ avatar?  │   FK  │ frequency        │
│ created  │       │ status           │
└──────────┘       │ due_date?        │
                   │ assigned_to? ────│── FK → User.id
                   │ completed_at?    │
                   │ created_at       │
                   └──────────────────┘

┌──────────────────┐    ┌──────────────────────┐
│ ChecklistItem    │    │    ShoppingItem      │
│──────────────────│    │──────────────────────│
│ id (PK)          │    │ id (PK)              │
│ title            │    │ name                 │
│ week_start (date)│    │ quantity (default 1) │
│ completed (bool) │    │ unit?                │
│ completed_by? ───│── FK → User.id           │
│ completed_at?    │    │ category?            │
│ created_at       │    │ purchased (bool)     │
└──────────────────┘    │ added_by? ───────────│── FK → User.id
                        │ purchased_by? ───────│── FK → User.id
                        │ estimated_price?     │
                        │ purchased_at?        │
                        │ created_at           │
                        └──────────────────────┘

┌──────────────────┐
│   BudgetItem     │
│──────────────────│
│ id (PK)          │
│ month (YYYY-MM)  │
│ type (income/exp)│
│ category         │
│ description?     │
│ amount           │
│ user_id? ────────│── FK → User.id
│ created_at       │
└──────────────────┘
```

### Resumen de tablas

| Tabla | Columnas aprox. | FK (todas → User, ON DELETE SET NULL) | Crecimiento esperado |
|-------|-----------------|----|---------------------|
| User | 5 | 0 | 2-10 por hogar (estable) |
| Task | 9 | 1 (assigned_to) | ~50 activas + históricas |
| ChecklistItem | 7 | 1 (completed_by) | ~10 por semana |
| ShoppingItem | 11 | 2 (added_by, purchased_by) | ~30-50 activas |
| BudgetItem | 8 | 1 (user_id) | ~50-100 por mes |

### Convenciones de naming
- Tablas: `snake_case` plural (users, tasks, checklist_items, shopping_items, budget_items)
- Columnas: `snake_case`
- PK: `id` (Integer auto-increment)
- FK: `{tabla_singular}_id` (ej: `user_id`)
- Timestamps: `created_at`, `updated_at?` (no en MVP), `completed_at`, `purchased_at`

### Tipos de datos PostgreSQL

| Concepto | Tipo PostgreSQL |
|----------|----------------|
| IDs | `SERIAL PRIMARY KEY` |
| Texto corto | `VARCHAR(255)` |
| Texto largo | `TEXT` |
| Booleanos | `BOOLEAN` |
| Fechas | `DATE` (week_start, due_date) |
| Fechas+horas | `TIMESTAMP WITH TIME ZONE` (created_at, etc.) |
| Montos | `NUMERIC(10,2)` (estimated_price, amount) |
| Mes/año | `VARCHAR(7)` con CHECK (formato YYYY-MM) |
| Enum (Task.status) | `VARCHAR(20)` con CHECK |
| Enum (Task.frequency) | `VARCHAR(20)` con CHECK |
| Enum (Budget.type) | `VARCHAR(10)` con CHECK |

### Valores enumerados (CHECK constraints)

| Columna | Valores permitidos |
|---------|--------------------|
| `Task.status` | `pending` \| `in_progress` \| `done` |
| `Task.frequency` | `daily` \| `weekly` \| `monthly` \| `once` |
| `BudgetItem.type` | `income` \| `expense` |

Cada uno se implementa con `CHECK (col IN (...))` a nivel de tabla. Pydantic los valida en el request body con `Literal[...]` o `Enum`.

### Foreign Keys y política ON DELETE

Política unificada: **todas las FK que apuntan a `users.id` usan `ON DELETE SET NULL`**. Eliminar un usuario no borra históricos; solo desreferencia.

| FK | Nullable | ON DELETE | Razón |
|----|----------|-----------|-------|
| `tasks.assigned_to → users.id` | ✅ | SET NULL | Tareas sin asignar quedan visibles para reasignar |
| `checklist_items.completed_by → users.id` | ✅ | SET NULL | Histórico de completados se mantiene |
| `shopping_items.added_by → users.id` | ✅ | SET NULL | Históricos de compra se mantienen |
| `shopping_items.purchased_by → users.id` | ✅ | SET NULL | Histórico se mantiene |
| `budget_items.user_id → users.id` | ✅ | SET NULL | Movimientos sobreviven al borrado del usuario |

Implicación: `DELETE /api/users/{id}` siempre devuelve **204** (no hay 409 por FK violation). El frontend muestra "Usuario eliminado; sus tareas pasaron a 'sin asignar'".

---

## 2.1 Autenticación y perfil (replanteamiento 2026-06)

> Con el paso a **PWA con login por dispositivo** (ver `docs/PRODUCT_PLAN.md` §6), `User` se amplía con campos de cuenta/perfil y se añaden `Invite` y `RefreshToken`. Modelo de **un hogar por instancia** (sin entidad `Household`); el acceso se restringe por **código de invitación**. Esto **supera el "sin auth"** de `architecture.md` §8 / ADR-005.

### `User` (campos añadidos)

| Campo | Tipo PostgreSQL | Notas |
|-------|-----------------|-------|
| `email` | `CITEXT UNIQUE NOT NULL` | identificador de login (case-insensitive) |
| `password_hash` | `VARCHAR(255) NOT NULL` | bcrypt/argon2; **nunca** en `UserOut` ni en logs |
| `display_name` | `VARCHAR(255) NOT NULL` | sustituye al antiguo `name` |
| `bio` | `TEXT` | editable por el propio usuario |
| `theme_preference` | `VARCHAR(10)` CHECK (`light`/`dark`/`system`) | sincroniza tema entre dispositivos |
| `role` | `VARCHAR(10)` CHECK (`admin`/`member`) | el primer registro (bootstrap) es `admin` |
| `is_active` | `BOOLEAN DEFAULT true` | `false` desactiva el login sin borrar históricos |
| `last_login_at` | `TIMESTAMPTZ` | |
| `updated_at` | `TIMESTAMPTZ` | |

`name` previo → `display_name`. `color` y `avatar` se mantienen (parte del perfil personalizable).

### `Invite` (nueva)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `SERIAL PK` | |
| `code` | `VARCHAR(64) UNIQUE NOT NULL` | token URL-safe aleatorio |
| `role` | `VARCHAR(10)` CHECK (`admin`/`member`) | rol con el que entra el invitado (`member` por defecto) |
| `created_by` | FK → `users.id` (ON DELETE SET NULL) | quién la generó |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | caducidad (p. ej. +7 días) |
| `used_at` | `TIMESTAMPTZ` | null = sin usar |
| `used_by` | FK → `users.id` (ON DELETE SET NULL) | quién la canjeó |
| `created_at` | `TIMESTAMPTZ DEFAULT now()` | |

Reglas: **un solo uso**, caduca. Registro válido ⇔ `code` existe, `used_at IS NULL` y `expires_at > now()`. **Excepción bootstrap**: si `SELECT count(*) FROM users = 0`, el primer registro crea al `admin` **sin código**.

### `RefreshToken` (nueva)

| Campo | Tipo | Notas |
|-------|------|-------|
| `id` | `SERIAL PK` | |
| `user_id` | FK → `users.id` (ON DELETE CASCADE) | dueño de la sesión |
| `token_hash` | `VARCHAR(255) NOT NULL` | hash del refresh token (no en claro) |
| `expires_at` | `TIMESTAMPTZ NOT NULL` | caducidad larga (p. ej. +30 días) |
| `revoked_at` | `TIMESTAMPTZ` | logout o rotación → revocado |
| `created_at` | `TIMESTAMPTZ DEFAULT now()` | |

> **Nota**: a diferencia de las FK hacia `users.id` del dominio (ADR-007: SET NULL), `refresh_tokens.user_id` usa **CASCADE** — al borrar un usuario se eliminan sus sesiones.

### Actor derivado del token (cambio de contrato)

Las columnas de "quién hizo la acción" (`tasks.assigned_to` para auto-asignación, `checklist_items.completed_by`, `shopping_items.added_by`/`purchased_by`, `budget_items.user_id`) **se rellenan con el usuario autenticado** (`current_user.id`), **no** con un valor del request body. La política ON DELETE SET NULL (ADR-007) no cambia. Excepción: `tasks.assigned_to` y los `user_ids` de la ruleta sí viajan en el body cuando referencian a *otros* usuarios.

---

## 3. Índices recomendados

```sql
-- Tasks: filtros comunes
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_assigned_to ON tasks(assigned_to);

-- Checklist: consulta por semana
CREATE INDEX idx_checklist_week_start ON checklist_items(week_start);

-- Shopping: filtros de lista de compras
CREATE INDEX idx_shopping_purchased ON shopping_items(purchased);
CREATE INDEX idx_shopping_category ON shopping_items(category);

-- Budget: consulta por mes + agregación
CREATE INDEX idx_budget_month ON budget_items(month);
CREATE INDEX idx_budget_month_type ON budget_items(month, type);
CREATE INDEX idx_budget_month_category ON budget_items(month, category);

-- Auth: login y canje de invitación
CREATE UNIQUE INDEX idx_users_email ON users(email);          -- (CITEXT ya es único)
CREATE UNIQUE INDEX idx_invites_code ON invites(code);
CREATE INDEX idx_refresh_tokens_user ON refresh_tokens(user_id);
```

---

## 4. Estrategia de schema management

**Sin Alembic** (por decisión del equipo). Alternativa:

```python
# app/database.py
from sqlalchemy import text

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    # Índices y constraints adicionales se definen en el modelo
```

Para cambios destructivos (renombrar columna, cambiar tipo), se ejecuta un script SQL manual en `scripts/migrate.sql`. Esto es aceptable para el volumen actual.

---

## 5. Batch operations y transacciones

Toda operación batch debe ejecutarse dentro de una transacción explícita:

```python
# En el repository
async def batch_purchase(self, ids: list[int], purchased_by: int) -> int:
    async with self.db.begin():
        result = await self.db.execute(
            update(ShoppingItem)
            .where(ShoppingItem.id.in_(ids))
            .where(ShoppingItem.purchased == False)
            .values(
                purchased=True,
                purchased_at=func.now(),
                purchased_by=purchased_by,
            )
        )
        return result.rowcount
```

Reglas:
- Validar existencia de todos los IDs **antes** de abrir la transacción.
- Si un ID no existe, lanzar 404 antes de cualquier escritura.
- La transacción cubre solo las escrituras, no las lecturas de validación.
