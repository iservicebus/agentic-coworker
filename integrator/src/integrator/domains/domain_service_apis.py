from fastapi import APIRouter, Depends, HTTPException, Path, Header, Request
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID

from integrator.utils.db import get_db
from integrator.utils.oauth import validate_token
from integrator.utils.llm import Embedder
from integrator.domains.domain_db_model import Domain, Capability, DomainCapability
from integrator.tools.tool_db_model import Skill, CapabilitySkill
from integrator.iam.iam_db_model import AgentProfile, User, Agent, RoleAgent, Role, RoleDomain
from integrator.iam.iam_db_crud import get_roles_by_username
from integrator.iam.iam_auth import validate_tenant
from sqlalchemy import func, text, bindparam
import numpy as np

# Create router for domain APIs
domain_router = APIRouter(prefix="/domains", tags=["domains"])

# === Tenant Helper Functions ===

def validate_tenant_access(sess, payload: dict, tenant_name: str):
    if not validate_tenant(sess,payload, tenant_name):
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied to tenant '{tenant_name}'"
        )

# === API Models ===
class DomainInfo(BaseModel):
    id: UUID
    name: str
    label: str
    description: Optional[str] = None
    scope: Optional[str] = None
    domain_entities: Optional[List] = None
    domain_purposes: Optional[str] = None
    value_metrics: Optional[List] = None
    created_at: Optional[str] = None
    workflows: Optional[List] = None
    services: Optional[List] = None

    class Config:
        from_attributes = True

class CapabilityInfo(BaseModel):
    id: UUID
    name: str
    label: str
    description: Optional[str] = None
    business_context: Optional[List] = None
    business_processes: Optional[List] = None
    outcome: Optional[str] = None
    business_intent: Optional[List] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

class SkillInfo(BaseModel):
    name: str
    label: str
    description: Optional[str] = None
    operational_entities: Optional[List] = None
    operational_procedures: Optional[List] = None
    operational_intent: Optional[str] = None
    preconditions: Optional[List] = None
    postconditions: Optional[List] = None
    proficiency: Optional[str] = None

    class Config:
        from_attributes = True

class DomainWithCapabilities(BaseModel):
    id: UUID
    name: str
    label: str
    description: Optional[str] = None
    scope: Optional[str] = None
    domain_entities: Optional[List] = None
    domain_purposes: Optional[str] = None
    value_metrics: Optional[List] = None
    created_at: Optional[str] = None
    capabilities: List[CapabilityInfo] = []

    class Config:
        from_attributes = True


class CapabilitySearchResult(BaseModel):
    name: str
    label: str
    description: Optional[str] = None
    outcome: Optional[str] = None
    similarity: float

    class Config:
        from_attributes = True

# === Helper Functions ===

def get_capabilities_by_vector_query_for_user(db: Session, emb: Embedder, query: str, username: str, k: int = 10) -> List[CapabilitySearchResult]:
    """
    Get capabilities by vector search restricted to user's active agent roles.
    Uses single JOIN query: username → active agent → roles → domains → capabilities + vector search
    
    Args:
        db: Database session
        emb: Embedder instance
        query: capability query string
        username: username from token
        k: number of results to return
    
    Returns:
        List of CapabilitySearchResult with name, label, description, outcome, and similarity
    """
    vec = np.array(emb.encode([query])[0])
    
    sql = text(
        """
        SELECT DISTINCT
            c.name,
            c.label,
            c.description,
            c.outcome,
            1 - (c.emb <=> (:v)::vector) AS cosine_sim,
            c.emb <=> (:v)::vector AS emb_distance
        FROM capabilities c
        JOIN domain_capability dc ON c.name = dc.capability_name
        JOIN role_domain rd ON dc.domain_name = rd.domain_name
        JOIN role_agent ra ON rd.role_name = ra.role_name
        JOIN users u ON ra.agent_id = u.working_agent_id
        WHERE u.username = :username
        ORDER BY emb_distance
        LIMIT :k
        """
    )
    
    rows = db.execute(
        sql.bindparams(
            bindparam("v", value=vec.tolist()),
            bindparam("username", value=username),
            bindparam("k", value=k)
        )
    ).all()
    
    return [
        CapabilitySearchResult(
            name=row[0],
            label=row[1],
            description=row[2],
            outcome=row[3],
            similarity=float(row[4])
        )
        for row in rows
    ]

