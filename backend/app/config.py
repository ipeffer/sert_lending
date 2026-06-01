from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_env: str = "development"
    app_secret: str = "dev-secret"
    public_base_url: str = "http://localhost:3000"
    api_base_url: str = "http://localhost:8000"

    database_url: str = "postgresql+asyncpg://k8cert:change-me@localhost:5432/k8certificates"

    admin_username: str = "admin"
    admin_password: str = "change-me-admin"
    admin_ip_allowlist: str = ""

    reserve_ttl_minutes: int = 30

    payment_provider: str = "mock"  # mock | yookassa
    yookassa_shop_id: str = ""
    yookassa_secret_key: str = ""
    yookassa_return_url: str = "http://localhost:3000/payment/success"
    # Comma-separated YooKassa notification IPs (empty = skip check)
    yookassa_webhook_ips: str = "185.71.76.0/27,185.71.77.0/27,77.75.153.0/25,77.75.156.11,77.75.156.35,77.75.153.1"

    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from: str = "noreply@k8.ru"
    smtp_use_tls: bool = True

    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def admin_ips(self) -> list[str]:
        if not self.admin_ip_allowlist.strip():
            return []
        return [ip.strip() for ip in self.admin_ip_allowlist.split(",") if ip.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
