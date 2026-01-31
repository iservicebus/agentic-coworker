"""Authentication service for MCP provider."""

from typing import Dict, Any, Optional, Tuple
import os
import httpx

from mcp_services.services.http_client import HttpClientService
from mcp_services.utils.logger import get_logger
from mcp_services.utils.oauth import get_auth_agent
from mcp_services.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)


class AuthService:
    """Handles authentication and authorization operations."""
    
    def __init__(self, http_client: HttpClientService):
        self.integrator_url = os.getenv("INTEGRATOR_URL", "http://localhost:6060")
        self.authorization_host = os.getenv("META_AUTHORIZATION_LINK", "http://localhost:3000")
        self.http_client = http_client
    
    async def validate_auth(self, headers):
        """Validate token asynchronously."""
        try:
            return await get_auth_agent(headers, self.validate_working_agent_id)
        except Exception as e:
            logger.warning(f"Token validation failed: {e}")
            return None, None, None
    
    def validate_working_agent_id(self, agent_id: Optional[str], auth_header: Optional[str], tenant_name:Optional[str]) -> Optional[bool]:
        """Get working agent ID from the integrator service."""
        if not agent_id:
            return False
        
        sec_headers = {
            "Authorization": auth_header,
            "X-Agent-ID": agent_id,
            "X-Tenant": tenant_name
        }
        
        agents_url = f"{self.integrator_url}/users/login-user-agents"
        
        try:
            response = self.http_client.sync_get(
                agents_url,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                agents=response.json()
                for agent in agents:
                    if agent.get("agent_id")==agent_id:
                        return True
                return False

            else:
                logger.warning(f"Failed to get  agents: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Error getting working agent ID: {e}")
            return False
    
    def create_security_headers(self, agent_id: Optional[str], authorization: Optional[str], tenant_name: Optional[str]) -> Dict[str, str]:
        """Create security headers for API requests."""
        headers = {}
        if agent_id:
            headers["X-Agent-ID"] = agent_id
        if authorization:
            headers["Authorization"] = authorization
        if tenant_name:
            headers["X-Tenant"]= tenant_name    
        return headers
    
    def get_provider_token(
        self, 
        agent_id,
        auth_token,
        tenant_name: str, 
        provider_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get provider token for authentication."""
        if not provider_name:
            return {}
        
        if not agent_id:
            return {}
        
        sec_headers = self.create_security_headers(
            agent_id, 
            auth_token,
            tenant_name
        )
        
        token_url = (
            f"{self.integrator_url}/provider_tokens/tenants/{tenant_name}/"
            f"providers/{provider_name}/agents/{agent_id}"
        )
        
        try:
            response = self.http_client.sync_get(
                token_url,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                return response.json().get("token", {})
            else:
                logger.warning(
                    f"Failed to get provider token for {provider_name}: "
                    f"{response.status_code}"
                )
                return {}
                
        except Exception as e:
            logger.error(f"Error getting provider token for {provider_name}: {e}")
            return {}
    
    def create_auth_error_message(self, provider_name: str, agent_id: str) -> str:
        """Create authentication error message with authorization URL."""
        auth_url = f"{self.authorization_host}/token/start/oauth_providers/{provider_name}?agent_id={agent_id}"
        return (
            f"Authorization required. Please use this provided link {auth_url} "
            "to authorize the application and try again."
        )
    
    def is_auth_error(self, status_code: int, provider_name: Optional[str]) -> bool:
        """Check if the error is an authentication error."""
        return status_code == 401 and provider_name is not None


class TenantService:
    """Handles tenant-related operations."""
    
    def __init__(self, http_client: HttpClientService):
        self.integrator_url = os.getenv("INTEGRATOR_URL", "http://localhost:6060")
        self.http_client = http_client
    
    def get_sec_headers(self, headers):
        auth = headers.get("Authorization".lower())
        x_agent_id = headers.get("X-Agent-ID".lower())
        x_tenant_name =headers.get("X-Tenant".lower())
        return {
            "X-Agent-ID": x_agent_id,
            "Authorization": auth,
            "X-Tenant": x_tenant_name
        }
    
    def validate_tenant(
            self,
            headers
        ):
        auth = headers.get("Authorization".lower())
        x_agent_id = headers.get("X-Agent-ID".lower())
        x_tenant_name =headers.get("X-Tenant".lower())
        sec_headers = self.get_sec_headers(headers)

        user_url = f"{self.integrator_url}/users/tenants/{x_tenant_name}/agents/{x_agent_id}"
            
        try:
            response = self.http_client.sync_get(
                user_url,
                headers=sec_headers,
                raise_for_status=False
            )
            if response.status_code == 200:
                return True, sec_headers
            else:
                logger.warning(f"Failed to validate tenant: {response.status_code}")
                return False, None
                    
        except Exception as e:
            logger.error(f"Error to validate tenan=t {e}")
            return False, None
        return False, None

    def get_app_keys(
        self, 
        agent_id: str,
        auth_token: str, 
        tenant_name: str, 
        app_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Get application keys for a specific tenant and app."""
        if not app_name:
            return {}
        
        if not agent_id:
            return {}
        
        sec_headers = {
            "X-Agent-ID": agent_id,
            "Authorization": auth_token,
            "X-Tenant": tenant_name
        }
        
        secrets_url = (
            f"{self.integrator_url}/users/agents/{agent_id}/"
            f"tenants/{tenant_name}/app_keys/{app_name}"
        )
        
        try:
            response = self.http_client.sync_get(
                secrets_url,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                return response.json().get(app_name, {})
            else:
                logger.warning(f"Failed to get app keys for {app_name}: {response.status_code}")
                return {}
                
        except Exception as e:
            logger.error(f"Error getting app keys for {app_name}: {e}")
            return {}
