"""Base dichiarativa condivisa dai modelli."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass


# L'import rende disponibili tutte le tabelle a Base.metadata e ad Alembic.
from backend.app.models import entities as _entities  # noqa: E402,F401

