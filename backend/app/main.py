from __future__ import annotations

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .api import admin, auth, publication, student, teacher
from .core.config import settings
from .core.database import Base, engine
from .core.errors import AppError, ErrorCode
from .core.response import fail, ok

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(name)s %(message)s')
logger = logging.getLogger('selection')

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        '把学生实训室选组选拔流程软件工程化：宣讲/开放日信息采集、平行志愿、'
        '统一面试评分、拟录取确认、分轮补录、统筹调剂、公示与入组。'
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.include_router(auth.router)
app.include_router(student.router)
app.include_router(teacher.router)
app.include_router(admin.router)
app.include_router(publication.router)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return JSONResponse(
        status_code=exc.status_code,
        content=fail(exc.code, exc.message),
    )


@app.exception_handler(RequestValidationError)
async def validation_handler(request: Request, exc: RequestValidationError):
    details = [
        {'loc': list(err.get('loc', [])), 'msg': err.get('msg', ''), 'type': err.get('type', '')}
        for err in exc.errors()
    ]
    return JSONResponse(
        status_code=422,
        content=fail(ErrorCode.PARAM, '参数校验失败', details),
    )


@app.exception_handler(IntegrityError)
async def integrity_handler(request: Request, exc: IntegrityError):
    logger.warning('integrity error: %s', exc)
    return JSONResponse(
        status_code=409,
        content=fail(ErrorCode.CONFLICT, '数据冲突：可能重复提交或违反唯一约束'),
    )


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_handler(request: Request, exc: SQLAlchemyError):
    logger.exception('database error')
    return JSONResponse(
        status_code=500,
        content=fail(ErrorCode.INTERNAL, '数据库操作失败'),
    )


@app.exception_handler(Exception)
async def unhandled_handler(request: Request, exc: Exception):
    logger.exception('unhandled error')
    return JSONResponse(
        status_code=500,
        content=fail(ErrorCode.INTERNAL, '服务器内部错误'),
    )


@app.get('/health', tags=['meta'])
def health():
    return ok({'status': 'up', 'version': settings.app_version, 'demo_mode': settings.demo_mode})


@app.get('/', tags=['meta'])
def index():
    return ok(
        {
            'name': settings.app_name,
            'version': settings.app_version,
            'docs': '/docs',
            'redoc': '/redoc',
            'health': '/health',
        }
    )
