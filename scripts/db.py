"""数据库备份、恢复与 SQLite → 目标库数据迁移。

用法::

    python scripts/db.py backup
    python scripts/db.py migrate --source sqlite:///data/app.db --truncate --yes
    python scripts/db.py restore --file backups/xxx.sql --yes
"""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, create_engine, func, select, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'backend'))

from app import models  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.database import Base  # noqa: E402

DEFAULT_BACKUP_DIR = ROOT / 'backups'
DEFAULT_SOURCE = f"sqlite:///{(ROOT / 'data' / 'app.db').as_posix()}"
COPY_ORDER = (
    models.Lab,
    models.Mentor,
    models.Round,
    models.User,
    models.Intention,
    models.Interview,
    models.Offer,
    models.Publication,
    models.Appeal,
    models.AuditLog,
)


def _now() -> str:
    return datetime.now().strftime('%Y%m%d-%H%M%S')


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path
    for index in range(2, 1000):
        candidate = path.with_name(f'{path.stem}-{index}{path.suffix}')
        if not candidate.exists():
            return candidate
    raise SystemExit(f'无法生成唯一备份文件名: {path}')


def _resolve_url(raw: str) -> URL:
    url = make_url(raw)
    if url.drivername.startswith('sqlite') and url.database and url.database != ':memory:':
        path = Path(url.database)
        if not path.is_absolute():
            path = (ROOT / path).resolve()
        url = url.set(database=path.as_posix())
    return url


def _make_engine(url: URL) -> Engine:
    options: dict = {'future': True}
    if url.drivername.startswith('sqlite'):
        options['connect_args'] = {'check_same_thread': False}
    elif url.drivername.startswith('mysql'):
        options['connect_args'] = {'charset': 'utf8mb4'}
        options['pool_pre_ping'] = True
    return create_engine(url, **options)


def _sqlite_file(url: URL) -> Path:
    if not url.drivername.startswith('sqlite'):
        raise SystemExit('该操作需要 SQLite 数据库')
    if not url.database or url.database == ':memory:':
        raise SystemExit('SQLite 内存库无法备份或恢复')
    return Path(url.database)


def _sqlite_source(url: URL) -> Path:
    path = _sqlite_file(url)
    if not path.exists():
        raise SystemExit(f'SQLite 数据库不存在: {path}')
    return path


def _mysql_parts(url: URL) -> dict[str, str]:
    if not url.database:
        raise SystemExit('MySQL URL 缺少数据库名')
    return {
        'host': url.host or '127.0.0.1',
        'port': str(url.port or 3306),
        'user': url.username or 'root',
        'password': url.password or os.environ.get('MYSQL_PWD', ''),
        'database': url.database,
    }


def _mysql_env(password: str) -> dict[str, str]:
    env = os.environ.copy()
    if password:
        env['MYSQL_PWD'] = password
    else:
        env.pop('MYSQL_PWD', None)
    return env


def _find_tool(name: str, explicit: str | None = None) -> str:
    if explicit:
        path = Path(explicit)
        if path.exists():
            return str(path)
        raise SystemExit(f'指定的 {name} 不存在: {path}')

    found = shutil.which(name)
    if found:
        return found

    suffixes = ['.exe', ''] if os.name == 'nt' else ['']
    roots = [
        os.environ.get('MYSQL_HOME'),
        os.environ.get('MYSQL_BIN'),
        r'C:\Program Files\MySQL\MySQL Server 8.0\bin',
        r'D:\Program Files\MySQL\MySQL Server 8.0\bin',
        '/usr/bin',
        '/usr/local/mysql/bin',
    ]
    for root in roots:
        if not root:
            continue
        for suffix in suffixes:
            candidate = Path(root) / f'{name}{suffix}'
            if candidate.exists():
                return str(candidate)
    raise SystemExit(f'未找到 {name}，请用 --{name}-path 指定路径')


def _table_counts(connection) -> dict[str, int]:  # noqa: ANN001
    return {
        model.__tablename__: connection.execute(
            select(func.count()).select_from(model.__table__)
        ).scalar()
        or 0
        for model in COPY_ORDER
    }


def _set_mysql_fk(connection, enabled: bool) -> None:  # noqa: ANN001
    connection.execute(text(f'SET FOREIGN_KEY_CHECKS={1 if enabled else 0}'))


