from typing import Dict, Any, Optional, List, Union
# import etcd3 # No longer needed directly here
import json
# from collections import defaultdict # May not be needed after refactor
from typing import Dict, Any, Optional, List, Union
# import etcd3 # No longer needed directly here
import json
# from collections import defaultdict # May not be needed after refactor
from fastapi import FastAPI, HTTPException, Body, Query, Path, Depends, Request
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
from pydantic import BaseModel, Field, ValidationError
import io
import sys
from fastapi import APIRouter, File, UploadFile # Added for schema generation
from pydantic import HttpUrl # Added for schema generation

# SQLAlchemy imports for DB session
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


from integrator.tools.tool_etcd_crud import delete_service_metadata
from integrator.tools.tool_db_crud import search_mcp_tools,delete_tool_by_id,check_duplicate_tool, get_mcp_tool_by_name_tenant

from integrator.tools.tool_ingestion import enqueue_tool
from integrator.tools.publish.registration import register_single_service

from integrator.tools.publish.retrieve import retrieve_all_services # Import retrieval function
from integrator.utils.etcd import get_etcd_client as get_etcd_utility_client
from integrator.utils.logger import get_logger # Import the logger
from integrator.utils.db import get_db
from integrator.utils.graph import get_graph_driver, close_graph_driver
from integrator.tools.tool_graph_crud import delete_tool_node
from integrator.utils.queue.queue_factory import queue_manager
from integrator.utils.oauth import validate_token # Import for token validation
from integrator.iam.iam_db_model import AgentProfile # Import AgentProfile model
from integrator.utils.llm import Embedder # Import embedding model
from integrator.iam.iam_auth import get_auth_agent
# Initialize logger for this module
logger = get_logger(__name__)

# --- Configuration ---
METADATA_PREFIX = "services_metadata/" # Should match registration.py
# Default fields to exclude for the GET /services/metadata endpoint
DEFAULT_GET_EXCLUDED_FIELDS = ["protocol", "output_schema"]


# --- Import Service and Utility Functions ---
# Assuming functions are in src/services/ and src/utils/
try:
    # Add the 'src' directory to sys.path if necessary, depending on how the API is run
    # This might be needed if running `python service_api.py` directly from the root
    import os
    # Get the directory containing service_api.py
    api_dir = os.path.dirname(os.path.abspath(__file__))
    # Get the parent directory (project root)
    project_root = os.path.dirname(api_dir)
    src_path = os.path.join(project_root, 'src')
    if src_path not in sys.path:
         sys.path.insert(0, src_path)

    # Now try the imports from the correct location (imports were moved outside try block previously)
    from integrator.tools.publish.retrieve import retrieve_all_services, retrieve_service_by_name, retrieve_services_by_tenant # Add new function
    from integrator.utils.etcd import get_etcd_client as get_etcd_utility_client

    logger.info("✅ Successfully imported registration, retrieval, and utility functions.")
    REGISTRATION_AVAILABLE = True # Keep this flag for now, although retrieval might still work
except ImportError as e:
    logger.error(f"❌ Error: Could not import registration functions from src.services.registration: {e}", exc_info=True)
    logger.error("   Ensure the file exists and the path is correct relative to the project root.")
    REGISTRATION_AVAILABLE = False
    # Define dummy functions if import fails
    def register_single_service(*args, **kwargs):
        raise HTTPException(status_code=501, detail="Registration function not available due to import error.")
    def delete_service_metadata(*args, **kwargs):
        raise HTTPException(status_code=501, detail="Deletion function not available due to import error.")
    # Dummy for retrieve_all_services if import fails
    def retrieve_all_services(*args, **kwargs):
        raise HTTPException(status_code=501, detail="Retrieval function not available due to import error.")
    # Dummy for retrieve_service_by_name if import fails
    def retrieve_service_by_name(*args, **kwargs):
        raise HTTPException(status_code=501, detail="Single retrieval function not available due to import error.")
    # Dummy for retrieve_services_by_tenant if import fails
    def retrieve_services_by_tenant(*args, **kwargs):
        raise HTTPException(status_code=501, detail="Tenant-specific retrieval function not available due to import error.")
    # Dummy for get_etcd_utility_client if import fails (less likely but for completeness)
    def get_etcd_utility_client(*args, **kwargs):
         raise ImportError("Failed to import get_etcd_client from utils.utils")


# Initialize logger for this module
logger = get_logger(__name__)

# --- Pydantic Models ---

class UrlInput(BaseModel): # Added for schema generation
    openapi_url: HttpUrl

