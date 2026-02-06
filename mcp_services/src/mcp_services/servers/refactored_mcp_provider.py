"""
Refactored MCP Provider using the new service architecture.
This demonstrates the clean, maintainable structure achieved through refactoring.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Optional, List
from fastapi import  HTTPException
import anyio
import mcp.types as types
from mcp.server.lowlevel import Server
from pydantic import AnyUrl, FileUrl
from starlette.applications import Starlette
from starlette.routing import Mount, Route
from starlette.responses import Response

# Import our refactored services
from mcp_services.services import (
    get_http_client, close_http_client,
    AuthService, TenantService, RequestProcessor, 
    ToolService, get_stream_service
)
from mcp_services.utils.env import load_env
from mcp_services.servers.custom_sse_transport import CustomSseServerTransport
from mcp_services.utils.logger import get_logger
from mcp_services.utils.db import get_db_cm
from mcp_services.mcp_sessions.session_db_crud import upsert_mcp_session

# Graphiti imports (optional)
try:
    from graphiti_core import Graphiti
    from graphiti_core.nodes import EpisodeType
    from openai import AsyncAzureOpenAI
    from graphiti_core.llm_client import OpenAIClient
    from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
    from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
    GRAPHITI_AVAILABLE = True
except ImportError:
    GRAPHITI_AVAILABLE = False

logger = get_logger(__name__)
from mcp.types import (
    JSONRPCMessage,
    JSONRPCNotification,
)
from mcp.shared.message import  ServerMessageMetadata, SessionMessage


async def notify_tools_changed(writer: anyio.abc.ByteStream, notification: JSONRPCNotification=None)-> bool:

    try:

        if not notification:

            notification = JSONRPCNotification(
                jsonrpc="2.0",
                method="notifications/tools/list_changed"
            )
        session_message = SessionMessage(  # pragma: no cover
            message=JSONRPCMessage(notification)
            #metadata=ServerMessageMetadata(related_request_id=related_request_id) if related_request_id else None,
        )

        await writer.send(session_message)
        return True
    
    except Exception as e:
        logger.error(f"Unexpected error while sending tool list change notification: {e}")
        return False



class RefactoredMCPProvider:
    """
    Clean, maintainable MCP provider using the new service architecture.
    
    This class demonstrates how the refactored services make the code:
    - Much easier to understand and maintain
    - Fully testable with dependency injection
    - Better performance through connection pooling and caching
    - Proper separation of concerns
    """
    
    def __init__(self):
        # Load environment variables
        load_env()
        
        # Load configuration from environment
        import os
        self.port = int(os.getenv("MCP_PORT", "8000"))
        self.transport = os.getenv("MCP_TRANSPORT", "stdio")
        self.authorization_enabled = os.getenv("AUTHORIZATION_ENABLED", "false").lower() == "true"
        self.resource_url = os.getenv("RESOURCE_URL", f"http://127.0.0.1:{self.port}/sse")
        self.oidc_issuer = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/mcp")
        
        # Initialize services
        self.http_client = get_http_client()
        self.auth_service = AuthService(self.http_client)
        self.tenant_service = TenantService(self.http_client)
        self.request_processor = RequestProcessor(self.http_client)
        self.tool_service = ToolService(self.http_client)
        self.stream_service = get_stream_service(self.auth_service)
        
        # Initialize MCP server
        self.server = Server("refactored_mcp_services")
        self.graphiti_client = None
        
        # Setup server handlers
        self._setup_handlers()
        
        logger.info(f"Initialized RefactoredMCPProvider with clean service architecture")
    
    async def initialize_graphiti(self):
        """Initialize Graphiti client if Azure configuration is available."""
        if not GRAPHITI_AVAILABLE:
            logger.info("Graphiti not available - skipping initialization")
            return
        
        # Check if Graphiti is enabled
        import os
        graphiti_enabled = os.getenv("GRAPHITI_ENABLED", "false").lower() == "true"
        if not graphiti_enabled:
            logger.info("Graphiti is disabled via GRAPHITI_ENABLED environment variable")
            return

        # Load Azure configuration from environment
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        azure_api_version = os.getenv("AZURE_OPENAI_API_VERSION")
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOIN")
        azure_llm_deployment = os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME")
        azure_embedding_deployment = os.getenv("AZURE_OPENAI_EMBEDDING_MODEL")
        graphiti_uri = os.getenv("GRAPHITI_URI")
        graphiti_user = os.getenv("GRAPHITI_USER")
        graphiti_password = os.getenv("GRAPHITI_PASSWORD")
        
        if not all([azure_api_key, azure_api_version, azure_endpoint, azure_llm_deployment,
                    azure_embedding_deployment, graphiti_uri, graphiti_user, graphiti_password]):
            logger.warning("Azure credentials for Graphiti are not fully configured. Skipping Graphiti initialization.")
            return
        
        try:
            azure_llm_client = AsyncAzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint,
                azure_deployment=azure_llm_deployment,
            )

            azure_embed_client = AsyncAzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint,
                azure_deployment=azure_embedding_deployment,
            )

            self.graphiti_client = Graphiti(
                uri=graphiti_uri,
                user=graphiti_user,
                password=graphiti_password,
                llm_client=OpenAIClient(client=azure_llm_client),
                embedder=OpenAIEmbedder(
                    config=OpenAIEmbedderConfig(embedding_model=azure_embedding_deployment),
                    client=azure_embed_client,
                ),
                cross_encoder=OpenAIRerankerClient(client=azure_llm_client)
            )
            await self.graphiti_client.build_indices_and_constraints()
            logger.info("Graphiti client initialized successfully.")
        except Exception as e:
            logger.error(f"Failed to initialize Graphiti client: {e}")
    
    def _setup_handlers(self):
        """Setup MCP server handlers using the clean service architecture."""
        
        # Sample resources for demonstration
        self.sample_resources = {
            "greeting": {
                "content": "Hello! This is a sample text resource from the refactored MCP provider.",
                "title": "Welcome Message",
            },
            "help": {
                "content": "This server provides a few sample text resources for testing the refactored architecture.",
                "title": "Help Documentation",
            },
            "about": {
                "content": "This is the refactored MCP server implementation using clean service architecture.",
                "title": "About This Server",
            },
        }
        
        @self.server.list_resources()
        async def list_resources() -> List[types.Resource]:
            """List available resources."""
            return [
                types.Resource(
                    uri=FileUrl(f"file:///{name}.txt"),
                    name=name,
                    title=self.sample_resources[name]["title"],
                    description=f"A sample text resource named {name}",
                    mimeType="text/plain",
                )
                for name in self.sample_resources.keys()
            ]

        @self.server.read_resource()
        async def read_resource(uri: AnyUrl):
            """Read a specific resource."""
            if uri.path is None:
                raise ValueError(f"Invalid resource path: {uri}")
            name = uri.path.replace(".txt", "").lstrip("/")

            if name not in self.sample_resources:
                raise ValueError(f"Unknown resource: {uri}")

            return [types.TextContent(
                type="text", 
                text=self.sample_resources[name]["content"]
            )]

        @self.server.list_tools()
        async def list_tools(
            cursor: Optional[str] = None,
            limit: Optional[int] = None
        ) -> List[types.Tool]:
            """List available tools using the tool service with intelligent caching."""
            try:
                # Get request context headers
                ctx_headers = dict(self.server.request_context.request.headers)

                session_id = self.server.request_context.request.query_params.get("session_id")
                logger.info(f"list_tools called with session_id: {session_id}")

                agent_id, tenant_name, _ = await self.auth_service.validate_auth(ctx_headers)
                auth_token = ctx_headers.get("authorization", "")
                
                # Get tenant configuration
                sec_headers=self.tenant_service.get_sec_headers(ctx_headers)                
                # Get database session for context operations using proper context manager
                with get_db_cm() as db:
                    # Use tool service to list tools with intelligent caching
                    tools = await self.tool_service.list_tools(
                        tenant_name, 
                        sec_headers, 
                        cursor, 
                        limit,
                        db=db,
                        session_id=session_id,
                        agent_id=agent_id
                    )
                    
                    logger.info(f"Listed {len(tools)} tools for tenant {tenant_name}")
                    return tools
                
            except Exception as e:
                logger.error(f"Error listing tools: {e}")
                return []

        @self.server.call_tool()
        async def fetch_tool(
            name: str, 
            arguments: dict
        ) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
            """
            Execute a tool using the clean service architecture.
            
            This demonstrates how much cleaner the code becomes with proper
            separation of concerns and service-oriented architecture.
            """
            try:
                # Get request context
                ctx_headers = dict(self.server.request_context.request.headers)
                logger.info(f"Processing tool '{name}' with clean architecture")

                # Access SSE streams if available
                sse_streams = await self.stream_service.get_current_sse_streams(self.server.request_context)
                if sse_streams:
                    logger.info(f"SSE streams available for session {sse_streams['session_id'].hex}")

                agent_id, tenant_name, _ = await self.auth_service.validate_auth(ctx_headers)
                auth_token=ctx_headers.get("authorization", "")

                # Get tenant configuration using tenant service
                sec_headers= self.tenant_service.get_sec_headers(ctx_headers)
                # Get tool definition using tool service
                service_data = await self.tool_service.get_tool_definition(tenant_name, name, sec_headers)
                if not service_data:
                    raise ValueError(f"Tool '{name}' not found for tenant '{tenant_name}'")

                # Extract service information
                predefined_data = service_data["staticInput"]
                auth_info = service_data.get("auth")
                provider_name = auth_info.get("provider") if auth_info else None
                app_name = service_data.get("appName")

                # Handle authentication if needed
                token = {}
  
                if provider_name:
                    token = self.auth_service.get_provider_token(agent_id, ctx_headers.get("authorization", ""), tenant_name, provider_name)
                app_keys={}
                # Get additional app keys if needed
                if app_name:
                    additional_keys = self.tenant_service.get_app_keys(agent_id, ctx_headers.get("authorization", ""), tenant_name, app_name)
                    app_keys.update(additional_keys)

                # Parse predefined data if it's a string
                if isinstance(predefined_data, str):
                    predefined_data = json.loads(predefined_data)

                # Process arguments using tool service
                tools = await self.tool_service.list_tools(tenant_name, sec_headers)
                tool_def = next((tool for tool in tools if tool.name == name), None)
                
                if tool_def:
                    arguments = self.tool_service.process_arguments(arguments, tool_def.inputSchema)

                # Generate HTTP request using request processor
                req = self.request_processor.generate_http_request(
                    tenant_name, app_keys, ctx_headers, arguments, predefined_data, token
                )
                if service_data.get("tool_type","")=="system":
                    req["headers"]["Authorization"]=auth_token
                    req["headers"]["X-Agent-ID"]=agent_id
                    req["headers"]["X-Tenant"]=tenant_name
                print(" fetch call request", req)
                # Execute request using request processor
                response = await self.request_processor.execute_request(req)
                print(" fetch call response", response)
                # Log to Graphiti if available
                if self.graphiti_client:
                    await self._log_to_graphiti(name, arguments, response.text, tenant_name, agent_id)

                return [types.TextContent(type="text", text=response.text)]

            except Exception as e:
                # Handle authentication errors
                if hasattr(e, 'response') and self.auth_service.is_auth_error(e.response.status_code, provider_name):
                    error_message = self.auth_service.create_auth_error_message(provider_name,agent_id)
                    raise ValueError(error_message)
                
                logger.error(f"Error executing tool '{name}': {e}")
                raise ValueError(f"Error executing tool '{name}': {str(e)}")

    async def _log_to_graphiti(self, tool_name: str, arguments: dict, response: str, tenant_name: str, agent_id: str):
        """Log tool call to Graphiti if available."""
        try:
            tool_call_info = {
                "tool_name": tool_name,
                "arguments": arguments,
                "response": response,
                "tenant": tenant_name,
                "agent_id": agent_id,
                "timestamp": datetime.now().isoformat()
            }
            await self.graphiti_client.add_episode(
                name=f"ToolCall-{tool_name}-{time.time()}",
                episode_body=json.dumps(tool_call_info, default=str),
                source=EpisodeType.json,
                reference_time=datetime.now(),
                source_description="MCPToolCall"
            )
            logger.info(f"Logged tool call for '{tool_name}' to Graphiti.")
        except Exception as e:
            logger.error(f"Failed to log tool call to Graphiti: {e}")

    async def create_sse_app(self) -> Starlette:
        """Create Starlette app for SSE transport."""
        sse = CustomSseServerTransport("/messages/")

        async def ensure_valid_token(request):
            """Validate token if authorization is enabled."""
            if not self.authorization_enabled:
                return None, None, None
            
            try:
                headers = dict(request.headers)
                return await self.auth_service.validate_auth(headers) 
                
            except Exception:
                return None, None, None

        async def notify_change(request):
            """Handle POST notification requests with clean architecture."""
            # Authentication check
            agent_id, _ = await ensure_valid_token(request)
            if not agent_id:
                prm_url = f"http://127.0.0.1:{self.port}/.well-known/oauth-protected-resource/sse"
                return Response(
                    status_code=401,
                    headers={"WWW-Authenticate": f'Bearer resource_metadata="{prm_url}"'}
                )
            try:
                # Try to parse as JSON first
                try:
                    data = await request.json()
                    logger.info(f"Received JSON notification data from agent {agent_id}: {data}")
                except json.JSONDecodeError:
                    # If not JSON, get raw body and convert to JSON structure
                    body = await request.body()
                    body_text = body.decode('utf-8') if body else ""
                    data=json.loads(body_text)
                notification=JSONRPCNotification(**data)
                stream_info=self.stream_service.get_stream_info(agent_id)
                for id in stream_info.keys():
                    _, w_stream_str, _, _=stream_info[id]
                    w_stream=stream_info[id][w_stream_str]
                    await notify_tools_changed(w_stream, notification)
                
                logger.info(f"Received non-JSON notification data from agent {agent_id}, converted to JSON: {data}")
                
                # Process the notification data here
                # You can add your custom logic to handle the notification
                
                return Response(
                    status_code=200,
                    media_type="application/json",
                    content=json.dumps({
                        "status": "success",
                        "message": "Notification received and processed",
                        "agent_id": agent_id,
                        "data_received": data
                    })
                )
            except Exception as e:
                logger.error(f"Error processing notification: {e}")
                return Response(
                    status_code=500,
                    media_type="application/json",
                    content=json.dumps({
                        "status": "error",
                        "message": "Internal server error"
                    })
                )



        async def handle_sse(request):
            """Handle SSE connections with clean architecture."""
            # Authentication check
            if self.authorization_enabled:
                agent_id, tenant_name, _ = await ensure_valid_token(request)
                if not agent_id:
                    prm_url = f"http://127.0.0.1:{self.port}/.well-known/oauth-protected-resource/sse"
                    return Response(
                        status_code=401,
                        headers={"WWW-Authenticate": f'Bearer resource_metadata="{prm_url}"'}
                    )
            
            # Get tenant_name for the agent
            try:
                headers = dict(request.headers)
                validate, _= self.tenant_service.validate_tenant(headers)
                if not validate:
                    raise HTTPException(status_code=404, detail="tenant can not be validated")

            except Exception as e:
                logger.warning(f"Could not validate tenant for agent {agent_id}: {e}")
                raise HTTPException(status_code=500, detail="tenant can not be validated")


            # Handle SSE connection
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                read_stream, write_stream, session_id = streams
                session_id_str = str(session_id)
                logger.info(f"New SSE session: {session_id.hex}")
                
                # Insert session into database
                try:
                    with get_db_cm() as db:
                        mcp_session = upsert_mcp_session(
                            sess=db,
                            session_id=session_id_str,
                            tenant_name=tenant_name,
                            agent_id=agent_id
                        )
                        db.commit()
                        logger.info(f"Created MCP session record for session {session_id_str}")
                except Exception as e:
                    logger.error(f"Failed to create MCP session record: {e}")
                
                # Register streams with stream service
                self.stream_service.register_stream(agent_id, session_id, read_stream, write_stream)

                try:
                    await self.server.run(
                        read_stream, 
                        write_stream, 
                        self.server.create_initialization_options(), 
                        request.headers
                    )
                finally:
                    # Clean up streams
                    self.stream_service.unregister_stream(agent_id, session_id)
                    logger.info(f"Cleaned up SSE session: {session_id.hex}")

            return Response(status_code=200)

        async def protected_resource_metadata(request):
            """Provide OAuth protected resource metadata."""
            return Response(
                media_type="application/json",
                content=json.dumps({
                    "resource": self.resource_url,
                    "authorization_servers": [self.oidc_issuer],
                    "bearer_methods_supported": ["header"]
                })
            )

        async def health_check(request):
            """Simple health check endpoint."""
            return Response(
                status_code=200,
                media_type="application/json",
                content=json.dumps({"status": "healthy"})
            )

        async def startup_event():
            """Initialize services on startup."""
            await self.initialize_graphiti()
            logger.info("Refactored MCP server startup complete")

        async def shutdown_event():
            """Clean up resources on shutdown."""
            self.stream_service.cleanup_sessions()
            await close_http_client()
            logger.info("Refactored MCP server shutdown complete")

        # Create Starlette app
        app = Starlette(
            debug=True,
            routes=[
                Route("/", endpoint=health_check),
                Route("/health", endpoint=health_check),
                Route("/sse", endpoint=handle_sse),
                Route("/notify", endpoint=notify_change, methods=["POST"]),
                Route("/.well-known/oauth-protected-resource/sse", endpoint=protected_resource_metadata),
                Mount("/messages/", app=sse.handle_post_message),
            ],
            on_startup=[startup_event],
            on_shutdown=[shutdown_event]
        )

        return app

    async def run_stdio(self):
        """Run server with STDIO transport."""
        from mcp.server.stdio import stdio_server
        
        await self.initialize_graphiti()
        
        async with stdio_server() as streams:
            await self.server.run(
                streams[0], streams[1], self.server.create_initialization_options()
            )

    async def run_sse_async(self):
        """Run server with SSE transport asynchronously."""
        import uvicorn
        
        logger.info(
            f"Starting refactored MCP server on port {self.port} "
            f"with transport '{self.transport}', "
            f"Authorization: {'Enabled' if self.authorization_enabled else 'Disabled'}"
        )
        
        app = await self.create_sse_app()
        
        # Use uvicorn programmatically
        config = uvicorn.Config(app, host="0.0.0.0", port=self.port)
        server = uvicorn.Server(config)
        await server.serve()

    def run_sse(self):
        """Run server with SSE transport."""
        anyio.run(self.run_sse_async)

    def run_stdio(self):
        """Run server with STDIO transport."""
        async def run_stdio_async():
            from mcp.server.stdio import stdio_server
            await self.initialize_graphiti()
            async with stdio_server() as streams:
                await self.server.run(
                    streams[0], streams[1], self.server.create_initialization_options()
                )
        
        anyio.run(run_stdio_async)

    def run(self):
        """Run the server with the configured transport."""
        if self.transport == "sse":
            self.run_sse()
        else:
            self.run_stdio()


def main() -> int:
    """
    Main entry point demonstrating the clean, refactored architecture.
    
    Compare this to the original 800+ line monolithic main() function!
    This is now clean, readable, and maintainable.
    """
    try:
        provider = RefactoredMCPProvider()
        provider.run()
        return 0
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        return 0
    except Exception as e:
        logger.error(f"Server error: {e}")
        return 1


if __name__ == "__main__":
    exit(main())
