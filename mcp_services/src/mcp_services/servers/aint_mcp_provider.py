import anyio
import httpx
import json # Added for config file reading
import os,io # Added for path joining
import time
import pathlib
import mcp.types as types
# Conditionally import Server and SseServerTransport
from mcp.server.lowlevel import Server # Moved down
from mcp.server.sse import SseServerTransport # Moved down
from mcp_services.utils.host import generate_host_id
from mcp_services.utils.json_norm import preprocess_keys, transform_json_with_schema
from mcp_services.utils.schema_parser import generalized_schema_parser
#from servers.aint_sse_transport import AintSseTransport
#from servers.aint_mcp_server import AintMCPServer
from string import Template
from mcp_services.utils.oauth import validate_token
from mcp_services.servers.custom_sse_transport import CustomSseServerTransport
from mcp_services.utils.env import load_env
from datetime import datetime
from graphiti_core import Graphiti
from graphiti_core.nodes import EpisodeType
from openai import AsyncAzureOpenAI
from graphiti_core.llm_client import OpenAIClient
from graphiti_core.embedder.openai import OpenAIEmbedder, OpenAIEmbedderConfig
from graphiti_core.cross_encoder.openai_reranker_client import OpenAIRerankerClient
from typing import Any, Dict, Tuple,  Union, Optional

# Load environment variables
load_env()

# --- Centralized Logging Setup ---
from mcp_services.utils.logger import  get_logger
logger = get_logger(__name__) # Get a logger for this module


FileLike = Union[io.IOBase, io.BytesIO]
FileTuple = Tuple[str, Union[bytes, FileLike], str]  # (filename, content, mime)

def _looks_like_file_tuple(v: Any) -> bool:
    # ("name.ext", bytes_or_file, "mime/type")
    return (
        isinstance(v, tuple)
        and len(v) in (2, 3)  # allow (filename, content) or (filename, content, mime)
        and isinstance(v[0], str)
        and (isinstance(v[1], (bytes, bytearray, memoryview, io.IOBase, io.BytesIO)))
    )

def _split_form_body_for_multipart(form: Dict[str, Any]):
    """Split a mixed dict into data (non-file fields) and files (file fields)."""
    data_part = {}
    files_part = {}

    for k, v in form.items():
        if _looks_like_file_tuple(v):
            # Normalize to (filename, fileobj/bytes, mime?) for httpx/requests
            if len(v) == 2:
                files_part[k] = (v[0], v[1])  # client figures out mime if omitted
            else:
                files_part[k] = (v[0], v[1], v[2])
        elif isinstance(v, (bytes, bytearray, memoryview)):
            # Treat raw bytes in a dict as a file only if caller wrapped as a tuple.
            data_part[k] = v.decode("utf-8", errors="ignore")
        elif isinstance(v, pathlib.Path):
            files_part[k] = (v.name, v.open("rb"))
        else:
            data_part[k] = v

    return data_part, files_part



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






