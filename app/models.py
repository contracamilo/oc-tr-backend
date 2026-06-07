"""
Modelos ORM de SQLAlchemy.

ESQUELETO — iteración 1.
La forma definitiva de cada modelo se describe en docs/PRODUCT_PLAN.md §6
y se implementa en iteraciones posteriores.
"""
from datetime import datetime

from sqlalchemy import DateTime, Integer
from sqlalchemy.orm import Mapped, declarative_base, mapped_column

Base = declarative_base()


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# TODO iter 2: User
# TODO iter 2: Task
# TODO iter 4: ChecklistItem
# TODO iter 5: ShoppingItem
# TODO iter 6: BudgetItem
