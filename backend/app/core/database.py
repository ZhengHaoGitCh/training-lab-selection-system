from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from .config import PROJECT_ROOT, settings

url = settings.database_url
if url.startswith('sqlite:///'):
    raw_path = url[len('sqlite:///'):]
    db_path = Path(raw_path)
    if not db_path.is_absolute():
        db_path = (PROJECT_ROOT / raw_path).resolve()
    db_path.parent.mkdir(parents=True, exist_ok=True)
    url = f'sqlite:///{db_path.as_posix()}'

if url.startswith('sqlite'):
    connect_args = {'check_same_thread': False}
    engine_options = {}
elif url.startswith('mysql'):
    connect_args = {'charset': 'utf8mb4'}
    engine_options = {'pool_pre_ping': True, 'pool_recycle': 3600}
else:
    connect_args = {}
    engine_options = {}

engine = create_engine(url, future=True, connect_args=connect_args, **engine_options)

if url.startswith('sqlite'):
    @event.listens_for(engine, 'connect')
    def _sqlite_pragma(dbapi_connection, _record):  # noqa: ANN001
        cursor = dbapi_connection.cursor()
        cursor.execute('PRAGMA foreign_keys=ON')
        cursor.execute('PRAGMA journal_mode=WAL')
        cursor.close()

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
