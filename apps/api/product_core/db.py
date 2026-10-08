from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .config import get_settings


class Base(DeclarativeBase):
    pass


settings = get_settings()
if settings.database_url.startswith("sqlite"):
    filename = make_url(settings.database_url).database
    if filename and filename != ":memory:":
        Path(filename).parent.mkdir(parents=True, exist_ok=True)
engine = create_engine(
    settings.database_url,
    pool_pre_ping=True,
    connect_args={"check_same_thread": False} if settings.database_url.startswith("sqlite") else {},
)
SessionLocal = sessionmaker(engine, expire_on_commit=False)
if settings.database_url.startswith("sqlite"):

    @event.listens_for(engine, "connect")
    def sqlite_integrity(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=10000")


def init_db():
    from . import models  # noqa: F401

    Base.metadata.create_all(engine)


def set_workspace(session, workspace_id: str):
    if engine.dialect.name == "postgresql":
        session.execute(
            text("SELECT set_config('app.workspace_id', :workspace, true)"), {"workspace": workspace_id}
        )
