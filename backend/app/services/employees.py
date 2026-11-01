"""Employee emails: leave requests and questions.

- The sender must be a known employee (matched by email address in code, not by the AI).
- Leave request -> the AI (or offline rules) reads who/when/type; the dates are checked by code;
  a LeaveRequest is created with a recommendation. HR approves or rejects; the reply is a draft.
- Question -> answered ONLY from the handbook (sections cited) and the employee's own balance;
  if the handbook does not answer it, the reply says it was forwarded to HR. HR approves every reply.
"""
import re
from datetime import date, datetime, timedelta
from pathlib import Path

from sqlmodel import Session, select

from ..audit import log_audit
from ..config import settings
from ..llm import LLMError, complete_json
from ..models import Draft, DraftType, Email, Employee, LeaveRequest, LeaveStatus, LeaveType
from ..schemas import HandbookAnswer, LeaveExtraction
from . import leave as L

PROMPTS = Path(__file__).resolve().parent.parent / "prompts"
HANDBOOK = Path(__file__).resolve().parents[2] / "demo_data" / "handbook.md"
STOP = set("a an the i my me you your we our to of in on for and or is are am be can could would will do does did "
           "how what when where which who much many there it this that with at as if have has get from by about "
           "please hi hello thanks thank regards best any some".split())


# ---------------------------------------------------------------- handbook
def sections() -> list[dict]:
    text = HANDBOOK.read_text(encoding="utf-8")
    out = []
    for m in re.finditer(r"^## (\d+)\. (.+?)\n(.*?)(?=^## |\Z)", text, re.S | re.M):
        out.append({"n": int(m.group(1)), "title": m.group(2).strip(), "text": m.group(3).strip()})
    return out


def _words(text: str) -> set[str]:
    words = {w for w in re.findall(r"[a-z]+", text.lower()) if w not in STOP and len(w) > 2}
    return words | {w[:-1] for w in words if w.endswith("s")}  # crude plural folding


def relevant_sections(question: str, k: int = 2) -> list[tuple[int, dict]]:
    q = _words(question)
    scored = []
    for s in sections():
        score = len(q & _words(s["title"])) * 2 + len(q & _words(s["text"]))
        if score:
            scored.append((score, s))
    scored.sort(key=lambda x: -x[0])
    return scored[:k]


BALANCE_RE = re.compile(r"how many (?:leave |holiday |vacation |paid )?days|days (?:do i have )?left|remaining (?:leave )?days|"
                        r"leave balance|my balance|days i have left", re.I)


def balance_text(db: Session, emp: Employee) -> str:
    year = date.today().year
    used = L.days_used(db, emp.id, LeaveType.ANNUAL, year)
    left = max(0, settings.annual_leave_days - used)
    return (f"You have used {used} of your {settings.annual_leave_days} paid leave days for {year}, "
            f"so {left} day{'s' if left != 1 else ''} remain (Handbook §1).")


def answer_question(db: Session, question: str, emp: Employee | None) -> dict:
    """Returns {answered, answer, sections:[{n,title}], source, forwarded}."""
    parts, cited, source = [], [], "rules"
    if emp and BALANCE_RE.search(question):
        parts.append(balance_text(db, emp))
        cited.append(1)
    rest = BALANCE_RE.sub("", question)
    top = relevant_sections(rest)
    other_question = len(_words(rest) - {"leave", "day", "days", "question"}) >= 2
    from_handbook = False
    if top and other_question:
        try:
            ctx = "\n\n".join(f"<section n=\"{s['n']}\" title=\"{s['title']}\">\n{s['text']}\n</section>" for _, s in top)
            res = complete_json(task="answer_handbook", system=(PROMPTS / "answer_handbook.md").read_text(encoding="utf-8"),
                                user=f"{ctx}\n\n<question>\n{question[:2000]}\n</question>", schema=HandbookAnswer,
                                prompt_version="handbook_v1", db=db)
            allowed = {s["n"] for _, s in top}
            used = [n for n in res.cited_sections if n in allowed]
            if res.found and res.answer.strip() and used:  # an answer must cite a section it was given
                parts.append(res.answer.strip()[:800] + " (Handbook " + ", ".join(f"§{n}" for n in used) + ")")
                cited += used
                source, from_handbook = "ai", True
        except LLMError:
            best_score, best = top[0]
            if best_score >= 2:
                sents = re.split(r"(?<=\.)\s+", best["text"])
                qw = _words(rest)
                keep = sorted(sorted(range(len(sents)), key=lambda i: -len(qw & _words(sents[i])))[:2])
                first = " ".join(sents[i] for i in keep)
                parts.append(f"According to the handbook (§{best['n']} {best['title']}): {first}")
                cited.append(best["n"])
                from_handbook = True
    forwarded = (other_question and not from_handbook) or not parts
    by_n = {s["n"]: s for s in sections()}
    return {
        "answered": bool(parts),
        "answer": " ".join(parts),
        "sections": [{"n": n, "title": by_n[n]["title"]} for n in dict.fromkeys(cited) if n in by_n],
        "source": source,
        "forwarded": forwarded,
    }


