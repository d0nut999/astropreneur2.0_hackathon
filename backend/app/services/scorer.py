"""Score candidate against job rubric."""


def score_candidate(anonymized_profile: dict, rubric: dict) -> dict:
    """
    Score candidate using LLM and rubric.
    Stub: Returns mock result.
    Real implementation will call llm.complete_json().
    """
    # TODO: Use LLM to score each criterion
    return {
        "criteria": {
            "experience": 8,
            "skills": 7,
            "education": 6,
        },
        "total": 7.0,
        "evidence_quotes": {
            "experience": "5 years in backend development",
        },
    }
