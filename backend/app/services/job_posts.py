"""Job posts: HR gives the facts, the AI writes the prose, code checks and completes it, HR publishes.

Safety:
- The AI writes only the descriptive parts. Contract details, salary, start date and HOW TO APPLY
  (with the HR address and the job code) are written by code from HR's input, so they are always exact.
- Fact check: any number in the AI text that HR did not give is removed (and reported).
- Fairness check (rules): wording that excludes by age, gender, nationality, family status, appearance...
  is flagged with a neutral suggestion. Publishing with open issues needs a written reason.
- The same must-haves / nice-to-haves become the CV scoring criteria (approved by HR when publishing).
- Nothing is public until a human clicks Publish.
"""
import re
import secrets
from datetime import datetime

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..llm import LLMError, complete_json
from ..models import Job, JobPost
from ..schemas import JobPostDraft
from pathlib import Path

PROMPT = Path(__file__).resolve().parent.parent / "prompts" / "write_job_post.md"

CONTRACT_LABEL = {"permanent": "Permanent contract", "fixed_term": "Fixed-term contract",
                  "internship": "Internship", "freelance": "Freelance / contractor"}
MODE_LABEL = {"onsite": "On-site", "hybrid": "Hybrid", "remote": "Remote"}

# (pattern, why, suggestion)
FAIRNESS_RULES = [
    (r"\byoung(er)?\b", "Age: 'young' excludes older candidates.", "motivated"),
    (r"\b\d{2}\s*(?:-|–|to)\s*\d{2}\s*years?\s*old\b|\bunder\s+\d{2}\b|\bmax(?:imum)?\s+age\b|\bage\s+(?:limit|between)\b",
     "Age limit: asking for an age range is age discrimination.", "(remove the age requirement)"),
    (r"\brecent(?:ly)?\s+graduat\w*\b", "Age proxy: 'recent graduate' often excludes older career-changers.",
     "early-career (0-2 years of experience)"),
    (r"\bdigital natives?\b", "Age proxy: 'digital native' implies a generation.", "comfortable with digital tools"),
    (r"\bnative\s+(?:english|french|arabic|german|spanish|italian)?\s*speakers?\b",
     "Origin: 'native speaker' excludes fluent non-native speakers.", "fluent in the language"),
    (r"\b(?:he|him|his|she|her|hers)\b", "Gendered pronoun: the post should address everyone.", "you / the candidate"),
    (r"\b(?:salesman|salesmen|chairman|manpower|workmanship|foreman)\b", "Gendered job word.", "salesperson / chair / workforce"),
    (r"\b(?:rock\s?stars?|ninjas?|gurus?|wizards?|superstars?)\b", "Exclusionary jargon: discourages many qualified people.", "expert / skilled"),
    (r"\b(?:good[- ]looking|attractive|presentable|well[- ]groomed)\b", "Appearance is not a job requirement.", "(remove)"),
    (r"\b(?:married|single|no children|without children|childless)\b", "Family status is not a job requirement.", "(remove)"),
    (r"\b(?:able[- ]bodied|physically fit|in good health)\b", "Disability: describe the actual task instead.",
     "describe the physical task (e.g. 'lift boxes up to 10 kg')"),
    (r"\b(?:must be|only)\s+(?:a\s+)?(?:tunisian|french|european|local)s?(?:\s+(?:national|citizen)s?)?\b",
     "Nationality: ask for the right to work instead.", "must have the right to work in the country"),
    (r"\baggressive\b", "Masculine-coded word: may discourage some applicants.", "ambitious"),
    (r"\b(?:military service completed)\b", "Excludes people exempt from military service.", "(remove)"),
]


def _lines(v) -> list[str]:
    if isinstance(v, list):
        items = v
    else:
        items = re.split(r"[\n;]+", str(v or ""))
    return [re.sub(r"^\s*[-•*]\s*", "", x).strip()[:200] for x in items if str(x).strip()][:10]