def _reply_body(first: str, ans: dict) -> str:
    body = f"Hello {first},\n\n"
    if ans["answer"]:
        body += ans["answer"] + "\n\n"
    if ans["forwarded"]:
        body += ("I could not find " + ("the rest of " if ans["answer"] else "") +
                 "the answer to your question in the employee handbook, so I have passed it to the HR team. "
                 "Someone will get back to you within 2 working days.\n\n")
    return body + "Best regards,\nHR Team"


# ---------------------------------------------------------------- reading a leave request
def extract_leave(db: Session, email: dict, today: date) -> tuple[LeaveExtraction | None, str]:
    text = f"{email['subject']}\n{email['body']}"
    try:
        res = complete_json(task="extract_leave", system=(PROMPTS / "extract_leave.md").read_text(encoding="utf-8"),
                            user=f"Today: {today.isoformat()} ({today:%A})\n\n<email>\n{text[:4000]}\n</email>",
                            schema=LeaveExtraction, prompt_version="leave_v1", db=db)
        if res.is_leave_request and res.start:
            s = date.fromisoformat(res.start)
            e = date.fromisoformat(res.end or res.start)
            if s <= e <= s + timedelta(days=120) and today - timedelta(days=60) <= s <= today + timedelta(days=365):
                res.leave_type = "sick" if res.leave_type == "sick" else "annual"
                return res, "ai"
    except (LLMError, ValueError):
        pass
    if not L.looks_like_leave_request(text):
        return None, "rules"
    s, e = L.parse_dates(text, today)
    if not s:
        return None, "rules"
    reason = ""
    m = re.search(r"\b(?:for|because of|due to)\s+(?:a\s+|my\s+)?([a-z' ]{3,40}?)(?:[.,\n]|$)", email["body"].lower())
    if m and L.leave_type_of(text) == LeaveType.ANNUAL and not re.match(r"\d|one|two|three|four|five", m.group(1)):
        reason = m.group(1).strip()[:40]
    return LeaveExtraction(is_leave_request=True, leave_type=L.leave_type_of(text).value, start=s.isoformat(),
                           end=e.isoformat(), short_reason=reason), "rules"


def find_employee(db: Session, addr: str) -> Employee | None:
    return db.exec(select(Employee).where(Employee.email == (addr or "").strip().lower())).first()


