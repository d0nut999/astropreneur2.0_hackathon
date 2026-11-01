"""Leave management: balances, team presence, and a recommendation for each request.

The AI only READS the email (who, which dates, which type). Everything below is plain code:
  - annual leave:  used + requested must stay within `annual_leave_days` (30)  -> else "over_limit"
                   each day, the team must keep >= `team_min_presence` (70%) -> else "move" (+ other dates)
  - sick leave:    never refused for staffing; above `sick_alert_days` (60) in a year -> "sick_alert" for HR
Only a human approves or rejects. Every outcome is a reply draft that HR sends.
"""
import re
from datetime import date, datetime, timedelta

from sqlmodel import Session, select

from ..config import settings
from ..models import Employee, LeaveRequest, LeaveStatus, LeaveType

MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october",
     "november", "december"], 1)}
MONTHS.update({k[:3]: v for k, v in list(MONTHS.items())})
WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


# ---------------------------------------------------------------- calendar helpers
def is_workday(d: date) -> bool:
    return d.weekday() < 5


def workdays(start: date, end: date) -> list[date]:
    out, d = [], start
    while d <= end:
        if is_workday(d):
            out.append(d)
        d += timedelta(days=1)
    return out


def add_workdays(d: date, n: int) -> date:
    while n > 0:
        d += timedelta(days=1)
        if is_workday(d):
            n -= 1
    return d


def next_workday(d: date) -> date:
    while not is_workday(d):
        d += timedelta(days=1)
    return d


def week_day(today: date, weeks_ahead: int, weekday: int) -> date:
    """Monday=0 ... of the week `weeks_ahead` after this one."""
    monday = today - timedelta(days=today.weekday()) + timedelta(weeks=weeks_ahead)
    return monday + timedelta(days=weekday)


def human(d: date) -> str:
    return d.strftime("%A %d %B")


# ---------------------------------------------------------------- reading dates from an email (offline rules)
def _year_for(month: int, day: int, today: date) -> date | None:
    for y in (today.year, today.year + 1):
        try:
            d = date(y, month, day)
        except ValueError:
            return None
        if d >= today - timedelta(days=60):
            return d
    return None


def parse_dates(text: str, today: date) -> tuple[date | None, date | None]:
    t = text.lower()
    found: list[date] = []
    for y, m, d in re.findall(r"\b(20\d\d)-(\d\d)-(\d\d)\b", t):
        try:
            found.append(date(int(y), int(m), int(d)))
        except ValueError:
            pass
    month_re = "|".join(sorted(MONTHS, key=len, reverse=True))
    # "9 to 13 November", "9-13 November"
    for a, b, mon in re.findall(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s*(?:-|–|to|until|till)\s*(?:\w+day\s+)?(\d{{1,2}})(?:st|nd|rd|th)?\s+({month_re})\b", t):
        for day in (a, b):
            d = _year_for(MONTHS[mon], int(day), today)
            if d:
                found.append(d)
    # "9 November", "Monday 09 November"
    for day, mon in re.findall(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:of\s+)?({month_re})\b", t):
        d = _year_for(MONTHS[mon], int(day), today)
        if d:
            found.append(d)
    # "November 9"
    for mon, day in re.findall(rf"\b({month_re})\s+(\d{{1,2}})(?:st|nd|rd|th)?\b", t):
        d = _year_for(MONTHS[mon], int(day), today)
        if d:
            found.append(d)
    if not found:
        if "tomorrow" in t:
            found.append(today + timedelta(days=1))
        elif re.search(r"\btoday\b", t):
            found.append(today)
        m = re.search(r"next week", t)
        if m and not found:
            found += [week_day(today, 1, 0), week_day(today, 1, 4)]
    if not found:
        return None, None
    start, end = min(found), max(found)
    n = re.search(r"\bfor\s+(\d{1,2}|one|two|three|four|five)\s+(?:working\s+)?days?\b", t)
    if n and start == end:
        words = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5}
        k = int(n.group(1)) if n.group(1).isdigit() else words[n.group(1)]
        start = next_workday(start)
        end = add_workdays(start, k - 1)
    return start, end


