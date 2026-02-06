"""Tool service for MCP provider."""

from typing import Dict, Any, List, Optional
from datetime import datetime
import os
import mcp.types as types
from sqlalchemy.orm import Session

from mcp_services.services.http_client import HttpClientService
from mcp_services.utils.logger import get_logger
from mcp_services.utils.json_norm import preprocess_keys, transform_json_with_schema
from mcp_services.utils.schema_parser import generalized_schema_parser
from mcp_services.mcp_sessions.session_db_crud import get_latest_context, ensure_latest_context
from mcp_services.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)


def normalize_schema(schema):
    """
    Recursively traverses a JSON schema to normalize it and ensure compatibility.
    - Converts boolean 'required' fields to a valid list of strings.
    - Ensures 'type' is a string.
    - Ensures 'properties' and 'items' are dictionaries if they exist.
    """
    if not isinstance(schema, dict):
        return

    # Fix boolean 'required' field
    if 'required' in schema and isinstance(schema.get('required'), bool):
        if schema['required'] and 'properties' in schema and isinstance(schema.get('properties'), dict):
            schema['required'] = list(schema['properties'].keys())
        else:
            # If required is false or properties are missing, make it an empty list
            schema['required'] = []

    # Ensure 'type' is a string (some schemas might incorrectly use a list)
    if 'type' in schema and isinstance(schema.get('type'), list):
        # Default to the first type in the list, or 'object' if empty
        schema['type'] = schema['type'][0] if schema['type'] else 'object'

    # Recursively normalize nested schemas in 'properties'
    if 'properties' in schema and isinstance(schema.get('properties'), dict):
        for prop_name, prop_schema in schema['properties'].items():
            normalize_schema(prop_schema)

    # Recursively normalize 'items' for arrays
    if 'items' in schema and isinstance(schema.get('items'), dict):
        normalize_schema(schema['items'])


