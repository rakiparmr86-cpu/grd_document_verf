from __future__ import annotations

import hashlib
import warnings
from dataclasses import dataclass
from pathlib import Path
from uuid import uuid4

import fitz
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
        final_path = root / f"{random_name}{CANONICAL_EXTENSIONS[detected_type]}"
        temporary_path.replace(final_path)
        final_path.chmod(0o600)
        return QuarantinedUpload(
            original_filename=original_filename,
            storage_key=final_path.name,
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
    if not storage_key or Path(storage_key).name != storage_key:
        raise ValueError("Invalid quarantine storage key")
    root = _quarantine_root()
    path = (root / storage_key).resolve()
    if path.parent != root:
        raise ValueError("Invalid quarantine storage key")
    return path


def delete_quarantined(storage_key: str) -> None:
    resolve_quarantined_path(storage_key).unlink(missing_ok=True)
