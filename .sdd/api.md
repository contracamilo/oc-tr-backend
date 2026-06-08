# API Reference — Hogar BFF

> Contratos completos de la API REST. Todos los endpoints tienen prefijo `/api`.
> Formato de errores: `{"detail": "...", "code": "..."}` (ver `.sdd/architecture.md` §4).
> Paginación: `{"items": [...], "total": int, "limit": int, "offset": int}` (ver `.sdd/api-pagination.md`).

---

## 1. Health

### `GET /api/health`

**Response 200**:
```json
{
  "status": "ok",
  "db": "connected",
  "env": "development",
  "uptime": 3600
}
```

### `GET /api/health/ready`

**Response 200**: `{"status": "ready"}`
**Response 503**: `{"status": "not ready", "detail": "Base de datos no disponible"}`

### `GET /api/health/live`

**Response 200**: `{"status": "alive"}`

---

## 2. Users

### `GET /api/users`

Listar usuarios. Sin paginación (pocos registros).

**Response 200**:
```json
[
  {"id": 1, "name": "Ana", "color": "#FF5733", "avatar": null, "created_at": "2026-06-01T10:00:00"},
  {"id": 2, "name": "Luis", "color": "#33FF57", "avatar": "luis.png", "created_at": "2026-06-01T10:00:00"}
]
```

### `POST /api/users`

**Request**:
```json
{"name": "Ana", "color": "#FF5733", "avatar": null}
```

**Response 201**:
```json
{"id": 3, "name": "Ana", "color": "#FF5733", "avatar": null, "created_at": "2026-06-08T12:00:00"}
```

**Errors**: 409 (name duplicado)

### `GET /api/users/{user_id}`

**Response 200**: User object
**Response 404**: `{"detail": "Usuario no encontrado", "code": "NOT_FOUND"}`

### `PATCH /api/users/{user_id}`

**Request**: Partial user fields (exclude_unset=True)

**Response 200**: User object actualizado
**Errors**: 404, 409 (name duplicado)

### `DELETE /api/users/{user_id}`

**Response 204**: No content
**Errors**: 404, 409 (tiene tareas asignadas — FK violation)

---

## 3. Tasks

### `GET /api/tasks`

**Query params**: `status`, `assigned_to`, `limit` (default 20, max 100), `offset` (default 0)

**Filtros**:
- `status`: `pending` | `done` | `in_progress`
- `assigned_to`: int (user_id)

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "Lavar platos",
      "description": "Después de cenar",
      "frequency": "daily",
      "status": "pending",
      "due_date": "2026-06-08",
      "assigned_to": 2,
      "created_at": "2026-06-01T10:00:00",
      "completed_at": null
    }
  ],
  "total": 15,
  "limit": 20,
  "offset": 0
}
```

### `POST /api/tasks`

**Request**:
```json
{
  "title": "Lavar platos",
  "description": "Después de cenar",
  "frequency": "daily",
  "status": "pending",
  "due_date": "2026-06-08",
  "assigned_to": 2
}
```

**Response 201**: Task object
**Errors**: 400 (FK inválida en assigned_to)

### `GET /api/tasks/{task_id}`

**Response 200**: Task object
**Response 404**: `{"detail": "Tarea no encontrada", "code": "NOT_FOUND"}`

### `PATCH /api/tasks/{task_id}`

**Request**: Partial task fields

**Comportamiento especial**: Si `status` cambia a `done`, setea `completed_at`. Si `status` cambia a otro valor, limpia `completed_at`.

**Response 200**: Task object actualizado
**Errors**: 404, 400 (FK inválida)

### `DELETE /api/tasks/{task_id}`

**Response 204**
**Errors**: 404

---

## 4. Roulette

### `POST /api/roulette`

Asignación aleatoria balanceada de tareas a usuarios.

**Request**:
```json
{
  "task_ids": [1, 2, 3, 4, 5],
  "user_ids": [10, 20, 30],
  "seed": 42
}
```

**Response 200**:
```json
{
  "assignments": [
    {"task_id": 1, "user_id": 20},
    {"task_id": 2, "user_id": 30},
    {"task_id": 3, "user_id": 10},
    {"task_id": 4, "user_id": 20},
    {"task_id": 5, "user_id": 30}
  ],
  "unassigned_tasks": []
}
```

**Behavior**:
1. Valida que todos los `task_ids` y `user_ids` existan
2. Delega en `services/roulette.assign_tasks()` (pure function, round-robin balanceado)
3. **Auto-apply**: Aplica asignaciones en una transacción (setea `Task.assigned_to`) — el frontend no necesita un segundo paso
4. `seed` opcional — si se omite, usa random sin semilla

**Errors**: 400 (IDs inválidos), 404 (task o user no existe)

---

## 5. Dashboard

### `GET /api/dashboard`

KPIs agregados para la vista de inicio del frontend.

**Response 200**:
```json
{
  "tasks_pending": 12,
  "tasks_overdue": 3,
  "checklist_unchecked": 5,
  "shopping_unpurchased": 18,
  "budget_month": "2026-06",
  "budget_balance": 650.00,
  "budget_expense": 1850.00,
  "budget_income": 2500.00
}
```

**Comportamiento**:
- `tasks_pending`: tareas con `status != 'done'`
- `tasks_overdue`: tareas con `due_date < today` y `status != 'done'`
- `checklist_unchecked`: items de la semana actual con `completed = false`
- `shopping_unpurchased`: items con `purchased = false`
- `budget_*`: datos del mes actual (o del último mes con movimientos)

**Errors**: Ninguno (siempre devuelve KPIs, aunque sean 0)

---

## 6. Checklist

### `GET /api/checklist`

**Query params**: `week_start` (YYYY-MM-DD), `limit` (default 50, max 200), `offset` (default 0)

**Comportamiento**: Si no se envía `week_start`, usa la semana ISO actual (lunes).

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "title": "Regar plantas",
      "week_start": "2026-06-08",
      "completed": false,
      "completed_by": null,
      "completed_at": null,
      "created_at": "2026-06-08T08:00:00"
    }
  ],
  "total": 8,
  "limit": 50,
  "offset": 0
}
```