def handle_employee_email(db: Session, email_row: Email, raw: dict, now: datetime) -> str | None:
    """Called by triage for emails from known employees. Returns the new category, or None."""
    emp = find_employee(db, email_row.from_addr)
    if not emp or email_row.urgency == "flagged":
        return None
    ext, source = extract_leave(db, raw, now.date())
    first = emp.name.split(" ")[0]
    if ext:
        req = LeaveRequest(employee_id=emp.id, type=LeaveType(ext.leave_type), start=date.fromisoformat(ext.start),
                           end=date.fromisoformat(ext.end), email_id=email_row.id,
                           reason_from_employee=ext.short_reason[:60], extracted_by=source)
        db.add(req)
        db.commit()
        db.refresh(req)
        ev = L.evaluate(db, req)
        email_row.category = "leave_request"
        kind = "Sick leave" if req.type == LeaveType.SICK else "Leave request"
        email_row.summary = (f"{kind}: {emp.name} ({emp.team}), {L.human(req.start)}"
                             + (f" → {L.human(req.end)}" if req.end != req.start else "") + f", {ev['days']} working day(s). "
                             + {"approve": "Within the rules.", "move": f"Team would drop to {ev['min_presence']}%.",
                                "over_limit": "Over the yearly limit.",
                                "sick_alert": "Above 60 sick days this year: HR follow-up needed."}[ev["recommendation"]])
        email_row.needs_human = True
        if email_row.urgency == "low":
            email_row.urgency = "normal"
            email_row.urgency_reasons_json = ["Leave request from an employee: HR decides"]
        if ev["recommendation"] == "sick_alert" and email_row.urgency != "urgent":
            email_row.urgency = "urgent"
            email_row.urgency_reasons_json = [f"{emp.name}: {ev['sick_used'] + ev['days']} sick days this year (above "
                                              f"{settings.sick_alert_days}) - HR follow-up"]
        db.add(email_row)
        db.commit()
        log_audit(db, actor="ai" if source == "ai" else "system", action="leave_request_read", entity="leave_request",
                  entity_id=req.id, payload={"employee": emp.id, "type": req.type.value, "start": ext.start,
                                             "end": ext.end, "recommendation": ev["recommendation"]})
        return "leave_request"

    ans = answer_question(db, f"{raw['subject']}\n{raw['body']}", emp)
    if not ans["answered"] and not ("?" in raw["body"] or "?" in raw["subject"]):
        return None  # not a question: leave the normal triage result
    email_row.category = "employee_question"
    email_row.summary = (f"Question from {emp.name} ({emp.team}). "
                         + ("Answer drafted from the handbook" + (" + forwarded to HR for the rest." if ans["forwarded"] and ans["answered"] else ".")
                            if ans["answered"] else "Not covered by the handbook: needs an HR answer."))
    email_row.needs_human = True
    if email_row.urgency == "low":
        email_row.urgency = "normal"
        email_row.urgency_reasons_json = ["Question from an employee: reply drafted for HR approval"]
    db.add(email_row)
    db.add(Draft(email_id=email_row.id, to_addr=emp.email, type=DraftType.REPLY,
                 subject=f"Re: {raw['subject']}"[:200], body=_reply_body(first, ans)))
    db.commit()
    log_audit(db, actor="ai" if ans["source"] == "ai" else "system", action="employee_question_answered",
              entity="email", entity_id=email_row.id,
              payload={"sections": [s["n"] for s in ans["sections"]], "forwarded": ans["forwarded"]})
    return "employee_question"


# ---------------------------------------------------------------- HR decisions on leave (human only)
def _reply(db: Session, req: LeaveRequest, subject: str, body: str) -> Draft:
    emp = db.get(Employee, req.employee_id)
    email = db.get(Email, req.email_id) if req.email_id else None
    d = Draft(email_id=req.email_id, to_addr=emp.email, type=DraftType.REPLY,
              subject=(f"Re: {email.subject}" if email else subject)[:200], body=body)
    db.add(d)
    if email:
        email.status = "handled"
        db.add(email)
    db.commit()
    db.refresh(d)
    return d


