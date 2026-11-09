"""pytest 共享夹具。

环境变量必须在导入 app 之前设置，所以放在模块顶层（pytest 会先加载 conftest）。
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

_TMP_DIR = Path(tempfile.mkdtemp(prefix='tls-test-'))

os.environ.setdefault('DATABASE_URL', f"sqlite:///{(_TMP_DIR / 'test.db').as_posix()}")
os.environ.setdefault('DEMO_MODE', 'true')
os.environ.setdefault('ENFORCE_TIME_WINDOW', 'false')
os.environ.setdefault('SECRET_KEY', 'test-secret-key')


@pytest.fixture(scope='session')
def app_module():
    from app.main import app

    return app


@pytest.fixture()
def client(app_module):
    from fastapi.testclient import TestClient

    with TestClient(app_module) as test_client:
        yield test_client


@pytest.fixture()
def db_session(app_module):
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def clean_database(app_module):
    """每个用例前清空业务表，保证用例互相独立。"""
    from app import models
    from app.core.database import Base, engine

    Base.metadata.create_all(bind=engine)
    for model in (
        models.AuditLog,
        models.Appeal,
        models.Publication,
        models.Offer,
        models.Interview,
        models.Intention,
        models.User,
        models.Round,
        models.Mentor,
        models.Lab,
    ):
        with engine.begin() as conn:
            conn.execute(model.__table__.delete())
    yield