SICK_WORDS = ["sick", "ill ", "illness", "doctor", "medical", "certificate", "fever", "flu", "hospital", "malade"]
LEAVE_WORDS = ["leave", "day off", "days off", "vacation", "holiday", "time off", "congé", "conge", "absent",
               "absence", "off work"] + SICK_WORDS
QUESTION_WORDS = ["?", "how many", "can i", "could i", "is it possible", "what is", "policy", "do i have"]


def looks_like_leave_request(text: str) -> bool:
    t = text.lower()
    asks = any(w in t for w in ["request", "would like", "i'd like", "i want", "can i take", "could i take",
                                "may i take", "i need", "i will be", "i'll be", "i am sick", "i'm sick",
                                "i am ill", "i'm ill", "take ", "book "])
    return any(w in t for w in LEAVE_WORDS) and asks and parse_dates(t, date.today())[0] is not None


def leave_type_of(text: str) -> LeaveType:
    t = f" {text.lower()} "
    return LeaveType.SICK if any(w in t for w in SICK_WORDS) else LeaveType.ANNUAL


# ---------------------------------------------------------------- balances and presence
def _approved(db: Session) -> list[LeaveRequest]:
    return list(db.exec(select(LeaveRequest).where(LeaveRequest.status == LeaveStatus.APPROVED)).all())


def days_used(db: Session, emp_id: int, kind: LeaveType, year: int, exclude_id: int | None = None) -> int:
    total = 0
    for r in _approved(db):
        if r.employee_id != emp_id or r.type != kind or r.id == exclude_id:
            continue
        total += len([d for d in workdays(r.start, r.end) if d.year == year])
    return total


def absent_on(db: Session, day: date, approved: list[LeaveRequest] | None = None) -> dict[int, LeaveRequest]:
    approved = approved if approved is not None else _approved(db)
    return {r.employee_id: r for r in approved if r.start <= day <= r.end}


def team_members(db: Session, team: str) -> list[Employee]:
    return list(db.exec(select(Employee).where(Employee.team == team)).all())


def presence(db: Session, team: str, day: date, extra_absent: set[int] | None = None,
             approved: list[LeaveRequest] | None = None) -> tuple[int, int]:
    members = team_members(db, team)
    away = set(absent_on(db, day, approved)) | (extra_absent or set())
    present = len([m for m in members if m.id not in away])
    return present, len(members)


def _worst_day(db: Session, emp: Employee, start: date, end: date, approved) -> tuple[float, date | None, int, int]:
    worst, worst_day, wp, wt = 1.0, None, 0, 0
    for d in workdays(start, end):
        p, t = presence(db, emp.team, d, {emp.id}, approved)
        pct = p / t if t else 1
        if pct < worst:
            worst, worst_day, wp, wt = pct, d, p, t
    return worst, worst_day, wp, wt


def alternatives(db: Session, emp: Employee, start: date, end: date, count: int = 2) -> list[dict]:
    """Closest periods of the same length (after the requested start) where the team stays >= 70%."""
    length = len(workdays(start, end))
    approved = _approved(db)
    out, s = [], next_workday(start + timedelta(days=1))
    for _ in range(60):
        e = add_workdays(s, max(0, length - 1))
        worst, _, _, _ = _worst_day(db, emp, s, e, approved)
        if worst >= settings.team_min_presence:
            out.append({"start": s.isoformat(), "end": e.isoformat(), "label": f"{human(s)} → {human(e)}",
                        "min_presence": round(worst * 100)})
            if len(out) >= count:
                break
            s = add_workdays(e, 1)
        else:
            s = add_workdays(s, 1)
    return out


