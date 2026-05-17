from __future__ import annotations

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker


class DatabaseSessionFactory:
    """Thin wrapper around SQLAlchemy engine/session creation."""

    def __init__(self, database_url: str, echo: bool = False) -> None:
        self.engine = create_engine(database_url, echo=echo, future=True)
        self._session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    def session(self) -> Session:
        return self._session_factory()

    def ping(self) -> bool:
        with self.session() as session:
            session.execute(text("SELECT 1"))
        return True
