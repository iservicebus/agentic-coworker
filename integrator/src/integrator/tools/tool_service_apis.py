from typing import Dict, Any, Optional, List
from fastapi import APIRouter, HTTPException, Query, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import os

from integrator.utils.db import get_db
from integrator.utils.llm import Embedder, LLM
from integrator.utils.oauth import validate_token
from integrator.utils.logger import get_logger
from integrator.tools.tool_db_crud import search_mcp_tools
from integrator.tools.tool_db_model import McpTool, ToolSkill
from integrator.tools.tool_annotation import annotate_tool_by_llm
from integrator.iam.iam_db_crud import is_admin_user

logger = get_logger(__name__)

# Initialize router
tools_router = APIRouter(prefix="/tools", tags=["tools"])

# Pydantic models for request/response
class McpToolResponse(BaseModel):
    """Response model for MCP tool information"""
    id: str
    name: str
    description: Optional[str] = None
    document: Optional[Dict[str, Any]] = None
    canonical_data: Optional[Dict[str, Any]] = None
    tenant: str
    cosine_similarity: Optional[float] = None

class McpToolSearchRequest(BaseModel):
    """Request model for MCP tool search"""
    agent_id: Optional[str] = Field(None, description="Agent ID to filter tools")
    filter: Optional[Dict[str, Any]] = Field(None, description="Hierarchical filter following tool_filter_schema.json structure")
    tool_query: Optional[str] = Field(None, description="Tool description query for vector search")
    k: int = Field(10, description="Number of results to return for vector search", ge=1, le=100)

class ToolAnnotationRequest(BaseModel):
    """Request model for tool annotation"""
    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    inputSchema: Dict[str, Any] = Field(..., description="Tool input schema")

class ToolAnnotationResponse(BaseModel):
    """Response model for tool annotation"""
    annotation_result: Optional[Dict[str, Any]] = Field(None, description="Full annotation result from LLM")
    success: bool = Field(..., description="Whether the annotation was successful")
    error_message: Optional[str] = Field(None, description="Error message if annotation failed")

# Helper function to get username from token
def get_username_from_token(current_user: dict) -> str:
    username = current_user.get("preferred_username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token: preferred_username missing")
    return username

