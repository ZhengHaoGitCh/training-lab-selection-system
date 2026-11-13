from __future__ import annotations

from fastapi import APIRouter, Depends, Query, Request
from sqlalchemy.orm import Session

from ..core.config import settings
from ..core.database import get_db
from ..core.deps import client_ip, get_current_user, require_admin, write_audit
from ..core.errors import AppError, ErrorCode
from ..core.response import ok
from ..core.security import create_access_token, hash_password, verify_password
from ..models import Role, User
from ..schemas import AdminCreateUserIn, LoginIn, RegisterIn, UserOut

router = APIRouter(prefix='/auth', tags=['auth'])


def _token_payload(user: User) -> dict:
    token = create_access_token(str(user.id), {'role': user.role.value, 'no': user.student_no})
    return {
        'access_token': token,
        'token_type': 'bearer',
        'expires_in': settings.token_expire_minutes * 60,
        'user': UserOut.model_validate(user).model_dump(mode='json'),
    }


@router.post('/register')
def register(payload: RegisterIn, request: Request, db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise AppError(ErrorCode.FORBIDDEN, '注册已关闭，请使用统一身份认证登录')

    exists = db.query(User).filter(User.student_no == payload.student_no).first()
    if exists:
        raise AppError(ErrorCode.CONFLICT, '学号已注册')

    user = User(
        student_no=payload.student_no,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=Role.student,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db, actor=user, action='register', entity='user', entity_id=user.id,
        ip=client_ip(request), commit=True,
    )
    return ok(_token_payload(user), '注册成功')


@router.post('/login')
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.student_no == payload.student_no).first()
    if not user or not verify_password(payload.password, user.password_hash):
        raise AppError(ErrorCode.AUTH, '账号或密码错误')
    if not user.is_active:
        raise AppError(ErrorCode.FORBIDDEN, '账号已停用')
    return ok(_token_payload(user), '登录成功')


@router.post('/login-demo')
def login_demo(db: Session = Depends(get_db)):
    """演示登录：直接返回一个管理员与一个学生令牌，便于课程演示。"""
    if not settings.demo_mode:
        raise AppError(ErrorCode.FORBIDDEN, '演示登录已关闭')

    admin = db.query(User).filter(User.role == Role.admin).first()
    student = db.query(User).filter(User.role == Role.student).first()
    teacher = db.query(User).filter(User.role == Role.mentor).first()
    if not admin or not student or not teacher:
        raise AppError(ErrorCode.NOT_FOUND, '演示账号未初始化，请先执行 scripts/seed.py')

    return ok(
        {
            'admin': _token_payload(admin),
            'student': _token_payload(student),
            'teacher': _token_payload(teacher),
        },
        '演示账号已返回',
    )


@router.get('/me')
def me(user: User = Depends(get_current_user)):
    return ok(UserOut.model_validate(user).model_dump(mode='json'))


@router.post('/users')
def create_user(
    payload: AdminCreateUserIn,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    if db.query(User).filter(User.student_no == payload.student_no).first():
        raise AppError(ErrorCode.CONFLICT, '账号已存在')
    user = User(
        student_no=payload.student_no,
        name=payload.name,
        password_hash=hash_password(payload.password),
        role=payload.role,
        lab_id=payload.lab_id,
        email=payload.email,
        phone=payload.phone,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    write_audit(
        db, actor=actor, action='create_user', entity='user', entity_id=user.id,
        after={'student_no': user.student_no, 'role': user.role.value},
        ip=client_ip(request), commit=True,
    )
    return ok(UserOut.model_validate(user).model_dump(mode='json'))


@router.get('/users')
def list_users(
    role: Role | None = None,
    keyword: str = '',
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_admin),
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    if keyword:
        like = f'%{keyword}%'
        query = query.filter((User.name.like(like)) | (User.student_no.like(like)))
    total = query.count()
    rows = query.order_by(User.id).limit(limit).offset(offset).all()
    return ok(
        {
            'total': total,
            'limit': limit,
            'offset': offset,
            'items': [UserOut.model_validate(u).model_dump(mode='json') for u in rows],
        }
    )


@router.patch('/users/{user_id}/reset-password')
def reset_password(
    user_id: int,
    payload: LoginIn,
    db: Session = Depends(get_db),
    actor: User = Depends(require_admin),
):
    user = db.get(User, user_id)
    if not user:
        raise AppError(ErrorCode.NOT_FOUND, '用户不存在')
    user.password_hash = hash_password(payload.password)
    db.commit()
    write_audit(
        db, actor=actor, action='reset_password', entity='user', entity_id=user.id,
        ip='', commit=True,
    )
    return ok({'user_id': user.id}, '密码已重置')
