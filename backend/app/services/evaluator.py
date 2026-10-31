"""Evaluate written interview answers and produce a RECOMMENDATION (never a decision).

Design:
- AI scores each answer 0-5 with a quote from the answer; code checks the quote exists.
- The recommendation is computed by CODE from the CV score and the interview score,
  so it is consistent and explainable. HR makes the final decision.
- Offline fallback (no AI): simple overlap between the answer and the question's rubric.
"""
import re
from pathlib import Path

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..llm import LLMError, complete_json
from ..models import Application, ApplicationStatus, Evaluation, Job, Score, VideoSubmission
from ..schemas import AnswerEvaluation, CriterionScore
from ..state_machine import transition
from .interview import questions_for
from .scorer import evidence_match
from .security_gate import scan_text_for_injection

PROMPT_PATH = Path(__file__).resolve().parent.parent / "prompts" / "evaluate_answers.md"
CV_WEIGHT, INTERVIEW_WEIGHT = 0.4, 0.6
STOPWORDS = set("a an the and or of to in on for with is are be it this that how what why your you their real "
                "clear shows mentions gives example examples concrete".split())


def recommend(combined: float, flags: list[str], low_evidence: bool) -> tuple[str, list[str]]:
    """Rules that turn numbers into a recommendation + human-readable reasons."""
    reasons = []
    if flags:
        reasons.append("Manipulation attempt found in the answers: needs a careful human review")
        return "Hold", reasons
    if low_evidence:
        reasons.append("Answers are very short or vague: not enough evidence")
        return "Hold", reasons
    if combined >= 70:
        reasons.append(f"Combined score {combined:.0f}/100 is at least 70")
        return "Advance", reasons
    if combined >= 50:
        reasons.append(f"Combined score {combined:.0f}/100 is between 50 and 69")
        return "Hold", reasons
    reasons.append(f"Combined score {combined:.0f}/100 is below 50")
    return "Not recommended", reasons


def _offline(answers: list[dict], rubrics: dict[int, str]) -> AnswerEvaluation:
    per = {}
    for a in answers:
        words = re.findall(r"[a-zA-Z][a-zA-Z+#./-]{2,}", a["answer"].lower())
        rubric_words = {w for w in re.findall(r"[a-z]{4,}", rubrics.get(a["question_id"], "").lower())} - STOPWORDS
        overlap = len(rubric_words & set(words))
        concrete = bool(re.search(r"\d|built|wrote|used|implemented|deployed|tested|designed", a["answer"].lower()))
        score = 0 if len(words) < 5 else min(5, 1 + overlap + (1 if concrete else 0) + (1 if len(words) > 40 else 0))
        first = re.split(r"(?<=[.!?])\s+", a["answer"].strip())[0][:150]
        per[str(a["question_id"])] = CriterionScore(score=score, evidence=first,
                                                    reason=f"{len(words)} words, {overlap} rubric points mentioned")
    return AnswerEvaluation(per_question=per, summary="Evaluated offline (no AI available): length, concreteness "
                                                      "and overlap with the expected points.")


def evaluate_interview(db: Session, app: Application) -> Evaluation:
    sub = db.exec(select(VideoSubmission).where(VideoSubmission.application_id == app.id)
                  .order_by(VideoSubmission.id.desc())).first()
    answers = (sub.transcript_json or {}).get("answers") if sub else None
    if not answers:
        raise ValueError("No answers to evaluate yet.")

    qs = {q.id: q for q in questions_for(db, app)}
    rubrics = {qid: q.rubric for qid, q in qs.items()}
    job = db.get(Job, app.job_id)

    try:
        blocks = "\n\n".join(
            f'<question id="{a["question_id"]}">\n{a["question"]}\nRubric: {rubrics.get(a["question_id"], "")}\n'
            f'</question>\n<answer_data id="{a["question_id"]}">\n{a["answer"][:4000]}\n</answer_data>'
            for a in answers
        )
        result = complete_json(task="evaluate_answers", system=PROMPT_PATH.read_text(encoding="utf-8"),
                               user=f"<job>{job.title}</job>\n\n{blocks}", schema=AnswerEvaluation,
                               prompt_version="evaluate_v2", db=db)
        source = "ai"
    except LLMError as e:
        print(f"[evaluator] AI unavailable, using offline evaluation: {e}")
        result, source = _offline(answers, rubrics), "offline"

    flags = list((sub.transcript_json or {}).get("injection_flags", []))
    if result.injection_suspected and result.injection_text:
        flags.append(result.injection_text)
    for a in answers:
        flags += [f for f in scan_text_for_injection(a["answer"]) if f not in flags]

    per_q, total, verified_count, words = [], 0.0, 0, 0
    for a in answers:
        cs = result.per_question.get(str(a["question_id"])) or CriterionScore()
        match = evidence_match(cs.evidence, a["answer"]) if cs.evidence else None
        verified = match is not None
        score = cs.score if (verified or cs.score == 0) else 0
        note = "" if (verified or cs.score == 0) else "Quote not found in the answer: no points given."
        if scan_text_for_injection(a["answer"]):
            score, note = 0, "This answer tries to give instructions to the AI: no points given."
        verified_count += verified
        words += len(a["answer"].split())
        total += score
        per_q.append({"question_id": a["question_id"], "question": a["question"], "is_tailored": a.get("is_tailored"),
                      "score": score, "ai_score": cs.score, "evidence": cs.evidence, "verified": verified, "match": match,
                      "reason": cs.reason, "note": note})

    interview_score = round(total / (5 * len(answers)) * 100, 1)
    cv = db.exec(select(Score).where(Score.application_id == app.id).order_by(Score.id.desc())).first()
    cv_score = cv.total if cv else interview_score
    combined = round(CV_WEIGHT * cv_score + INTERVIEW_WEIGHT * interview_score, 1)
    low_evidence = words < 15 * len(answers)
    recommendation, reasons = recommend(combined, flags, low_evidence)

    # Confidence (not how "sure" the AI sounds):
    # 1) how much solid evidence we have, 2) how far the score is from a decision line (50 / 70).
    evidence_strength = 0.3 + 0.5 * verified_count / len(answers) + min(0.2, words / 1500)
    margin = min(abs(combined - 50), abs(combined - 70))
    margin_factor = min(1.0, 0.5 + margin / 20)  # 2 points from the line -> 0.6, 10+ points -> 1.0
    confidence = round(min(0.95, evidence_strength * margin_factor), 2)
    if low_evidence or flags:
        confidence = min(confidence, 0.4)

    ev = Evaluation(
        application_id=app.id,
        per_question_json={"questions": per_q},
        recommendation=recommendation,
        confidence=confidence,
        summary_json={"summary": result.summary, "interview_score": interview_score, "cv_score": cv_score,
                      "combined": combined, "weights": {"cv": CV_WEIGHT, "interview": INTERVIEW_WEIGHT},
                      "reasons": reasons, "flags": flags, "source": source,
                      "model": settings.llm_model if source == "ai" else "offline-rules"},
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    if app.status == ApplicationStatus.VIDEO_SUBMITTED:
        transition(db, app, ApplicationStatus.EVALUATED, actor="ai" if source == "ai" else "system")
    log_audit(db, actor="ai" if source == "ai" else "system", action="evaluate_interview", entity="application",
              entity_id=app.id, payload={"recommendation": recommendation, "combined": combined})
    return ev
