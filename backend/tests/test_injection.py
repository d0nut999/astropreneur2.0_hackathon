"""Security gate tests on real files from demo_data/cvs."""
from pathlib import Path

from app.services.security_gate import check_upload

CVS = Path(__file__).resolve().parents[1] / "demo_data" / "cvs"


def test_clean_cv_passes():
    r = check_upload(CVS / "cv_strong_sara_ben_ali.pdf")
    assert r.is_safe and r.flags == []


def test_hidden_white_text_injection_is_caught():
    r = check_upload(CVS / "cv_EVIL_hidden_injection.pdf")
    assert not r.is_safe
    assert "hidden_text" in r.flags and "prompt_injection" in r.flags
    assert any("Ignore all previous instructions" in t for t in r.hidden_text)


def test_exe_renamed_to_pdf_is_blocked():
    r = check_upload(CVS / "fake_cv_really_an_exe.pdf")
    assert not r.is_safe
    assert r.flags[0].startswith("file_type_not_allowed")
