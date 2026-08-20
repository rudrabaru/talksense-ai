from unittest.mock import MagicMock, patch
patch("transformers.pipeline", return_value=MagicMock()).start()

import pytest
from fastapi.testclient import TestClient
from main import app
import json
import time

@pytest.fixture(autouse=True)
def mock_ml_models():
    with patch("audio.transcriber.get_transcriber") as mock_t, \
         patch("services.post_session_pipeline.LLMEngine") as mock_llm, \
         patch("services.nlp_engine.pipeline") as mock_nlp_pipeline, \
         patch("audio.vad.get_vad") as mock_vad:
         
        mock_t.return_value = MagicMock()
        
        # Mock LLMEngine to return valid JSON
        mock_llm_instance = MagicMock()
        mock_llm_instance.generate_structured.return_value = '{"executive_summary": "Test", "decisions": [], "action_items": []}'
        mock_llm_instance.generate.return_value = '{"executive_summary": "Test", "decisions": [], "action_items": []}'
        mock_llm.return_value = mock_llm_instance
        
        mock_nlp_pipeline.return_value = MagicMock()
        mock_vad.return_value = MagicMock()
        yield

@pytest.fixture
def client():
    with TestClient(app) as c:
        yield c

def test_normal_successful_session(client: TestClient):
    # 1. Create client
    r = client.post("/clients", json={"name": "E2E Normal", "industry": "Tech"})
    client_id = r.json()["id"]
    
    # 2. Create session
    r = client.post("/sessions", json={
        "client_id": client_id,
        "mode": "meeting",
        "host_embedding": [0.0] * 512
    })
    session_id = r.json()["session_id"]
    
    # 3. Stream audio
    with client.websocket_connect(f"/ws/audio/{session_id}") as websocket:
        # Inject some fake transcript
        websocket.send_text("inject:Speaker A|Hello, this is a normal test.")
        time.sleep(0.5)
        # End session normally
        websocket.send_text("end")
        
    # 4. Polling race check
    for _ in range(10):
        r = client.get(f"/dashboard/{session_id}")
        data = r.json()
        if data.get("post_session_ai") or data.get("speaker_attribution_status") in ["completed", "skipped", "failed"]:
            break
        time.sleep(1)
        
    assert data["status"] == "completed"
    assert data["speaker_attribution_status"] == "completed"
    assert "post_session_ai" in data
    print("Normal session verified!")

def test_empty_transcript(client: TestClient):
    r = client.post("/clients", json={"name": "E2E Empty", "industry": "Tech"})
    client_id = r.json()["id"]
    
    r = client.post("/sessions", json={
        "client_id": client_id,
        "mode": "meeting",
        "host_embedding": [0.0] * 512
    })
    session_id = r.json()["session_id"]
    
    with client.websocket_connect(f"/ws/audio/{session_id}") as websocket:
        # Send nothing, just end
        websocket.send_text("end")
        try:
            websocket.receive()
        except Exception:
            pass
        
    for _ in range(10):
        r = client.get(f"/dashboard/{session_id}")
        data = r.json()
        if data.get("speaker_attribution_status") in ["completed", "skipped", "failed"]:
            break
        time.sleep(1)
        
    assert data["status"] == "completed"
    assert data["speaker_attribution_status"] == "skipped"
    assert "post_session_ai" in data # Fallback empty result should be present
    print("Empty transcript verified!")

def test_rest_delete_race(client: TestClient):
    r = client.post("/clients", json={"name": "E2E Race", "industry": "Tech"})
    client_id = r.json()["id"]
    
    r = client.post("/sessions", json={
        "client_id": client_id,
        "mode": "meeting",
        "host_embedding": [0.0] * 512
    })
    session_id = r.json()["session_id"]
    
    with client.websocket_connect(f"/ws/audio/{session_id}") as websocket:
        websocket.send_text("inject:Speaker A|Testing REST race.")
        time.sleep(0.5)
        
        # Call REST DELETE while WS is active
        r = client.delete(f"/sessions/{session_id}")
        assert r.status_code == 200
        
        # Expect the websocket to be closed by server
        try:
            websocket.receive()
        except Exception:
            pass
            
    for _ in range(10):
        r = client.get(f"/dashboard/{session_id}")
        data = r.json()
        if data.get("speaker_attribution_status") in ["completed", "skipped", "failed"]:
            break
        time.sleep(1)
        
    assert data["status"] == "completed"
    assert data["speaker_attribution_status"] == "completed"
    assert "post_session_ai" in data
    print("REST Race verified!")
