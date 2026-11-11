from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Iterable

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from ..models import AuditLog, Role, Round, User
from .config import settings
from .database import get_db
from .clock import utcnow
from .errors import AppError, ErrorCode
from .security import JWTError, decode_access_token

bearer = HTTPBearer(auto_error=False)


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: Session = Depends(get_db),
) -> User:
    token = credentials.credentials if credentials else None
    if not token:
        raise AppError(ErrorCode.AUTH, '未登录或令牌缺失')

    try:
        payload = decode_access_token(token)
    except JWTError:
        raise AppError(ErrorCode.AUTH, '令牌无效或已过期') from None

    subject = payload.get('sub')
    user = db.get(User, int(subject)) if subject and str(subject).isdigit() else None
    if not user or not user.is_active:
        raise AppError(ErrorCode.AUTH, '用户不存在或已停用')
    request.state.user = user
    return user


def require_roles(*roles: Role):
    allowed = set(roles)

    def dependency(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed:
            raise AppError(ErrorCode.FORBIDDEN, '无权访问该资源')
        return user

    return dependency


require_admin = require_roles(Role.admin)


def get_current_student(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.student:
        raise AppError(ErrorCode.FORBIDDEN, '仅学生可执行该操作')
    return user


def get_current_mentor(user: User = Depends(get_current_user)) -> User:
    if user.role != Role.mentor:
        raise AppError(ErrorCode.FORBIDDEN, '仅老师可执行该操作')
    if not user.mentor_id:
        raise AppError(ErrorCode.FORBIDDEN, '老师账号未绑定导师档案')
    return user


def client_ip(request: Request) -> str:
    forwarded = request.headers.get('x-forwarded-for')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.client.host if request.client else ''


def write_audit(
    db: Session,
    *,
    actor: User | None,
    action: str,
    entity: str = '',
    entity_id: int = 0,
    before: Any = None,
    after: Any = None,
    ip: str = '',
    commit: bool = False,
) -> AuditLog:
    log = AuditLog(
        actor=actor.student_no if actor else 'system',
        actor_id=actor.id if actor else None,
        action=action,
        entity=entity,
        entity_id=entity_id or 0,
        before_json=json.dumps(before, ensure_ascii=False, default=str) if before is not None else '',
        after_json=json.dumps(after, ensure_ascii=False, default=str) if after is not None else '',
        ip=ip,
    )
    db.add(log)
    if commit:
        db.commit()
    return log


def find_round(db: Session, round_id: int) -> Round:
    round_obj = db.get(Round, round_id)
    if not round_obj:
        raise AppError(ErrorCode.NOT_FOUND, f'轮次 {round_id} 不存在')
    return round_obj


def ensure_in_window(
    db: Session,
    round_id: int,
    *,
    now: datetime | None = None,
    action: str = '当前操作',
) -> Round:
    """校验轮次是否开放。ENFORCE_TIME_WINDOW=false 时仅记录不拦截（便于演练）。"""
    round_obj = find_round(db, round_id)
    if not settings.enforce_time_window:
        return round_obj
    now = now or utcnow()
    if not (round_obj.starts_at <= now <= round_obj.ends_at):
        raise AppError(
            ErrorCode.WINDOW,
            f'{action}不在开放时间内（{round_obj.starts_at:%Y-%m-%d %H:%M} ~ {round_obj.ends_at:%Y-%m-%d %H:%M}）',
        )
    return round_obj


def ensure_no_duplicate(values: Iterable[int], message: str) -> None:
    values = list(values)
    if len(set(values)) != len(values):
        raise AppError(ErrorCode.PARAM, message)