def clean_details(d: dict) -> dict:
    out = {
        "title": str(d.get("title", "")).strip()[:120],
        "team": str(d.get("team", "")).strip()[:80],
        "location": str(d.get("location", "")).strip()[:120],
        "work_mode": d.get("work_mode") if d.get("work_mode") in MODE_LABEL else "onsite",
        "contract_type": d.get("contract_type") if d.get("contract_type") in CONTRACT_LABEL else "permanent",
        "contract_length": str(d.get("contract_length", "")).strip()[:60],
        "start_date": str(d.get("start_date", "")).strip()[:60],
        "hours": str(d.get("hours", "")).strip()[:60],
        "salary_min": _int(d.get("salary_min")),
        "salary_max": _int(d.get("salary_max")),
        "currency": str(d.get("currency", "TND")).strip()[:6] or "TND",
        "experience": str(d.get("experience", "")).strip()[:80],
        "must_haves": _lines(d.get("must_haves")),
        "nice_to_haves": _lines(d.get("nice_to_haves")),
        "tasks": _lines(d.get("tasks")),
        "benefits": _lines(d.get("benefits")),
        "about": str(d.get("about", "")).strip()[:500],
    }
    if not out["title"]:
        raise ValueError("A job title is required.")
    if not out["must_haves"]:
        raise ValueError("Give at least one must-have skill (they become the CV scoring criteria).")
    if out["contract_type"] in ("fixed_term", "internship") and not out["contract_length"]:
        raise ValueError("Give the contract length for a fixed-term contract or an internship.")
    if out["salary_min"] and out["salary_max"] and out["salary_min"] > out["salary_max"]:
        raise ValueError("The minimum salary is higher than the maximum.")
    return out


def _int(v):
    try:
        n = int(float(str(v).replace(" ", "").replace(",", "")))
        return n if n > 0 else None
    except (TypeError, ValueError):
        return None


# ---------------------------------------------------------------- writing
def _template(d: dict) -> JobPostDraft:
    team = f" in our {d['team']} team" if d["team"] else ""
    intro = (f"{settings.company_name} is looking for a {d['title']}{team}. "
             + (d["about"] + " " if d["about"] else "")
             + "You will work with a friendly team that values quality, learning and clear communication.")
    return JobPostDraft(
        intro=intro,
        responsibilities=d["tasks"] or [f"Contribute to the daily work of the {d['team'] or 'team'}."],
        requirements=d["must_haves"], nice_to_have=d["nice_to_haves"], offer=d["benefits"])


def _numbers(text: str) -> set[str]:
    return set(re.findall(r"\d+(?:[.,]\d+)?", text))


def _fact_check(draft: JobPostDraft, d: dict) -> tuple[JobPostDraft, list[str]]:
    """Remove AI sentences/bullets with numbers HR never gave."""
    allowed = _numbers(" ".join(str(v) for v in d.values()))
    removed = []

    def ok(s: str) -> bool:
        bad = _numbers(s) - allowed
        if bad:
            removed.append(s)
        return not bad

    sentences = re.split(r"(?<=[.!?])\s+", draft.intro)
    draft.intro = " ".join(s for s in sentences if ok(s))
    for f in ("responsibilities", "requirements", "nice_to_have", "offer"):
        setattr(draft, f, [x for x in getattr(draft, f) if ok(x)])
    # every must-have must still be visible
    if len(draft.requirements) < len(d["must_haves"]):
        draft.requirements = d["must_haves"]
    return draft, removed


def write(db: Session, d: dict) -> tuple[str, str, list[str]]:
    source, removed = "template", []
    try:
        facts = "\n".join(f"{k}: {v}" for k, v in d.items() if v not in (None, "", []))
        draft = complete_json(task="write_job_post", system=PROMPT.read_text(encoding="utf-8"),
                              user=f"<facts>\n{facts}\n</facts>", schema=JobPostDraft, prompt_version="jobpost_v1", db=db)
        draft, removed = _fact_check(draft, d)
        if not draft.intro.strip() or not draft.requirements:
            raise LLMError("empty draft")
        source = "ai"
    except LLMError:
        draft = _template(d)
    return assemble(draft, d), source, removed


def facts_block(d: dict) -> str:
    rows = [f"- Contract: {CONTRACT_LABEL[d['contract_type']]}"
            + (f", {d['contract_length']}" if d["contract_length"] else "")]
    where = MODE_LABEL[d["work_mode"]] + (f" - {d['location']}" if d["location"] else "")
    rows.append(f"- Workplace: {where}")
    if d["start_date"]:
        rows.append(f"- Start date: {d['start_date']}")
    if d["hours"]:
        rows.append(f"- Working hours: {d['hours']}")
    if d["experience"]:
        rows.append(f"- Experience: {d['experience']}")
    if d["salary_min"] or d["salary_max"]:
        if d["salary_min"] and d["salary_max"]:
            sal = f"{d['salary_min']:,} - {d['salary_max']:,} {d['currency']}"
        else:
            sal = f"{(d['salary_min'] or d['salary_max']):,} {d['currency']}"
        rows.append(f"- Salary: {sal} per month (gross)")
    return "\n".join(rows)


