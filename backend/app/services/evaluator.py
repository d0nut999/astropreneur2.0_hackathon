"""Evaluate interview responses."""


def evaluate_interview(transcript: str, questions: list[dict], rubric: dict) -> dict:
    """
    Evaluate interview using LLM.
    Stub: Returns mock result.
    Real implementation will call llm.complete_json().
    """
    # TODO: Use LLM to evaluate responses
    return {
        "per_question_scores": {
            "q1": 8,
            "q2": 7,
        },
        "recommendation": "Advance",
        "confidence": 0.85,
        "summary": "Strong technical skills and communication",
    }
