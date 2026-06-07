"""
Router de tareas. ESQUELETO — iter 1.

La forma final del router está en docs/PRODUCT_PLAN.md §7.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/tasks", tags=["tasks"])


# TODO iter 2:
#   GET    /             -> listar (filtros: status, assigned_to)
#   POST   /             -> crear
#   GET    /{task_id}    -> detalle
#   PATCH  /{task_id}    -> editar / cambiar estado (setea completed_at)
#   DELETE /{task_id}    -> eliminar
