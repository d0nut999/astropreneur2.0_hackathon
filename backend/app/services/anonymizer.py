"""Remove personal information from a CV before the AI scores it (fairness).

Removed: the candidate's name, emails, phone numbers, links, address/birth/age/gender/
nationality/marital-status lines. HR still sees the full identity on the candidate page.
"""
import re

PERSONAL_LINE = re.compile(
    r"^\s*(address|adresse|date of birth|birth ?date|born|age|gender|sex|nationality|"
    r"marital status|family status|religion|photo|place of birth)\b.*$",
    re.IGNORECASE | re.MULTILINE,
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(\+?\d[\d\s().-]{7,}\d)")
URL = re.compile(r"(https?://\S+|www\.\S+|linkedin\.com/\S+)", re.IGNORECASE)
AGE = re.compile(r"\b\d{2}\s?(years old|ans)\b", re.IGNORECASE)
GENDER_WORDS = re.compile(r"\b(male|female|mr\.?|mrs\.?|ms\.?|miss|he/him|she/her)\b", re.IGNORECASE)


def anonymize_text(text: str, candidate_name: str = "") -> tuple[str, list[str]]:
    """Return (anonymized_text, list of what was removed)."""
    removed: list[str] = []

    def sub(rx, label, s):
        def repl(m):
            removed.append(f"{label}: {m.group(0).strip()[:60]}")
            return f"[{label} removed]"
        return rx.sub(repl, s)

    out = text
    out = sub(PERSONAL_LINE, "personal info", out)
    out = sub(EMAIL, "email", out)
    out = sub(URL, "link", out)
    out = sub(PHONE, "phone", out)
    out = sub(AGE, "age", out)
    out = sub(GENDER_WORDS, "gender", out)

    for part in sorted({p for p in re.split(r"[\s\-]+", candidate_name or "") if len(p) >= 3}, key=len, reverse=True):
        rx = re.compile(rf"\b{re.escape(part)}\b", re.IGNORECASE)
        if rx.search(out):
            removed.append(f"name: {part}")
            out = rx.sub("[name]", out)
    return out, removed


def anonymize_profile(parsed_cv: dict, candidate_name: str = "") -> dict:
    """Kept for compatibility with TEAM_GUIDE: returns {"text", "removed"}."""
    text, removed = anonymize_text(parsed_cv.get("raw_text", ""), candidate_name)
    return {"text": text, "removed": removed}
