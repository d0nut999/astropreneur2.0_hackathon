"""Score a candidate's CV against the job rubric.

Safety design:
- The AI only sees VISIBLE, ANONYMIZED text (no hidden text, no name/age/gender...).
- The AI gives a score per criterion WITH a quote. Code checks the quote is really in the CV;
  if not, that criterion gets 0 ("unsupported claim") -> the AI cannot invent qualifications.
- The TOTAL is computed here in Python, not by the AI.
- If the AI is unavailable, an offline keyword scorer is used (marked as such).
"""
import re
from datetime import datetime
from pathlib import Path

from rapidfuzz import fuzz
from sqlmodel import Session

from ..audit import log_audit
from ..config import settings
from ..llm import LLMError, complete_json
from ..models import Application, ApplicationStatus, Candidate, Job, Score
from ..schemas import CriterionScore, CVScoring
from ..state_machine import transition
from .anonymizer import anonymize_text
from .parser import parse_cv
from .rubric import normalize_rubric
from .security_gate import scan_text_for_injection

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "score_cv.md"
PROMPT_VERSION = "score_v1"
MUST_HAVE_CAP = 40  # max total if a must-have criterion is missing


def evidence_is_real(evidence: str, text: str) -> bool:
    """Anti-hallucination: the quote must exist in the CV (small differences allowed)."""
    ev = " ".join(evidence.lower().split())
    if len(ev) < 4:
        return False
    cv = " ".join(text.lower().split())
    return ev in cv or fuzz.partial_ratio(ev, cv) >= 90


def score_candidate(anonymized_text: str, rubric: list[dict], job: Job, db: Session | None = None) -> tuple[CVScoring, str]:
    """Return (scoring, source) with source "ai" or "offline"."""
    try:
        return _score_with_ai(anonymized_text, rubric, job, db), "ai"
    except LLMError as e:
        print(f"[scorer] AI unavailable, using offline keyword scorer: {e}")
        return score_offline(anonymized_text, rubric), "offline"


def _score_with_ai(text: str, rubric: list[dict], job: Job, db: Session | None) -> CVScoring:
    crit_lines = "\n".join(
        f'- "{c["key"]}": {c["label"]}{" (MUST-HAVE)" if c["must_have"] else ""} — {c["description"]}'
        for c in rubric
    )
    user = (
        f"<job>\n{job.title}\n{job.description[:3000]}\n</job>\n\n"
        f"<criteria>\n{crit_lines}\n</criteria>\n\n"
        f"<resume_data>\n{text[:10000]}\n</resume_data>"
    )
    return complete_json(task="score_cv", system=PROMPT_PATH.read_text(encoding="utf-8"), user=user,
                         schema=CVScoring, prompt_version=PROMPT_VERSION, db=db)


def score_offline(text: str, rubric: list[dict]) -> CVScoring:
    """Simple, explainable keyword scorer used when no AI is available."""
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    low = text.lower()
    criteria = {}
    for c in rubric:
        hits = [k for k in c.get("keywords", []) if re.search(rf"\b{re.escape(k)}", low)]
        score = min(5, len(hits) + 1) if hits else 0
        evidence = ""
        if hits:
            # prefer a real sentence over a section title like "PROJECTS"
            matching = [l for l in lines if any(h in l.lower() for h in hits)]
            good = [l for l in matching if len(l) > 15 and not l.isupper()]
            evidence = (good or matching or [""])[0][:150]
        reason = f"Mentions: {', '.join(hits[:4])}" if hits else "Nothing found for this criterion"
        criteria[c["key"]] = CriterionScore(score=score, evidence=evidence, reason=reason)
    return CVScoring(criteria=criteria, summary="Scored offline by keyword matching (no AI available).")


def score_application(db: Session, app: Application, actor: str = "ai") -> Score:
    """Parse -> anonymize -> score -> verify evidence -> compute total -> save. Moves SCREENED -> SCORED."""
    if app.status == ApplicationStatus.QUARANTINED:
        raise ValueError("This CV is quarantined by the security gate and will not be scored.")
    if not app.cv_path:
        raise ValueError("No CV file for this application.")

    job = db.get(Job, app.job_id)
    candidate = db.get(Candidate, app.candidate_id)
    rubric = normalize_rubric(job.rubric_json)

    visible = parse_cv(app.cv_path)["raw_text"]
    anon, removed = anonymize_text(visible, candidate.name if candidate else "")
    app.anonymized_profile_json = {"text": anon, "removed": removed}

    result, source = score_candidate(anon, rubric, job, db)

    flags: list[str] = []
    injection = scan_text_for_injection(visible)
    if result.injection_suspected or injection:
        flags.append("Possible manipulation text in CV: " + (result.injection_text or injection[0])[:150])

    rows, total, missing_must = [], 0.0, []
    for c in rubric:
        cs = result.criteria.get(c["key"]) or CriterionScore()
        verified = evidence_is_real(cs.evidence, anon) if cs.evidence else False
        score = cs.score
        note = ""
        if cs.score > 0 and not verified:
            score, note = 0, "Unsupported: the quote was not found in the CV, so no points were given."
        if c["must_have"] and score <= 1:
            missing_must.append(c["label"])
        total += score / 5 * c["weight"]
        rows.append({
            "key": c["key"], "label": c["label"], "weight": c["weight"], "must_have": c["must_have"],
            "score": score, "ai_score": cs.score, "evidence": cs.evidence, "verified": verified,
            "reason": cs.reason, "note": note,
        })

    if missing_must:
        total = min(total, MUST_HAVE_CAP)
        flags.append(f"Missing must-have: {', '.join(missing_must)} (score capped at {MUST_HAVE_CAP})")

    score_row = Score(
        application_id=app.id,
        criteria_json={"criteria": rows, "summary": result.summary, "strengths": result.strengths[:3],
                       "gaps": result.gaps[:3], "flags": flags, "source": source},
        total=round(total, 1),
        model=settings.llm_model if source == "ai" else "offline-keywords",
        prompt_version=PROMPT_VERSION,
        created_at=datetime.now(),
    )
    db.add(score_row)
    db.add(app)
    db.commit()
    db.refresh(score_row)

    if app.status == ApplicationStatus.SCREENED:
        transition(db, app, ApplicationStatus.SCORED, actor=actor if source == "ai" else "system")
    log_audit(db, actor="ai" if source == "ai" else "system", action="score_cv", entity="application",
              entity_id=app.id, payload={"total": score_row.total, "source": source})
    return score_row