def decide(db: Session, req: LeaveRequest, action: str, user_id: int, note: str = "",
           alt_start: str | None = None, alt_end: str | None = None) -> Draft:
    """✋ approve | reject | propose | meeting. Going against the recommendation needs a reason."""
    if req.status != LeaveStatus.PENDING:
        raise ValueError("This request was already decided.")
    ev = L.evaluate(db, req)
    rec = ev["recommendation"]
    emp = db.get(Employee, req.employee_id)
    first = emp.name.split(" ")[0]
    period = L.human(req.start) + (f" to {L.human(req.end)}" if req.end != req.start else "")
    note = (note or "").strip()
    against = (action == "approve" and rec in ("over_limit", "move")) or (action == "reject" and rec in ("approve", "sick_alert"))
    if (against or action == "reject") and len(note) < 10:
        raise ValueError("Please write a short reason (10+ characters). It is saved in the audit log"
                         + (" because you are going against the recommendation." if against else "."))
    if action == "approve":
        req.status = LeaveStatus.APPROVED
        if req.type == LeaveType.SICK:
            body = (f"Hello {first},\n\nThank you for letting us know. Your sick leave from {period} is recorded. "
                    f"Please send your medical certificate within 48 hours (no details about your health are needed). "
                    f"Take care and get well soon.\n\nBest regards,\nHR Team")
        else:
            left = ev["annual_left"] - ev["days"]
            body = (f"Hello {first},\n\nYour leave from {period} ({ev['days']} working day{'s' if ev['days'] != 1 else ''}) "
                    f"is approved. You will have {max(0, left)} paid leave day{'s' if left != 1 else ''} left for "
                    f"{req.start.year}.\n\nEnjoy your time off!\n\nBest regards,\nHR Team")
    elif action == "reject":
        req.status = LeaveStatus.REJECTED
        body = (f"Hello {first},\n\nThank you for your request for {period}. Unfortunately we cannot approve it: "
                f"{note}\n\nIf you would like to discuss it, just reply to this email.\n\nBest regards,\nHR Team")
    elif action == "propose":
        alts = ev["alternatives"]
        if alt_start:
            s = date.fromisoformat(alt_start)
            e = date.fromisoformat(alt_end) if alt_end else L.add_workdays(s, ev["days"] - 1)
            options = [f"{L.human(s)} to {L.human(e)}"]
        else:
            options = [a["label"].replace(" → ", " to ") for a in alts]
        if not options:
            raise ValueError("No other dates found that keep the team at 70%. Reject or approve with a reason.")
        req.status = LeaveStatus.PROPOSED
        lines = "\n".join(f"  - {o}" for o in options)
        body = (f"Hello {first},\n\nThank you for your request for {period}. On those dates too many people in "
                f"{emp.team} would be away (our rule is to keep at least {round(settings.team_min_presence * 100)}% "
                f"of the team at work, handbook §2).\n\nCould one of these periods work for you instead?\n{lines}\n\n"
                f"Just reply with your choice and we will confirm it.\n\nBest regards,\nHR Team")
    elif action == "meeting":
        req.status = LeaveStatus.REJECTED
        body = (f"Hello {first},\n\nThank you for your request for {period}. You have already used "
                f"{ev['annual_used']} of your {settings.annual_leave_days} paid leave days for {req.start.year}, "
                f"so we cannot approve more paid leave this year (handbook §1-2).\n\n"
                f"If your situation is exceptional, we would be happy to talk about it: please reply with a short "
                f"explanation and two or three times that suit you this week, and we will set up a meeting.\n\n"
                f"Best regards,\nHR Team")
    else:
        raise ValueError("Unknown action.")
    req.hr_note = note[:500]
    req.decided_by = f"user:{user_id}"
    db.add(req)
    db.commit()
    draft = _reply(db, req, f"Your leave request ({period})", body)
    log_audit(db, actor=f"user:{user_id}", action=f"leave_{action}", entity="leave_request", entity_id=req.id,
              payload={"recommendation": rec, "against_recommendation": against, "note": note[:200],
                       "draft_id": draft.id})
    return draft


