from __future__ import annotations

import hashlib
import warnings
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from uuid import uuid4

import boto3
import fitz
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import UploadFile, status
from PIL import Image, UnidentifiedImageError

from app.core.config import settings
from app.schemas.document import DetectedFileType

EXTENSION_TYPES = {
    ".pdf": DetectedFileType.PDF,
    ".jpg": DetectedFileType.JPEG,
    ".jpeg": DetectedFileType.JPEG,
    ".png": DetectedFileType.PNG,
    ".tif": DetectedFileType.TIFF,
    ".tiff": DetectedFileType.TIFF,
}

CANONICAL_EXTENSIONS = {
    DetectedFileType.PDF: ".pdf",
    DetectedFileType.JPEG: ".jpg",
    DetectedFileType.PNG: ".png",
    DetectedFileType.TIFF: ".tiff",
}


class UploadValidationError(Exception):
    def __init__(
        self, detail: str, status_code: int = status.HTTP_422_UNPROCESSABLE_CONTENT
    ):
        super().__init__(detail)
        self.detail = detail
        self.status_code = status_code


class StorageOperationError(RuntimeError):
    """Raised when configured quarantine storage cannot complete an operation."""


class StorageObjectNotFoundError(StorageOperationError):
    """Raised when a quarantine object no longer exists."""


@dataclass(frozen=True)
class QuarantinedUpload:
    original_filename: str
    storage_key: str
    sha256: str
    size_bytes: int
    detected_file_type: DetectedFileType
    page_count: int
    password_protected: bool


def _safe_original_filename(filename: str | None) -> str:
    cleaned = (filename or "").replace("\\", "/").rsplit("/", 1)[-1].strip()
    if not cleaned or cleaned in {".", ".."}:
        raise UploadValidationError(
            "A filename with an allowed extension is required",
            status.HTTP_400_BAD_REQUEST,
        )
    return cleaned[:500]


def _allowed_extensions() -> set[str]:
    allowed = {".pdf", ".jpg", ".jpeg", ".png"}
    if settings.allow_tiff_uploads:
        allowed.update({".tif", ".tiff"})
    return allowed


def _detect_signature(header: bytes) -> DetectedFileType | None:
    if header.startswith(b"%PDF-"):
        return DetectedFileType.PDF
    if header.startswith(b"\xff\xd8\xff"):
        return DetectedFileType.JPEG
    if header.startswith(b"\x89PNG\r\n\x1a\n"):
        return DetectedFileType.PNG
    if header.startswith((b"II*\x00", b"MM\x00*")):
        return DetectedFileType.TIFF
    return None


def _inspect_pdf(path: Path) -> tuple[int, bool]:
    try:
        # A byte stream avoids an OS file lock if MuPDF rejects corrupt input.
        with fitz.open(stream=path.read_bytes(), filetype="pdf") as document:
            password_protected = bool(document.needs_pass)
            if (
                password_protected
                and settings.password_protected_pdf_policy == "reject"
            ):
                raise UploadValidationError("Password-protected PDFs are not accepted")
            page_count = document.page_count
            if page_count < 1:
                raise UploadValidationError("The PDF has no readable pages")
            if page_count > settings.max_document_pages:
                raise UploadValidationError(
                    (
                        f"The document exceeds the "
                        f"{settings.max_document_pages}-page limit"
                    ),
                    status.HTTP_413_CONTENT_TOO_LARGE,
                )
            if not password_protected:
                for page_number in range(page_count):
                    document.load_page(page_number)
            return page_count, password_protected
    except UploadValidationError:
        raise
    except (fitz.FileDataError, RuntimeError, ValueError):
        raise UploadValidationError(
            "The PDF is corrupted or cannot be read safely"
        ) from None


def _inspect_image(path: Path, expected: DetectedFileType) -> int:
    image_formats = {
        "JPEG": DetectedFileType.JPEG,
        "PNG": DetectedFileType.PNG,
        "TIFF": DetectedFileType.TIFF,
    }
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(path) as image:
                actual = image_formats.get(image.format or "")
                if actual != expected:
                    raise UploadValidationError(
                        "The file signature does not match its encoded image format"
                    )
                page_count = int(getattr(image, "n_frames", 1))
                if page_count < 1:
                    raise UploadValidationError("The image has no readable pages")
                if page_count > settings.max_document_pages:
                    raise UploadValidationError(
                        (
                            f"The document exceeds the "
                            f"{settings.max_document_pages}-page limit"
                        ),
                        status.HTTP_413_CONTENT_TOO_LARGE,
                    )
                for frame_number in range(page_count):
                    image.seek(frame_number)
                    image.load()
                return page_count
    except UploadValidationError:
        raise
    except (
        Image.DecompressionBombError,
        Image.DecompressionBombWarning,
        UnidentifiedImageError,
        OSError,
        ValueError,
    ):
        raise UploadValidationError(
            "The image is corrupted or cannot be read safely"
        ) from None


