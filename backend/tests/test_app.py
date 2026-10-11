import os

# Point the app at ports where nothing is running, so tests need no real database or Redis.
# These must be set before importing the app, because app.py reads them at import time.
os.environ["APP_VERSION"] = "test-version"
os.environ["DB_HOST"] = "127.0.0.1"
os.environ["DB_PORT"] = "1"
os.environ["REDIS_HOST"] = "127.0.0.1"
os.environ["REDIS_PORT"] = "1"

import pytest

from app import app


@pytest.fixture
def client():
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        yield test_client


def test_health_reports_version(client):
    response = client.get("/api/health")
    assert response.get_json()["version"] == "test-version"


def test_health_returns_503_when_dependencies_are_down(client):
    response = client.get("/api/health")
    body = response.get_json()
    assert response.status_code == 503
    assert body["postgres"] == "error"
    assert body["redis"] == "error"


def test_unknown_route_returns_404(client):
    assert client.get("/api/does-not-exist").status_code == 404


def test_visit_rejects_get(client):
    assert client.get("/api/visit").status_code == 405