# ---------------------------------------------------------------- fictional staff for the demo
TEAMS = {
    "Engineering": ["Walid Gharbi", "Ines Trabelsi", "Karim Ayari", "Sami Bouzid", "Lina Chaouch", "Hedi Mrad",
                    "Yasmine Feki", "Ali Jebali"],
    "Sales": ["Mehdi Saidi", "Rania Ben Salem", "Fares Khelifi", "Dorra Hamdi", "Nizar Belhaj", "Sonia Mejri",
              "Tarek Ouali", "Emna Ghali"],
    "Customer Support": ["Hatem Riahi", "Nour Kefi", "Salma Dridi", "Bilel Zouari", "Asma Lahmar", "Oussema Toumi"],
    "Finance": ["Amira Sassi", "Mounir Baccar", "Hela Abid", "Zied Karray", "Olfa Chebbi"],
    "Operations": ["Omar Jaziri", "Meriem Sfar", "Anis Brahmi", "Wafa Guizani", "Rami Hachani", "Ichraf Mansouri"],
    "Marketing": ["Sarra Ellouze", "Aymen Nasri", "Khadija Ferchichi", "Malek Hadded"],
    "HR": ["Leila Hamza", "Imen Bouaziz", "Chiheb Rekik"],
}
TITLES = {"Engineering": "Software engineer", "Sales": "Account manager", "Customer Support": "Support specialist",
          "Finance": "Financial analyst", "Operations": "Operations officer", "Marketing": "Marketing specialist",
          "HR": "HR officer"}


def email_of(name: str) -> str:
    parts = name.lower().replace("'", "").split(" ")
    return f"{parts[0]}.{''.join(parts[1:])}@fictional-company.test"


def seed_employees(db: Session, today: date | None = None) -> None:
    """Fictional staff + this year's approved leave, relative to today so the demo always works."""
    today = today or date.today()
    for r in db.exec(select(LeaveRequest)).all():
        db.delete(r)
    for e in db.exec(select(Employee)).all():
        db.delete(e)
    db.commit()
    by_name = {}
    for team, names in TEAMS.items():
        for n in names:
            e = Employee(name=n, email=email_of(n), team=team, title=TITLES[team])
            db.add(e)
            by_name[n] = e
    db.commit()
    year_start = date(today.year, 1, 5)

    def add(name, start, end, kind=LeaveType.ANNUAL):
        db.add(LeaveRequest(employee_id=by_name[name].id, type=kind, start=start, end=end,
                            status=LeaveStatus.APPROVED, decided_by="history"))

    def past_block(name, days, kind=LeaveType.ANNUAL, offset_weeks=0, gap_weeks=3):
        """`days` working days spread in 5-day blocks earlier this year (never after today)."""
        s = L.next_workday(year_start + timedelta(weeks=offset_weeks))
        while days > 0:
            n = min(5, days)
            e = L.add_workdays(s, n - 1)
            if e >= today:
                break
            add(name, s, e, kind)
            days -= n
            s = L.next_workday(e + timedelta(days=1, weeks=gap_weeks))

    # usual history: everyone has taken some leave this year (deterministic)
    for i, (n, e) in enumerate(by_name.items()):
        past_block(n, 6 + (i * 7) % 15, offset_weeks=i % 6)
    # demo cases
    for n in ("Mehdi Saidi",):                                  # nearly at the limit
        for r in db.exec(select(LeaveRequest).where(LeaveRequest.employee_id == by_name[n].id)).all():
            db.delete(r)
        db.commit()
        past_block(n, 28, offset_weeks=1, gap_weeks=2)
    past_block("Walid Gharbi", 58, LeaveType.SICK, offset_weeks=4, gap_weeks=0)  # long sick leave this year
    # who is away today / next working day
    d0 = L.next_workday(today)
    add("Ines Trabelsi", d0, L.add_workdays(d0, 2))
    add("Fares Khelifi", d0, L.add_workdays(d0, 1))
    add("Hela Abid", d0, d0, LeaveType.SICK)
    add("Anis Brahmi", L.add_workdays(d0, -0), L.add_workdays(d0, 4))
    # Customer Support: Nour is already off next week -> Hatem asking for the same week drops the team below 70%
    add("Nour Kefi", L.week_day(today, 1, 0), L.week_day(today, 1, 4))
    db.commit()


def ensure_employees(db: Session) -> None:
    if not db.exec(select(Employee)).first():
        seed_employees(db)
