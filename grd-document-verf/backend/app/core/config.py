from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_ROOT.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BACKEND_ROOT / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "mysql+pymysql://grd:grd@localhost:3306/grd_document_verf"
    redis_url: str = "redis://localhost:6379/0"
    rate_limit_enabled: bool = True
    rate_limit_fail_open: bool = False
    rate_limit_redis_timeout_seconds: float = Field(default=1.0, gt=0)
    api_rate_limit_user_requests: int = Field(default=120, gt=0)
    api_rate_limit_tenant_requests: int = Field(default=1000, gt=0)
    api_rate_limit_window_seconds: int = Field(default=60, gt=0)
    upload_rate_limit_user_requests: int = Field(default=10, gt=0)
    upload_rate_limit_tenant_requests: int = Field(default=100, gt=0)
    upload_rate_limit_window_seconds: int = Field(default=600, gt=0)
    login_rate_limit_requests: int = Field(default=10, gt=0)
    login_rate_limit_window_seconds: int = Field(default=300, gt=0)
    minio_endpoint: str = "http://localhost:9000"
    minio_access_key: str = "minioadmin"
    minio_secret_key: str = "minioadmin"
    minio_bucket_name: str = "grd-quarantine"
    minio_region: str = "us-east-1"
    storage_backend: Literal["local", "minio"] = "local"
    secret_key: SecretStr = Field(min_length=32)
    jwt_algorithm: str = "HS256"
    jwt_issuer: str = "grd-document-verification"
    jwt_audience: str = "grd-api"
    local_auth_enabled: bool = False
    local_accounts_json: SecretStr = SecretStr("[]")

    max_upload_size_bytes: int = Field(default=25 * 1024 * 1024, gt=0)
    max_document_pages: int = Field(default=100, gt=0)
    max_files_per_case: int = Field(default=20, gt=0)
    upload_chunk_size_bytes: int = Field(default=1024 * 1024, gt=0)
    allow_tiff_uploads: bool = False
    password_protected_pdf_policy: Literal["reject", "review"] = "reject"
    quarantine_storage_path: Path = PROJECT_ROOT / "storage" / "quarantine"
    document_expiry_enabled: bool = True
    document_retention_days: int = Field(default=30, gt=0)
    document_expiry_sweep_seconds: int = Field(default=3600, gt=0)
    document_expiry_batch_size: int = Field(default=100, gt=0, le=1000)

    malware_scan_enabled: bool = True
    malware_scan_fail_closed: bool = True
    clamav_command: str = "clamscan"
    malware_scan_timeout_seconds: int = Field(default=60, gt=0)
    celery_dispatch_enabled: bool = True


settings = Settings()