class ToolService:
    """Handles tool-related operations."""
    
    def __init__(self, http_client: HttpClientService):
        self.integrator_url = os.getenv("INTEGRATOR_URL", "http://localhost:6060")
        self.http_client = http_client
    
    async def list_tools(
        self, 
        tenant_name: str, 
        sec_headers: Dict[str, str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None,
        db: Optional[Session] = None,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None
    ) -> List[types.Tool]:
        """
        List available tools for a tenant with intelligent caching.
        
        This method implements a two-tier caching strategy:
        1. Check session context cache (if session_id provided)
        2. Compare agent profile update time with context creation time
        3. Use cached tools if context is newer, otherwise fetch from API
        4. Save fetched tools to session context
        
        Args:
            tenant_name: Tenant name
            sec_headers: Security headers for API calls
            cursor: Optional pagination cursor
            limit: Optional result limit
            db: Optional database session for context operations
            session_id: Optional MCP session ID for context caching
            agent_id: Optional agent ID for profile checking
            
        Returns:
            List of MCP tools
        """
        # Step 1: Try to get latest context from session if available
        latest_context = None
        context_created_at = None
        
        if db and session_id:
            try:
                latest_context_data = get_latest_context(db, session_id=session_id, tenant_name=tenant_name)
                if latest_context_data:
                    latest_context = latest_context_data.get("context")
                    context_created_at_str = latest_context_data.get("created_at")
                    if context_created_at_str:
                        context_created_at = datetime.fromisoformat(context_created_at_str)
                    logger.info(f"Retrieved latest context for session {session_id} (tenant: {tenant_name}), created at {context_created_at}")
            except ValueError as e:
                logger.info(f"No context found for session {session_id} (tenant: {tenant_name}): {e}")
            except Exception as e:
                logger.warning(f"Error retrieving latest context: {e}")
        
        # Step 2: If we have context, check agent profile to compare timestamps
        if latest_context and context_created_at and agent_id:
            try:
                # Call agent profile API
                profile_url = f"{self.integrator_url}/users/agent-profile/{agent_id}"
                profile_response = await self.http_client.get(
                    profile_url,
                    headers=sec_headers,
                    raise_for_status=False
                )
                
                if profile_response.status_code == 200:
                    profile_data = profile_response.json()
                    profile_updated_at_str = profile_data.get("updated_at")
                    
                    if profile_updated_at_str:
                        profile_updated_at = datetime.fromisoformat(profile_updated_at_str.replace('Z', '+00:00'))
                        
                        # Step 3: Compare timestamps - if context is newer, use cached tools
                        if context_created_at > profile_updated_at:
                            logger.info(
                                f"Context ({context_created_at}) is newer than profile ({profile_updated_at}), "
                                f"using cached tools from context"
                            )
                            
                            # Extract tools from context and convert back to Tool objects
                            if "tools" in latest_context and isinstance(latest_context["tools"], list):
                                tools = [
                                    types.Tool(
                                        name=tool["name"],
                                        description=tool["description"],
                                        inputSchema=tool["inputSchema"]
                                    )
                                    for tool in latest_context["tools"]
                                ]
                                return tools
                        else:
                            logger.info(
                                f"Profile ({profile_updated_at}) is newer than context ({context_created_at}), "
                                f"fetching fresh tools from API"
                            )
                else:
                    logger.warning(f"Failed to get agent profile: {profile_response.status_code}")
            except Exception as e:
                logger.warning(f"Error checking agent profile: {e}")
        
        # Step 4: Fetch tools from integrator service
        url = f"{self.integrator_url}/mcp/list_tools"
        params = {"tenant": tenant_name}
        
        try:
            response = await self.http_client.get(
                url,
                params=params,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                mcp_tools_data = response.json()
                tools = []
                
                if mcp_tools_data:
                    for tool in mcp_tools_data:
                        input_schema = tool.get("inputSchema", {})
                        normalize_schema(input_schema)
                        tools.append(
                            types.Tool(
                                name=tool["name"],
                                description=tool["description"],
                                inputSchema=input_schema
                            )
                        )
                
                # Save tools to session context if session_id provided
                if db and session_id and tools:
                    try:
                        # Convert tools to serializable format (Tool objects are not JSON serializable)
                        serializable_tools = [
                            {
                                "name": tool.name,
                                "description": tool.description,
                                "inputSchema": tool.inputSchema
                            }
                            for tool in tools
                        ]
                        
                        context = {"tools": serializable_tools}
                        ensure_latest_context(db, session_id=session_id, tenant_name=tenant_name, context=context)
                        db.commit()
                        logger.info(f"Saved {len(tools)} tools to session context for session {session_id} (tenant: {tenant_name})")
                    except Exception as e:
                        logger.warning(f"Failed to save tools to session context: {e}")
                        db.rollback()
                
                return tools
            else:
                logger.warning(f"Failed to list tools: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    def sync_list_tools(
        self, 
        tenant_name: str, 
        sec_headers: Dict[str, str],
        cursor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[types.Tool]:
        """List available tools for a tenant (sync version)."""
        url = f"{self.integrator_url}/mcp/list_tools"
        params = {"tenant": tenant_name}
        
        try:
            response = self.http_client.sync_get(
                url,
                params=params,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                mcp_tools_data = response.json()
                tools = []
                
                if mcp_tools_data:
                    for tool in mcp_tools_data:
                        input_schema = tool.get("inputSchema", {})
                        normalize_schema(input_schema)
                        tools.append(
                            types.Tool(
                                name=tool["name"],
                                description=tool["description"],
                                inputSchema=input_schema
                            )
                        )
                
                return tools
            else:
                logger.warning(f"Failed to list tools: {response.status_code}")
                return []
                
        except Exception as e:
            logger.error(f"Error listing tools: {e}")
            return []
    
    async def get_tool_definition(
        self, 
        tenant_name: str, 
        tool_name: str, 
        sec_headers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Get tool definition from integrator service."""
        url = f"{self.integrator_url}/mcp/services/{tenant_name}/{tool_name}"
        
        try:
            response = await self.http_client.get(
                url,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get tool definition for {tool_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting tool definition for {tool_name}: {e}")
            return None
    
    def sync_get_tool_definition(
        self, 
        tenant_name: str, 
        tool_name: str, 
        sec_headers: Dict[str, str]
    ) -> Optional[Dict[str, Any]]:
        """Get tool definition from integrator service (sync version)."""
        url = f"{self.integrator_url}/mcp/services/{tenant_name}/{tool_name}"
        
        try:
            response = self.http_client.sync_get(
                url,
                headers=sec_headers,
                raise_for_status=False
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.warning(f"Failed to get tool definition for {tool_name}: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting tool definition for {tool_name}: {e}")
            return None
    
    def process_arguments(self, arguments: Dict[str, Any], input_schema: Dict[str, Any]) -> Dict[str, Any]:
        """Process and validate tool arguments against schema."""
        processed_args = arguments.copy()
        
        name_list = ["aint_body", "aint_query", "aint_path", "aint_headers"]
        for param_name in name_list:
            if input_schema and processed_args.get(param_name):
                param_schema = input_schema.get("properties", {}).get(param_name, {})
                if param_schema and param_schema.get("type") == "object":
                    try:
                        # Use the new generalized schema parser for complex schemas
                        processed_args[param_name] = generalized_schema_parser(
                            processed_args[param_name], param_schema
                        )
                        logger.info(f"Successfully parsed {param_name} using generalized schema parser")
                    except Exception as e:
                        logger.warning(
                            f"Generalized parser failed for {param_name}: {e}. "
                            "Falling back to legacy parser."
                        )
                        # Fallback to the original method
                        try:
                            preprocessed_param = preprocess_keys(processed_args[param_name])
                            processed_args[param_name] = transform_json_with_schema(
                                preprocessed_param, param_schema
                            )
                            logger.info(f"Successfully parsed {param_name} using legacy parser")
                        except Exception as fallback_e:
                            logger.error(
                                f"Both parsers failed for {param_name}: {fallback_e}. "
                                "Using original data."
                            )
        
        return processed_args
