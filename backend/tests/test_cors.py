"""CORS is what lets the Vite dev server talk to the API at all.

The origin list is intentionally two explicit localhost origins rather than a
wildcard. These assertions exist so a later change cannot loosen the policy
without a test failing.
"""

from fastapi.testclient import TestClient

from app.main import app

DEV_ORIGIN = "http://localhost:5173"
LOOPBACK_ORIGIN = "http://127.0.0.1:5173"

client = TestClient(app)


def test_preflight_from_the_vite_dev_server_is_allowed():
    response = client.options(
        "/health",
        headers={
            "Origin": DEV_ORIGIN,
            "Access-Control-Request-Method": "PATCH",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DEV_ORIGIN
    allowed_methods = response.headers["access-control-allow-methods"]
    for method in ("GET", "POST", "PATCH", "PUT", "DELETE"):
        assert method in allowed_methods


def test_preflight_from_the_loopback_origin_is_allowed():
    response = client.options(
        "/health",
        headers={
            "Origin": LOOPBACK_ORIGIN,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )

    assert response.headers["access-control-allow-origin"] == LOOPBACK_ORIGIN


def test_a_simple_request_from_the_dev_server_carries_the_allow_origin_header():
    response = client.get("/health", headers={"Origin": DEV_ORIGIN})

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == DEV_ORIGIN


def test_the_pdf_filename_header_is_exposed_to_javascript():
    response = client.get("/health", headers={"Origin": DEV_ORIGIN})

    assert "Content-Disposition" in response.headers["access-control-expose-headers"]


def test_credentials_are_not_allowed():
    response = client.get("/health", headers={"Origin": DEV_ORIGIN})

    assert "access-control-allow-credentials" not in response.headers


def test_an_unlisted_origin_gets_no_allow_origin_header():
    """The server still answers; the browser is what refuses to hand the body over."""
    response = client.get("/health", headers={"Origin": "http://evil.example"})

    assert "access-control-allow-origin" not in response.headers


def test_a_request_with_no_origin_still_works():
    """curl, the test suite, and server-to-server callers send no Origin header."""
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