def evaluate(db: Session, req: LeaveRequest) -> dict:
    """Recommendation for HR (rules in code, explained). HR decides."""
    emp = db.get(Employee, req.employee_id)
    days = len(workdays(req.start, req.end))
    year = req.start.year
    limit, sick_limit, min_p = settings.annual_leave_days, settings.sick_alert_days, settings.team_min_presence
    approved = _approved(db)
    reasons, alts = [], []
    worst, worst_day, wp, wt = _worst_day(db, emp, req.start, req.end, approved)
    annual_used = days_used(db, emp.id, LeaveType.ANNUAL, year, exclude_id=req.id)
    sick_used = days_used(db, emp.id, LeaveType.SICK, year, exclude_id=req.id)

    if req.type == LeaveType.SICK:
        total = sick_used + days
        reasons.append("Sick leave is a right: team staffing rules do not apply.")
        if total > sick_limit:
            rec = "sick_alert"
            reasons.append(f"{total} sick days this year (above {sick_limit}). Handbook §3: HR should contact "
                           f"the employee about support, occupational health and an adjusted return.")
        else:
            rec = "approve"
            reasons.append(f"{total}/{sick_limit} sick days this year after this absence.")
        reasons.append("Remember to ask for the medical certificate (within 48 h). No diagnosis is stored.")
    else:
        after = annual_used + days
        if annual_used >= limit or after > limit:
            rec = "over_limit"
            reasons.append(f"Already used {annual_used}/{limit} days; this request ({days} days) would make "
                           f"{after}/{limit}." + (f" Only {max(0, limit - annual_used)} day(s) left." if annual_used < limit else ""))
            reasons.append("Suggested: decline politely and offer a meeting if the situation is exceptional (§2).")
        elif worst < min_p:
            rec = "move"
            reasons.append(f"{emp.team} would be at {round(worst * 100)}% on {human(worst_day)} "
                           f"({wp} of {wt} at work) - below {round(min_p * 100)}%.")
            alts = alternatives(db, emp, req.start, req.end)
            if alts:
                reasons.append("Closest dates that keep the team at 70% or more: " +
                               "; ".join(a["label"] for a in alts) + ".")
        else:
            rec = "approve"
            reasons.append(f"{after}/{limit} days used after this leave ({limit - after} left).")
            reasons.append(f"{emp.team} stays at {round(worst * 100)}% or more every day.")
    overlap = [r for r in db.exec(select(LeaveRequest).where(
        LeaveRequest.employee_id != emp.id, LeaveRequest.status == LeaveStatus.PENDING,
        LeaveRequest.id != req.id)).all()
        if r.start <= req.end and req.start <= r.end and db.get(Employee, r.employee_id).team == emp.team]
    if overlap and req.type == LeaveType.ANNUAL:
        reasons.append(f"Note: {len(overlap)} other pending request(s) in {emp.team} overlap these dates.")
    return {
        "recommendation": rec,
        "reasons": reasons,
        "days": days,
        "annual_used": annual_used,
        "annual_left": max(0, limit - annual_used),
        "sick_used": sick_used,
        "min_presence": round(worst * 100),
        "worst_day": worst_day.isoformat() if worst_day else None,
        "alternatives": alts,
    }


def request_json(db: Session, r: LeaveRequest, with_eval: bool = True) -> dict:
    emp = db.get(Employee, r.employee_id)
    out = {
        "id": r.id, "employee_id": r.employee_id, "employee_name": emp.name if emp else "", "team": emp.team if emp else "",
        "email": emp.email if emp else "", "type": r.type.value, "start": r.start.isoformat(), "end": r.end.isoformat(),
        "label": f"{human(r.start)} → {human(r.end)}" if r.start != r.end else human(r.start),
        "status": r.status.value, "email_id": r.email_id, "reason_from_employee": r.reason_from_employee,
        "hr_note": r.hr_note, "extracted_by": r.extracted_by, "created_at": r.created_at.isoformat(),
    }
    if with_eval and r.status == LeaveStatus.PENDING:
        out["evaluation"] = evaluate(db, r)
    return out


def today_or_next_workday() -> date:
    return next_workday(date.today())


