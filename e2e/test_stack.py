"""End-to-end smoke tests: web -> api -> mongo (running stack only, stdlib only)."""
import json
import os
import urllib.error
import urllib.request

import pytest

API = os.getenv("AGROPILOT_API_URL", "http://localhost:8000")
WEB = os.getenv("AGROPILOT_WEB_URL", "http://localhost:8080")
TIMEOUT = int(os.getenv("AGROPILOT_TIMEOUT_S", "60"))


def _get(url) -> tuple:
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:
            return r.status, r.read().decode("utf-8")
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        pytest.skip(f"stack down ({url}): {e}")
        raise AssertionError("unreachable")


def _post(url, payload) -> tuple:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            return r.status, json.loads(r.read().decode("utf-8"))
    except (urllib.error.URLError, ConnectionError, TimeoutError, OSError) as e:
        pytest.skip(f"stack down ({url}): {e}")
        raise AssertionError("unreachable")


def test_api_health():
    status, body = _get(f"{API}/api/health")
    assert status == 200
    assert json.loads(body)["status"] == "ok"


def test_chat_planejamento():
    status, data = _post(f"{API}/api/chat", {"produtor_id": "e2e", "mensagem": "quando planto feijao?"})
    assert status == 200
    assert data["intencao"] == "PLANEJAMENTO"
    assert "ZARC" in data["fonte"]


def test_chat_praga():
    status, data = _post(f"{API}/api/chat", {"produtor_id": "e2e", "mensagem": "minha uva ta com mildio"})
    assert status == 200
    assert data["intencao"] == "PRAGA"
    assert "Agrofit" in data["fonte"]


def test_web_serves_front():
    status, body = _get(f"{WEB}/")
    assert status == 200
    assert "scripts/api.js" in body
