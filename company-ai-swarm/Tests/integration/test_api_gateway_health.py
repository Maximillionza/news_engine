"""Phase 0 exit-criteria test: the dev environment builds and serves a health-check endpoint."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "apps" / "api_gateway"))

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health_endpoint_responds() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "api_gateway"}