class ServiceMetadata(BaseModel):
    """Model for registering a new service."""
    id: Optional[str] = Field(None, description="Optional ID for updating existing service.", example="123e4567-e89b-12d3-a456-426614174000")
    name: str = Field(..., description="Unique name for the service.", example="my-new-service")
    description: Optional[str] = Field(None, description="Description of the service.", example="Processes user data.")
    appName: Optional[str] = Field(None, description="name of the application. default is host id", example="localhost6666")
    tool_type: Optional[str] = Field("general", description="Type of the tool. Defaults to 'general'.", example="general")

    inputSchema: Optional[Dict[str, Any]] = Field(None, description="JSON schema for the dynamic input.", example={"type": "object", "properties": {"data": {"type": "string"}}})
    staticInput: Optional[Dict[str, Any]] = Field(None, description="JSON data for the static input", example={"type": "object", "properties": {"result": {"type": "string"}}})
    transport: Optional[str] = Field("http", description="network transport. Defaults to 'http'.", example="http")
    auth: Optional[Dict[str, Any]] = Field(None, description="Authorization provider to be used for API access protection. If provided, it will overwrite the authorization in static input.", example={"provider": "github"})
    # Allow arbitrary extra fields if needed (e.g., custom metadata)
    # class Config:
    #     extra = "allow"

class RegistrationResponse(BaseModel):
    message: str
    service_name: str

class DeletionResponse(BaseModel):
    message: str
    service_id: str
    details: Optional[str] = None

class ErrorResponse(BaseModel):
    detail: str

class TransformedSchemaOutput(BaseModel):
    mcp_schema: Dict[str, Any] = Field(..., description="The Model Context Protocol (MCP) schema.")
    http_template: Any = Field(..., description="The JSON template for HTTP parameters.")


mcp_router = APIRouter(prefix="/mcp", tags=["mcp"])

# --- Etcd Connection Handling ---
# Dependency to get etcd client using the centralized utility function
async def get_etcd_client_dependency():
    """FastAPI dependency to provide an etcd client instance using the utility."""
    try:
        # Call the utility function (which handles connection and status check)
        # Pass configured host/port if different from default
        client = get_etcd_utility_client()
        return client
    except Exception as e:
        # Catch any exception from the utility function (incl. connection errors)
        logger.error(f"❌ Failed to get etcd client from utility: {e}", exc_info=True)
        # Return 503 Service Unavailable if etcd cannot be reached
        raise HTTPException(status_code=503, detail=f"Could not connect to etcd service: {e}")


# Helper to get username from token (similar to staging_services_api.py)
def get_username_from_token(current_user: dict) -> str:
    username = current_user.get("preferred_username")
    if not username:
        # This case should ideally be caught by validate_token if preferred_username is mandatory
        raise HTTPException(status_code=401, detail="Invalid token: preferred_username missing")
    return username



# --- API Endpoints ---

