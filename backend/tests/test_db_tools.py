"""数据库备份、迁移、恢复脚本测试（只使用临时 SQLite，不依赖 MySQL）。"""
from __future__ import annotations

import sys
from datetime import datetime
from pathlib import Path

import pytest
from sqlalchemy import create_engine, func, select

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts import db as db_tools  # noqa: E402

from app import models  # noqa: E402
from app.core.database import Base  # noqa: E402


def _url(path: Path) -> str:
    return f'sqlite:///{path.as_posix()}'


def _seed(path: Path) -> None:
    engine = create_engine(_url(path), future=True)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as connection:
        connection.execute(
            models.Lab.__table__.insert(),
            {
                'name': '测试实训室',
                'capacity': 2,
                'direction': '测试',
                'description': '',
                'open_day_at': None,
            },
        )
        connection.execute(
            models.Round.__table__.insert(),
            {
                'name': '测试轮次',
                'kind': models.RoundKind.intention,
                'round_no': 1,
                'starts_at': datetime(2026, 1, 1, 8, 0),
                'ends_at': datetime(2026, 1, 1, 12, 0),
            },
        )


def _count(path: Path, model) -> int:  # noqa: ANN001
    engine = create_engine(_url(path), future=True)
    with engine.connect() as connection:
        return connection.execute(
            select(func.count()).select_from(model.__table__)
        ).scalar() or 0


def test_sqlite_backup_and_restore(tmp_path: Path) -> None:
    source = tmp_path / 'source.db'
    _seed(source)

    backup_file = db_tools.backup_database(
        _url(source), tmp_path / 'backups', prefix='test'
    )
    assert backup_file.exists()
    assert backup_file.suffix == '.db'

    engine = create_engine(_url(source), future=True)
    with engine.begin() as connection:
        connection.execute(models.Lab.__table__.delete())
    assert _count(source, models.Lab) == 0

    pre_backup = db_tools.restore_database(
        _url(source),
        backup_file,
        yes=True,
        output_dir=tmp_path / 'backups',
    )
    assert pre_backup is not None and pre_backup.exists()
    assert _count(source, models.Lab) == 1


def test_migrate_sqlite_to_sqlite(tmp_path: Path) -> None:
    source = tmp_path / 'source.db'
    target = tmp_path / 'target.db'
    _seed(source)

    counts = db_tools.migrate_database(
        _url(source),
        _url(target),
        truncate=False,
        yes=False,
        dry_run=False,
        backup_before=True,
        output_dir=tmp_path / 'backups',
    )
    assert counts['labs'] == 1
    assert counts['rounds'] == 1
    assert counts['users'] == 0
    assert _count(target, models.Lab) == 1


def test_migrate_refuses_non_empty_target_without_truncate(tmp_path: Path) -> None:
    source = tmp_path / 'source.db'
    target = tmp_path / 'target.db'
    _seed(source)
    db_tools.migrate_database(
        _url(source),
        _url(target),
        truncate=False,
        yes=False,
        dry_run=False,
        backup_before=True,
        output_dir=tmp_path / 'backups',
    )

    with pytest.raises(SystemExit):
        db_tools.migrate_database(
            _url(source),
            _url(target),
            truncate=False,
            yes=False,
            dry_run=False,
            backup_before=True,
            output_dir=tmp_path / 'backups',
        )