async def initialize_graphiti():
    # Check if Graphiti is enabled
    graphiti_enabled = os.getenv("GRAPHITI_ENABLED", "false").lower() == "true"
    if not graphiti_enabled:
        logger.info("Graphiti is disabled via GRAPHITI_ENABLED environment variable")
        return None
    
    # Check if Azure configuration is available
    azure_api_key = os.getenv("AZURE_API_KEY")
    azure_api_version = os.getenv("AZURE_API_VERSION")
    azure_endpoint = os.getenv("AZURE_ENDPOINT")
    azure_llm_deployment = os.getenv("AZURE_LLM_DEPLOYMENT")
    azure_embedding_deployment = os.getenv("AZURE_EMBEDDING_DEPLOYMENT")
    graphiti_uri = os.getenv("GRAPHITI_URI")
    graphiti_user = os.getenv("GRAPHITI_USER")
    graphiti_password = os.getenv("GRAPHITI_PASSWORD")
    
    if not all([azure_api_key, azure_api_version, azure_endpoint, azure_llm_deployment, 
                azure_embedding_deployment, graphiti_uri, graphiti_user, graphiti_password]):
        logger.warning("Azure credentials for Graphiti are not fully configured. Skipping Graphiti initialization.")
        return None
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

        client = Graphiti(
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
        await client.build_indices_and_constraints()
        logger.info("Graphiti client initialized successfully.")
        return client
    except Exception as e:
        logger.error(f"Failed to initialize Graphiti client: {e}")
        return None

def main() -> int:
    # Load configuration from environment variables
    port = int(os.getenv("MCP_PORT", "6666"))
    transport = os.getenv("TRANSPORT", "stdio")
    authorization_enabled = os.getenv("AUTHORIZATION_ENABLED", "false").lower() == "true"
    authorization_host = os.getenv("META_AUTHORIZATION_LINK", "http://localhost:3000")
    INTEGRATOR_URL = os.getenv("INTEGRATOR_URL", "http://localhost:6060")
    PROXY_URL = os.getenv("PROXY_URL", "http://localhost")


    # === MCP Authorization constants ===
    # VS Code will connect to 127.0.0.1; keep RESOURCE_URL an exact match of the client URL.
    RESOURCE_PATH = "/sse"
    RESOURCE_URL = f"http://127.0.0.1:{port}{RESOURCE_PATH}"
    # Your Keycloak issuer base (realm URL). If you have it in env/config, use that; otherwise default:
    OIDC_ISSUER = os.getenv("OIDC_ISSUER", "http://localhost:8080/realms/mcp")


    logger.info(f"Starting server on port {port} with transport '{transport}', Authorization: {'Enabled' if authorization_enabled else 'Disabled'}")

    #aint_server = AintMCPServer("mcp_services")
    aint_server = Server("mcp_services")
    aint_server.tools_cache = {}
    aint_server.graphiti_client = None
    
    # Store SSE streams for each session
    aint_server.sse_streams = {}

    def get_current_sse_streams():
        """
        Get the SSE streams for the current request context.
        Returns a dict with 'read_stream', 'write_stream', and 'session_id' if available.
        Returns None if not in an SSE context or streams not found.
        """
        try:
            # Try to get session_id from query params first
            session_id = aint_server.request_context.request.query_params.get("session_id")
            if session_id:
                return aint_server.sse_streams.get(session_id)
            
            # If no session_id in query params, try to find by matching request headers
            # This is a fallback approach
            ctx_headers = dict(aint_server.request_context.request.headers)
            agent_id = ctx_headers.get("x-agent-id")
            
            if agent_id:
                # Find session by matching agent_id (this is less precise but can work as fallback)
                for session_id, stream_info in aint_server.sse_streams.items():
                    # You could store additional context in stream_info to match
                    return stream_info
            
            return None
        except Exception as e:
            logger.warning(f"Could not retrieve SSE streams from context: {e}")
            return None

    logger.info("Using SecuredServer.")

    def get_app_keys(headers, tenant_name, app_name=None):
        agent_id = headers.get("x-agent-id")
        sec_headers = {}
        if agent_id:
            sec_headers={"X-Agent-ID":agent_id, "Authorization": headers.get("authorization") }

            GET_SECRETS_URL = f"{INTEGRATOR_URL}/users/agents/{agent_id}/tenants/{tenant_name}/app_keys/{app_name}"

            client = httpx.Client()
            secrets_response = client.request(
                        method="get",
                        url=GET_SECRETS_URL,
                        headers= sec_headers
                    )
            if secrets_response.status_code == 200:
                app_keys=secrets_response.json().get(app_name, {})
            else:
                app_keys={}
        else:
            app_keys={}
        return app_keys

    def get_working_agent_id(agent_id, auth_header):
        sec_headers = {}
        if agent_id:
            sec_headers={"X-Agent-ID":agent_id, "Authorization": auth_header }

            AGENT_ID_URL = f"{INTEGRATOR_URL}/users/working-agent-id"

            client = httpx.Client()
            id_response = client.request(
                        method="get",
                        url=AGENT_ID_URL,
                        headers= sec_headers
                    )
            if id_response.status_code == 200:
                working_agent_id=id_response.json().get("working_agent_id", {})
            else:
                working_agent_id=None
        else:
            working_agent_id=None
        return working_agent_id

    def get_provider_token(headers, tenant_name, provider_name=None):
        agent_id = headers.get("x-agent-id")
        sec_headers = {}
        if agent_id:
            sec_headers={"X-Agent-ID":agent_id, "Authorization": headers.get("authorization") }

            GET_TOKEN_URL = f"{INTEGRATOR_URL}/provider_tokens/tenants/{tenant_name}/providers/{provider_name}/agents/{agent_id}"

            client = httpx.Client()
            token_response = client.request(
                        method="get",
                        url=GET_TOKEN_URL,
                        headers= sec_headers
                    )
            if token_response.status_code == 200:
                token=token_response.json().get("token", {})
            else:
                token={}
        else:
            token={}
        return token
 

    def generate_http_request(tenant, app_keys, headers, arguments, predefined_data, token ):
        req = {}
        pre_headers=predefined_data.get("headers", {})
        content_type= pre_headers.get("Content-Type") 
#        if content_type is None:
#                content_type=headers.get("Content-Type", "application/json")       
        
        if content_type == "application/json":
            req["body"]=json.dumps(arguments.get("aint_body", {})) 
        elif arguments.get("aint_body") != None:
            req["body"]= arguments.get("aint_body") 

        
        req["method"] = predefined_data.get("method")
        url = predefined_data.get("url")
        host_id, base_url, path = generate_host_id(url)
        host_id = f"{tenant}-{host_id}"

        if path and arguments.get("aint_path"):
            path = Template(path).substitute(arguments.get("aint_path"))

        if path:
            req["url"]=f"{PROXY_URL}/{host_id}/{path}"
        else:
            req["url"]=f"{PROXY_URL}/{host_id}"

        query = predefined_data.get("url").get("query", {})
        #if query:
        #    query_str=Template(json.dumps(query)).substitute(tenant_config.get("query", {}))
        #    if query_str:
        #        query = json.loads(query_str)

        if app_keys.get("query"):
            query = {**query, **app_keys.get("query")}
        

        if arguments.get("aint_query"):
            req["params"] = {**query, **arguments.get("aint_query")}
        else:    
            req["params"] = query

        headers = predefined_data.get("headers", {})
        #if headers:
        #    headers_str=Template(json.dumps(headers)).substitute(tenant_config.get("headers", {}))
        #    if headers_str:
        #        headers = json.loads(headers_str)
        if app_keys.get("headers"):
            headers = {**headers, **app_keys.get("headers")}

        if token.get("accessToken"):
            headers["Authorization"] = f"Bearer {token.get('accessToken')}"
      

        if arguments.get("aint_headers"):
            req["headers"] = {**headers, **arguments.get("aint_headers")}
        else:
            req["headers"] = headers            
        req["headers"]["Host"] = ".".join(url.get("host", []))

        return req

    # --- MCP Authorization: Protected Resource Metadata (PRM) ---
    async def protected_resource_metadata(request):
        # RFC 9728-style metadata for the /sse resource
        return Response(
            media_type="application/json",
            content=json.dumps({
                "resource": RESOURCE_URL,                      # MUST exactly match the URL clients use
                "authorization_servers": [OIDC_ISSUER],        # Keycloak issuer URL
                "bearer_methods_supported": ["header"],        # optional hint
                "scopes_supported": ["mcp:invoke"]             # optional; tailor to your needs
            })
        )


    from pydantic import AnyUrl, FileUrl
    from starlette.requests import Request

    SAMPLE_RESOURCES = {
        "greeting": {
            "content": "Hello! This is a sample text resource.",
            "title": "Welcome Message",
        },
        "help": {
            "content": "This server provides a few sample text resources for testing.",
            "title": "Help Documentation",
        },
        "about": {
            "content": "This is the simple-resource MCP server implementation.",
            "title": "About This Server",
        },
    }


    @aint_server.list_resources()
    async def list_resources() -> list[types.Resource]:
        return [
            types.Resource(
                uri=FileUrl(f"file:///{name}.txt"),
                name=name,
                title=SAMPLE_RESOURCES[name]["title"],
                description=f"A sample text resource named {name}",
                mimeType="text/plain",
            )
            for name in SAMPLE_RESOURCES.keys()
        ]

    @aint_server.read_resource()
    async def read_resource(uri: AnyUrl):
        if uri.path is None:
            raise ValueError(f"Invalid resource path: {uri}")
        name = uri.path.replace(".txt", "").lstrip("/")

        if name not in SAMPLE_RESOURCES:
            raise ValueError(f"Unknown resource: {uri}")

        return [ReadResourceContents(content=SAMPLE_RESOURCES[name]["content"], mime_type="text/plain")]







    # Tool definition needs to be compatible with both Server types.
    # SecuredServer's call_tool expects a 'header' argument, BaseServer's does not.
    # We define the tool function to accept 'header' but only use it if app is SecuredServer.
    @aint_server.call_tool()
    async def fetch_tool(
        name: str, arguments: dict
    ) -> list[types.TextContent | types.ImageContent | types.EmbeddedResource]:

        # 'header' argument will be None if authorization_enabled is False and BaseServer is used.
        # If you need to use the header for secured operations, check if it's present.
        # For this example, fetch_tool logic doesn't directly use the header for its core operation,
        # but a real secured tool might.
        ctx_headers = dict(aint_server.request_context.request.headers)
        logger.info(f"fetch_tool accessed headers via context: {ctx_headers}")

        # Access SSE streams for this session
        sse_streams = get_current_sse_streams()
        if sse_streams:
            logger.info(f"SSE streams available for session {sse_streams['session_id'].hex}")
            logger.info(f"Read stream: {type(sse_streams['read_stream'])}")
            logger.info(f"Write stream: {type(sse_streams['write_stream'])}")
        else:
            logger.info("No SSE streams found for current context")

        tenant_name, app_keys, sec_headers = get_tenant_config(ctx_headers, name)
  

        url=f"{INTEGRATOR_URL}/mcp/services/{tenant_name}/{name}"
        client = httpx.Client()
        response = client.request(
                    method="get",
                    url=url,
                    headers= sec_headers
                )

        if response.status_code == 200:
            try:
                # Parse the JSON response
                token={}
                service = response.json()
                predefined_data = service["staticInput"]
                auth_info = service.get("auth")
                provider_name = None
                app_name = service.get("appName")
                if auth_info and isinstance(auth_info, dict):
                    provider_name = auth_info.get("provider")

                if provider_name:
                    token = get_provider_token(ctx_headers, tenant_name, provider_name)

                if app_name:
                    app_keys = get_app_keys(ctx_headers, tenant_name, app_name)
                if isinstance(predefined_data, str):
                    predefined_data = json.loads(predefined_data)
                
                tools = await list_tools()
                tool_def = next((tool for tool in tools if tool.name == name), None)
                
                if tool_def:
                    input_schema = tool_def.inputSchema

                    name_list=["aint_body", "aint_query", "aint_path", "aint_headers"]
                    for param_name in name_list:
                        if input_schema and arguments.get(param_name):
                            param_schema = input_schema.get("properties", {}).get(param_name, {})
                            if param_schema and param_schema.get("type") == "object":
                                try:
                                    # Use the new generalized schema parser for complex schemas
                                    arguments[param_name] = generalized_schema_parser(arguments[param_name], param_schema)
                                    logger.info(f"Successfully parsed {param_name} using generalized schema parser")
                                except Exception as e:
                                    logger.warning(f"Generalized parser failed for {param_name}: {e}. Falling back to legacy parser.")
                                    # Fallback to the original method
                                    try:
                                        preprocessed_param = preprocess_keys(arguments[param_name])
                                        arguments[param_name] = transform_json_with_schema(preprocessed_param, param_schema)
                                        logger.info(f"Successfully parsed {param_name} using legacy parser")
                                    except Exception as fallback_e:
                                        logger.error(f"Both parsers failed for {param_name}: {fallback_e}. Using original data.")

                req =generate_http_request(tenant_name, app_keys, ctx_headers, arguments, predefined_data, token)

                body = req.get("body")
                headers=req.get("headers", {})
                content_type = headers.get("Content-Type", "").lower().strip()

                # 0) No body at all
                if body is None:
                    ext_response= client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                    )
                 # 1) JSON: explicit or inferred
                elif isinstance(body, dict) and ("application/json" in content_type or content_type == ""):
                    # JSON body
                    if "Content-Type" not in headers:
                        headers["Content-Type"] = "application/json"
                    ext_response = client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        json=body
                    )

                # 2) application/x-www-form-urlencoded (typical HTML forms)
                elif isinstance(body, dict) and ("application/x-www-form-urlencoded" in content_type):
                    headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
                    ext_response=client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        data=body,  # <-- DATA (form-encoded)
                    )
                # 3) Multipart form with files (multipart/form-data)
                #    Trigger if Content-Type says multipart/form-data OR the dict contains file-tuples/Paths.
                elif isinstance(body, dict) and (("multipart/form-data" in content_type) or any(_looks_like_file_tuple(v) or isinstance(v, pathlib.Path) for v in body.values())):
                    data_part, files_part = _split_form_body_for_multipart(body)

                    # Let the client set the multipart boundary & header automatically.
                    if "Content-Type" in headers and "multipart/form-data" in headers["Content-Type"].lower():
                        headers.pop("Content-Type", None)
                    ext_response = client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        data=data_part if data_part else None,   # <-- extra non-file fields
                        files=files_part if files_part else None # <-- FILES
                    )


                # 4) Raw body via content= (bytes/str/stream or any custom Content-Type, including multipart/related, etc.)
                #    Use this for arbitrary payloads (e.g., Google Drive multipart/related, binary uploads, NDJSON streams).
                elif isinstance(body, (bytes, bytearray, memoryview, io.IOBase, io.BytesIO)):
                    # If caller didn’t set Content-Type, choose a safe default
                    headers.setdefault("Content-Type", "application/octet-stream")
                    ext_response= client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        content=body,  # <-- CONTENT (raw)
                    )

                # 4b) String body: send raw text (client will set text/* only if you set it)
                elif isinstance(body, str):
                    headers.setdefault("Content-Type", "text/plain; charset=utf-8")
                    ext_response= client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        content=body,  # <-- CONTENT (raw text)
                    )

                # 5) Fallback: if caller passed an iterator/generator (streaming) or unknown type → try content=
                #    Many HTTP clients accept iterables/async generators for streaming request bodies.
                else:
                    ext_response = client.request(
                        method=req["method"],
                        url=req["url"],
                        headers=headers,
                        params=req.get("params"),
                        content=body,  # <-- CONTENT (stream/iterable or last-resort)
                        #data=body
                    )
                ext_response.raise_for_status()
                if aint_server.graphiti_client:
                    try:
                        tool_call_info = {
                            "tool_name": name,
                            "arguments": arguments,
                            "response": ext_response.text,
                            "tenant": tenant_name,
                            "agent_id": ctx_headers.get("x-agent-id"),
                            "timestamp": datetime.now().isoformat()
                        }
                        await aint_server.graphiti_client.add_episode(
                            name=f"ToolCall-{name}-{time.time()}",
                            episode_body=json.dumps(tool_call_info, default=str),
                            source=EpisodeType.json,
                            reference_time=datetime.now(),
                            source_description="MCPToolCall"
                        )
                        logger.info(f"Logged tool call for '{name}' to Graphiti.")
                    except Exception as e:
                        logger.error(f"Failed to log tool call to Graphiti: {e}")
                return [types.TextContent(type="text", text=ext_response.text)]

            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401 and provider_name:
                    auth_url = f"{authorization_host}/token/start/oauth_providers/{provider_name}"
                    error_message = (
                        f"Authorization required. Please use this provided  link {auth_url} to authorize the application and try again. "
                    )
                    client.close()
                    raise ValueError(error_message)
                else:
                    client.close()
                    raise ValueError(f"error: {str(e)}")
            except Exception as e:
                client.close()
                raise ValueError(f"error: {str(e)}")
        else:
            client.close()
            error_message = f"Failed to fetch tool definition for '{name}'. Status: {response.status_code}, Response: {response.text}"
            logger.error(error_message)
            raise ValueError(error_message)


    @aint_server.list_tools()
    async def list_tools(
        cursor: Optional[str] = None,
        limit: Optional[int] = None
    ) -> types.ListToolsResult:
    #async def list_tools() -> list[types.Tool]:
        ctx_headers = dict(aint_server.request_context.request.headers)

        session_id = aint_server.request_context.request.query_params.get("session_id")
        print(" session_id in list_tools", session_id)
        
        tenant_name, _, sec_headers = get_tenant_config(ctx_headers)
        cache_key = f"tools:{tenant_name}"
        cached_data = aint_server.tools_cache.get(cache_key)
        
        if cached_data and time.time() - cached_data['timestamp'] < 60:
            return cached_data['tools']

        client = httpx.Client()
        url=f"{INTEGRATOR_URL}/mcp/list_tools"
        params={"tenant":tenant_name}
        response = client.request(
                    method="get",
                    url=url,
                    params=params,
                    headers=sec_headers
                )
        if response.status_code == 200:
            try:
                mcp_tools_data = response.json()
                tools=[]
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
                
                aint_server.tools_cache[cache_key] = {
                    'timestamp': time.time(),
                    'tools': tools
                }
                return tools
            except json.JSONDecodeError:
                logger.info("Error: Failed to decode JSON response.")
                return []
            except Exception as e:
                logger.info(f"An unexpected error occurred: {e}")
                return []
        else:
            logger.info("Error: Request failed.")
            return []

    if transport == "sse":
        from starlette.applications import Starlette
        from starlette.routing import Mount, Route
        from starlette.responses import Response

        #sse = AintSseTransport("/messages/", config)
        sse = CustomSseServerTransport("/messages/")

        logger.info("Using SecuredSse transport.")

        async def ensure_valid_token(request):
            try:
                res = await validate_token(request, get_working_agent_id)
            except Exception:
                return None
            return res or None

        async def handle_sse(request):
            # ---- AUTH BEFORE HANDSHAKE ----
            if authorization_enabled:
                claims = await ensure_valid_token(request)
                if not claims:
                    prm_url = f"http://127.0.0.1:{port}/.well-known/oauth-protected-resource{RESOURCE_PATH}"
                    return Response(
                        status_code=401,
                        headers={"WWW-Authenticate": f'Bearer resource_metadata="{prm_url}"'}
                    )

            # Only start the SSE connection after auth succeeds
            async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
                read_stream, write_stream, session_id = streams
                print(" session_id ", session_id.hex)
                
                # Store SSE streams for this session
                aint_server.sse_streams[session_id] = {
                    'read_stream': read_stream,
                    'write_stream': write_stream,
                    'session_id': session_id
                }

                try:
                    await aint_server.run(
                        read_stream, write_stream, aint_server.create_initialization_options(), request.headers
                    )
                finally:
                    # Clean up streams when session ends
                    aint_server.sse_streams.pop(session_id, None)
            return Response(status_code=200)



        async def startup_event():
            aint_server.graphiti_client = await initialize_graphiti()

        starlette_app = Starlette(
            debug=True,
            routes=[
                Route("/sse", endpoint=handle_sse),
                Route("/.well-known/oauth-protected-resource/sse", endpoint=protected_resource_metadata),
                Mount("/messages/", app=sse.handle_post_message),

            ],
            on_startup=[startup_event]
        )

        import uvicorn

        uvicorn.run(starlette_app, host="0.0.0.0", port=port)
    else:
        from mcp.server.stdio import stdio_server

        async def arun():
            aint_server.graphiti_client = await initialize_graphiti()
            async with stdio_server() as streams:
                await aint_server.run(
                    streams[0], streams[1], aint_server.create_initialization_options()
                )

        anyio.run(arun)

    return 0

if __name__ =="__main__":
    main() # Call main without arguments
