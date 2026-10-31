"""Turn a CV file into plain text.

Only VISIBLE text is kept: white or tiny "hidden" text is dropped here, so a hidden
instruction in a CV never even reaches the AI (the security gate reports it separately).
"""
from pathlib import Path


def parse_cv(file_path: str) -> dict:
    """Return {"raw_text": visible text, "pages": n, "format": "pdf"|"docx"}."""
    path = Path(file_path)
    with open(path, "rb") as f:
        head = f.read(4)
    if head.startswith(b"%PDF"):
        return {"raw_text": _pdf_visible_text(path), "format": "pdf"}
    if head.startswith(b"PK"):
        return {"raw_text": _docx_text(path), "format": "docx"}
    raise ValueError("Unsupported file type (only PDF and DOCX)")


def _pdf_visible_text(path: Path) -> str:
    import pymupdf

    lines = []
    with pymupdf.open(path) as doc:
        for page in doc:
            for block in page.get_text("dict")["blocks"]:
                for line in block.get("lines", []):
                    parts = []
                    for span in line.get("spans", []):
                        color = span.get("color", 0)
                        r, g, b = (color >> 16) & 255, (color >> 8) & 255, color & 255
                        if min(r, g, b) >= 235 or span.get("size", 12) < 4:
                            continue  # hidden text: skip
                        parts.append(span.get("text", ""))
                    text = "".join(parts).strip()
                    if text:
                        lines.append(text)
    return "\n".join(lines)


def _docx_text(path: Path) -> str:
    import docx

    d = docx.Document(str(path))
    return "\n".join(p.text for p in d.paragraphs if p.text.strip())
