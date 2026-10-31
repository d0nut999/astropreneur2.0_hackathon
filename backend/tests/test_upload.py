"""Upload checks on files that are not in the demo set: size limit and disguised files."""
from pathlib import Path

from app.config import settings
from app.services.security_gate import check_upload


def test_oversized_file_is_blocked(tmp_path: Path):
    big = tmp_path / "huge.pdf"
    big.write_bytes(b"%PDF-1.4\n" + b"0" * (settings.max_upload_mb * 1024 * 1024 + 10))
    r = check_upload(big)
    assert not r.is_safe and r.flags[0].startswith("file_too_large")


def test_script_disguised_as_pdf_is_blocked(tmp_path: Path):
    fake = tmp_path / "cv.pdf"
    fake.write_bytes(b"#!/bin/sh\nrm -rf /\n")
    r = check_upload(fake)
    assert not r.is_safe and "file_type_not_allowed" in r.flags[0]
