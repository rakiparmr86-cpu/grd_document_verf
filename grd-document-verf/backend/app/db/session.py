from collections.abc import Generator

from sqlalchemy import create_engine, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import settings
from app.db.base import Base
from app.schemas.case import DocumentStatus


def _create_engine() -> Engine:
    if settings.database_url.startswith("sqlite"):
        return create_engine(
            settings.database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
    return create_engine(settings.database_url, pool_pre_ping=True)


engine = _create_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    # The API imports its mapped models before application startup.
    Base.metadata.create_all(bind=engine)
    _ensure_document_schema_compatibility()


def _ensure_document_schema_compatibility() -> None:
    """Apply the small additive migration required by pre-feature MySQL installs."""
    if engine.dialect.name != "mysql":
        return

    with engine.begin() as connection:
        inspector = inspect(connection)
        if "documents" not in inspector.get_table_names():
            return

        columns = {
            column["name"]: column
            for column in inspector.get_columns("documents")
        }
        if "storage_deleted_at" not in columns:
            connection.exec_driver_sql(
                "ALTER TABLE documents "
                "ADD COLUMN storage_deleted_at DATETIME(6) NULL"
            )

        status_type = columns.get("status", {}).get("type")
        existing_statuses = set(getattr(status_type, "enums", ()) or ())
        required_statuses = {item.name for item in DocumentStatus}
        if not required_statuses.issubset(existing_statuses):
            enum_values = ", ".join(f"'{item.name}'" for item in DocumentStatus)
            connection.exec_driver_sql(
                "ALTER TABLE documents "
                f"MODIFY COLUMN status ENUM({enum_values}) NOT NULL"
            )

        inspector = inspect(connection)
        index_names = {
            index["name"] for index in inspector.get_indexes("documents")
        }
        if "ix_documents_storage_deleted_at" not in index_names:
            connection.exec_driver_sql(
                "CREATE INDEX ix_documents_storage_deleted_at "
                "ON documents (storage_deleted_at)"
            )


def get_db() -> Generator[Session, None, None]:
    with SessionLocal() as session:
        yield session