def apply_block(code: str, title: str) -> str:
    return (f"HOW TO APPLY\nSend your CV (PDF or DOCX) to {settings.hr_contact_email} with the subject "
            f"\"Application {code} - {title}\".\n"
            f"Every application is read, and you will hear from us either way. We only assess job-related "
            f"skills and experience; your CV is anonymized before it is assessed.")


def assemble(draft: JobPostDraft, d: dict, code: str = "{CODE}") -> str:
    def bullets(xs):
        return "\n".join(f"- {x.strip()}" for x in xs if x.strip())
    parts = [d["title"].upper(), draft.intro.strip()]
    if draft.responsibilities:
        parts.append("WHAT YOU WILL DO\n" + bullets(draft.responsibilities))
    parts.append("WHAT WE ARE LOOKING FOR\n" + bullets(draft.requirements))
    if draft.nice_to_have:
        parts.append("NICE TO HAVE\n" + bullets(draft.nice_to_have))
    if draft.offer:
        parts.append("WHAT WE OFFER\n" + bullets(draft.offer))
    parts.append("THE DETAILS\n" + facts_block(d))
    parts.append(apply_block(code, d["title"]))
    return "\n\n".join(parts)


# ---------------------------------------------------------------- checks
def fairness_issues(text: str) -> list[dict]:
    issues, seen = [], set()
    for pattern, why, suggestion in FAIRNESS_RULES:
        for m in re.finditer(pattern, text, re.I):
            phrase = m.group(0)
            if phrase.lower() in seen:
                continue
            seen.add(phrase.lower())
            line = next((ln for ln in text.splitlines() if phrase in ln), "")
            issues.append({"phrase": phrase, "why": why, "suggestion": suggestion, "context": line.strip()[:160]})
    return issues


def checks(post: JobPost) -> dict:
    d = post.details_json
    contact_ok = settings.hr_contact_email in post.text and post.code in post.text
    facts_ok = facts_block(d) in post.text
    return {
        "fairness": fairness_issues(post.text),
        "contact_ok": contact_ok,
        "facts_ok": facts_ok,
        "removed_by_fact_check": post.checks_json.get("removed_by_fact_check", []),
        "excluded_from_scoring": excluded_points(d) if d else [],
    }


# ---------------------------------------------------------------- criteria for CV scoring
STOP = {"and", "or", "with", "the", "of", "in", "a", "an", "to", "for", "experience", "knowledge", "good", "strong",
        "skills", "years", "year", "at", "least", "basic", "solid", "using", "on", "plus"}


def _keywords(text: str) -> list[str]:
    words = [w for w in re.findall(r"[a-zA-Z+#.]{2,}", text.lower()) if w not in STOP]
    return list(dict.fromkeys(words))[:8]


def excluded_points(d: dict) -> list[dict]:
    """Key points that fail the fairness check are never used to score CVs."""
    out = []
    for kind in ("must_haves", "nice_to_haves"):
        for x in d[kind]:
            issues = fairness_issues(x)
            if issues:
                out.append({"point": x, "why": issues[0]["why"]})
    return out


def rubric_from(d: dict) -> dict:
    bad = {e["point"] for e in excluded_points(d)}
    musts = [m for m in d["must_haves"] if m not in bad][:5] or ["Skills described in the job post"]
    d = {**d, "nice_to_haves": [n for n in d["nice_to_haves"] if n not in bad]}
    crit = []
    share = 70 / len(musts)
    for i, m in enumerate(musts):
        crit.append({"key": f"must_{i + 1}", "label": m[:60], "weight": share, "must_have": True,
                     "description": f"Must-have from the job post: {m}", "keywords": _keywords(m)})
    if d["nice_to_haves"]:
        crit.append({"key": "nice", "label": "Nice to have", "weight": 15, "must_have": False,
                     "description": "Nice-to-have from the job post: " + "; ".join(d["nice_to_haves"]),
                     "keywords": _keywords(" ".join(d["nice_to_haves"]))})
    crit.append({"key": "experience", "label": "Relevant experience", "weight": 15 if d["nice_to_haves"] else 30,
                 "must_have": False,
                 "description": "Work, internships or projects related to: " + "; ".join(d["tasks"] or [d["title"]])
                                + (f". Expected: {d['experience']}." if d["experience"] else ""),
                 "keywords": _keywords(" ".join(d["tasks"]) or d["title"]) + ["intern", "project"]})
    return {"criteria": crit}