### `POST /api/checklist`

**Request**:
```json
{"title": "Regar plantas", "week_start": "2026-06-08"}
```

**Response 201**: ChecklistItem object

### `PATCH /api/checklist/{item_id}`

**Comportamiento especial**: Si `completed` cambia a `true`, setea `completed_at` y requiere `completed_by`. Si cambia a `false`, limpia ambos.

**Request**:
```json
{"completed": true, "completed_by": 2}
```

**Response 200**: ChecklistItem actualizado
**Errors**: 400 (completed=true sin completed_by), 404

### `DELETE /api/checklist/{item_id}`

**Response 204**
**Errors**: 404

---

## 7. Shopping

### `GET /api/shopping`

**Query params**: `purchased` (bool), `category` (string), `limit` (default 50, max 200), `offset` (default 0)

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "name": "Leche",
      "quantity": 2,
      "unit": "litro",
      "category": "Lácteos",
      "purchased": false,
      "added_by": 1,
      "purchased_by": null,
      "estimated_price": 1.50,
      "created_at": "2026-06-07T10:00:00",
      "purchased_at": null
    }
  ],
  "total": 25,
  "limit": 50,
  "offset": 0
}
```

### `POST /api/shopping`

**Request**:
```json
{
  "name": "Leche",
  "quantity": 2,
  "unit": "litro",
  "category": "Lácteos",
  "added_by": 1,
  "estimated_price": 1.50
}
```

**Response 201**: ShoppingItem object

### `PATCH /api/shopping/{item_id}`

**Comportamiento especial**: Si `purchased` cambia a `true`, setea `purchased_at` y requiere `purchased_by`. Si cambia a `false`, limpia ambos.

**Response 200**: ShoppingItem actualizado
**Errors**: 400, 404

### `DELETE /api/shopping/{item_id}`

**Response 204**
**Errors**: 404

### `POST /api/shopping/batch-purchase`

Marcar múltiples items como comprados en una sola transacción.

**Request**:
```json
{"ids": [1, 5, 12, 18], "purchased_by": 2}
```

**Response 200**:
```json
{"updated": 4}
```

**Behavior**:
- Solo actualiza items donde `purchased == false` (idempotente)
- Si algún `id` no existe, lanza 404 y no aplica cambios
- Atómico: una transacción

**Errors**: 404 (ID no existe), 400 (purchased_by inválido)

---

## 8. Budget

### `GET /api/budget`

**Query params**: `month` (YYYY-MM), `limit` (default 20, max 100), `offset` (default 0)

**Response 200**:
```json
{
  "items": [
    {
      "id": 1,
      "month": "2026-06",
      "type": "expense",
      "category": "Comida",
      "description": "Supermercado",
      "amount": 85.50,
      "user_id": 1,
      "created_at": "2026-06-03T15:00:00"
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

### `POST /api/budget`

**Request**:
```json
{
  "month": "2026-06",
  "type": "expense",
  "category": "Comida",
  "description": "Supermercado",
  "amount": 85.50,
  "user_id": 1
}
```

**Response 201**: BudgetItem object
**Errors**: 422 (month inválido), 400 (type no es income|expense)

### `GET /api/budget/summary?month=2026-06`

**Response 200** (sin paginación — es agregado):
```json
{
  "month": "2026-06",
  "total_income": 2500.00,
  "total_expense": 1850.00,
  "balance": 650.00,
  "by_category": {
    "Comida": 450.00,
    "Servicios": 300.00,
    "Ocio": 200.00
  }
}
```

**Errors**: 422 (month inválido)

### `PATCH /api/budget/{item_id}`

**Response 200**: BudgetItem actualizado
**Errors**: 404, 422

### `DELETE /api/budget/{item_id}`

**Response 204**
**Errors**: 404

---

## 9. Status Codes Summary

| Código | Significado | Uso |
|--------|-------------|-----|
| 200 | OK | GET, PATCH exitoso, POST batch |
| 201 | Created | POST de nuevo recurso |
| 204 | No Content | DELETE exitoso |
| 400 | Bad Request | Validación de negocio, FK inválida |
| 404 | Not Found | Recurso no existe |
| 409 | Conflict | Unique violation, FK violation |
| 422 | Validation Error | Formato inválido (Pydantic) |
| 429 | Too Many Requests | Rate limit excedido |
| 500 | Internal Error | Error no capturado |

---

## 10. Response Format Consistency

Todas las respuestas siguen estas reglas:

- **Listas con paginación**: `PaginatedResponse[T]` con `items`, `total`, `limit`, `offset`
- **Listas sin paginación** (users): Array plano `[T]`
- **Recurso individual**: El objeto directamente
- **Batch**: `{"updated": N}` o `{assignments: [...], unassigned_tasks: [...]}`
- **Summary** (budget): Objeto con campos agregados
- **Errores 4xx**: `{"detail": "...", "code": "..."}`
- **Errores 5xx**: `{"detail": "Error interno del servidor", "code": "INTERNAL_ERROR"}` (detail genérico en prod)
