"""
Router de ruleta. ESQUELETO — iter 1.

Implementación en iter 3. La lógica de asignación vive en
app/services/roulette.py y se invoca desde aquí.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/roulette", tags=["roulette"])


# TODO iter 3:
#   POST /   -> body: {task_ids: int[], user_ids: int[], seed?: int}
#             -> devuelve {assignments: [{task_id, user_id}], unassigned_tasks: int[]}
#             -> aplica las asignaciones actualizando Task.assigned_to en la DB
