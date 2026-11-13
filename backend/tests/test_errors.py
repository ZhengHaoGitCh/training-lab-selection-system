"""错误码与统一响应契约测试。"""
from __future__ import annotations

from app.core.errors import AppError, ErrorCode


def test_app_error_maps_known_codes_to_http_status():
    assert AppError(ErrorCode.PARAM, 'x').status_code == 400
    assert AppError(ErrorCode.AUTH, 'x').status_code == 401
    assert AppError(ErrorCode.FORBIDDEN, 'x').status_code == 403
    assert AppError(ErrorCode.NOT_FOUND, 'x').status_code == 404
    assert AppError(ErrorCode.WINDOW, 'x').status_code == 409
    assert AppError(ErrorCode.CONFLICT, 'x').status_code == 409
    assert AppError(ErrorCode.INTERNAL, 'x').status_code == 500


def test_app_error_accepts_plain_int_code():
    """int 与 ErrorCode 等价。"""
    err = AppError(1001, '参数错误')
    assert err.code == 1001
    assert err.status_code == 400


def test_app_error_with_unknown_code_falls_back_to_400():
    """回归：曾用 ``ErrorCode(self.code)`` 查表，未知码会抛 ValueError。"""
    err = AppError(1234, '自定义码')
    assert err.code == 1234
    assert err.status_code == 400


def test_app_error_explicit_status_code_wins():
    err = AppError(ErrorCode.CONFLICT, '冲突', status_code=422)
    assert err.status_code == 422


def test_app_error_message_is_preserved():
    err = AppError(ErrorCode.NOT_FOUND, '轮次 9 不存在')
    assert err.message == '轮次 9 不存在'
    assert str(err) == '轮次 9 不存在'