@mcp_router.get(
    "/list_tools",
    summary="Retrieve MCP Tools Metadata for an Agent",
    description="Fetches metadata for registered MCP tools for the specified agent using tool filters from agent context. Uses the new search_mcp_tools method with role-based filtering.",
    response_model=List[Dict[str, Any]]
)
async def get_service_metadata(
    request: Request,
    exclude: Optional[List[str]] = Query(DEFAULT_GET_EXCLUDED_FIELDS, description="List of top-level fields to exclude from each service's metadata."),
    current_user: dict = Depends(validate_token), # Add token validation
    db: Session = Depends(get_db)
):
    """
    Retrieves metadata for MCP tools for the specified agent using the new search_mcp_tools method.
    Gets tool filter from agent context and applies role-based filtering.
    """
    excluded_set = set(exclude) if exclude else set()
    logger.info(f"Request received for /mcp/list_tools (excluding: {excluded_set})")
    # Try both x-tenant and x_tenant (underscore version)
    tenant_name = request.headers.get("x-tenant") or request.headers.get("x_tenant")
    if not tenant_name:
        raise HTTPException(status_code=400, detail="X-Tenant header is required")
    agent_id, _ = get_auth_agent(db, current_user, tenant_name)
    if not agent_id or not tenant_name:
        raise HTTPException(status_code=400, detail="Agent ID is not provided in token")
    
    try:
        # Get embedding model
        emb = Embedder()
        
        # Get agent profile to retrieve tool filter
        agent_profile = db.query(AgentProfile).filter(AgentProfile.agent_id == agent_id).first()
        
        # Initialize filter parameters
        tool_filter = None
        tool_query = None

        # Extract filter parameters from agent profile if available
        if agent_profile and agent_profile.context:
            tool_filter = agent_profile.context
            # Extract tool_query separately if it exists
            tool_query = tool_filter.get("tool_query", "").strip() or None

        logger.info(
            "Using tool filter - agent_id: %s, filter: %s, query: %s",
            agent_id,
            tool_filter,
            tool_query,
        )

        # Call search_mcp_tools with the filter parameters
        tools = search_mcp_tools(
            sess=db,
            emb=emb,
            tenant_name=tenant_name,
            agent_id=agent_id,
            filter=tool_filter,
            tool_query=tool_query,
            k=100,  # Get more results, can be made configurable
        )

        
        # Process the results, applying exclusions to each tool's data
        processed_tools_list = []
        for tool_data in tools:
            # Convert tool data to the expected format and filter out excluded fields
            # The search_mcp_tools returns tool info with document field containing the MCP tool schema
            tool_document = tool_data.get("document", {})
            
            # Create a service-like structure from the tool data
            service_data = {
                "name": tool_data.get("name"),
                "description": tool_data.get("description"),
                "inputSchema": tool_document.get("inputSchema", {}),
                "tenant": tool_data.get("tenant"),
                "canonical_data": tool_data.get("canonical_data", {}),
                "id": tool_data.get("id"),
                "tool_type": tool_data.get("tool_type", "general")
            }
            
            # Add similarity score if available
            if "cosine_similarity" in tool_data:
                service_data["cosine_similarity"] = tool_data["cosine_similarity"]
            
            # Filter out excluded fields
            filtered_data = {k: v for k, v in service_data.items() if k not in excluded_set}
            processed_tools_list.append(filtered_data)

        logger.info(f"✅ Returning metadata for {len(processed_tools_list)} MCP tool(s) for agent '{agent_id}' in tenant '{tenant_name}'.")
        return processed_tools_list
        
    except HTTPException as http_exc:
        # Re-raise exceptions from the dependency or explicit raises here
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Unexpected error in /mcp/list_tools endpoint for agent '{agent_id}' in tenant '{tenant_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during MCP tools retrieval for agent '{agent_id}': {e}")


