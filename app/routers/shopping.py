"""
Router de lista de mercado. ESQUELETO — iter 1.

Implementación en iter 5.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/shopping", tags=["shopping"])


# TODO iter 5:
#   GET    /?purchased=&category=    -> listar
#   POST   /                          -> añadir
#   PATCH  /{item_id}                 -> editar / marcar comprado
#   DELETE /{item_id}                 -> eliminar
