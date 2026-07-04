from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Declarative base class for all ORM models.

    Domain models will inherit from this base in later phases.
    """
