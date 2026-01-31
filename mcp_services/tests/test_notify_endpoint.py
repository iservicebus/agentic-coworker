#!/usr/bin/env python3
"""
Test suite for the /notify endpoint in the refactored MCP provider.
This tests the notify_change function that handles notification requests with POST data,
including non-JSON body conversion to JSON.
"""

import asyncio
import pytest
import requests
import json
from typing import Optional, Dict, Any
from unittest.mock import Mock, patch, AsyncMock
from starlette.testclient import TestClient
from starlette.requests import Request
from starlette.responses import Response

# Import the MCP provider and related modules
from mcp_services.servers.refactored_mcp_provider import RefactoredMCPProvider
from mcp_services.services import get_config

# Test configuration constants
TEST_PORT = 6667  # Use a different port for testing
TEST_HOST = "127.0.0.1"
TEST_BASE_URL = f"http://{TEST_HOST}:{TEST_PORT}"

# Mock authentication data (similar to test_mcp.py)
TENANT = "default"
AGENT_ID = "test-agent-client"
AGENT_SECRET = "test-agent-secret"
AUTH_URL = "http://localhost:8888"
TOKEN_URL = f"{AUTH_URL}/realms/{TENANT}/protocol/openid-connect/token"


class TestNotifyEndpoint:
    """Test class for the /notify endpoint functionality."""
    
    @pytest.fixture
    def mock_config(self):
        """Create a mock configuration for testing."""
        config = Mock()
        config.port = TEST_PORT
        config.authorization_enabled = True
        config.resource_url = f"{TEST_BASE_URL}/sse"
        config.oidc_issuer = AUTH_URL
        config.has_azure_config.return_value = False
        return config
    
    @pytest.fixture
    def mock_config_no_auth(self):
        """Create a mock configuration with authorization disabled."""
        config = Mock()
        config.port = TEST_PORT
        config.authorization_enabled = False
        config.resource_url = f"{TEST_BASE_URL}/sse"
        config.oidc_issuer = AUTH_URL
        config.has_azure_config.return_value = False
        return config
    
    @pytest.fixture
    async def mcp_provider(self, mock_config):
        """Create a RefactoredMCPProvider instance for testing."""
        with patch('mcp_services.servers.refactored_mcp_provider.get_config', return_value=mock_config):
            provider = RefactoredMCPProvider()
            return provider
    
    @pytest.fixture
    async def mcp_provider_no_auth(self, mock_config_no_auth):
        """Create a RefactoredMCPProvider instance with no auth for testing."""
        with patch('mcp_services.servers.refactored_mcp_provider.get_config', return_value=mock_config_no_auth):
            provider = RefactoredMCPProvider()
            return provider
    
    def get_test_headers(self, include_agent_id: bool = True) -> Dict[str, str]:
        """Generate test headers for requests."""
        headers = {
            "Content-Type": "application/json",
            "X-Tenant": TENANT,
        }
        if include_agent_id:
            headers["X-Agent-ID"] = AGENT_ID
        return headers
    
    def get_auth_headers(self, include_bearer: bool = True) -> Dict[str, str]:
        """Generate authentication headers for requests."""
        headers = self.get_test_headers()
        if include_bearer:
            # Mock bearer token for testing
            headers["Authorization"] = "Bearer mock_test_token_12345"
        return headers

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_valid_json(self, mcp_provider_no_auth):
        """Test the /notify endpoint with POST request containing valid JSON."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            headers = self.get_test_headers()
            test_data = {
                "message": "Test notification",
                "timestamp": "2024-01-01T00:00:00Z",
                "event_type": "tool_update",
                "data": {"tool_id": "test-tool", "status": "active"}
            }
            
            # Make POST request to /notify endpoint
            response = client.post("/notify", headers=headers, json=test_data)
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            assert response_data["message"] == "Notification received and processed"
            assert response_data["agent_id"] == AGENT_ID
            assert response_data["data_received"] == test_data

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_non_json_body(self, mcp_provider_no_auth):
        """Test the /notify endpoint with POST request containing non-JSON body (should convert to JSON)."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            headers = self.get_test_headers()
            headers["Content-Type"] = "text/plain"  # Non-JSON content type
            
            # Make POST request with plain text data
            plain_text_data = "This is a plain text notification message"
            response = client.post("/notify", headers=headers, data=plain_text_data)
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            assert response_data["message"] == "Notification received and processed"
            assert response_data["agent_id"] == AGENT_ID
            
            # Verify the non-JSON body was converted to JSON structure
            data_received = response_data["data_received"]
            assert "raw_body" in data_received
            assert data_received["raw_body"] == plain_text_data
            assert data_received["content_type"] == "text/plain"
            assert "timestamp" in data_received

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_form_data(self, mcp_provider_no_auth):
        """Test the /notify endpoint with POST request containing form data (should convert to JSON)."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            headers = self.get_test_headers()
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            # Make POST request with form data
            form_data = {"field1": "value1", "field2": "value2"}
            response = client.post("/notify", headers=headers, data=form_data)
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            
            # Verify the form data was converted to JSON structure
            data_received = response_data["data_received"]
            assert "raw_body" in data_received
            assert data_received["content_type"] == "application/x-www-form-urlencoded"
            assert "field1=value1&field2=value2" in data_received["raw_body"]

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_empty_body(self, mcp_provider_no_auth):
        """Test the /notify endpoint with POST request containing empty body."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            headers = self.get_test_headers()
            
            # Make POST request with empty body
            response = client.post("/notify", headers=headers, data="")
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            
            # Verify empty body was handled correctly
            data_received = response_data["data_received"]
            assert "raw_body" in data_received
            assert data_received["raw_body"] == ""

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_valid_auth(self, mcp_provider):
        """Test the /notify endpoint with POST request and valid authentication."""
        # Create the Starlette app
        app = await mcp_provider.create_sse_app()
        
        # Mock the auth validation to return valid claims
        with patch.object(mcp_provider.auth_service, 'validate_token_async', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = {"sub": "test_user", "agent_id": AGENT_ID}
            
            # Create test client
            with TestClient(app) as client:
                headers = self.get_auth_headers()
                test_data = {
                    "message": "Test notification",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "event_type": "tool_update",
                    "data": {"tool_id": "test-tool", "status": "active"}
                }
                
                # Make POST request to /notify endpoint
                response = client.post("/notify", headers=headers, json=test_data)
                
                # Verify response
                assert response.status_code == 200
                response_data = response.json()
                assert response_data["status"] == "success"
                assert response_data["message"] == "Notification received and processed"
                assert response_data["agent_id"] == AGENT_ID
                assert response_data["data_received"] == test_data
                mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_with_invalid_auth(self, mcp_provider):
        """Test the /notify endpoint with POST request and invalid authentication."""
        # Create the Starlette app
        app = await mcp_provider.create_sse_app()
        
        # Mock the auth validation to return None (invalid)
        with patch.object(mcp_provider.auth_service, 'validate_token_async', new_callable=AsyncMock) as mock_validate:
            mock_validate.return_value = None
            
            # Create test client
            with TestClient(app) as client:
                headers = self.get_auth_headers()
                test_data = {"message": "Test notification"}
                
                # Make POST request to /notify endpoint
                response = client.post("/notify", headers=headers, json=test_data)
                
                # Verify response
                assert response.status_code == 401
                assert "WWW-Authenticate" in response.headers
                assert "Bearer" in response.headers["WWW-Authenticate"]
                assert "resource_metadata" in response.headers["WWW-Authenticate"]
                mock_validate.assert_called_once()

    @pytest.mark.asyncio
    async def test_notify_endpoint_post_complex_data(self, mcp_provider_no_auth):
        """Test the /notify endpoint with POST request containing complex JSON data."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            headers = self.get_test_headers()
            complex_data = {
                "notification_id": "notif_12345",
                "event_type": "system_update",
                "timestamp": "2024-01-01T12:00:00Z",
                "source": {
                    "service": "tool_manager",
                    "version": "1.2.3",
                    "instance_id": "tm_001"
                },
                "payload": {
                    "tools_updated": [
                        {"id": "tool_1", "name": "Calculator", "status": "active"},
                        {"id": "tool_2", "name": "Weather", "status": "inactive"}
                    ],
                    "metadata": {
                        "update_reason": "scheduled_maintenance",
                        "affected_users": 150,
                        "rollback_available": True
                    }
                },
                "recipients": ["agent_1", "agent_2", "agent_3"]
            }
            
            # Make POST request to /notify endpoint
            response = client.post("/notify", headers=headers, json=complex_data)
            
            # Verify response
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["status"] == "success"
            assert response_data["message"] == "Notification received and processed"
            assert response_data["data_received"] == complex_data

    @pytest.mark.asyncio
    async def test_notify_endpoint_agent_id_extraction(self, mcp_provider_no_auth):
        """Test that the /notify endpoint correctly extracts agent ID from headers."""
        # Create the Starlette app
        app = await mcp_provider_no_auth.create_sse_app()
        
        # Create test client
        with TestClient(app) as client:
            # Test with agent ID in headers
            headers_with_agent = self.get_test_headers(include_agent_id=True)
            test_data = {"message": "Test with agent ID"}
            response = client.post("/notify", headers=headers_with_agent, json=test_data)
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["agent_id"] == AGENT_ID
            
            # Test without agent ID in headers
            headers_without_agent = self.get_test_headers(include_agent_id=False)
            response = client.post("/notify", headers=headers_without_agent, json=test_data)
            assert response.status_code == 200
            response_data = response.json()
            assert response_data["agent_id"] == ""


class TestNotifyEndpointIntegration:
    """Integration tests for the /notify endpoint using actual HTTP requests."""
    
    def get_mock_access_token(self) -> str:
        """Generate a mock access token for testing."""
        return "mock_access_token_for_testing_12345"
    
    def get_integration_headers(self) -> Dict[str, str]:
        """Generate headers for integration testing."""
        return {
            "Authorization": f"Bearer {self.get_mock_access_token()}",
            "X-Tenant": TENANT,
            "X-Agent-ID": AGENT_ID,
            "Content-Type": "application/json"
        }
    
    @pytest.mark.integration
    def test_notify_endpoint_post_json_integration(self):
        """Test the /notify endpoint with POST JSON request (requires running server)."""
        try:
            headers = self.get_integration_headers()
            test_data = {
                "message": "Integration test notification",
                "timestamp": "2024-01-01T00:00:00Z",
                "test_type": "integration"
            }
            
            response = requests.post(f"{TEST_BASE_URL}/notify", headers=headers, json=test_data, timeout=5)
            
            # The response should be either 200 (success) or 401 (auth required)
            assert response.status_code in [200, 401]
            
            if response.status_code == 200:
                response_data = response.json()
                assert response_data["status"] == "success"
                assert "data_received" in response_data
            elif response.status_code == 401:
                # Check for proper WWW-Authenticate header
                assert "WWW-Authenticate" in response.headers
                
        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running - skipping integration test")
    
    @pytest.mark.integration
    def test_notify_endpoint_post_text_integration(self):
        """Test the /notify endpoint with POST text request (requires running server)."""
        try:
            headers = self.get_integration_headers()
            headers["Content-Type"] = "text/plain"
            
            text_data = "This is a plain text integration test notification"
            response = requests.post(f"{TEST_BASE_URL}/notify", headers=headers, data=text_data, timeout=5)
            
            # The response should be either 200 (success) or 401 (auth required)
            assert response.status_code in [200, 401]
            
            if response.status_code == 200:
                response_data = response.json()
                assert response_data["status"] == "success"
                assert "data_received" in response_data
                assert response_data["data_received"]["raw_body"] == text_data
                
        except requests.exceptions.ConnectionError:
            pytest.skip("MCP server not running - skipping integration test")


def run_manual_tests():
    """
    Manual test function that can be run directly to test the /notify endpoint.
    This is useful for quick testing without pytest.
    """
    print("=== Manual Test for /notify Endpoint ===")
    
    # Test configuration
    test_url = f"{TEST_BASE_URL}/notify"
    headers = {
        "Authorization": "Bearer test_token_12345",
        "X-Tenant": TENANT,
        "X-Agent-ID": AGENT_ID,
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Testing POST request with JSON to {test_url}")
        test_data = {
            "message": "Manual test notification",
            "timestamp": "2024-01-01T00:00:00Z",
            "event_type": "manual_test",
            "data": {
                "test_id": "manual_001",
                "description": "Testing POST functionality"
            }
        }
        response = requests.post(test_url, headers=headers, json=test_data, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Response: {response.text}")
        
        print(f"\nTesting POST request with plain text to {test_url}")
        text_headers = headers.copy()
        text_headers["Content-Type"] = "text/plain"
        response = requests.post(test_url, headers=text_headers, data="Plain text notification", timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        print(f"\nTesting POST request with form data to {test_url}")
        form_headers = headers.copy()
        form_headers["Content-Type"] = "application/x-www-form-urlencoded"
        response = requests.post(test_url, headers=form_headers, data={"key": "value", "message": "form test"}, timeout=5)
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
    except requests.exceptions.ConnectionError as e:
        print(f"Connection Error: {e}")
        print("Make sure the MCP server is running on the expected port.")
    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    # Run manual tests if this file is executed directly
    run_manual_tests()