def backup_database(
    raw_url: str,
    output_dir: Path,
    prefix: str = 'backup',
    mysqldump_path: str | None = None,
) -> Path:
    url = _resolve_url(raw_url)
    output_dir.mkdir(parents=True, exist_ok=True)

    if url.drivername.startswith('sqlite'):
        source = _sqlite_source(url)
        destination = _unique_path(
            output_dir / f'{prefix}-sqlite-{source.stem}-{_now()}.db'
        )
        with sqlite3.connect(source) as src, sqlite3.connect(destination) as dst:
            src.backup(dst)
        return destination

    if url.drivername.startswith('mysql'):
        parts = _mysql_parts(url)
        destination = _unique_path(
            output_dir / f"{prefix}-mysql-{parts['database']}-{_now()}.sql"
        )
        tool = _find_tool('mysqldump', mysqldump_path)
        command = [
            tool,
            f"--host={parts['host']}",
            f"--port={parts['port']}",
            f"--user={parts['user']}",
            '--default-character-set=utf8mb4',
            '--single-transaction',
            '--routines',
            '--triggers',
            '--no-tablespaces',
            '--set-gtid-purged=OFF',
            parts['database'],
        ]
        with destination.open('wb') as output:
            result = subprocess.run(
                command,
                stdout=output,
                stderr=subprocess.PIPE,
                env=_mysql_env(parts['password']),
                check=False,
            )
        if result.returncode != 0 or destination.stat().st_size == 0:
            destination.unlink(missing_ok=True)
            message = result.stderr.decode('utf-8', 'replace').strip()
            raise SystemExit(f'mysqldump 失败: {message[-800:]}')
        return destination

    raise SystemExit(f'不支持的数据库类型: {url.drivername}')


def restore_database(
    raw_url: str,
    backup_file: Path,
    *,
    yes: bool,
    output_dir: Path,
    mysql_path: str | None = None,
    mysqldump_path: str | None = None,
) -> Path | None:
    if not yes:
        raise SystemExit('恢复会覆盖当前数据库，请确认后加 --yes')
    if not backup_file.exists() or backup_file.stat().st_size == 0:
        raise SystemExit(f'备份文件不存在或为空: {backup_file}')

    url = _resolve_url(raw_url)
    output_dir.mkdir(parents=True, exist_ok=True)

    if url.drivername.startswith('sqlite'):
        target = _sqlite_file(url)
        target.parent.mkdir(parents=True, exist_ok=True)
        pre_backup = None
        if target.exists():
            pre_backup = backup_database(raw_url, output_dir, prefix='pre-restore')
        try:
            with sqlite3.connect(backup_file) as src, sqlite3.connect(target) as dst:
                src.backup(dst)
        except sqlite3.DatabaseError as exc:
            raise SystemExit(f'备份文件不是有效的 SQLite 数据库: {backup_file}') from exc
        return pre_backup

    if url.drivername.startswith('mysql'):
        parts = _mysql_parts(url)
        pre_backup = backup_database(
            raw_url,
            output_dir,
            prefix='pre-restore',
            mysqldump_path=mysqldump_path,
        )
        tool = _find_tool('mysql', mysql_path)
        command = [
            tool,
            f"--host={parts['host']}",
            f"--port={parts['port']}",
            f"--user={parts['user']}",
            '--default-character-set=utf8mb4',
            parts['database'],
        ]
        with backup_file.open('rb') as source:
            result = subprocess.run(
                command,
                stdin=source,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=_mysql_env(parts['password']),
                check=False,
            )
        if result.returncode != 0:
            message = result.stderr.decode('utf-8', 'replace').strip()
            raise SystemExit(f'mysql 恢复失败: {message[-800:]}')
        return pre_backup

    raise SystemExit(f'不支持的数据库类型: {url.drivername}')


def migrate_database(
    source_raw: str,
    target_raw: str,
    *,
    truncate: bool,
    yes: bool,
    dry_run: bool,
    backup_before: bool,
    output_dir: Path,
    mysqldump_path: str | None = None,
) -> dict[str, int]:
    source_url = _resolve_url(source_raw)
    target_url = _resolve_url(target_raw)
    if source_url == target_url:
        raise SystemExit('源库和目标库相同，拒绝迁移')
    if source_url.drivername.startswith('sqlite'):
        _sqlite_source(source_url)

    source_engine = _make_engine(source_url)
    try:
        with source_engine.connect() as source_connection:
            source_counts = _table_counts(source_connection)
    except SQLAlchemyError as exc:
        raise SystemExit(f'读取源库失败，请确认已运行 seed.py: {exc}') from exc

    if dry_run:
        return source_counts

    target_engine = _make_engine(target_url)
    Base.metadata.create_all(bind=target_engine)

    with target_engine.connect() as target_connection:
        target_counts = _table_counts(target_connection)
    target_has_data = any(target_counts.values())

    if target_has_data and not truncate:
        raise SystemExit('目标库已有数据；如需覆盖请加 --truncate --yes')
    if truncate and target_has_data and not yes:
        raise SystemExit('--truncate 会清空目标业务表，请加 --yes')
    if truncate and target_has_data and backup_before:
        pre_backup = backup_database(
            target_raw,
            output_dir,
            prefix='pre-migrate',
            mysqldump_path=mysqldump_path,
        )
        print(f'迁移前备份: {pre_backup}')

    with source_engine.connect() as source_connection, target_engine.begin() as target_connection:
        if truncate:
            if target_url.drivername.startswith('mysql'):
                _set_mysql_fk(target_connection, False)
            try:
                for model in reversed(COPY_ORDER):
                    target_connection.execute(model.__table__.delete())
            finally:
                if target_url.drivername.startswith('mysql'):
                    _set_mysql_fk(target_connection, True)

        for model in COPY_ORDER:
            rows = source_connection.execute(
                select(model.__table__)
            ).mappings().all()
            if rows:
                target_connection.execute(
                    model.__table__.insert(),
                    [dict(row) for row in rows],
                )

        migrated_counts = _table_counts(target_connection)
        mismatches = {
            name: (source_counts[name], migrated_counts[name])
            for name in source_counts
            if source_counts[name] != migrated_counts[name]
        }
        if mismatches:
            raise SystemExit(f'迁移后行数不一致，已回滚: {mismatches}')

    source_engine.dispose()
    target_engine.dispose()
    return migrated_counts


