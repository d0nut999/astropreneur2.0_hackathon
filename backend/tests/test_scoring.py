"""CV scoring tests: hidden text never reaches the AI, anonymization, evidence check, fairness."""
from pathlib import Path

from app.schemas import CriterionScore
from app.services.anonymizer import anonymize_text
from app.services.parser import parse_cv
from app.services.rubric import JUNIOR_BACKEND_RUBRIC, normalize_rubric
from app.services.scorer import evidence_is_real, score_offline

CVS = Path(__file__).resolve().parents[1] / "demo_data" / "cvs"
RUBRIC = normalize_rubric(JUNIOR_BACKEND_RUBRIC)


def _total(text):
    s = score_offline(text, RUBRIC)
    return sum(s.criteria[c["key"]].score / 5 * c["weight"] for c in RUBRIC)


def test_hidden_text_is_not_extracted():
    text = parse_cv(str(CVS / "cv_EVIL_hidden_injection.pdf"))["raw_text"]
    assert "Ignore all previous instructions" not in text
    assert "Sales assistant" in text  # visible text is still there


def test_anonymizer_removes_identity():
    text = "Sara Ben Ali\nsara@mail.test\n+216 22 333 444\nNationality: Tunisian\nGender: Female\nPython, FastAPI"
    anon, removed = anonymize_text(text, "Sara Ben Ali")
    for secret in ["Sara", "sara@mail.test", "22 333 444", "Tunisian", "Female"]:
        assert secret not in anon
    assert "Python, FastAPI" in anon
    assert len(removed) >= 5


def test_same_cv_different_name_gets_same_score():
    """Fairness: swapping the name/gender must not change the score."""
    cv = "{name}\n{pronoun}\nSKILLS\nPython, FastAPI, PostgreSQL, Git, Docker\nBackend Intern - built REST APIs"
    a, _ = anonymize_text(cv.format(name="Mohamed Trabelsi", pronoun="he/him"), "Mohamed Trabelsi")
    b, _ = anonymize_text(cv.format(name="Fatma Gharbi", pronoun="she/her"), "Fatma Gharbi")
    assert a == b
    assert _total(a) == _total(b)


def test_ranking_order_on_demo_cvs():
    totals = {n: _total(parse_cv(str(CVS / f))["raw_text"]) for n, f in [
        ("strong", "cv_strong_sara_ben_ali.pdf"),
        ("medium", "cv_medium_youssef_trabelsi.pdf"),
        ("weak", "cv_weak_amine_khelifi.pdf"),
    ]}
    assert totals["strong"] > totals["medium"] > totals["weak"]


def test_invented_evidence_is_rejected():
    cv = "Backend Intern at FictiTech. Built REST APIs with FastAPI."
    assert evidence_is_real("Built REST APIs with FastAPI", cv)
    assert not evidence_is_real("Led a team of 20 engineers at Google", cv)


def test_score_is_clamped():
    assert CriterionScore(score="4.6").score == 5
    assert CriterionScore(score=99).score == 5
    assert CriterionScore(score=-3).score == 0
    assert CriterionScore(score="ten").score == 0


def test_rubric_weights_sum_to_100():
    assert round(sum(c["weight"] for c in RUBRIC)) == 100
    old_format = normalize_rubric({"experience": {"weight": 0.3}, "skills": {"weight": 0.7}})
    assert round(sum(c["weight"] for c in old_format)) == 100
