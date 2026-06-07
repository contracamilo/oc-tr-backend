"""
Router de presupuesto. ESQUELETO — iter 1.

Implementación en iter 6.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/budget", tags=["budget"])


# TODO iter 6:
#   GET    /?month=YYYY-MM            -> listar movimientos del mes
#   POST   /                          -> crear movimiento
#   PATCH  /{item_id}                 -> editar
#   DELETE /{item_id}                 -> eliminar
#   GET    /summary?month=YYYY-MM     -> resumen (total income/expense, balance, by_category)