def command_backup(args: argparse.Namespace) -> None:
    raw_url = args.database_url or settings.database_url
    path = backup_database(
        raw_url,
        Path(args.output_dir),
        prefix=args.prefix,
        mysqldump_path=args.mysqldump_path,
    )
    print(f'备份完成: {path} ({path.stat().st_size} bytes)')


def command_restore(args: argparse.Namespace) -> None:
    raw_url = args.database_url or settings.database_url
    pre_backup = restore_database(
        raw_url,
        Path(args.file),
        yes=args.yes,
        output_dir=Path(args.output_dir),
        mysql_path=args.mysql_path,
        mysqldump_path=args.mysqldump_path,
    )
    if pre_backup:
        print(f'恢复前备份: {pre_backup}')
    url = _resolve_url(raw_url)
    print(f'恢复完成: {args.file} -> {url.render_as_string(hide_password=True)}')


def command_migrate(args: argparse.Namespace) -> None:
    target_raw = args.target or settings.database_url
    source_display = _resolve_url(args.source).render_as_string(hide_password=True)
    target_display = _resolve_url(target_raw).render_as_string(hide_password=True)
    print(f'源库: {source_display}')
    print(f'目标库: {target_display}')

    counts = migrate_database(
        args.source,
        target_raw,
        truncate=args.truncate,
        yes=args.yes,
        dry_run=args.dry_run,
        backup_before=not args.no_backup,
        output_dir=Path(args.output_dir),
        mysqldump_path=args.mysqldump_path,
    )
    if args.dry_run:
        print('干跑完成，源库行数：')
    else:
        print('迁移完成，目标库行数：')
    for name, count in counts.items():
        print(f'  {name}: {count}')


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description='数据库备份、恢复与数据迁移')
    subparsers = parser.add_subparsers(dest='command', required=True)

    backup = subparsers.add_parser('backup', help='备份当前 DATABASE_URL 指向的数据库')
    backup.add_argument('--database-url', help='默认取 .env 的 DATABASE_URL')
    backup.add_argument('--output-dir', default=str(DEFAULT_BACKUP_DIR))
    backup.add_argument('--prefix', default='backup')
    backup.add_argument('--mysqldump-path')
    backup.set_defaults(func=command_backup)

    migrate = subparsers.add_parser('migrate', help='把 SQLite 数据迁移到目标库')
    migrate.add_argument('--source', default=DEFAULT_SOURCE)
    migrate.add_argument('--target', help='默认取 .env 的 DATABASE_URL')
    migrate.add_argument('--truncate', action='store_true', help='清空目标业务表后复制')
    migrate.add_argument('--yes', action='store_true', help='确认允许清空目标库')
    migrate.add_argument('--dry-run', action='store_true', help='只统计源库行数，不写入')
    migrate.add_argument('--no-backup', action='store_true', help='清空前不备份目标库')
    migrate.add_argument('--output-dir', default=str(DEFAULT_BACKUP_DIR))
    migrate.add_argument('--mysqldump-path')
    migrate.set_defaults(func=command_migrate)

    restore = subparsers.add_parser('restore', help='从备份恢复数据库')
    restore.add_argument('--file', required=True)
    restore.add_argument('--database-url', help='默认取 .env 的 DATABASE_URL')
    restore.add_argument('--yes', action='store_true', help='确认覆盖当前数据库')
    restore.add_argument('--output-dir', default=str(DEFAULT_BACKUP_DIR))
    restore.add_argument('--mysql-path')
    restore.add_argument('--mysqldump-path')
    restore.set_defaults(func=command_restore)

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == '__main__':
    main()
