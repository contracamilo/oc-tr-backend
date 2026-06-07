# Backend Spec — Hogar

> Spec-driven development plan for the FastAPI backend.
> Cada iteración se desglosa en issues separados. Esta es la visión general.

---

## 1. Overview

API REST con **FastAPI + SQLAlchemy 2 + SQLite**. Sin auth, sync, file-based DB. Sirve también los estáticos del frontend en producción (decisión pendiente de iter 7).

Convenciones:
- REST, prefijo `/api`, JSON.
- Errores: `{"detail": "..."}` (default de FastAPI).
- Códigos: 200/201/204/400/404/409.
- Timestamps: `datetime.utcnow` server-side.

---

## 2. Iteraciones

### iter 1 — Setup ✅

- [x] Scaffold del proyecto
- [x] `requirements.txt`, `.env.example`, `.gitignore`
- [x] Estructura `app/{routers,services}`
- [x] `GET /api/health`

---

### iter 2 — Users + Tasks

**Objetivo:** CRUD de los dos recursos base. Sin esto no se puede probar nada.

**Modelos:**

```
User(id, name UNIQUE, color, avatar?, created_at)
Task(id, title, description?, frequency, status, due_date?, assigned_to? FK, created_at, completed_at?)
```

**Endpoints Users:** `GET/POST /api/users`, `GET/PATCH/DELETE /api/users/{id}`
**Endpoints Tasks:** `GET/POST /api/tasks`, `GET/PATCH/DELETE /api/tasks/{id}` (GET con filtros `status`, `assigned_to`)

**Acceptance criteria:**

- [ ] `User.name` único → 409 en POST/PATCH si se repite
- [ ] `Task.assigned_to` valida FK → 400 si no existe
- [ ] `Task.status=done` setea `completed_at` automáticamente
- [ ] `Task.status≠done` limpia `completed_at`
- [ ] PATCH con `exclude_unset=True` no blanka campos
- [ ] Listar tasks ordena por status, due_date, id
- [ ] Smoke tests por endpoint (201, 204, 404, 409, 400)

---

### iter 3 — Roulette

**Objetivo:** asignación aleatoria balanceada de tareas pendientes.

**Lógica pura en `services/roulette.py`:**

```python
def assign_tasks(
    task_ids: list[int],
    user_ids: list[int],
    seed: Optional[int] = None,
) -> tuple[list[tuple[int, int]], list[int]]:
    ...
```

Estrategia: baraja usuarios (semilla opcional), round-robin sobre tareas. Devuelve `(assignments, unassigned)`.

**Endpoint:** `POST /api/roulette` body `{task_ids, user_ids, seed?}` → aplica a DB y devuelve `{assignments, unassigned_tasks}`.

**Acceptance criteria:**

- [ ] Función pura testeable sin DB
- [ ] Balanceo correcto con más tareas que usuarios (y al revés)
- [ ] `seed` reproducible (test lo verifica)
- [ ] Endpoint valida que todos los ids existan
- [ ] Unit tests + 1 integration test

---

### iter 4 — Checklist semanal

**Objetivo:** tareas recurrentes marcables, agrupadas por semana ISO (lunes).

**Modelo:**

```
ChecklistItem(id, title, week_start: date, completed: bool,
              completed_by? FK, completed_at?, created_at)
```

**Endpoints:** `GET/POST /api/checklist`, `PATCH/DELETE /api/checklist/{id}`

**Acceptance criteria:**

- [ ] `completed=true` setea `completed_at`
- [ ] `completed=false` limpia `completed_at` y `completed_by`
- [ ] GET con `week_start` filtra; sin filtro → semana actual
- [ ] Smoke tests

---

### iter 5 — Lista de mercado

**Objetivo:** lista compartida con categorías y precio estimado.

**Modelo:**

```
ShoppingItem(id, name, quantity=1, unit?, category?, purchased: bool,
             added_by? FK, purchased_by? FK, estimated_price?,
             created_at, purchased_at?)
```

**Endpoints:** `GET/POST /api/shopping`, `PATCH/DELETE /api/shopping/{id}` (GET filtra por `purchased` y `category`)

**Acceptance criteria:**

- [ ] `purchased=true` setea `purchased_at`
- [ ] `purchased=false` limpia `purchased_at` y `purchased_by`
- [ ] `estimated_price` opcional y formateable
- [ ] Smoke tests

---

### iter 6 — Presupuesto mensual

**Objetivo:** ingresos/gastos con resumen por categoría.

**Modelo:**

```
BudgetItem(id, month: 'YYYY-MM', type: 'income'|'expense',
           category, description?, amount, user_id? FK, created_at)
```

**Endpoints:**

- `GET/POST /api/budget`, `PATCH/DELETE /api/budget/{id}`
- `GET /api/budget/summary?month=YYYY-MM` → `{total_income, total_expense, balance, by_category}`

**Acceptance criteria:**

- [ ] `month` validado con regex `^\d{4}-\d{2}$`
- [ ] `type ∈ {income, expense}`
- [ ] Summary agrega correctamente
- [ ] `by_category` incluye ambos tipos (decisión en su issue)

---

### iter 7 — Pulido + tests

**Objetivo:** calidad, deploy, robustez.

- [ ] Servir frontend como static desde FastAPI (`app.mount("/")`)
- [ ] `pytest` + `httpx.AsyncClient` con DB en memoria
- [ ] Smoke test por router
- [ ] CORS configurable dev/prod
- [ ] README actualizado con quickstart completo
- [ ] Manejo de errores uniforme (`{"detail", "code"}`)

---

## 3. Cross-cutting

### CORS
- **Dev**: lista explícita de localhosts
- **Prod**: variable de entorno

### Errores
Formato `{"detail": "..."}` en 4xx. En iter 7 se amplía a `{"detail", "code"}` si se justifica.

### Migrations
- `Base.metadata.create_all` en startup es suficiente hasta iter 7.
- **Alembic** se introduce cuando se cambie un modelo y ya haya DBs en uso.

---

## 4. Decisiones

| Tema | Decisión | Reversible? |
|---|---|---|
| Sync vs async | **Sync** | sí, capa a capa |
| DB | **SQLite** con WAL | migrar a Postgres = cambiar URL |
| ORM | **SQLAlchemy 2.0** | caro |
| Auth | **Ninguna** | añadir middleware si se expone |
| Validación FK | explícita en router (400) | trivial |
| Migrations | `create_all` → Alembic en iter 7 | sí |

---

## 5. Out of scope (v1)

- Multi-hogar (varios hogares en una instancia)
- Auth real
- WebSockets / real-time
- File uploads
- Cache (Redis, etc.)
- Métricas / observabilidad

---

## 6. Mapa de issues

| Iter | Issue | Título |
|---|---|---|
| 2 | #1 | feat(api): implement User model and CRUD |
| 2 | #2 | feat(api): implement Task model and CRUD |
| 3 | #3 | feat(api): implement Roulette service and endpoint |
| 4 | #4 | feat(api): implement ChecklistItem model and CRUD |
| 5 | #5 | feat(api): implement ShoppingItem model and CRUD |
| 6 | #6 | feat(api): implement BudgetItem model and CRUD |
| 6 | #7 | feat(api): implement Budget summary endpoint |
| 7 | #8 | chore: serve frontend as static files |
| 7 | #9 | test: pytest setup + smoke tests per router |
| 7 | #10 | docs: full quickstart in README + env handling |