# ---------------------------------------------------------------- lifecycle
def next_code(db: Session, job_id: int) -> str:
    return f"JOB-{job_id:03d}"


def generate(db: Session, details: dict, user_id: int, job_id: int | None = None) -> JobPost:
    d = clean_details(details)
    if job_id:
        job = db.get(Job, job_id)
        post = db.exec(select(JobPost).where(JobPost.job_id == job_id)).first()
        if not job or not post:
            raise ValueError("Job post not found.")
        if post.status == "published":
            raise ValueError("This post is published. Close it before changing it.")
        job.title = d["title"]
    else:
        job = Job(title=d["title"], description="")
        db.add(job)
        db.commit()
        db.refresh(job)
        post = JobPost(job_id=job.id, code=next_code(db, job.id))
    text, source, removed = write(db, d)
    post.text = text.replace("{CODE}", post.code)
    post.details_json = d
    post.generated_by = source
    post.checks_json = {"removed_by_fact_check": removed}
    job.description = post.text
    job.rubric_json = rubric_from(d)
    job.rubric_approved_by = None
    db.add(job)
    db.add(post)
    db.commit()
    db.refresh(post)
    log_audit(db, actor="ai" if source == "ai" else "system", action="draft_job_post", entity="job",
              entity_id=job.id, payload={"by": f"user:{user_id}", "source": source, "removed": len(removed)})
    return post


def update_text(db: Session, post: JobPost, text: str, user_id: int) -> JobPost:
    if post.status == "published":
        raise ValueError("This post is published. Close it before changing it.")
    post.text = text[:20000]
    job = db.get(Job, post.job_id)
    job.description = post.text
    db.add(post)
    db.add(job)
    db.commit()
    log_audit(db, actor=f"user:{user_id}", action="edit_job_post", entity="job", entity_id=post.job_id)
    return post


def publish(db: Session, post: JobPost, user_id: int, note: str = "") -> JobPost:
    """✋ HUMAN ONLY. Refused if the contact/facts were removed; open fairness issues need a reason."""
    c = checks(post)
    if not c["contact_ok"]:
        raise ValueError(f"The 'How to apply' part must keep {settings.hr_contact_email} and the code {post.code} "
                         f"(applications are routed with it).")
    if c["fairness"] and len(note.strip()) < 10:
        raise ValueError(f"{len(c['fairness'])} wording issue(s) are still open. Fix them, or write a reason "
                         f"(10+ characters) to publish anyway - it is saved in the audit log.")
    post.status = "published"
    post.public_slug = post.public_slug or f"{post.code.lower()}-{secrets.token_urlsafe(6)}"
    post.published_by = user_id
    post.published_at = datetime.now()
    job = db.get(Job, post.job_id)
    job.rubric_approved_by = user_id  # the criteria were shown next to the post
    db.add(post)
    db.add(job)
    db.commit()
    log_audit(db, actor=f"user:{user_id}", action="publish_job_post", entity="job", entity_id=post.job_id,
              payload={"open_fairness_issues": len(c["fairness"]), "note": note[:200]})
    return post


def close(db: Session, post: JobPost, user_id: int) -> JobPost:
    post.status = "closed"
    db.add(post)
    db.commit()
    log_audit(db, actor=f"user:{user_id}", action="close_job_post", entity="job", entity_id=post.job_id)
    return post


def post_json(db: Session, post: JobPost) -> dict:
    job = db.get(Job, post.job_id)
    from .rubric import normalize_rubric
    return {
        "job_id": post.job_id, "code": post.code, "status": post.status, "title": job.title,
        "details": post.details_json, "text": post.text, "generated_by": post.generated_by,
        "checks": checks(post), "public_slug": post.public_slug if post.status == "published" else "",
        "published_at": post.published_at.isoformat() if post.published_at else None,
        "rubric": normalize_rubric(job.rubric_json), "contact_email": settings.hr_contact_email,
        "dev": settings.app_env == "dev",
    }


def job_for_application(db: Session, subject: str, body: str) -> Job | None:
    """Route an application: job code in the subject/body first, then a published job title, else None."""
    text = f"{subject}\n{body}"
    m = re.search(r"\bJOB-(\d{3,})\b", text, re.I)
    if m:
        post = db.exec(select(JobPost).where(JobPost.code == f"JOB-{m.group(1)}")).first()
        if post and post.status == "published":
            return db.get(Job, post.job_id)
    for post in db.exec(select(JobPost).where(JobPost.status == "published")).all():
        job = db.get(Job, post.job_id)
        if job and job.title.lower() in subject.lower():
            return job
    return None


