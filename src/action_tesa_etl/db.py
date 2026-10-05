from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine, make_url
from sqlalchemy.orm import Session, sessionmaker

from action_tesa_etl.config import PROJECT_ROOT, settings
from action_tesa_etl.models import Base


def resolve_database_url(database_url: str | None = None) -> str:
    raw = database_url or settings.database_url
    if "://" not in raw:
        raw = f"sqlite:///{raw}"

    url = make_url(raw)
    if url.get_backend_name() != "sqlite":
        return raw

    database = url.database
    if not database or database == ":memory:":
        return raw

    path = Path(database)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.parent.mkdir(parents=True, exist_ok=True)
    return str(url.set(database=str(path.resolve())))


def make_engine(database_url: str | None = None) -> Engine:
    url = resolve_database_url(database_url)
    engine = create_engine(url)
    if engine.dialect.name == "sqlite":

        @event.listens_for(engine, "connect")
        def _enable_foreign_keys(dbapi_conn, _connection_record) -> None:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)


def session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine)
