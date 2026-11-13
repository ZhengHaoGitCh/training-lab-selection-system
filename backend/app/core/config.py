from __future__ import annotations

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_SECRET_KEY = 'change-me-in-production'


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / '.env'),
        env_file_encoding='utf-8',
        extra='ignore',
    )

    app_name: str = '实训室选组选拔系统'
    app_version: str = '0.2.0'
    database_url: str = 'sqlite:///./data/app.db'
    secret_key: str = DEFAULT_SECRET_KEY
    algorithm: str = 'HS256'
    token_expire_minutes: int = 720
    demo_mode: bool = True
    enforce_time_window: bool = False
    waitlist_min_size: int = 3
    internal_candidate_ratio: float = 0.2
    cors_origins: str = '*'

    @property
    def cors_origin_list(self) -> list[str]:
        raw = (self.cors_origins or '').strip()
        if raw in ('', '*'):
            return ['*']
        return [x.strip() for x in raw.split(',') if x.strip()]

    @property
    def cors_allow_credentials(self) -> bool:
        """通配符来源下必须关闭 credentials。

        CORS 规范禁止 `Access-Control-Allow-Origin: *` 与
        `Access-Control-Allow-Credentials: true` 同时生效；Starlette 在通配符
        模式下会回显请求方 Origin，若再允许凭证等于对任意站点开放带凭证请求。
        """
        return '*' not in self.cors_origin_list

    def production_warnings(self) -> list[str]:
        """以生产参数启动时的危险配置提示（由 main.py 在启动时记录）。"""
        problems: list[str] = []
        if self.demo_mode:
            problems.append(
                'DEMO_MODE=true：/auth/login-demo 会免密返回管理员令牌，且允许自助注册'
            )
        if self.secret_key == DEFAULT_SECRET_KEY:
            problems.append('SECRET_KEY 仍为默认占位值，JWT 可被伪造')
        if not self.enforce_time_window:
            problems.append('ENFORCE_TIME_WINDOW=false：轮次时间窗口不生效')
        if '*' in self.cors_origin_list:
            problems.append('CORS_ORIGINS=*：允许任意来源跨域访问')
        return problems


settings = Settings()
