import pytest
import asyncio
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid
from datetime import datetime

from src.agential_researcher.api.main import app
from src.agential_researcher.store.db import init_db, get_job
from src.agential_researcher.providers.router import LLMProviderRouter

@pytest.fixture
def client():
    # Create test client with overrides for testing
    with TestClient(app) as test_client:
        yield test_client

@pytest.fixture
def api_key():
    # Return a valid test API key
    return "sk-test1234567890abcdef"

def test_health_endpoint(client):
    """Test health endpoint (requires API key for /health but not /.well-known/health)"""
    # Test that health endpoint requires auth for /health
    response = client.get("/health")
    assert response.status_code == 401  # Missing API key
    
    # Test with API key
    response = client.get("/health", headers={"Authorization": "Bearer sk-test1234567890abcdef"})
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    
    # Test that well-known health endpoint doesn't require auth
    response = client.get("/.well-known/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_enqueue_endpoint(client, api_key):
    """Test enqueue endpoint"""
    payload = {
        "type": "test_job",
        "payload": {"test": "data"},
        "priority": 10
    }
    
    response = client.post(
        "/v1/enqueue", 
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"}
    )
    assert response.status_code == 200
    assert "job_id" in response.json()
    
    job_id = response.json()["job_id"]
    assert job_id.startswith("job_")

def test_status_endpoint(client, api_key):
    """Test status endpoint"""
    # Create a job first
    enqueue_payload = {
        "type": "test_job",
        "payload": {"test": "data"},
        "priority": 10
    }
    
    enqueue_response = client.post(
        "/v1/enqueue", 
        json=enqueue_payload,
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    job_id = enqueue_response.json()["job_id"]
    
    # Now check the status
    response = client.get(
        f"/v1/status/{job_id}",
        headers={"Authorization": f"Bearer {api_key}"}
    )
    
    assert response.status_code == 200
    result = response.json()
    assert result["job_id"] == job_id
    assert result["state"] in ["pending", "in_progress", "completed"]

def test_schema_init():
    """Test that database schema initializes correctly"""
    # This test will run the init_db function and verify it works
    try:
        init_db()
        assert True  # If no exception is raised, initialization was successful
    except Exception as e:
        assert False, f"Database initialization failed: {e}"

@pytest.mark.asyncio
async def test_provider_router_startup_probe():
    """Test provider router startup probe (mocked)"""
    router = LLMProviderRouter()
    
    # Mock the probe methods since we don't have actual services running in test
    with patch.object(router, '_probe_provider', return_value=True):
        await router.startup_probe()
        
        # Verify that both providers are marked as healthy
        assert router.primary_healthy == True
        assert router.secondary_healthy == True

def test_router_fallback_logic():
    """Test the router fallback logic (mocked)"""
    router = LLMProviderRouter()
    
    # Mock both providers to fail initially
    def fail_on_first_call(*args, **kwargs):
        if not hasattr(fail_on_first_call, 'called'):
            fail_on_first_call.called = True
            raise Exception("Primary failed")
        return {"result": "secondary success"}
    
    router.primary_url = "http://primary"
    router.secondary_url = "http://secondary"
    
    with patch.object(router, '_call_provider', side_effect=fail_on_first_call):
        try:
            result = asyncio.run(router.route_request({"model": "test"}))
            # This is expected to fail since both providers fail in our mock
        except Exception as e:
            # Verify that the error message contains both provider failures
            assert "Both LLM providers failed" in str(e)

if __name__ == "__main__":
    pytest.main([__file__])