def _inspect_file(
    path: Path, extension: str, header: bytes
) -> tuple[DetectedFileType, int, bool]:
    expected = EXTENSION_TYPES[extension]
    detected = _detect_signature(header)
    if detected is None:
        raise UploadValidationError(
            "The actual file type is not allowed",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    if detected != expected:
        raise UploadValidationError(
            "The file extension does not match the actual file type",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )
    if detected == DetectedFileType.PDF:
        page_count, password_protected = _inspect_pdf(path)
        return detected, page_count, password_protected
    return detected, _inspect_image(path, detected), False


def _quarantine_root() -> Path:
    root = settings.quarantine_storage_path.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    root.chmod(0o700)
    return root


def _validate_storage_key(storage_key: str) -> str:
    if not storage_key or Path(storage_key).name != storage_key:
        raise ValueError("Invalid quarantine storage key")
    return storage_key


@lru_cache(maxsize=4)
def _create_s3_client(
    endpoint: str,
    access_key: str,
    secret_key: str,
    region: str,
):
    return boto3.client(
        "s3",
        endpoint_url=endpoint,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=Config(
            signature_version="s3v4",
            connect_timeout=5,
            read_timeout=60,
            retries={"max_attempts": 3, "mode": "standard"},
        ),
    )


def _minio_client():
    return _create_s3_client(
        settings.minio_endpoint,
        settings.minio_access_key,
        settings.minio_secret_key,
        settings.minio_region,
    )


def _is_not_found(exc: ClientError) -> bool:
    code = str(exc.response.get("Error", {}).get("Code", ""))
    status_code = exc.response.get("ResponseMetadata", {}).get("HTTPStatusCode")
    return (
        code in {"404", "NoSuchBucket", "NoSuchKey", "NotFound"}
        or status_code == 404
    )


def _ensure_minio_bucket() -> None:
    client = _minio_client()
    try:
        client.head_bucket(Bucket=settings.minio_bucket_name)
        return
    except ClientError as exc:
        if not _is_not_found(exc):
            raise StorageOperationError("MinIO quarantine bucket is unavailable") from exc
    except BotoCoreError as exc:
        raise StorageOperationError("MinIO quarantine service is unavailable") from exc

    create_args: dict = {"Bucket": settings.minio_bucket_name}
    if settings.minio_region != "us-east-1":
        create_args["CreateBucketConfiguration"] = {
            "LocationConstraint": settings.minio_region
        }
    try:
        client.create_bucket(**create_args)
    except (BotoCoreError, ClientError) as exc:
        raise StorageOperationError("MinIO quarantine bucket could not be created") from exc


def _store_in_minio(
    source: Path,
    storage_key: str,
    detected_type: DetectedFileType,
    sha256: str,
) -> None:
    content_types = {
        DetectedFileType.PDF: "application/pdf",
        DetectedFileType.JPEG: "image/jpeg",
        DetectedFileType.PNG: "image/png",
        DetectedFileType.TIFF: "image/tiff",
    }
    _ensure_minio_bucket()
    try:
        _minio_client().upload_file(
            str(source),
            settings.minio_bucket_name,
            storage_key,
            ExtraArgs={
                "ContentType": content_types[detected_type],
                "Metadata": {"sha256": sha256, "state": "quarantined"},
            },
        )
    except (BotoCoreError, ClientError, OSError) as exc:
        raise StorageOperationError("The document could not be saved to MinIO") from exc


async def quarantine_upload(upload: UploadFile) -> QuarantinedUpload:
    original_filename = _safe_original_filename(upload.filename)
    extension = Path(original_filename).suffix.lower()
    if extension not in _allowed_extensions():
        formats = "PDF, JPG/JPEG, PNG" + (
            ", TIFF" if settings.allow_tiff_uploads else ""
        )
        raise UploadValidationError(
            f"Unsupported file extension. Allowed formats: {formats}",
            status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
        )

    root = _quarantine_root()
    random_name = uuid4().hex
    temporary_path = root / f"{random_name}.upload"
    digest = hashlib.sha256()
    total_size = 0
    header = b""
    max_size_mb = settings.max_upload_size_bytes // (1024 * 1024)

    try:
        with temporary_path.open("xb") as destination:
            while chunk := await upload.read(settings.upload_chunk_size_bytes):
                total_size += len(chunk)
                if total_size > settings.max_upload_size_bytes:
                    raise UploadValidationError(
                        (f"The file exceeds the {max_size_mb} MB limit"),
                        status.HTTP_413_CONTENT_TOO_LARGE,
                    )
                if len(header) < 16:
                    header = (header + chunk)[:16]
                digest.update(chunk)
                destination.write(chunk)

        if total_size == 0:
            raise UploadValidationError(
                "Empty files are not accepted", status.HTTP_400_BAD_REQUEST
            )

        detected_type, page_count, password_protected = _inspect_file(
            temporary_path, extension, header
        )
        storage_key = f"{random_name}{CANONICAL_EXTENSIONS[detected_type]}"
        if settings.storage_backend == "minio":
            _store_in_minio(
                temporary_path, storage_key, detected_type, digest.hexdigest()
            )
            temporary_path.unlink(missing_ok=True)
        else:
            final_path = root / storage_key
            temporary_path.replace(final_path)
            final_path.chmod(0o600)
        return QuarantinedUpload(
            original_filename=original_filename,
            storage_key=storage_key,
            sha256=digest.hexdigest(),
            size_bytes=total_size,
            detected_file_type=detected_type,
            page_count=page_count,
            password_protected=password_protected,
        )
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    finally:
        await upload.close()


def resolve_quarantined_path(storage_key: str) -> Path:
    _validate_storage_key(storage_key)
    if settings.storage_backend != "local":
        raise StorageOperationError(
            "MinIO objects must be materialized before local file access"
        )
    root = _quarantine_root()
    path = (root / storage_key).resolve()
    if path.parent != root:
        raise ValueError("Invalid quarantine storage key")
    return path


@contextmanager
def materialize_quarantined(storage_key: str) -> Iterator[Path]:
    """Yield a local read-only path regardless of the configured storage backend."""
    storage_key = _validate_storage_key(storage_key)
    if settings.storage_backend == "local":
        path = resolve_quarantined_path(storage_key)
        if not path.is_file():
            raise StorageObjectNotFoundError("The quarantined file does not exist")
        yield path
        return

    root = _quarantine_root()
    temporary_path = root / f"{uuid4().hex}.download"
    try:
        _minio_client().download_file(
            settings.minio_bucket_name, storage_key, str(temporary_path)
        )
        temporary_path.chmod(0o600)
        yield temporary_path
    except ClientError as exc:
        if _is_not_found(exc):
            raise StorageObjectNotFoundError(
                "The quarantined MinIO object does not exist"
            ) from exc
        raise StorageOperationError(
            "The quarantined document could not be downloaded from MinIO"
        ) from exc
    except (BotoCoreError, OSError) as exc:
        raise StorageOperationError(
            "The quarantined document could not be downloaded from MinIO"
        ) from exc
    finally:
        temporary_path.unlink(missing_ok=True)


def quarantined_exists(storage_key: str) -> bool:
    storage_key = _validate_storage_key(storage_key)
    if settings.storage_backend == "local":
        return resolve_quarantined_path(storage_key).is_file()
    try:
        _minio_client().head_object(
            Bucket=settings.minio_bucket_name, Key=storage_key
        )
        return True
    except ClientError as exc:
        if _is_not_found(exc):
            return False
        raise StorageOperationError(
            "The MinIO quarantine object could not be checked"
        ) from exc
    except BotoCoreError as exc:
        raise StorageOperationError(
            "The MinIO quarantine service is unavailable"
        ) from exc


def delete_quarantined(storage_key: str) -> None:
    storage_key = _validate_storage_key(storage_key)
    if settings.storage_backend == "local":
        resolve_quarantined_path(storage_key).unlink(missing_ok=True)
        return
    try:
        _minio_client().delete_object(
            Bucket=settings.minio_bucket_name, Key=storage_key
        )
    except (BotoCoreError, ClientError) as exc:
        raise StorageOperationError(
            "The quarantined MinIO object could not be deleted"
        ) from exc
