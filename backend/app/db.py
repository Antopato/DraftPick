from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from .config import settings

# check_same_thread only applies to SQLite; any other backend (e.g. Postgres)
# works by just changing DATABASE_URL.
connect_args = (
    {"check_same_thread": False}
    if settings.database_url.startswith("sqlite")
    else {}
)

engine = create_engine(settings.database_url, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


def create_tables() -> None:
    from . import models  # noqa: F401  (register mappings)

    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()
