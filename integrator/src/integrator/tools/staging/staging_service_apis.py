import uuid # Added for UUID
from fastapi import APIRouter, Depends, HTTPException, Body, Path, Query, File, UploadFile
from sqlalchemy.orm import Session

from integrator.tools.tool_db_crud import (
    upsert_staging_service,
    get_staging_service_by_id,
    get_staging_service_by_name,
    get_all_staging_services,
    delete_staging_service_by_id,
    search_staging_services
)
from integrator.tools.staging import staging_services_handler
from integrator.tools.tool_db_model import StagingService as DBStagingService # To avoid Pydantic model name clash
from integrator.utils.db import get_db
from integrator.utils.oauth import validate_token # Assuming this path is correct
from integrator.utils.llm import LLM

from pydantic import BaseModel, Field, field_validator, HttpUrl

from datetime import datetime

import json
import yaml
import logging
from pathlib import Path as PathLibPath
from typing import List, Dict, Any, Optional, Union

import os

# Pydantic Models for Staging Services
class StagingServiceBase(BaseModel):
    tenant: str = Field(..., example="default", description="Tenant identifier for the service.")
    service_data: Dict[str, Any] = Field(..., example={"name": "my-service", "description": "Service details object"})

    @field_validator('service_data')
    def service_data_must_contain_name(cls, v):
        if not isinstance(v, dict) or "name" not in v or not isinstance(v["name"], str) or not v["name"]:
            raise ValueError("service_data must be a dictionary and contain a non-empty 'name' field of type string.")
        return v

class StagingServiceCreate(StagingServiceBase):
    pass

class StagingServiceUpdate(BaseModel):
    # Tenant cannot be updated. Name is part of service_data.
    service_data: Dict[str, Any] = Field(..., example={"name": "updated-service-name", "description": "Updated details"})

    @field_validator('service_data')
    def update_service_data_must_contain_name(cls, v):
        if not isinstance(v, dict) or "name" not in v or not isinstance(v["name"], str) or not v["name"]:
            raise ValueError("service_data must be a dictionary and contain a non-empty 'name' field of type string.")
        return v

class StagingServiceResponse(BaseModel):
    id: uuid.UUID # Changed from int
    tenant: str
    name: str # Extracted name for convenience
    service_data: Dict[str, Any]
    created_by: Optional[str]
    created_at: datetime
    updated_by: Optional[str]
    updated_at: datetime

    class Config:
        from_attributes = True


staging_router = APIRouter(prefix="/staging", tags=["staging Services"])


# Helper to get username from token
def get_username_from_token(current_user: dict) -> str:
    username = current_user.get("preferred_username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token: username missing")
    return username

# API Endpoints

@staging_router.post("/tenants/{tenant_name}/staging-services/", response_model=StagingServiceResponse, status_code=201)
def add_staging_service_api(
    tenant_name: str = Path(..., description="The name of the tenant"),
    service_create: StagingServiceCreate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    username = get_username_from_token(current_user)
    if service_create.tenant != tenant_name:
        raise HTTPException(status_code=400, detail="Tenant in path does not match tenant in request body.")
    
    # The Pydantic model's validator already checks for 'name' in service_data
    
    try:
        db_service = upsert_staging_service(
            sess=db,
            staging_service_data=service_create.service_data,
            tenant=service_create.tenant,
            username=username
        )
        db.commit()  # Commit the transaction
        return db_service
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"An unexpected error occurred in add_staging_service_api for tenant '{tenant_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@staging_router.get("/tenants/{tenant_name}/staging-services/", response_model=List[StagingServiceResponse])
def list_staging_services_api(
    tenant_name: str = Path(..., description="The name of the tenant"),
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination"),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return"),
    db: Session = Depends(get_db),
    _: dict = Depends(validate_token) # Add auth if listing should be protected
):
    # username = get_username_from_token(current_user) # If needed for authorization checks
    services = get_all_staging_services(sess=db, tenant=tenant_name,  skip=skip, limit=limit)
    return services


