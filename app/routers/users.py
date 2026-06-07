"""
Router de usuarios. ESQUELETO — iter 1.

La forma final del router está en docs/PRODUCT_PLAN.md §7.
"""
from fastapi import APIRouter

router = APIRouter(prefix="/users", tags=["users"])


# TODO iter 2:
#   GET    /            -> listar
#   POST   /            -> crear
#   GET    /{user_id}   -> detalle
#   PATCH  /{user_id}   -> editar
#   DELETE /{user_id}   -> eliminar
