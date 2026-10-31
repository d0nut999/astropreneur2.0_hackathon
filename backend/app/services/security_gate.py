"""Security gate for uploaded files."""
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GateResult:
    is_safe: bool
    flags: list[str]
    confidence: float


def check_upload(file_path: Path) -> GateResult:
    """
    Check if uploaded file is safe.
    Stub: Returns mock result. Real implementation will check:
    - File type validation
    - Hidden text/metadata
    - Prompt injection patterns
    """
    # TODO: Implement real security checks
    return GateResult(
        is_safe=True,
        flags=[],
        confidence=1.0,
    )


def find_hidden_text(file_path: Path) -> list[str]:
    """
    Find hidden text in PDF/DOCX (metadata, comments, etc).
    Stub: Returns empty list.
    """
    # TODO: Use PyMuPDF, python-docx to extract metadata
    return []