def get_username_from_token(current_user: dict) -> str:
    """Extract username from the validated token."""
    username = current_user.get("preferred_username")
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token: preferred_username missing")
    return username

def get_user_capabilities(db: Session, username: str) -> List[CapabilityInfo]:
    """
    Fetches the complete role 0 domain 0 capability hierarchy for an agent.
    Returns a nested structure showing what the agent can access.
    """
    capabilities = db.query(Capability).join(
        DomainCapability, Capability.name == DomainCapability.capability_name
    ).join(
        RoleDomain, DomainCapability.domain_name == RoleDomain.domain_name
    ).join(
        RoleAgent, RoleDomain.role_name == RoleAgent.role_name
    ).join(
        User, RoleAgent.agent_id == User.working_agent_id
    ).filter(
        User.username == username
    ).distinct().all()
    
    return [CapabilityInfo.from_orm(cap) for cap in capabilities]

def get_user_domains_with_capabilities(db: Session, username: str) -> List[DomainWithCapabilities]:
    """
    Get domains with their capabilities for a user's active agent.
    """
    # Get domains accessible to the user's active agent (backed by Domain model)
    domains = db.query(Domain).join(
        RoleDomain, Domain.name == RoleDomain.domain_name
    ).join(
        RoleAgent, RoleDomain.role_name == RoleAgent.role_name
    ).join(
        User, RoleAgent.agent_id == User.working_agent_id
    ).filter(
        User.username == username
    ).distinct().all()
    
    result = []
    for domain in domains:
        # Get capabilities for this domain
        capabilities = db.query(Capability).join(
            DomainCapability, Capability.name == DomainCapability.capability_name
        ).filter(
            DomainCapability.domain_name == domain.name
        ).all()
        
        domain_with_caps = DomainWithCapabilities(
            id=domain.id,
            name=domain.name,
            label=domain.label,
            description=domain.description,
            capabilities=[CapabilityInfo.from_orm(cap) for cap in capabilities]
        )
        result.append(domain_with_caps)
    
    return result

# === API Endpoints ===

