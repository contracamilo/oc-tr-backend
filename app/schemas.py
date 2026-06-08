"""
Schemas Pydantic (in/out) de la API.

ESQUELETO — iteración 1.
Los schemas definitivos están en docs/PRODUCT_PLAN.md §6.
"""
from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PaginatedResponse(BaseModel, Generic[T]):
    items: list[T]
    total: int
    limit: int
    offset: int


# TODO iter 2: UserCreate, UserUpdate, UserOut
# TODO iter 2: TaskCreate, TaskUpdate, TaskOut
# TODO iter 2: Token, TokenRefresh, RegisterRequest, LoginRequest
# TODO iter 2: InviteCreate, InviteOut
# TODO iter 4: ChecklistCreate, ChecklistUpdate, ChecklistOut
# TODO iter 5: ShoppingCreate, ShoppingUpdate, ShoppingOut
# TODO iter 6: BudgetCreate, BudgetUpdate, BudgetOut, BudgetSummary
# TODO iter 3: RouletteRequest, RouletteResult
