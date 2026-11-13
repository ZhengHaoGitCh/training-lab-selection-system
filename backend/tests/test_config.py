"""配置安全默认值测试。"""
from __future__ import annotations

from app.core.config import DEFAULT_SECRET_KEY, Settings


def _settings(**env: str) -> Settings:
    return Settings(**env)


def test_wildcard_origins_disable_credentials():
    """回归：曾固定 allow_credentials=True，配合 * 等于回显任意 Origin。"""
    settings = _settings(cors_origins='*')
    assert settings.cors_origin_list == ['*']
    assert settings.cors_allow_credentials is False


def test_explicit_origins_allow_credentials():
    settings = _settings(cors_origins='http://localhost:5173, https://a.example.com')
    assert settings.cors_origin_list == ['http://localhost:5173', 'https://a.example.com']
    assert settings.cors_allow_credentials is True


def test_blank_origins_behaves_like_wildcard():
    settings = _settings(cors_origins='')
    assert settings.cors_origin_list == ['*']
    assert settings.cors_allow_credentials is False


def test_production_warnings_flag_unsafe_defaults():
    settings = _settings(
        demo_mode=True,
        secret_key=DEFAULT_SECRET_KEY,
        enforce_time_window=False,
        cors_origins='*',
    )
    warnings = settings.production_warnings()
    assert len(warnings) == 4
    assert any('DEMO_MODE' in w for w in warnings)
    assert any('SECRET_KEY' in w for w in warnings)
    assert any('ENFORCE_TIME_WINDOW' in w for w in warnings)
    assert any('CORS_ORIGINS' in w for w in warnings)


def test_production_warnings_empty_when_hardened():
    settings = _settings(
        demo_mode=False,
        secret_key='a-real-secret',
        enforce_time_window=True,
        cors_origins='https://app.example.com',
    )
    assert settings.production_warnings() == []
