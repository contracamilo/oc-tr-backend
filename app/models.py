"""
Modelos ORM de SQLAlchemy.

ESQUELETO — iteración 1.
La forma definitiva de cada modelo está en docs/PRODUCT_PLAN.md §6
y se implementa en iteraciones posteriores.

IMPORTANTE: importar Base desde database.py, no declarar uno nuevo aquí,
para que init_db() vea las tablas en Base.metadata.create_all.
"""
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


# TODO iter 2: User, Invite, RefreshToken
# TODO iter 2: Task
# TODO iter 4: ChecklistItem
# TODO iter 5: ShoppingItem
# TODO iter 6: BudgetItem
