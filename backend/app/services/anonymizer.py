"""Anonymize candidate profile."""


def anonymize_profile(parsed_cv: dict) -> dict:
    """
    Anonymize CV: remove name, email, contact info.
    Stub: Returns mock result.
    """
    # TODO: Strip PII from parsed_cv
    return {
        "experience_years": 5,
        "education": "Bachelor's in Computer Science",
        "key_skills": ["Python", "FastAPI", "SQL"],
        "relevant_experience": "5 years in backend development",
    }
