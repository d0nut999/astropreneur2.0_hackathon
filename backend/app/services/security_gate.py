"""Security gate: checks files and text BEFORE the AI reads them."""
import re
from dataclasses import dataclass, field
from pathlib import Path

from ..config import settings

# Phrases people use to manipulate an AI ("prompt injection").
INJECTION_PATTERNS = [
    r"ignore (all |any )?(the )?(previous|prior|above|earlier) (instructions|prompts?|rules)",
    r"disregard (all |any )?(the )?(previous|prior|above) (instructions|rules)",
    r"forget (all |your )?(previous )?instructions",
    r"you are now (a|an|the) ",
    r"\bsystem (prompt|note|message|override)\b",
    r"(ai|assistant|model|llm|chatbot)[,:]? (please )?(mark|rate|rank|score|give|classify|forward|send)",
    r"(rank|rate|score) (this|me|the) candidate (as )?(#?1|first|10/10|5/5|top)",
    r"give (this candidate|me) (a )?(5/5|10/10|full marks|the (top|highest) score)",
    r"forward (all|every) (cvs?|resumes?|emails?|applications?)",
    r"mark (this|me) as (urgent|important|top priority)",
]
_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in INJECTION_PATTERNS]

ALLOWED_TYPES = {
    b"%PDF": "pdf",
    b"PK\x03\x04": "docx",  # docx is a zip
}


@dataclass
class GateResult:
    is_safe: bool
    flags: list[str] = field(default_factory=list)
    confidence: float = 1.0
    hidden_text: list[str] = field(default_factory=list)


def scan_text_for_injection(text: str) -> list[str]:
    """Return the suspicious passages found in a piece of text."""
    text = text or ""
    spans = sorted(
        (max(0, m.start() - 40), min(len(text), m.end() + 60))
        for rx in _INJECTION_RE
        for m in rx.finditer(text)
    )
    merged: list[list[int]] = []
    for start, end in spans:  # merge overlapping matches into one passage
        if merged and start <= merged[-1][1]:
            merged[-1][1] = max(merged[-1][1], end)
        else:
            merged.append([start, end])
    return [" ".join(text[a:b].split()) for a, b in merged]


def find_hidden_text(file_path: Path) -> list[str]:
    """Find text a human can't see in a PDF: white/near-white text, tiny fonts, metadata."""
    file_path = Path(file_path)
    if file_path.suffix.lower() != ".pdf":
        return []
    import pymupdf

    hidden = []
    with pymupdf.open(file_path) as doc:
        for value in (doc.metadata or {}).values():
            if value and scan_text_for_injection(str(value)):
                hidden.append(f"[metadata] {value}")
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    for span in line.get("spans", []):
                        text = span.get("text", "").strip()
                        if not text:
                            continue
                        color = span.get("color", 0)
                        r, g, b = (color >> 16) & 255, (color >> 8) & 255, color & 255
                        near_white = min(r, g, b) >= 235
                        tiny = span.get("size", 12) < 4
                        if near_white or tiny:
                            hidden.append(text)
    return hidden


def check_upload(file_path: Path) -> GateResult:
    """Check an uploaded/attached file before anything reads it."""
    file_path = Path(file_path)
    flags: list[str] = []

    size_mb = file_path.stat().st_size / (1024 * 1024)
    if size_mb > settings.max_upload_mb:
        return GateResult(False, [f"file_too_large ({size_mb:.1f} MB)"], 1.0)

    with open(file_path, "rb") as f:
        head = f.read(8)
    kind = next((k for magic, k in ALLOWED_TYPES.items() if head.startswith(magic)), None)
    if kind is None:
        return GateResult(False, ["file_type_not_allowed (only real PDF/DOCX)"], 1.0)
    if kind != file_path.suffix.lower().lstrip("."):
        flags.append("extension_mismatch")

    hidden = find_hidden_text(file_path) if kind == "pdf" else []
    if hidden:
        flags.append("hidden_text")
    visible = ""
    if kind == "pdf":
        import pymupdf
        with pymupdf.open(file_path) as doc:
            visible = "\n".join(p.get_text() for p in doc)
    if scan_text_for_injection(visible + "\n" + "\n".join(hidden)):
        flags.append("prompt_injection")

    return GateResult(is_safe=not flags, flags=flags, confidence=1.0, hidden_text=hidden)
