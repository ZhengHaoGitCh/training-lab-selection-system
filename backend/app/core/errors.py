from __future__ import annotations

from enum import IntEnum


class ErrorCode(IntEnum):
    OK = 0
    PARAM = 1001
    AUTH = 2001
    WINDOW = 3001
    CONFLICT = 4001
    NOT_FOUND = 4004
    FORBIDDEN = 4003
    INTERNAL = 5000


_DEFAULT_STATUS = {
    ErrorCode.PARAM: 400,
    ErrorCode.AUTH: 401,
    ErrorCode.FORBIDDEN: 403,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.WINDOW: 409,
    ErrorCode.CONFLICT: 409,
    ErrorCode.INTERNAL: 500,
}


class AppError(Exception):
    """业务异常，统一由应用层转换为 {code, message, data} 响应。"""

    def __init__(self, code: ErrorCode | int, message: str, status_code: int | None = None):
        self.code = int(code)
        self.message = message
        self.status_code = status_code or _DEFAULT_STATUS.get(_as_error_code(self.code), 400)
        super().__init__(message)


def _as_error_code(code: int) -> ErrorCode | None:
    """未知错误码不做映射（回退到 400），避免构造 AppError 时抛 ValueError。"""
    try:
        return ErrorCode(code)
    except ValueError:
        return None