@tools_router.post(
    "/mcp-tools/search",
    summary="Search MCP Tools",
    description="Search MCP tools with flexible filtering options including agent and hierarchical filter (roles->domains->capabilities->skills) with strict tenant isolation",
    response_model=List[McpToolResponse]
)
async def search_mcp_tools_endpoint(
    request: McpToolSearchRequest,
    tenant_name: str = Query(..., description="Tenant name for strict isolation (REQUIRED)"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Search MCP tools with flexible filtering options and strict tenant isolation.
    
    Logic:
    1. All tools are filtered by tenant_name (required parameter)
    2. If agent_id is not provided, get all MCP tools for the tenant
    3. If agent_id is provided, follow the relationship chain: agent -> roles -> domains -> capabilities -> tools (within tenant)
    4. If filter (JSON schema) is provided, further filter tools based on the hierarchical structure
    5. If tool_query is provided, further narrow the tool output using vector search

    Request Body Example:
    {
        "agent_id": "agent-123",
        "filter": {
            "tool_query": "search string",
            "roles": [
                {
                    "name": "role_name",
                    "domains": [
                        {
                            "name": "domain_name",
                            "capabilities": [
                                {
                                    "name": "capability_name",
                                    "skills": ["skill1", "skill2"]
                                }
                            ]
                        }
                    ]
                }
            ]
        },
        "tool_query": "optional search query",
        "k": 10
    }
    
    Query Parameters:
    - tenant_name: REQUIRED - Tenant name for strict isolation
    """
    try:
        logger.info(
            "MCP tools search request from user %s for tenant %s",
            current_user.get("preferred_username", "unknown"),
            tenant_name,
        )
        logger.info(
            "Search parameters: tenant=%s, agent_id=%s, filter=%s, tool_query=%s, k=%s",
            tenant_name,
            request.agent_id,
            request.filter,
            request.tool_query,
            request.k,
        )

        # Get embedding model
        emb = Embedder()

        # Call the search function with tenant_name as required parameter
        results = search_mcp_tools(
            sess=db,
            emb=emb,
            tenant_name=tenant_name,
            agent_id=request.agent_id,
            filter=request.filter,
            tool_query=request.tool_query,
            k=request.k,
        )

        # Convert results to response model
        response_data: List[McpToolResponse] = []
        for tool in results:
            response_data.append(
                McpToolResponse(
                    id=tool["id"],
                    name=tool["name"],
                    description=tool.get("description"),
                    document=tool.get("document"),
                    canonical_data=tool.get("canonical_data"),
                    tenant=tool["tenant"],
                    cosine_similarity=tool.get("cosine_similarity"),
                )
            )

        logger.info("Returning %d MCP tools for tenant %s", len(response_data), tenant_name)
        return response_data
        
    except Exception as e:
        logger.error(f"Error searching MCP tools for tenant {tenant_name}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to search MCP tools: {str(e)}")

@tools_router.get(
    "/mcp-tools/agent/{agent_id}",
    summary="Get MCP Tools for Agent",
    description="Get all MCP tools available to a specific agent (legacy endpoint for backward compatibility)",
    response_model=List[McpToolResponse]
)
async def get_mcp_tools_for_agent_endpoint(
    agent_id: str,
    tool_query: Optional[str] = Query(None, description="Tool description query for vector search"),
    k: int = Query(10, description="Number of results to return for vector search", ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Legacy endpoint that gets MCP tools for a specific agent.
    This is a wrapper around the search endpoint for backward compatibility.
    """
    try:
        logger.info(f"Legacy MCP tools request for agent {agent_id} from user {current_user.get('preferred_username', 'unknown')}")
        
        # Get embedding model
        emb = Embedder()
        
        # Call the search function with agent_id
        results = search_mcp_tools(
            sess=db,
            emb=emb,
            agent_id=agent_id,
            filter=None,
            tool_query=tool_query,
            k=k
        )
        
        # Convert results to response model
        response_data = []
        for tool in results:
            response_data.append(McpToolResponse(
                id=tool["id"],
                name=tool["name"],
                description=tool.get("description"),
                document=tool.get("document"),
                canonical_data=tool.get("canonical_data"),
                tenant=tool["tenant"],
                cosine_similarity=tool.get("cosine_similarity")
            ))
        
        logger.info(f"Returning {len(response_data)} MCP tools for agent {agent_id}")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting MCP tools for agent {agent_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get MCP tools for agent: {str(e)}")

@tools_router.get(
    "/mcp-tools/admin",
    summary="Get All MCP Tools (Admin)",
    description="Get all MCP tools across all agents (admin endpoint)",
    response_model=List[McpToolResponse]
)
async def get_all_mcp_tools_admin_endpoint(
    tool_query: Optional[str] = Query(None, description="Tool description query for vector search"),
    k: int = Query(10, description="Number of results to return for vector search", ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Admin endpoint that gets all MCP tools across all agents.
    This endpoint is intended for administrative use.
    """
    try:
        logger.info(f"Admin MCP tools request from user {current_user.get('preferred_username', 'unknown')}")
        response_data = []
        is_admin=is_admin_user(db, current_user)
        if not is_admin: 
            return response_data
        
        # Get embedding model
        emb = Embedder()
        
        # Call the search function without agent_id to get all tools
        results = search_mcp_tools(
            sess=db,
            emb=emb,
            agent_id=None,  # No agent filter for admin view
            filter=None,
            tool_query=tool_query,
            k=k
        )
        
        # Convert results to response model

        for tool in results:
            response_data.append(McpToolResponse(
                id=tool["id"],
                name=tool["name"],
                description=tool.get("description"),
                document=tool.get("document"),
                canonical_data=tool.get("canonical_data"),
                tenant=tool["tenant"],
                cosine_similarity=tool.get("cosine_similarity")
            ))
        
        logger.info(f"Returning {len(response_data)} MCP tools for admin view")
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting all MCP tools for admin: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get MCP tools for admin: {str(e)}")

@tools_router.get(
    "/tenants/{tenant_name}/mcp-tools/{tool_id}/skills",
    summary="Get Skills for MCP Tool (Tenant Isolated)",
    description="Get all skills associated with a specific MCP tool within a tenant",
    response_model=List[str]
)
async def get_skills_for_mcp_tool(
    tenant_name: str,
    tool_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Get all skills associated with a specific MCP tool.

    This endpoint replaces the legacy "operations" API. It now returns skill
    names via the ``tool_skills`` relationship in the updated
    domain → capability → skill → tool model.
    """
    try:
        logger.info(
            "Skills for MCP tool request for tool_id %s from user %s",
            tool_id,
            current_user.get("preferred_username", "unknown"),
        )
        import uuid
        
        # Convert string to UUID if necessary
        try:
            tool_uuid = uuid.UUID(tool_id)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid tool_id format: {tool_id}")
        
        # Get skills associated with this tool
        skills_query = db.query(ToolSkill.skill_name).filter(
            ToolSkill.tool_id == tool_uuid
        ).all()
        
        # Extract skill names
        skill_names = [row.skill_name for row in skills_query]
        
        logger.info("Returning %d skills for tool_id %s", len(skill_names), tool_id)
        return skill_names
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(
            "Error getting skills for tool_id %s: %s", tool_id, str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get skills for tool: {str(e)}",
        )

@tools_router.get(
    "/tenants/{tenant_name}/capabilities/{capability_name}/mcp-tools",
    summary="Get MCP Tools by Capability (Tenant Isolated)",
    description="Get all MCP tools associated with a specific capability within a tenant",
    response_model=List[McpToolResponse]
)
async def get_mcp_tools_by_capability(
    tenant_name: str,
    capability_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get all MCP tools associated with a specific capability within a tenant.
    
    This endpoint uses the get_tools_by_capability_name function which retrieves
    tools through the capability_tool association table with tenant filtering.
    """
    try:
        logger.info(
            "MCP tools by capability request for capability %s in tenant %s from user %s",
            capability_name,
            tenant_name,
            current_user.get("preferred_username", "unknown"),
        )
        
        from integrator.tools.tool_db_crud import get_tools_by_capability_name
        
        # Get tools associated with this capability with tenant filtering
        tools = get_tools_by_capability_name(db, capability_name, tenant_name)
        
        # Convert results to response model
        response_data = []
        for tool in tools:
            response_data.append(McpToolResponse(
                id=str(tool.id),
                name=tool.name,
                description=tool.description,
                document=tool.document,
                canonical_data=tool.canonical_data,
                tenant=tool.tenant,
                cosine_similarity=None  # No similarity score for direct lookup
            ))
        
        logger.info(
            "Returning %d MCP tools for capability %s%s",
            len(response_data),
            capability_name,
            f" (tenant: {tenant_name})" if tenant_name else "",
        )
        return response_data
        
    except Exception as e:
        logger.error(
            "Error getting MCP tools for capability %s: %s", capability_name, str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MCP tools for capability: {str(e)}",
        )


@tools_router.get(
    "/tenants/{tenant_name}/skills/{skill_name}/mcp-tools",
    summary="Get MCP Tools by Skill (Tenant Isolated)",
    description="Get all MCP tools associated with a specific skill within a tenant",
    response_model=List[McpToolResponse]
)
async def get_mcp_tools_by_skill(
    tenant_name: str,
    skill_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get all MCP tools associated with a specific skill within a tenant.

    Note:
    - This endpoint reflects the updated domain → capability → skill → tool
      hierarchy and filters tools via the ``tool_skills`` relationship with tenant isolation.
    """
    try:
        logger.info(
            "MCP tools by skill request for skill %s in tenant %s from user %s",
            skill_name,
            tenant_name,
            current_user.get("preferred_username", "unknown"),
        )
        
        # Get tools associated with this skill with tenant filtering
        tools_query = db.query(McpTool).join(
            ToolSkill,
            ToolSkill.tool_id == McpTool.id,
        ).filter(
            ToolSkill.skill_name == skill_name,
            McpTool.tenant == tenant_name
        ).all()
        
        # Convert results to response model
        response_data = []
        for tool in tools_query:
            response_data.append(McpToolResponse(
                id=str(tool.id),
                name=tool.name,
                description=tool.description,
                document=tool.document,
                canonical_data=tool.canonical_data,
                tenant=tool.tenant,
                cosine_similarity=None  # No similarity score for direct lookup
            ))
        
        logger.info(
            "Returning %d MCP tools for skill %s",
            len(response_data),
            skill_name,
        )
        return response_data
        
    except Exception as e:
        logger.error(
            "Error getting MCP tools for skill %s: %s", skill_name, str(e), exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to get MCP tools for skill: {str(e)}",
        )


@tools_router.get(
    "/tenants/{tenant_name}/skills",
    summary="Get All Skills (Tenant Isolated)",
    description="Get all skills in a specific tenant",
    response_model=List[dict]
)
async def get_all_skills(
    tenant_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Get all skills in a specific tenant."""
    try:
        from integrator.tools.tool_db_model import Skill
        
        logger.info(
            "Get all skills request from user %s",
            current_user.get("preferred_username", "unknown"),
        )
        
        # Get all skills
        skills = db.query(Skill).all()
        
        # Convert to response format
        response_data = []
        for skill in skills:
            response_data.append({
                "name": skill.name,
                "label": skill.label,
                "description": skill.description,
                "operational_entities": skill.operational_entities,
                "operational_procedures": skill.operational_procedures,
                "operational_intent": skill.operational_intent,
                "preconditions": skill.preconditions,
                "postconditions": skill.postconditions,
                "proficiency": skill.proficiency
            })
        
        logger.info("Returning %d skills", len(response_data))
        return response_data
        
    except Exception as e:
        logger.error(f"Error getting all skills: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to get skills: {str(e)}")

@tools_router.get(
    "/tenants/{tenant_name}/capabilities/{capability_name}/skills",
    summary="Get Skills by Capability (Tenant Isolated)",
    description="Get all skills associated with a specific capability within a tenant",
    response_model=List[dict]
)
async def get_skills_by_capability(
    tenant_name: str,
    capability_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Get all skills associated with a specific capability within a tenant."""
    try:
        from integrator.tools.tool_db_model import Skill, CapabilitySkill
        
        logger.info(
            "Get skills by capability request for capability %s from user %s",
            capability_name,
            current_user.get("preferred_username", "unknown"),
        )
        
        # Get skills for this capability via CapabilitySkill relationship table
        skills = db.query(Skill).join(
            CapabilitySkill, Skill.name == CapabilitySkill.skill_name
        ).filter(
            CapabilitySkill.capability_name == capability_name
        ).all()
        
        # Convert to response format
        response_data = []
        for skill in skills:
            response_data.append({
                "name": skill.name,
                "label": skill.label,
                "description": skill.description,
                "operational_entities": skill.operational_entities,
                "operational_procedures": skill.operational_procedures,
                "operational_intent": skill.operational_intent,
                "preconditions": skill.preconditions,
                "postconditions": skill.postconditions,
                "proficiency": skill.proficiency
            })
        
        logger.info("Returning %d skills for capability %s", len(response_data), capability_name)
        return response_data
        
    except Exception as e:
        logger.error(
            f"Error getting skills for capability {capability_name}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get skills for capability: {str(e)}"
        )

@tools_router.get(
    "/tenants/{tenant_name}/skills/{skill_name}/capabilities",
    summary="Get Capabilities by Skill (Tenant Isolated)",
    description="Get all capabilities associated with a specific skill within a tenant",
    response_model=List[dict]
)
async def get_capabilities_by_skill(
    tenant_name: str,
    skill_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Get all capabilities associated with a specific skill within a tenant."""
    try:
        from integrator.domains.domain_db_model import Capability
        from integrator.tools.tool_db_model import CapabilitySkill
        
        logger.info(
            "Get capabilities by skill request for skill %s from user %s",
            skill_name,
            current_user.get("preferred_username", "unknown"),
        )
        
        # Get capabilities for this skill via CapabilitySkill relationship table
        capabilities = db.query(Capability).join(
            CapabilitySkill, Capability.name == CapabilitySkill.capability_name
        ).filter(
            CapabilitySkill.skill_name == skill_name
        ).all()
        
        # Convert to response format
        response_data = []
        for cap in capabilities:
            response_data.append({
                "id": str(cap.id),
                "name": cap.name,
                "label": cap.label,
                "description": cap.description,
                "business_context": cap.business_context,
                "business_processes": cap.business_processes,
                "outcome": cap.outcome,
                "business_intent": cap.business_intent,
                "created_at": str(cap.created_at) if cap.created_at else None
            })
        
        logger.info("Returning %d capabilities for skill %s", len(response_data), skill_name)
        return response_data
        
    except Exception as e:
        logger.error(
            f"Error getting capabilities for skill {skill_name}: {str(e)}", 
            exc_info=True
        )
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to get capabilities for skill: {str(e)}"
        )

@tools_router.post(
    "/annotate",
    summary="Annotate Tool",
    description="Annotate a tool using LLM to generate enhanced metadata from name, description, and inputSchema",
    response_model=ToolAnnotationResponse
)
async def annotate_tool_endpoint(
    request: ToolAnnotationRequest,
    current_user: dict = Depends(validate_token)
):
    """
    Annotate a tool using LLM to generate enhanced metadata.
    
    Takes the old Tool representation (name, description, inputSchema) and generates:
    1. Combined name and description data element
    2. Full annotation result from LLM processing
    
    Args:
        request: ToolAnnotationRequest containing name, description, and inputSchema
        current_user: Validated user token
        
    Returns:
        ToolAnnotationResponse with name_and_description and annotation_result
    """
    try:
        logger.info(f"Tool annotation request from user {current_user.get('preferred_username', 'unknown')}")
        logger.info(f"Annotating tool: {request.name}")
        
        # Construct tool_dict from request
        tool_dict = {
            "name": request.name,
            "description": request.description,
            "inputSchema": request.inputSchema
        }
        
        # Get system prompt path
        system_prompt_path = os.path.join(
            os.path.dirname(__file__), 
            "../../../config/prompts/tool_annotation_system_prompt.txt"
        )
        
        # Initialize LLM
        llm = LLM()
        
        # Call the annotation function
        annotation_result = await annotate_tool_by_llm(
            tool_dict=tool_dict,
            llm=llm,
            system_prompt_path=system_prompt_path
        )
        
        if annotation_result is None:
            logger.error(f"Tool annotation failed for tool: {request.name}")
            return ToolAnnotationResponse(
                annotation_result=None,
                success=False,
                error_message="Tool annotation failed - LLM returned None"
            )
        
        logger.info(f"Successfully annotated tool: {request.name}")
        
        return ToolAnnotationResponse(
            annotation_result=annotation_result,
            success=True,
            error_message=None
        )
        
    except FileNotFoundError as e:
        logger.error(f"System prompt file not found: {str(e)}", exc_info=True)
        return ToolAnnotationResponse(
            annotation_result=None,
            success=False,
            error_message=f"System prompt file not found: {str(e)}"
        )
    except Exception as e:
        logger.error(f"Error annotating tool {request.name}: {str(e)}", exc_info=True)
        return ToolAnnotationResponse(
            annotation_result=None,
            success=False,
            error_message=f"Tool annotation failed: {str(e)}"
        )
