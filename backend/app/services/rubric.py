"""Job rubrics: job-related criteria only, with weights that add up to 100.

A rubric is stored in Job.rubric_json as:
{"criteria": [{"key", "label", "weight", "must_have", "description", "keywords": [...]}, ...]}
`keywords` are only used by the offline scorer (when no AI is available).
"""

JUNIOR_BACKEND_RUBRIC = {
    "criteria": [
        {"key": "python_backend", "label": "Python & a backend framework", "weight": 30, "must_have": True,
         "description": "Python plus at least one web framework (FastAPI, Django or Flask).",
         "keywords": ["python", "fastapi", "django", "flask", "rest api", "backend"]},
        {"key": "databases", "label": "Databases & SQL", "weight": 20, "must_have": False,
         "description": "Relational databases and SQL (PostgreSQL, MySQL, SQLite).",
         "keywords": ["sql", "postgresql", "mysql", "sqlite", "database"]},
        {"key": "experience", "label": "Relevant experience", "weight": 20, "must_have": False,
         "description": "Internships or jobs building software. 0-2 years expected; internships count.",
         "keywords": ["intern", "developer", "engineer", "built", "users", "backend"]},
        {"key": "projects", "label": "Projects & achievements", "weight": 15, "must_have": False,
         "description": "Personal/academic projects that show real building skills (deployed apps, APIs).",
         "keywords": ["project", "deployed", "api", "tracker", "website", "authentication"]},
        {"key": "tools", "label": "Git, Docker & testing", "weight": 15, "must_have": False,
         "description": "Version control, containers, automated tests, CI.",
         "keywords": ["git", "docker", "pytest", "test", "github actions", "ci"]},
    ]
}

GENERIC_RUBRIC = {
    "criteria": [
        {"key": "skills", "label": "Required skills", "weight": 40, "must_have": True,
         "description": "Skills explicitly required in the job description.", "keywords": []},
        {"key": "experience", "label": "Relevant experience", "weight": 30, "must_have": False,
         "description": "Work experience related to the role.", "keywords": ["experience", "intern"]},
        {"key": "projects", "label": "Projects & achievements", "weight": 20, "must_have": False,
         "description": "Concrete results and projects.", "keywords": ["project", "built", "led"]},
        {"key": "education", "label": "Education & certifications", "weight": 10, "must_have": False,
         "description": "Relevant degree or certifications (or equivalent practice).", "keywords": ["degree", "bachelor", "master", "certificate"]},
    ]
}


def normalize_rubric(rubric_json: dict | None) -> list[dict]:
    """Always return a clean list of criteria whose weights sum to 100.

    Accepts the new format and the old {"experience": {"weight": 0.3}, ...} format.
    """
    rubric_json = rubric_json or {}
    if "criteria" in rubric_json:
        crit = [dict(c) for c in rubric_json["criteria"]]
    elif rubric_json:
        crit = [{"key": k, "label": k.replace("_", " ").title(), "weight": float(v.get("weight", 1)),
                 "must_have": False, "description": "", "keywords": []} for k, v in rubric_json.items()]
    else:
        crit = [dict(c) for c in GENERIC_RUBRIC["criteria"]]
    total = sum(float(c.get("weight", 0)) for c in crit) or 1
    for c in crit:
        c["weight"] = round(float(c.get("weight", 0)) * 100 / total, 2)
        c.setdefault("must_have", False)
        c.setdefault("description", "")
        c.setdefault("keywords", [])
    return crit
