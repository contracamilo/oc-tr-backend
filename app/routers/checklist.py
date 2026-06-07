"""
Router de checklist semanal. ESQUELETO — iter 1.

Implementación en iter 4.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/checklist", tags=["checklist"])


# TODO iter 4:
#   GET    /?week_start=YYYY-MM-DD   -> listar items de la semana
#   POST   /                          -> crear item
#   PATCH  /{item_id}                 -> marcar / desmarcar (setea completed_at y completed_by)
#   DELETE /{item_id}                 -> eliminar