@domain_router.get("/domains", response_model=List[DomainInfo])
def get_all_domains(
    x_tenant: str = Header(..., alias="X-Tenant"),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches all domains for a specific tenant.
    Tenant is specified via X-Tenant header.
    """
    validate_tenant_access(db, current_user, x_tenant)
    domains = db.query(Domain).filter(Domain.tenant_name == x_tenant).all()
    return [DomainInfo.from_orm(domain) for domain in domains]

@domain_router.get("/capabilities", response_model=List[CapabilityInfo])
def get_capabilities_by_user(
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches capabilities available to the user's active agent.
    Uses access token to find active agent and filter based on agent's roles.
    Chain: username → active agent → roles → domains → capabilities
    """
    username = get_username_from_token(current_user)
    return get_user_capabilities(db, username)


@domain_router.get("/tenants/{tenant_name}/domains/{domain_name}/capabilities", response_model=List[CapabilityInfo])
def get_capabilities_by_domain(
    tenant_name: str = Path(...),
    domain_name: str = Path(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches all capabilities for a specific domain in a tenant.
    """
    validate_tenant_access(db, current_user, tenant_name)
    
    # Verify domain exists for this tenant
    domain = db.query(Domain).filter(
        (Domain.name == domain_name) &
        (Domain.tenant_name == tenant_name)
    ).first()
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found for tenant '{tenant_name}'")
    
    # Use JOIN to get capabilities for the domain
    capabilities = db.query(Capability).join(
        DomainCapability, 
        (Capability.name == DomainCapability.capability_name) &
        (Capability.tenant_name == DomainCapability.tenant_name)
    ).filter(
        (DomainCapability.domain_name == domain_name) &
        (DomainCapability.tenant_name == tenant_name)
    ).all()
    
    return [CapabilityInfo.from_orm(capability) for capability in capabilities]


@domain_router.get("/tenants/{tenant_name}/domains-with-capabilities", response_model=List[DomainWithCapabilities])
def get_domains_with_capabilities(
    tenant_name: str = Path(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches all domains with their associated capabilities for a specific tenant.
    """
    validate_tenant_access(db, current_user, tenant_name)
    
    # Get all domains for this tenant
    domains = db.query(Domain).filter(Domain.tenant_name == tenant_name).all()
    result = []
    
    for domain in domains:
        # Get capabilities for this domain
        capabilities = db.query(Capability).join(
            DomainCapability, 
            (Capability.name == DomainCapability.capability_name) &
            (Capability.tenant_name == DomainCapability.tenant_name)
        ).filter(
            (DomainCapability.domain_name == domain.name) &
            (DomainCapability.tenant_name == tenant_name)
        ).all()
        
        domain_with_caps = DomainWithCapabilities(
            id=domain.id,
            name=domain.name,
            label=domain.label,
            description=domain.description,
            capabilities=[CapabilityInfo.from_orm(cap) for cap in capabilities]
        )
        result.append(domain_with_caps)
    
    return result


@domain_router.get("/capabilities/query", response_model=List[CapabilitySearchResult])
def query_capabilities_by_vector(
    query: str,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Query capabilities using vector search, restricted to user's active agent roles.
    Uses access token to find active agent and filter based on agent's roles.
    Returns capabilities with similarity scores.
    """
    username = get_username_from_token(current_user)
    emb = Embedder()  # Initialize embedder
    return get_capabilities_by_vector_query_for_user(db, emb, query, username, limit)

@domain_router.get("/tenants/{tenant_name}/capabilities/search", response_model=List[CapabilityInfo])
def search_capabilities(
    tenant_name: str = Path(...),
    query: str = None,
    limit: int = 10,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Search capabilities by query string for a specific tenant.
    This is a simple text search - can be enhanced with vector search later.
    """
    validate_tenant_access(db, current_user, tenant_name)
    
    capabilities = db.query(Capability).filter(
        (Capability.tenant_name == tenant_name) &
        (
            func.lower(Capability.label).contains(func.lower(query)) |
            func.lower(Capability.description).contains(func.lower(query)) |
            func.lower(Capability.outcome).contains(func.lower(query))
        )
    ).limit(limit).all()
    
    return [CapabilityInfo.from_orm(capability) for capability in capabilities]

@domain_router.get("/tenants/{tenant_name}/capabilities/{capability_name}/domains", response_model=List[DomainInfo])
def get_domains_by_capability(
    tenant_name: str = Path(...),
    capability_name: str = Path(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Fetches all domains that contain a specific capability for a specific tenant."""
    validate_tenant_access(db, current_user, tenant_name)
    
    try:
        # Use JOIN to get domains for the capability within the tenant
        domains = db.query(Domain).join(
            DomainCapability, 
            (Domain.name == DomainCapability.domain_name) &
            (Domain.tenant_name == DomainCapability.tenant_name)
        ).filter(
            (DomainCapability.capability_name == capability_name) &
            (DomainCapability.tenant_name == tenant_name)
        ).all()
        
        return [DomainInfo.from_orm(domain) for domain in domains]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get domains for capability: {str(e)}")


# === New API Models for Tool and Skill Counts ===

class DomainToolCount(BaseModel):
    """Response model for domain with tool count."""
    name: str
    label: str
    description: Optional[str] = None
    tool_count: int

    class Config:
        from_attributes = True


class CapabilityToolSkillCount(BaseModel):
    """Response model for capability with tool and skill counts."""
    name: str
    label: str
    description: Optional[str] = None
    tool_count: int
    skill_count: int

    class Config:
        from_attributes = True


# === New API Endpoints for Tool and Skill Counts ===

@domain_router.get("/tenants/{tenant_name}/tool-counts", response_model=List[DomainToolCount])
def get_domains_tool_counts(
    tenant_name: str = Path(...),
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get all domains with their tool counts for a specific tenant.
    
    Returns all domains with the total count of tools in each domain.
    Tools are counted through two paths:
    - Domain → Capability → Tool (direct)
    - Domain → Capability → Skill → Tool
    
    If agent_id is provided, only returns domains associated with that agent
    through the agent's roles.
    
    Results are sorted by tool_count in descending order (largest to smallest).
    
    Args:
        tenant_name: Name of the tenant
        agent_id: Optional agent ID to filter domains by agent association
        db: Database session
        current_user: Validated user from token
        
    Returns:
        List of domains with their tool counts
    """
    validate_tenant_access(db, current_user, tenant_name)
    from integrator.domains.domain_db_crud import get_domains_with_tool_count
    
    results = get_domains_with_tool_count(db, tenant_name=tenant_name, agent_id=agent_id)
    return [DomainToolCount(**result) for result in results]


@domain_router.get("/tenants/{tenant_name}/domains/{domain_name}/capabilities/tool-skill-counts", response_model=List[CapabilityToolSkillCount])
def get_capabilities_tool_skill_counts(
    tenant_name: str = Path(...),
    domain_name: str = Path(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get all capabilities for a domain with their tool and skill counts for a specific tenant.
    
    Returns all capabilities in the specified domain with:
    - Total count of unique tools (via capability_tool and capability_skill → tool_skills)
    - Total count of unique skills (via capability_skill)
    
    Results are sorted by tool_count in descending order (largest to smallest).
    
    Args:
        tenant_name: Name of the tenant
        domain_name: Name of the domain to get capabilities for
        db: Database session
        current_user: Validated user from token
        
    Returns:
        List of capabilities with their tool and skill counts
    """
    validate_tenant_access(db, current_user, tenant_name)
    from integrator.domains.domain_db_crud import get_capabilities_with_tool_and_skill_count
    
    # Verify domain exists for this tenant
    domain = db.query(Domain).filter(
        (Domain.name == domain_name) &
        (Domain.tenant_name == tenant_name)
    ).first()
    if not domain:
        raise HTTPException(status_code=404, detail=f"Domain '{domain_name}' not found for tenant '{tenant_name}'")
    
    results = get_capabilities_with_tool_and_skill_count(db, domain_name=domain_name, tenant_name=tenant_name)
    return [CapabilityToolSkillCount(**result) for result in results]


# === Workflow API Models ===

class DomainToolCountInStep(BaseModel):
    """Response model for domain with tool count within a workflow step."""
    name: str
    label: str
    tool_count: int

    class Config:
        from_attributes = True


class WorkflowStepToolCount(BaseModel):
    """Response model for workflow step with tool count and domains."""
    id: str
    name: str
    label: str
    step_order: int
    intent: Optional[str] = None
    description: Optional[str] = None
    tool_count: int
    domains: List[DomainToolCountInStep] = []

    class Config:
        from_attributes = True


class WorkflowToolCount(BaseModel):
    """Response model for workflow with tool counts and workflow steps."""
    id: str
    name: str
    label: str
    description: Optional[str] = None
    tool_count: int
    workflow_steps: List[WorkflowStepToolCount] = []

    class Config:
        from_attributes = True


class WorkflowsWithTotalCount(BaseModel):
    """Response model for workflows with total MCP tool count."""
    total_mcp_tool_count: int
    workflows: List[WorkflowToolCount] = []

    class Config:
        from_attributes = True



# === Workflow API Endpoints ===


@domain_router.get("/tenants/{tenant_name}/workflows/tool-counts", response_model=WorkflowsWithTotalCount)
def get_workflows_tool_counts(
    tenant_name: str = Path(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get all workflows with their tool counts and workflow steps with tool counts for a specific tenant.
    
    Returns all workflows with:
    - Total count of unique tools across all workflow steps
    - List of workflow steps with their individual tool counts
    
    The relationship chain used:
    - Workflow → WorkflowStep (via workflow_name FK)
    - WorkflowStep → Domain (via workflow_step_domain)
    - Domain → Capability (via domain_capability)
    - Capability → Tool (via capability_tool and capability_skill → tool_skills)
    
    Additionally uses:
    - WorkflowStep → Capability (via workflow_step_capability) for direct capability associations
    
    Results are sorted by workflow name.
    
    Args:
        tenant_name: Name of the tenant
        db: Database session
        current_user: Validated user from token
        
    Returns:
        List of workflows with their tool counts and workflow steps
        
    Example response:
        [
            {
                "id": "uuid-1",
                "name": "campaign_management_workflow",
                "label": "Campaign Management Workflow",
                "description": "...",
                "tool_count": 25,
                "workflow_steps": [
                    {
                        "id": "uuid-step-1",
                        "name": "create_campaign_step",
                        "label": "Create Campaign",
                        "step_order": 1,
                        "intent": "create",
                        "description": "...",
                        "tool_count": 10
                    },
                    {
                        "id": "uuid-step-2",
                        "name": "configure_campaign_step",
                        "label": "Configure Campaign",
                        "step_order": 2,
                        "intent": "configure",
                        "description": "...",
                        "tool_count": 15
                    }
                ]
            }
        ]
    """
    validate_tenant_access(db, current_user, tenant_name)
    from integrator.domains.domain_db_crud import get_workflows_with_tool_count
    
    result = get_workflows_with_tool_count(db, tenant_name=tenant_name)
    return WorkflowsWithTotalCount(**result)
