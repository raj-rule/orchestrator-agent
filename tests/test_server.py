import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
from server import app
from security import sign_session_id

client = TestClient(app)

def test_root_endpoint():
    """Verify the health check endpoint returns 200."""
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"message": "CriticAI Swarm API is running! 🚀"}

def test_create_session_success():
    """Verify that a signed session is successfully created and returned."""
    response = client.post("/api/sessions")
    assert response.status_code == 200
    data = response.json()
    assert "session_id" in data
    assert "." in data["session_id"]  # Check that signature is appended

def test_get_session_invalid_signature():
    """Verify that retrieval fails with 403 if the session signature is invalid."""
    response = client.get("/api/sessions/invalid-session-id-no-sig")
    assert response.status_code == 403
    assert response.json()["detail"] == "Invalid session signature"

@patch("security.BACKEND_TOKEN", "test-token")
def test_backend_token_unauthorized():
    """Verify that requests are blocked with 401 if a backend token is required but missing/invalid."""
    # Try creating session without token
    response = client.post("/api/sessions")
    assert response.status_code == 401
    
    # Try creating session with wrong token
    headers = {"X-Backend-Token": "wrong-token"}
    response = client.post("/api/sessions", headers=headers)
    assert response.status_code == 401

    # Try creating session with correct token
    headers = {"X-Backend-Token": "test-token"}
    response = client.post("/api/sessions", headers=headers)
    assert response.status_code == 200

def test_get_session_not_found():
    """Verify that a 404 is returned if a signed session is valid but not stored in LangGraph state database."""
    signed_id = sign_session_id("non-existent-uuid")
    
    # Mock swarm_app.get_state to return a snapshot with empty values
    mock_snapshot = MagicMock()
    mock_snapshot.values = {}
    
    with patch("server.swarm_app.get_state", return_value=mock_snapshot):
        response = client.get(f"/api/sessions/{signed_id}")
        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"

def test_get_session_found():
    """Verify that session state is correctly returned when it exists in LangGraph checkpointer."""
    signed_id = sign_session_id("existing-uuid")
    
    # Mock swarm_app.get_state to return state values
    mock_snapshot = MagicMock()
    mock_snapshot.values = {
        "deliverables": {"Copywriter": "Draft text"},
        "execution_plan": [{"agent_role": "Copywriter"}],
        "agent_statuses": {"Copywriter": "completed"}
    }
    
    with patch("server.swarm_app.get_state", return_value=mock_snapshot):
        response = client.get(f"/api/sessions/{signed_id}")
        assert response.status_code == 200
        data = response.json()
        assert data["deliverables"] == {"Copywriter": "Draft text"}
        assert data["execution_plan"] == [{"agent_role": "Copywriter"}]
        assert data["agent_statuses"] == {"Copywriter": "completed"}
