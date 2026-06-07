"""
Lógica de la ruleta. ESQUELETO — iter 1.

Estrategia prevista (ver docs/ARCHITECTURE.md §3):
- Recibe lista de task_ids y user_ids.
- Baraja usuarios.
- Reparte en round-robin sobre las tareas (queda balanceado).
- Devuelve (assignments, unassigned) como datos puros, sin tocar la DB.
- El router aplica la asignación en la DB (separación service ↔ persistencia).
"""
from typing import Optional


def assign_tasks(
    task_ids: list[int],
    user_ids: list[int],
    seed: Optional[int] = None,
) -> tuple[list[tuple[int, int]], list[int]]:
    # TODO iter 3
    raise NotImplementedError