def overview(db: Session) -> dict:
    day = today_or_next_workday()
    employees = list(db.exec(select(Employee).order_by(Employee.team, Employee.name)).all())
    approved = _approved(db)
    away = absent_on(db, day, approved)
    teams: dict[str, dict] = {}
    for e in employees:
        t = teams.setdefault(e.team, {"team": e.team, "size": 0, "working": 0, "away": []})
        t["size"] += 1
        if e.id in away:
            t["away"].append({"name": e.name, "type": away[e.id].type.value})
        else:
            t["working"] += 1
    for t in teams.values():
        t["presence"] = round(100 * t["working"] / t["size"]) if t["size"] else 100
        t["below_min"] = t["presence"] < settings.team_min_presence * 100
    on_annual = sum(1 for r in away.values() if r.type == LeaveType.ANNUAL)
    on_sick = sum(1 for r in away.values() if r.type == LeaveType.SICK)
    total = len(employees)
    year = day.year
    rows, alerts = [], []
    for e in employees:
        a = days_used(db, e.id, LeaveType.ANNUAL, year)
        s = days_used(db, e.id, LeaveType.SICK, year)
        rows.append({"id": e.id, "name": e.name, "email": e.email, "team": e.team, "title": e.title,
                     "annual_used": a, "annual_left": max(0, settings.annual_leave_days - a), "sick_used": s,
                     "today": away[e.id].type.value if e.id in away else "working"})
        if s > settings.sick_alert_days:
            alerts.append({"kind": "sick", "employee_id": e.id, "name": e.name, "team": e.team,
                           "text": f"{e.name} ({e.team}) has {s} sick days this year (above {settings.sick_alert_days}). "
                                   f"Contact them about support, occupational health and an adjusted return (§3)."})
        if a >= settings.annual_leave_days:
            alerts.append({"kind": "limit", "employee_id": e.id, "name": e.name, "team": e.team,
                           "text": f"{e.name} ({e.team}) has used all {settings.annual_leave_days} leave days for {year}."})
    # teams that will drop below the minimum in the next 10 working days (approved leave only)
    d = day
    for _ in range(10):
        for team in teams:
            p, tot = presence(db, team, d, approved=approved)
            if tot and p / tot < settings.team_min_presence:
                alerts.append({"kind": "staffing", "team": team, "date": d.isoformat(),
                               "text": f"{team} at {round(100 * p / tot)}% on {human(d)} ({p} of {tot} at work)."})
        d = add_workdays(d, 1)
    pending = db.exec(select(LeaveRequest).where(LeaveRequest.status == LeaveStatus.PENDING)
                      .order_by(LeaveRequest.start)).all()
    recent = db.exec(select(LeaveRequest).where(LeaveRequest.email_id != None,  # noqa: E711
                                                LeaveRequest.status != LeaveStatus.PENDING)
                     .order_by(LeaveRequest.id.desc())).all()[:10]
    return {
        "day": day.isoformat(), "day_label": human(day), "is_today": day == date.today(),
        "total": total, "working": total - len(away), "on_annual": on_annual, "on_sick": on_sick,
        "working_pct": round(100 * (total - len(away)) / total) if total else 100,
        "teams": sorted(teams.values(), key=lambda t: t["presence"]),
        "requests": [request_json(db, r) for r in pending],
        "recent": [request_json(db, r, with_eval=False) for r in recent],
        "alerts": alerts,
        "employees": rows,
        "rules": {"annual_leave_days": settings.annual_leave_days, "sick_alert_days": settings.sick_alert_days,
                  "team_min_presence": round(settings.team_min_presence * 100)},
    }


def leave_on_day_for_calendar(db: Session, start: date, end: date) -> list[dict]:
    out = []
    for r in _approved(db):
        if r.end < start or r.start > end:
            continue
        emp = db.get(Employee, r.employee_id)
        d = max(r.start, start)
        while d <= min(r.end, end):
            if is_workday(d):
                out.append({"id": f"leave-{r.id}-{d.isoformat()}", "kind": "leave", "date": d.isoformat(),
                            "title": f"{emp.name} - {'sick' if r.type == LeaveType.SICK else 'on leave'}",
                            "status": "approved", "team": emp.team})
            d += timedelta(days=1)
    return out


def now_date() -> date:
    return datetime.now().date()
