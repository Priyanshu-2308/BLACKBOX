import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.config import SERVER_SECRET, ENV_PATH


client = TestClient(app)


def test_server_secret_exists_and_gitignored():
    assert SERVER_SECRET is not None
    assert len(SERVER_SECRET) >= 32
    # Verify .env exists
    assert ENV_PATH.exists()
    # Verify .gitignore contains .env
    gitignore_path = ENV_PATH.parent / ".gitignore"
    assert gitignore_path.exists()
    with open(gitignore_path, "r", encoding="utf-8") as f:
        content = f.read()
    assert ".env" in content


def test_today_api_does_not_leak_rule_data():
    resp = client.get("/api/today")
    assert resp.status_code == 200
    data = resp.json()

    # Public fields allowed
    assert "id" in data
    assert "tier" in data
    assert "input_type" in data
    assert "topics" in data
    assert "seconds_until_reset" in data

    # Secrecy: Rule internals must NEVER appear
    forbidden = ["rule_spec", "rule_spec_json", "pipeline", "params", "branch_true", "branch_false", "seed", "fingerprint"]
    for key in forbidden:
        assert key not in data, f"Leaked forbidden key '{key}' in /api/today"


def test_library_api_does_not_leak_rule_data():
    resp = client.get("/api/library?limit=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "questions" in data
    assert len(data["questions"]) > 0

    forbidden = ["rule_spec", "rule_spec_json", "pipeline", "params", "branch_true", "branch_false", "seed", "fingerprint"]
    for q in data["questions"]:
        for key in forbidden:
            assert key not in q, f"Leaked forbidden key '{key}' in /api/library"


def test_question_meta_does_not_leak_rule_data():
    lib_resp = client.get("/api/library?limit=1")
    q_id = lib_resp.json()["questions"][0]["id"]

    resp = client.get(f"/api/question/{q_id}")
    assert resp.status_code == 200
    data = resp.json()

    forbidden = ["rule_spec", "rule_spec_json", "pipeline", "params", "branch_true", "branch_false", "seed", "fingerprint"]
    for key in forbidden:
        assert key not in data, f"Leaked forbidden key '{key}' in /api/question/{q_id}"


def test_rule_reveal_strictly_forbidden_when_unsolved():
    lib_resp = client.get("/api/library?limit=1")
    q_id = lib_resp.json()["questions"][0]["id"]

    # Attempt to reveal rule for unsolved question with a fresh user
    headers = {"X-Username": "tester_unsolved"}
    resp = client.get(f"/api/reveal/{q_id}", headers=headers)
    assert resp.status_code == 403
    assert "Access Denied" in resp.json()["detail"]


def test_query_error_does_not_leak_internal_traceback():
    lib_resp = client.get("/api/library?limit=1")
    q_id = lib_resp.json()["questions"][0]["id"]

    # Send invalid type to trigger validation error
    resp = client.post("/api/query", json={"question_id": q_id, "input_value": {"bad": "object"}})
    assert resp.status_code == 400
    detail = resp.json()["detail"]
    # Ensure no python file paths or line numbers
    assert "File " not in detail
    assert "Traceback" not in detail
