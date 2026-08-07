from __future__ import annotations

import base64

from fastapi.testclient import TestClient

from backend.app.main import create_app


def _authorization(password: str) -> dict[str, str]:
    token = base64.b64encode(f"fantacalcio:{password}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def test_shared_mode_requires_password_and_blocks_mutations(monkeypatch) -> None:
    monkeypatch.setenv("FANTACALCIO_SHARE_PASSWORD", "segreto-test")
    monkeypatch.setenv("FANTACALCIO_READ_ONLY", "1")
    client = TestClient(create_app())

    assert client.get("/health").status_code == 401
    headers = _authorization("segreto-test")
    assert client.get("/health", headers=headers).status_code == 200
    assert client.post("/api/v1/ranking-configs", headers=headers, json={}).status_code == 403
    # Il calcolo non scrive nel database e resta disponibile in condivisione.
    assert client.post(
        "/api/v1/rankings/calculate", headers=headers, json={}
    ).status_code == 422