# ---------------------------------------------------------------- demo: fictional applicants for a published job
DEMO_PEOPLE = ["Yasmine Haddad", "Karim Lahmar", "Nadia Jelassi", "Firas Mabrouk", "Rim Souissi", "Hamza Dridi",
               "Ines Gharbi", "Skander Zaier", "Molka Ben Amor", "Aziz Khemiri"]


def _cv_docx(name: str, email: str, title: str, summary: str, jobs: list[tuple[str, list[str]]],
             skills: list[str], education: str) -> bytes:
    import io
    import docx
    d = docx.Document()
    d.add_heading(name, 0)
    d.add_paragraph(f"{email} · Tunis (fictional candidate - demo data)")
    d.add_heading("Profile", 1)
    d.add_paragraph(summary)
    d.add_heading("Experience", 1)
    for head, bullets in jobs:
        d.add_paragraph(head).runs[0].bold = True
        for b in bullets:
            d.add_paragraph(b, style="List Bullet")
    d.add_heading("Skills", 1)
    d.add_paragraph(", ".join(skills))
    d.add_heading("Education", 1)
    d.add_paragraph(education)
    buf = io.BytesIO()
    d.save(buf)
    return buf.getvalue()


def demo_applications(db: Session, post: JobPost) -> list[dict]:
    """Four fictional applicants (strong -> weak) emailed to HR with this job's code, through the normal pipeline."""
    import uuid
    from .triage import process_incoming
    d = post.details_json
    bad = {e["point"] for e in excluded_points(d)}
    musts = [m for m in d.get("must_haves", []) if m not in bad] or [d["title"]]
    nices = [n for n in d.get("nice_to_haves", []) if n not in bad]
    tasks = d.get("tasks", []) or [f"Daily work as {d['title']}"]
    title = d["title"]
    profiles = [
        ("strong", musts, nices, tasks, "3 years", f"{title} with 3 years of hands-on experience"),
        ("good", musts, [], tasks[:1], "2 years", f"{title} with 2 years of experience"),
        ("medium", musts[: max(1, len(musts) // 2)], [], [], "1 year", "Early-career professional moving into this field"),
        ("weak", [], [], [], "", "Hospitality professional looking for a new challenge"),
    ]
    out = []
    for i, (level, m, n, t, years, summary) in enumerate(profiles):
        name = DEMO_PEOPLE[(post.job_id * 3 + i) % len(DEMO_PEOPLE)]
        email = f"{name.lower().replace(' ', '.')}.{uuid.uuid4().hex[:4]}@candidate-mail.test"
        if level == "weak":
            jobs = [("Receptionist - Example Hotel (2021-2024)",
                     ["Welcomed guests and managed bookings", "Handled the front desk schedule"])]
            skills = ["Customer welcome", "Booking software", "Teamwork"]
            edu = "Diploma in hospitality management"
        else:
            bullets = [f"{x}" for x in t] + [f"Used {x} every day" for x in m] + [f"Also worked with {x}" for x in n]
            jobs = [(f"{title} - Example Company ({years})", bullets[:7])]
            if level in ("strong", "good"):
                jobs.append(("Intern - Sample Agency (6 months)", [f"Supported the team on: {tasks[0]}"]))
            skills = m + n
            edu = "Bachelor's degree related to the role"
        cv = _cv_docx(name, email, title, f"{summary}.", jobs, skills, edu)
        raw = {
            "message_id": f"demo-app-{uuid.uuid4().hex}",
            "from_name": name, "from_addr": email, "to_addr": settings.hr_contact_email,
            "subject": f"Application {post.code} - {title}",
            "body": f"Dear HR team,\n\nI would like to apply for the {title} position ({post.code}). "
                    f"Please find my CV attached.\n\nBest regards,\n{name}",
            "received_at": datetime.now().replace(microsecond=0),
            "attachments": [{"filename": f"{name.replace(' ', '_')}_CV.docx", "content": cv}],
        }
        row = process_incoming(db, raw)
        out.append({"name": name, "level": level, "email_id": row.id if row else None,
                    "application_id": row.application_id if row else None})
    log_audit(db, actor="system", action="demo_applications", entity="job", entity_id=post.job_id,
              payload={"count": len(out)})
    return out