@staging_router.get("/tenants/{tenant_name}/staging-services/{service_identifier}", response_model=StagingServiceResponse)
def get_staging_service_api(
    tenant_name: str = Path(..., description="The name of the tenant"),
    service_identifier: str = Path(..., description="The ID (UUID string) or name (string) of the staging service"), # Changed type hint
    db: Session = Depends(get_db),
    _: dict = Depends(validate_token) # Add auth if needed
):
    # username = get_username_from_token(current_user)
    service = None
    try:
        # Try to interpret as UUID first
        service_uuid = uuid.UUID(service_identifier)
        service = get_staging_service_by_id(sess=db, service_id=str(service_uuid))
    except ValueError:
        # If not a valid UUID, assume it's a name
        service = get_staging_service_by_name(sess=db, tenant=tenant_name, name=service_identifier)
    
    if not service or service.tenant != tenant_name: # Ensure service belongs to the tenant in path
        raise HTTPException(status_code=404, detail="Staging service not found for this tenant.")
    return service


@staging_router.put("/tenants/{tenant_name}/staging-services/{service_id}", response_model=StagingServiceResponse)
def update_staging_service_api(
    tenant_name: str = Path(..., description="The name of the tenant"),
    service_id: uuid.UUID = Path(..., description="The ID of the staging service to update"), # Changed type hint
    service_update: StagingServiceUpdate = Body(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    username = get_username_from_token(current_user)
    
    # Fetch service first to check tenant ownership before update attempt
    existing_service = get_staging_service_by_id(sess=db, service_id=str(service_id))
    if not existing_service or existing_service.tenant != tenant_name:
        raise HTTPException(status_code=404, detail="Staging service not found for this tenant to update.")

    # The Pydantic model's validator already checks for 'name' in service_data

    try:
        updated_service = upsert_staging_service(
            sess=db,
            staging_service_data=service_update.service_data,
            tenant=tenant_name,
            username=username,
            service_id=service_id
        )
        db.commit()  # Commit the transaction
        return updated_service
    except ValueError as e:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        db.rollback()
        logger.error(f"An unexpected error occurred in update_staging_service_api for tenant '{tenant_name}', service_id '{service_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@staging_router.delete("/tenants/{tenant_name}/staging-services/{service_id}", status_code=204) # 204 No Content for successful deletion
def delete_staging_service_api(
    tenant_name: str = Path(..., description="The name of the tenant"),
    service_id: str = Path(..., description="The id of the staging service to delete"), # Changed type hint
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    username = get_username_from_token(current_user) # For audit logging if deletion is tracked differently, or authorization

    # Fetch service first to check tenant ownership
    existing_service = get_staging_service_by_id(sess=db, service_id=service_id)
    if not existing_service or existing_service.tenant != tenant_name:
        raise HTTPException(status_code=404, detail="Staging service not found for this tenant to delete.")

    try:
        deleted = delete_staging_service_by_id(sess=db, service_id=str(existing_service.id))
        if not deleted:
            raise HTTPException(status_code=404, detail="Staging service not found.")
        db.commit()  # Commit the transaction
        # No body returned for 204
        return None
    except Exception as e:
        db.rollback()
        logger.error(f"Error deleting staging service '{service_id}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")






@staging_router.post("/tenants/{tenant_name}/staging-services/populate-from-config", response_model=List[StagingServiceResponse])
def populate_from_config_api(
    tenant_name: str = Path(..., description="The tenant for which to populate services from config (usually 'default')"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    username = get_username_from_token(current_user) # User performing this administrative action
    
    # For now, populate_services_from_config is hardcoded to use "config/split_services.json"
    # and extracts services for the 'tenant_name' passed to it.
    try:
        created_services = staging_services_handler.populate_services_from_config(
            db=db,
            tenant=tenant_name, # Pass the tenant from the path
            username=username
        )
        if not created_services:
            # This could mean all services already existed or config was empty for this tenant
            # Return 200 with empty list or a specific message
            pass
        return created_services
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"An unexpected error occurred during population for tenant '{tenant_name}': {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred during population: {str(e)}")





# Assuming the project structure where 'src' is a top-level directory
# and this file is in src/staging.
# So, to get to the project root (where 'schema' and '.env' might be),
# we go up three levels from this file's directory.
PROJECT_ROOT = PathLibPath(__file__).resolve().parent.parent.parent.parent.parent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

try:
    from integrator.tools.staging.api_doc import transform_api_doc_to_tool_definition
    from integrator.tools.staging.openapi import OpenAPIToToolConverter
    from integrator.tools.staging.postman import convert_postman_item_to_tool_definition
except ImportError as e:
    logger.error(f"Error importing conversion modules: {e}. Ensure they are in the correct path.")
    # Define dummy functions if imports fail, to allow FastAPI to start, though endpoints will fail.
    async def transform_api_doc_to_tool_definition(*args, **kwargs):
        raise ImportError("api_doc module not loaded")
    class OpenAPIToToolConverter:
        def __init__(self, *args, **kwargs):
            raise ImportError("openapi module not loaded")
        def convert(self):
            raise ImportError("openapi module not loaded")
    def convert_postman_item_to_tool_definition(*args, **kwargs):
        raise ImportError("postman module not loaded")


# --- Pydantic Models ---
class ApiDocUrlRequest(BaseModel):
    url: HttpUrl # Using HttpUrl for validation

class OpenApiLinkRequest(BaseModel):
    openapi_link: HttpUrl = Field(..., description="URL to the OpenAPI specification document (JSON or YAML).")

# --- Helper Functions ---
def get_schema_file_path(filename: str) -> PathLibPath:
    """Constructs the full path to a schema file."""
    return PROJECT_ROOT / "config" / "schema" / filename

def extract_requests_from_postman_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recursively extracts all request items from a Postman collection's item list,
    including those nested within folders.
    """
    request_items = []
    for item in items:
        if "request" in item: # This is a request item
            request_items.append(item)
        elif "item" in item: # This is a folder
            request_items.extend(extract_requests_from_postman_items(item["item"]))
    return request_items

# --- API Endpoints ---

@staging_router.post("/doc-to-tool", response_model=List[Dict[str, Any]])
async def convert_api_doc_to_tool(
    request_body: ApiDocUrlRequest,
    _: dict = Depends(validate_token) # Add auth if listing should be protected

    ):
    """
    Converts API documentation from a URL into a list of tool definition JSONs.
    """
    api_doc_url = str(request_body.url)

  
    # Use PROJECT_ROOT for consistent path construction
    system_prompt_path = PROJECT_ROOT / "config" / "prompts" / "api_doc_system_prompt.txt"
    gen_schema_path = PROJECT_ROOT / "config" / "schema" / "mcp_tool_schema.json"


    input_schema_system_prompt_path = PROJECT_ROOT / "config" / "prompts" /  "json_correction_prompt.txt"
    input_schema_path = PROJECT_ROOT / "config" / "schema" / "mcp_input_schema.json"


    llm = LLM()
#    llm_model = os.getenv("VLLM_MODEL")
    max_length = int(os.getenv("MAX_TEXT_EXTRACTION_LENGTH"))

    if not system_prompt_path.is_file():
        logger.error(f"System prompt file not found: {system_prompt_path}")
        raise HTTPException(status_code=500, detail=f"Server configuration error: System prompt file not found at {system_prompt_path}")
    if not gen_schema_path.is_file():
        logger.error(f"Generic schema file not found: {gen_schema_path}")
        raise HTTPException(status_code=500, detail=f"Server configuration error: Generic schema file not found at {gen_schema_path}")

    try:
        logger.info(f"Attempting to transform API doc from URL: {api_doc_url}")
        tool_definition = await transform_api_doc_to_tool_definition(
            api_doc_url=api_doc_url,
            system_prompt_template_path=system_prompt_path,
            generic_schema_path=gen_schema_path,
            input_schema_system_prompt_path=input_schema_system_prompt_path,
            input_schema_path=input_schema_path,
            llm = llm,
            max_length = max_length
            # llm_model can be omitted to use the default from api_doc.py
        )
        if tool_definition:
            logger.info(f"Successfully transformed API doc from URL: {api_doc_url}")
            return tool_definition # Wrap single definition in a list
        else:
            logger.warning(f"Transformation returned no tool definition for URL: {api_doc_url}")
            # Depending on desired behavior, could return empty list or error
            # Returning empty list as per plan for "failed" but not exceptional conversion
            return []
    except ImportError: # Catch if the module itself wasn't loaded
        logger.error("api_doc.py module is not available.")
        raise HTTPException(status_code=500, detail="Conversion service (api_doc) is not available.")
    except Exception as e:
        logger.error(f"Error transforming API doc from URL {api_doc_url}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to convert API documentation: {str(e)}")


@staging_router.post("/openapi-to-tool-by-link", response_model=List[Dict[str, Any]])
async def convert_openapi_to_tool_by_link(
    request_data: OpenApiLinkRequest = Body(...),
    _: dict = Depends(validate_token) # Add auth if listing should be protected

):
    """
    Converts an OpenAPI specification from a URL into a list of tool definition JSONs.
    """
    openapi_link_val = request_data.openapi_link
    spec_source_info = f"link {str(openapi_link_val)}"
    converter = None

    try:
        logger.info(f"Initializing OpenAPI converter from link: {openapi_link_val}")
        converter = OpenAPIToToolConverter(openapi_link=str(openapi_link_val))
        
        logger.info(f"Converting OpenAPI spec from {spec_source_info}...")
        tool_definitions = converter.convert()
        logger.info(f"Successfully converted OpenAPI spec from {spec_source_info}. Found {len(tool_definitions)} tools.")
        return tool_definitions

    except ImportError:
        logger.error("openapi.py module is not available.")
        raise HTTPException(status_code=500, detail="Conversion service (openapi) is not available.")
    except ValueError as ve:
        logger.error(f"ValueError during OpenAPI conversion from {spec_source_info}: {ve}")
        raise HTTPException(status_code=400, detail=f"Error processing OpenAPI specification: {str(ve)}")
    except Exception as e:
        logger.error(f"Unexpected error converting OpenAPI from {spec_source_info}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to convert OpenAPI specification: {str(e)}")

@staging_router.post("/openapi-to-tool-by-file", response_model=List[Dict[str, Any]])
async def convert_openapi_to_tool_by_file(
    openapi_file: UploadFile = File(...),
    _: dict = Depends(validate_token) # Add auth if listing should be protected

):
    """
    Converts an uploaded OpenAPI specification file into a list of tool definition JSONs.
    """
    spec_source_info = f"uploaded file '{openapi_file.filename}'"
    converter = None

    try:
        logger.info(f"Initializing OpenAPI converter from uploaded file: {openapi_file.filename}")
        content = await openapi_file.read()
        content_str = content.decode('utf-8')
        
        parsed_spec: Optional[Union[Dict, List]] = None
        try:
            parsed_spec = json.loads(content_str)
            logger.info(f"Parsed {openapi_file.filename} as JSON.")
        except json.JSONDecodeError:
            logger.warning(f"Failed to parse {openapi_file.filename} as JSON, attempting YAML.")
            try:
                parsed_spec = yaml.safe_load(content_str)
                logger.info(f"Parsed {openapi_file.filename} as YAML.")
            except yaml.YAMLError as ye:
                logger.error(f"Failed to parse {openapi_file.filename} as YAML: {ye}")
                raise HTTPException(status_code=400, detail=f"Invalid file format. Could not parse '{openapi_file.filename}' as JSON or YAML.")
        
        if not isinstance(parsed_spec, dict):
            logger.error(f"Parsed OpenAPI specification from {openapi_file.filename} is not a dictionary (got {type(parsed_spec)}).")
            raise HTTPException(status_code=400, detail=f"Invalid OpenAPI file content: Expected a JSON/YAML object, but got {type(parsed_spec).__name__}.")

        converter = OpenAPIToToolConverter(openapi_spec=parsed_spec)
        
        logger.info(f"Converting OpenAPI spec from {spec_source_info}...")
        tool_definitions = converter.convert()
        logger.info(f"Successfully converted OpenAPI spec from {spec_source_info}. Found {len(tool_definitions)} tools.")
        return tool_definitions

    except ImportError:
        logger.error("openapi.py module is not available.")
        raise HTTPException(status_code=500, detail="Conversion service (openapi) is not available.")
    except ValueError as ve:
        logger.error(f"ValueError during OpenAPI conversion from {spec_source_info}: {ve}")
        raise HTTPException(status_code=400, detail=f"Error processing OpenAPI specification: {str(ve)}")
    except Exception as e:
        logger.error(f"Unexpected error converting OpenAPI from {spec_source_info}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to convert OpenAPI specification: {str(e)}")


@staging_router.post("/postman-to-tool", response_model=List[Dict[str, Any]])
async def convert_postman_collection_to_tool(
    postman_file: UploadFile = File(..., description="Uploaded Postman Collection v2.1 JSON file."),
    _: dict = Depends(validate_token) # Add auth if listing should be protected

):
    """
    Converts an uploaded Postman Collection (v2.1 JSON format) into a list of tool definition JSONs.
    """
    if not postman_file.filename or not postman_file.filename.endswith(".json"):
        logger.warning(f"Postman file upload '{postman_file.filename}' is not a .json file.")
        # Allow it for now, but parsing will likely fail if not JSON.
        # raise HTTPException(status_code=400, detail="Invalid file type. Please upload a .json Postman collection.")

    try:
        logger.info(f"Reading Postman collection file: {postman_file.filename}")
        content = await postman_file.read()
        
        try:
            collection = json.loads(content.decode('utf-8'))
            logger.info(f"Successfully parsed Postman collection: {postman_file.filename}")
        except json.JSONDecodeError as je:
            logger.error(f"Invalid JSON in Postman collection file {postman_file.filename}: {je}")
            raise HTTPException(status_code=400, detail=f"Invalid Postman collection: Not a valid JSON file. Error: {str(je)}")

        if not isinstance(collection, dict) or "item" not in collection or not isinstance(collection["item"], list):
            logger.error(f"Invalid Postman collection structure in {postman_file.filename}. Missing 'item' list.")
            raise HTTPException(status_code=400, detail="Invalid Postman collection structure: Missing 'item' list at the root.")

        all_request_items = extract_requests_from_postman_items(collection["item"])
        
        if not all_request_items:
            logger.info(f"No processable request items found in Postman collection: {postman_file.filename}")
            return []

        tool_definitions: List[Dict[str, Any]] = []
        logger.info(f"Found {len(all_request_items)} request items in {postman_file.filename}. Converting...")
        for i, item in enumerate(all_request_items):
            try:
                item_name = item.get("name", f"UnnamedItem_{i+1}")
                logger.debug(f"Converting Postman item: {item_name}")
                tool_def = convert_postman_item_to_tool_definition(item)
                tool_definitions.append(tool_def)
                logger.debug(f"Successfully converted Postman item: {item_name}")
            except Exception as item_conversion_error:
                item_name_for_error = item.get("name", f"item at index {i}")
                logger.error(f"Failed to convert Postman item '{item_name_for_error}' from {postman_file.filename}: {item_conversion_error}", exc_info=True)
                # Optionally, skip failing items and continue, or raise an error for the whole batch.
                # For now, let's be strict and fail the request if any item fails.
                raise HTTPException(status_code=400, detail=f"Error converting Postman item '{item_name_for_error}': {str(item_conversion_error)}")
        
        logger.info(f"Successfully converted {len(tool_definitions)} items from Postman collection: {postman_file.filename}")
        return tool_definitions

    except ImportError: # Catch if the module itself wasn't loaded
        logger.error("postman.py module is not available.")
        raise HTTPException(status_code=500, detail="Conversion service (postman) is not available.")
    except HTTPException: # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.error(f"Unexpected error converting Postman collection {postman_file.filename}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to convert Postman collection: {str(e)}")

# To make this staging_router usable, it would typically be included in a main FastAPI app instance.
# Example (in your main app.py or similar):
# from fastapi import FastAPI
# from src.stagging import conversion_api
#
# app = FastAPI()
# app.include_staging_router(conversion_api.staging_router)
