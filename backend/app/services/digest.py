"""Generate daily digest."""


def generate_digest() -> dict:
    """
    Generate daily summary of emails and pending approvals.
    Stub: Returns mock data.
    """
    # TODO: Query high-urgency emails, pending approvals, applications
    return {
        "high_urgency_count": 2,
        "needs_human_count": 3,
        "pending_approvals_count": 5,
        "pending_applications_count": 10,
        "summary": "Daily digest stub",
    }
