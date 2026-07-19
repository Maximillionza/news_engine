"""Shared database engine/session setup.

Production target is PostgreSQL (see docker-compose.yml and
Documentation/operations/technology_decisions.md). Tests use SQLite in-memory so Phase 1's
test suite runs without requiring Docker - see technology_decisions.md for why this is a
test-only substitution, not a production storage decision.
"""

from __future__ import annotations

import os

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base so every service's tables register on one metadata object."""


def make_engine(database_url: str | None = None):
    url = database_url or os.environ.get("DATABASE_URL", "sqlite:///:memory:")
    connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
    return create_engine(url, connect_args=connect_args)


def make_session_factory(engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, autoflush=False, autocommit=False)
