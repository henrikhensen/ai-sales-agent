from fastapi.testclient import TestClient

from backend.main import app

# No context manager → lifespan (and thus DB init) does not run; the demo
# endpoint uses the mock LLM provider and touches no external services.
client = TestClient(app)


def test_demo_endpoint_returns_mock_result():
    response = client.post("/api/v1/agents/demo", json={"message": "hello"})

    assert response.status_code == 200
    data = response.json()
    assert data["agent"] == "demo"
    assert data["provider"] == "mock"

    expected_prompt = "Message: hello"
    assert data["output"]["reply"] == f"[mock] {expected_prompt}"
    assert data["output"]["char_count"] == len(expected_prompt)


def test_demo_endpoint_validates_empty_message():
    response = client.post("/api/v1/agents/demo", json={"message": ""})
    assert response.status_code == 422
