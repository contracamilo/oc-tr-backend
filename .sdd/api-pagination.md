# API Pagination & Batch Specification

> Especificación técnica de paginación y operaciones batch para la BFF mobile-first de Hogar.
> Esta BFF orquesta respuestas ligeras para la SPA mobile-first, usando PostgreSQL + async SQLAlchemy + Repository pattern.

---

## 1. Pagination

### 1.1 Request Format

Toda GET list endpoint acepta estos query parameters:

| Parameter | Type | Default | Max | Description |
|-----------|------|---------|-----|-------------|
| `limit` | `int` | 20-50* | 100-200* | Número de items por página |
| `offset` | `int` | 0 | — | Índice del primer item |

\* Límites por recurso:

| Endpoint | Default limit | Max limit |
|----------|---------------|-----------|
| `GET /api/tasks` | 20 | 100 |
| `GET /api/checklist` | 50 | 200 |
| `GET /api/shopping` | 50 | 200 |
| `GET /api/budget` | 20 | 100 |

### 1.2 Response Format

```json
{
  "items": [ ... ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `items` | `list[T]` | Array de items de la página actual |
| `total` | `int` | Número total de items (no filtrados por paginación) |
| `limit` | `int` | Echo del request (facilita al frontend saber cuántos pidió) |
| `offset` | `int` | Echo del request |

### 1.3 Generic Schema (Pydantic)

```python
from typing import Generic, TypeVar
from pydantic import BaseModel

T = TypeVar("T")

class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int
```

Uso en cada router:

```python
@router.get("", response_model=PaginatedResponse[TaskOut])
def list_tasks(
    status: Optional[str] = None,
    assigned_to: Optional[int] = None,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
) -> PaginatedResponse[TaskOut]:
    query = db.query(Task)
    if status:
        query = query.filter(Task.status == status)
    if assigned_to:
        query = query.filter(Task.assigned_to == assigned_to)
    query = query.order_by(Task.status, Task.due_date, Task.id)
    items, total = paginate(query, limit, offset)
    return PaginatedResponse(items=items, total=total, limit=limit, offset=offset)
```

### 1.4 Helper Function

```python
# app/services/pagination.py
from sqlalchemy.orm import Query

def paginate(query: Query, limit: int, offset: int) -> tuple[list, int]:
    total = query.count()
    items = query.offset(offset).limit(limit).all()
    return items, total
```

---

## 2. Batch Operations

### 2.1 Shopping Batch Purchase

`POST /api/shopping/batch-purchase`

**Request**:
```json
{
  "ids": [1, 5, 12, 18],
  "purchased_by": 2
}
```

**Response** (200):
```json
{
  "updated": 4
}
```

**Behavior**:
- Marca `purchased = True`, setea `purchased_at` y `purchased_by` en una sola transacción
- Solo actualiza items donde `purchased == False` (idempotente)
- Si algún `id` no existe, lanza 404 (la transacción no se aplica)
- No requiere validación de FK para `purchased_by` (se asume que el frontend envía un user_id válido)

**Schema**:
```python
class BatchPurchaseRequest(BaseModel):
    ids: list[int]
    purchased_by: int
```

### 2.2 Roulette Batch Assignment

`POST /api/roulette`

**Request**:
```json
{
  "task_ids": [1, 2, 3, 4, 5],
  "user_ids": [10, 20, 30],
  "seed": 42
}
```

**Response** (200):
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
- Delega en `services/roulette.assign_tasks()` (pure function)
- Valida que todos los `task_ids` y `user_ids` existan en DB
- Aplica asignaciones en una transacción (setea `Task.assigned_to`)
- `seed` es opcional — si se omite, usa `random` sin semilla
- Si no hay usuarios, todas las tareas quedan en `unassigned_tasks`

**Schema**:
```python
class RouletteRequest(BaseModel):
    task_ids: list[int]
    user_ids: list[int]
    seed: Optional[int] = None

class RouletteAssignment(BaseModel):
    task_id: int
    user_id: int

class RouletteResult(BaseModel):
    assignments: list[RouletteAssignment]
    unassigned_tasks: list[int]
```

---

## 3. Matrix de Endpoints

| Endpoint | Method | Paginación | Batch | Filtros |
|----------|--------|------------|-------|---------|
| `/api/users` | GET | No (pocos) | — | — |
| `/api/users` | POST | — | — | — |
| `/api/users/{id}` | GET/PATCH/DELETE | — | — | — |
| `/api/tasks` | GET | ✅ limit=20 | — | `status`, `assigned_to` |
| `/api/tasks` | POST | — | — | — |
| `/api/tasks/{id}` | PATCH/DELETE | — | — | — |
| `/api/roulette` | POST | — | ✅ batch | — |
| `/api/checklist` | GET | ✅ limit=50 | — | `week_start` |
| `/api/checklist` | POST | — | — | — |
| `/api/checklist/{id}` | PATCH/DELETE | — | — | — |
| `/api/shopping` | GET | ✅ limit=50 | — | `purchased`, `category` |
| `/api/shopping` | POST | — | — | — |
| `/api/shopping/{id}` | PATCH/DELETE | — | — | — |
| `/api/shopping/batch-purchase` | POST | — | ✅ batch | — |
| `/api/budget` | GET | ✅ limit=20 | — | `month` |
| `/api/budget` | POST | — | — | — |
| `/api/budget/{id}` | PATCH/DELETE | — | — | — |
| `/api/budget/summary` | GET | No (aggregate) | — | `month` |
| `/api/dashboard` | GET | No (aggregate) | — | — |

---

## 4. Implementation Order

1. **Phase A**: Create `services/pagination.py` + `PaginatedResponse` in `schemas.py`
2. **Phase B**: Add pagination to `tasks.py`
3. **Phase C**: Implement `services/roulette.py` + `routers/roulette.py`
4. **Phase D**: Add pagination to `checklist.py`
5. **Phase E**: Add pagination to `shopping.py` + batch-purchase endpoint
6. **Phase F**: Add pagination to `budget.py`
7. **Phase G**: Wire all routers in `main.py`

Cada fase es independiente (salvo que dependen de Phase A) y puede ser implementada por un agente distinto.
