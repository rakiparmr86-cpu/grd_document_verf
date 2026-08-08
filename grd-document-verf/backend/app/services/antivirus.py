from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

from app.core.config import settings

EICAR_MARKER = b"EICAR-STANDARD-ANTIVIRUS-TEST-FILE"


class MalwareScanResult(str, Enum):
    CLEAN = "CLEAN"
    INFECTED = "INFECTED"
    ERROR = "ERROR"


@dataclass(frozen=True)
class ScanOutcome:
    result: MalwareScanResult
    detail: str


def scan_file(path: Path) -> ScanOutcome:
    """Scan quarantine; report scanner errors so callers can fail closed."""
    if not settings.malware_scan_enabled:
        return ScanOutcome(MalwareScanResult.ERROR, "Malware scanning is disabled")

    try:
        with path.open("rb") as source:
            if EICAR_MARKER in source.read(min(path.stat().st_size, 1024 * 1024)):
                return ScanOutcome(
                    MalwareScanResult.INFECTED, "Malware test signature detected"
                )
    except OSError:
        return ScanOutcome(
            MalwareScanResult.ERROR,
            "The quarantined file could not be opened for scanning",
        )

    executable = shutil.which(settings.clamav_command)
    if executable is None:
        return ScanOutcome(
            MalwareScanResult.ERROR, "The configured malware scanner is unavailable"
        )

    try:
        completed = subprocess.run(
            [executable, "--no-summary", str(path)],
            capture_output=True,
            text=True,
            timeout=settings.malware_scan_timeout_seconds,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return ScanOutcome(
            MalwareScanResult.ERROR, "The malware scanner failed or timed out"
        )

    if completed.returncode == 0:
        return ScanOutcome(MalwareScanResult.CLEAN, "No malware detected")
    if completed.returncode == 1:
        return ScanOutcome(MalwareScanResult.INFECTED, "Malware detected")
    return ScanOutcome(MalwareScanResult.ERROR, "The malware scanner returned an error")
