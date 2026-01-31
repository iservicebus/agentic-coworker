import asyncio
import requests
from fastapi import APIRouter,  Depends, HTTPException, Request
from pydantic import BaseModel
from typing import Dict, Any, Optional
from integrator.utils.logger import get_logger
from integrator.utils.oauth import validate_token
import os
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from sqlalchemy.orm import Session
from integrator.utils.db import get_db
from httpx import HTTPStatusError
import traceback

from integrator.iam.iam_auth import get_auth_agent
logger = get_logger(__name__)

client_router = APIRouter(
    prefix="/clients",
    tags=["clients"],
)

class McpValidationInput(BaseModel):
    service_name: str
    data: Dict[str, Any]
    agent_id: Optional[str] = None

@client_router.post("/mcp_validation")
async def mcp_validation(
    request: Request,
    validation_input: McpValidationInput,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Receives a log message from the frontend and logs it on the backend.
    """
    server_url = os.getenv("MCP_URL")
    _streams_context = None
    _session_context = None
    session: Optional[ClientSession] = None
    auth_token=request.headers.get("authorization")
    agent_id=validation_input.agent_id
    tenant_name = request.headers.get("x-tenant")

    if not tenant_name:
        raise HTTPException(status_code=404, detail=f"tenant name is not found in headers")

    if not agent_id:
        agent_id, _ = get_auth_agent(db, user, tenant_name)

    username = user.get("preferred_username")
    if not agent_id:
        raise HTTPException(status_code=404, detail=f"agent is not found for user: {username}, or not provided. agent id must belongs to the user")

#    agent = get_active_agent_by_username(db, username)
    # agent=None
    # if not agent:
    #     raise HTTPException(status_code=404, detail="Active agent not found for user")

    # # Keycloak configuration
    # auth_url = os.getenv("IAM_URL", "http://localhost:8888")
    
    # token_url = f"{auth_url}/realms/{tenant}/protocol/openid-connect/token"

    # token_data = {
    #     "grant_type": "client_credentials",
    #     "client_id": agent.agent_id,
    #     "client_secret": agent.secret
    # }

    # response = requests.post(token_url, data=token_data)

    # if response.status_code != 200:
    #     logger.error(f"Failed to get access token: {response.status_code} {response.text}")
    #     raise HTTPException(status_code=500, detail="Failed to get access token")

    # access_token = response.json().get("access_token")

    # headers = {
    #     "Authorization": f"Bearer {access_token}",
    #     "X-Tenant": "default",
    #     "X-Agent-ID": agent.agent_id
    # }
    headers = {
         "Authorization": auth_token,
         "X-Tenant": tenant_name,
         "X-Agent-ID": agent_id
     }

    try:
        # Create SSE client connection
        _streams_context = sse_client(url=server_url, headers=headers)
        streams = await _streams_context.__aenter__()

        # Create MCP session using streams
        _session_context = ClientSession(*streams)
        session = await _session_context.__aenter__()

        await session.initialize()
        result = await session.call_tool(validation_input.service_name, validation_input.data)
        return result

    except asyncio.CancelledError:
        logger.error("MCP validation task was cancelled.")
        raise HTTPException(status_code=499, detail="Client closed request")
    except HTTPStatusError as e:
        # Handle HTTP errors from the MCP server
        status_code = e.response.status_code
        error_detail = f"MCP Server returned {status_code} {e.response.reason_phrase}"
        
        # Try to get more details from response body
        try:
            error_body = e.response.text
            if error_body:
                error_detail = f"{error_detail}: {error_body}"
        except:
            pass
        
        logger.error(f"HTTP error during MCP validation: {error_detail}")
        
        # Return appropriate status code to frontend
        if status_code == 401:
            raise HTTPException(status_code=401, detail=f"Unauthorized: {error_detail}. Please check your agent credentials.")
        elif status_code == 404:
            raise HTTPException(status_code=404, detail=f"Not Found: {error_detail}. The service '{validation_input.service_name}' may not exist.")
        else:
            raise HTTPException(status_code=status_code, detail=error_detail)
    except ExceptionGroup as eg:
        # Handle ExceptionGroup which may contain HTTPStatusError
        logger.error(f"ExceptionGroup occurred during MCP validation: {eg}")
        
        # Extract HTTPStatusError from ExceptionGroup if present
        http_errors = [e for e in eg.exceptions if isinstance(e, HTTPStatusError)]
        if http_errors:
            http_error = http_errors[0]
            status_code = http_error.response.status_code
            error_detail = f"MCP Server returned {status_code} {http_error.response.reason_phrase}"
            
            try:
                error_body = http_error.response.text
                if error_body:
                    error_detail = f"{error_detail}: {error_body}"
            except:
                pass
            
            if status_code == 401:
                raise HTTPException(status_code=401, detail=f"Unauthorized: {error_detail}. Please ensure that user {username} actually has the  agent id {agent_id} ")
            elif status_code == 404:
                raise HTTPException(status_code=404, detail=f"Not Found: {error_detail}. The service '{validation_input.service_name}' may not exist.")
            else:
                raise HTTPException(status_code=status_code, detail=error_detail)
        else:
            # No HTTP errors, return generic error
            raise HTTPException(status_code=500, detail=f"Multiple errors occurred: {str(eg)}")
    except Exception as e:
        logger.error(f"Unexpected error occurred during MCP validation: {e}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")
    finally:
        # Ensure proper cleanup
        if session and _session_context:
            await _session_context.__aexit__(None, None, None)
        if _streams_context:
            await _streams_context.__aexit__(None, None, None)
