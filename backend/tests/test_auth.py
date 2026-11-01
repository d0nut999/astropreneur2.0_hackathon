"""Login & web security tests."""
from fastapi.testclient import TestClient

from app.main import app
from tests.conftest import TEST_EMAIL, TEST_PASSWORD, ensure_test_user, logged_in_client


def test_hr_pages_require_login():
    c = TestClient(app)
    for path in ["/emails", "/digest/today", "/approvals", "/audit", "/jobs", "/candidates?job_id=1", "/events"]:
        assert c.get(path).status_code == 401, path


def test_actions_require_login():
    c = TestClient(app)
    assert c.post("/emails/load_demo").status_code == 401
    assert c.post("/candidates/1/shortlist").status_code == 401
    assert c.post("/approvals/1/approve").status_code == 401


def test_public_routes_stay_public():
    c = TestClient(app)
    assert c.get("/health").status_code == 200
    assert c.get("/portal/not-a-real-token").status_code == 404  # portal reachable, token checked


def test_wrong_password_is_rejected_with_generic_message():
    ensure_test_user()
    c = TestClient(app)
    r1 = c.post("/auth/login", json={"email": TEST_EMAIL, "password": "wrong"})
    r2 = c.post("/auth/login", json={"email": "nobody@nowhere.test", "password": "wrong"})
    assert r1.status_code == r2.status_code == 401
    assert r1.json() == r2.json()  # no hint whether the account exists


def test_session_cookie_is_httponly():
    ensure_test_user()
    c = TestClient(app)
    r = c.post("/auth/login", json={"email": TEST_EMAIL, "password": TEST_PASSWORD})
    cookie = r.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=lax" in cookie


def test_csrf_header_required_for_changes():
    c = logged_in_client()
    assert c.get("/emails").status_code == 200          # reading: cookie is enough
    del c.headers["X-CSRF-Token"]
    assert c.post("/emails/load_demo").status_code == 403  # changing: CSRF header required
    c.headers["X-CSRF-Token"] = "forged"
    assert c.post("/emails/load_demo").status_code == 403


def test_logout_ends_session():
    c = logged_in_client()
    assert c.get("/auth/me").status_code == 200
    c.post("/auth/logout")
    assert c.get("/auth/me").status_code == 401


def test_brute_force_lockout():
    ensure_test_user()
    c = TestClient(app)
    for _ in range(5):
        c.post("/auth/login", json={"email": "victim@fictional-company.test", "password": "guess"})
    r = c.post("/auth/login", json={"email": "victim@fictional-company.test", "password": "guess"})
    assert r.status_code == 429


def test_audit_log_is_admin_only():
    from tests.conftest import admin_client, logged_in_client
    assert logged_in_client().get("/audit").status_code == 403   # recruiter: no access to the trail of their own actions
    r = admin_client().get("/audit")
    assert r.status_code == 200 and isinstance(r.json(), list)