@mcp_router.get(
    "/services/{tenant}/{service_name}",
    summary="Retrieve Full Metadata for a Single Service by Tenant and Name",
    description="Fetches the complete metadata for a specific service by its tenant and name.",
    response_model=Dict[str, Any], # Return the full metadata dictionary
    responses={
        404: {"model": ErrorResponse, "description": "Service not found in the specified tenant"},
        503: {"model": ErrorResponse, "description": "Etcd connection unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_single_service_metadata(
    tenant: str = Path(..., description="The tenant of the service.", example="default"),
    service_name: str = Path(..., description="The name of the service to retrieve."),
    db: Session = Depends(get_db) # Add DB session dependency
):
    """
    Retrieves the complete metadata for a single service identified by its `tenant`
    and `service_name` using the `retrieve_service_by_name` function.
    """
    logger.info(f"Request received for /services/{tenant}/{service_name}")
    try:
        tool= get_mcp_tool_by_name_tenant(db,service_name, tenant)

        if tool is None:
            # Function returns None if not found or on error retrieving
            logger.info(f"ℹ️ Service '{service_name}' not found in tenant '{tenant}'.")
            raise HTTPException(status_code=404, detail=f"Service '{service_name}' not found in tenant '{tenant}'.")
        else:

            logger.info(f"✅ Returning full metadata for service '{service_name}' in tenant '{tenant}'.")
            return tool.document # Return the dictionary directly

    except HTTPException as http_exc:
        # Re-raise exceptions from the dependency or explicit raises here
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Unexpected error in /services/{tenant}/{service_name} endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred retrieving service '{service_name}' from tenant '{tenant}'.")


@mcp_router.get(
    "/tenants/{tenant_id}/services",
    summary="Retrieve All MCP Services for a Tenant",
    description="Fetches all registered MCP services (metadata) for the specified tenant ID.",
    response_model=List[Dict[str, Any]],
    responses={
        # 404 is not explicitly raised if tenant has no services, an empty list is returned.
        503: {"model": ErrorResponse, "description": "Etcd connection unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error"}
    }
)
async def get_all_mcp_services_by_tenant(
    tenant_id: str = Path(..., description="The ID of the tenant to retrieve services for.", example="default"),
    etcd_client = Depends(get_etcd_client_dependency),
    current_user: dict = Depends(validate_token) # Token validation dependency
):
    """
    Retrieves all MCP services (metadata) for the specified `tenant_id`.
    """
    logger.info(f"Request received for /mcp/tenants/{tenant_id}/services")
    try:
        # Call retrieve_services_by_tenant for the specified tenant.
        # This function returns a list of service dictionaries for that tenant, or an empty list.
        services_for_tenant = retrieve_services_by_tenant(etcd_client, tenant_id)

        # retrieve_services_by_tenant returns an empty list [] if tenant not found,
        # no services in tenant, or if an internal error occurred during its etcd operation.
        # Consistent with /mcp/list_tools, return [] in these cases.
        if not services_for_tenant:
             logger.info(f"✅ No services found for tenant '{tenant_id}' or retrieval issue, returning empty list.")
             return []

        logger.info(f"✅ Returning metadata for {len(services_for_tenant)} service(s) for tenant '{tenant_id}'.")
        return services_for_tenant
    except HTTPException as http_exc:
        # Re-raise exceptions from dependencies or explicit raises here
        raise http_exc
    except Exception as e:
        logger.error(f"❌ Unexpected error in /mcp/tenants/{tenant_id}/services endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during metadata retrieval for tenant '{tenant_id}'.")

@mcp_router.post(
    "/services",
    summary="Register a New Service",
    description="Registers a new service by storing its metadata and configuring routing in etcd.",
    response_model=RegistrationResponse,
    status_code=201,
    responses={
        501: {"model": ErrorResponse, "description": "Registration function not available"},
        503: {"model": ErrorResponse, "description": "Etcd connection unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error during registration"}
    }
)
async def register_service_endpoint(
    request: Request, # Added request parameter
    tenant: str = Query("default", description="The tenant to retrieve services for. Defaults to 'default'."),
    routing_overwrite: bool = Query(True, description="Whether to overwrite existing Traefik routing rules."),
    metadata_overwrite: bool = Query(True, description="Whether to overwrite existing service metadata."),
    etcd_client = Depends(get_etcd_client_dependency),
    db: Session = Depends(get_db), # Add DB session dependency
    current_user: dict = Depends(validate_token) # Add token validation
):
    """
    Registers a single service based on the provided metadata.
    This involves:
    1.  Registering Traefik routing rules based on `protocol.url`.
    2.  Storing the service metadata (description, schemas, protocol, etc.).
    """
    if not REGISTRATION_AVAILABLE:
         raise HTTPException(status_code=501, detail="Registration function not available due to import error.")


    # Parse request body first
    body_json = await request.json()
    try:
        service_data = ServiceMetadata(**body_json)
    except ValidationError as e:
        raise HTTPException(status_code=422, detail=e.errors())


    logger.info(f"Request received to register service: {service_data.name}")
    try:
        # Check for duplicate tool before processing registration
        # service_data.id is the tool_id, service_data.name is the tool_name
        tool_id_uuid = None
        if service_data.id:
            try:
                import uuid
                tool_id_uuid = uuid.UUID(service_data.id)
            except ValueError:
                logger.warning(f"Invalid UUID format for service ID: {service_data.id}")
                # Continue without tool_id_uuid, let the duplicate check handle it
        
        duplicate_error = check_duplicate_tool(db, service_data.name, tenant, tool_id_uuid)
        if duplicate_error:
            logger.error(f"Duplicate tool detected: {duplicate_error}")
            raise HTTPException(status_code=409, detail=duplicate_error)
        
        # Redirect stdout to capture print statements from the registration function
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Call the imported registration function
        username = get_username_from_token(current_user)


        rs= await enqueue_tool(queue_manager,db,service_data.model_dump(),tenant,username)
        if rs:

            # Restore stdout
            sys.stdout = old_stdout
            output_log = redirected_output.getvalue()
            logger.debug("--- Registration Function Output ---")
            logger.debug(output_log)
            logger.debug("--- End Registration Output ---")

            # Basic success check - could be improved if registration func returned status
            if "❌" in output_log or "Error" in output_log:
                # Attempt to return a more specific error if possible
                raise HTTPException(status_code=500, detail=f"Registration process reported errors. Check API logs. Log: {output_log[:500]}")

            logger.info(f"✅ Successfully processed registration request for service: {service_data.name}")
            return RegistrationResponse(message="Service registration processed successfully.", service_name=service_data.name)
        else:
            logger.error(f"❌ Error during service registration for {service_data.name}. Unable to enqueue the service data", exc_info=True)
            raise HTTPException(status_code=500, detail=f"Unable to enqueue service data during registration")


    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI/dependency errors
    except Exception as e:
        # Restore stdout in case of exception
        sys.stdout = old_stdout
        logger.error(f"❌ Error during service registration for '{service_data.name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during registration: {e}")



@mcp_router.delete(
    "/tenants/{tenant_name}/services/{service_id}",
    summary="Delete a Service by Tenant and Service ID",
    description="Deletes a service's metadata (for a specific tenant) and associated Traefik routing from etcd.",
    response_model=DeletionResponse,
    responses={
        404: {"model": ErrorResponse, "description": "Service not found to delete"}, # Added for clarity
        501: {"model": ErrorResponse, "description": "Deletion function not available"},
        503: {"model": ErrorResponse, "description": "Etcd connection unavailable"},
        500: {"model": ErrorResponse, "description": "Internal server error during deletion"}
    }
)
async def delete_service_endpoint(
    tenant_name: str = Path(..., description="The tenant of the service to delete.", example="default"),
    service_id: str = Path(..., description="The ID of the service to delete."),
    etcd_client = Depends(get_etcd_client_dependency),
    db: Session = Depends(get_db), # Add DB session dependency
    current_user: dict = Depends(validate_token) # Add token validation
):
    """
    Deletes a service identified by its `tenant` and `service_id`.
    This attempts to:
    1.  Delete the service's metadata from `services_metadata/{tenant}/`.
    2.  If metadata deletion is successful and a URL is found, attempt to delete the associated Traefik routing configuration, *only if the URL is not used by other remaining metadata across any tenant*.
    """
    if not REGISTRATION_AVAILABLE:
         raise HTTPException(status_code=501, detail="Deletion function not available due to import error.")

    logger.info(f"Request received to delete service: {service_id} from tenant: {tenant_name}")
    try:
        # Redirect stdout to capture logs from the deletion function
        old_stdout = sys.stdout
        redirected_output = io.StringIO()
        sys.stdout = redirected_output

        # Call the imported deletion function, now expecting tenant, db, and username
        username = get_username_from_token(current_user)
        agent_id = current_user.get("azp", None)  # Get agent_id from token for etcd operations
        rs=delete_tool_by_id(db,service_id)
        if rs:
            delete_service_metadata(etcd_client, db, service_id, tenant_name, agent_id, username)
            db.commit()

            # Attempt to delete from graph database (non-blocking if Neo4j is unavailable)
            try:
                driver=get_graph_driver()
                with driver.session() as gsess:
                    delete_tool_node(gsess, db, rs.name)
                close_graph_driver()
            except Exception as graph_error:
                # Log but don't fail the entire deletion if graph cleanup fails
                logger.warning(f"Graph cleanup failed for tool '{rs.name}', but continuing with deletion: {graph_error}")
                # Ensure driver is closed even if there's an error
                try:
                    close_graph_driver()
                except:
                    pass    
            # Restore stdout
            sys.stdout = old_stdout
            output_log = redirected_output.getvalue()
            logger.debug("--- Deletion Function Output ---")
            logger.debug(output_log)
            logger.debug("--- End Deletion Output ---")
        else:
            raise HTTPException(status_code=500, detail=f"Failed to find the tool  for '{service_id}' in tenant '{tenant_name}'")


        # Basic success check
        if "❌" in output_log or "Error" in output_log: # General error check
            raise HTTPException(status_code=500, detail=f"Deletion process for '{service_id}' in tenant '{tenant_name}' reported errors. Check API logs. Log: {output_log[:500]}")
        
        # Specific check for "No metadata found"
        # The delete_service_metadata function prints "ℹ️ No metadata found for service '{service_name}'. Nothing to delete."
        if f"No metadata found for service '{service_id}'" in output_log:
             logger.info(f"ℹ️ No metadata found for service '{service_id}' in tenant '{tenant_name}'. Assumed already deleted or never existed.")
             # Consider 404 if not found, or 200 if "deletion processed" means "it's gone now"
             raise HTTPException(status_code=404, detail=f"No metadata found for service '{service_id}' in tenant '{tenant_name}'. Nothing to delete.")
             # Alternatively, return a DeletionResponse indicating it was not found:
             # return DeletionResponse(message=f"No metadata found for service '{service_name}' in tenant '{tenant}'. Nothing deleted.", service_name=service_name, details=output_log.strip())


        logger.info(f"✅ Successfully processed deletion request for service: {service_id} in tenant: {tenant_name}")
        return DeletionResponse(message=f"Service '{service_id}' in tenant '{tenant_name}' deletion processed successfully.",service_id=service_id, details=output_log.strip())

    except HTTPException as http_exc:
        raise http_exc # Re-raise FastAPI/dependency errors
    except Exception as e:
        # Restore stdout in case of exception
        sys.stdout = old_stdout
        logger.error(f"❌ Error during service deletion for '{service_id}' in tenant '{tenant_name}': {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An error occurred during deletion of '{service_id}' in tenant '{tenant_name}': {e}")
