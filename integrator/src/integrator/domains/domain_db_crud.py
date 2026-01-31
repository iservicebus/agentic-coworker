import json
import os
from integrator.domains.domain_db_model import (
    Domain, Capability, DomainCapability, CanonicalSkill, CapabilityCanonicalSkill,
    Workflow, WorkflowStep, WorkflowStepDomain, WorkflowStepCapability
)
from integrator.tools.tool_db_model import Skill, CapabilitySkill
from integrator.utils.db import get_db_cm
from integrator.utils.llm import Embedder
from sqlalchemy import  select, insert
from integrator.utils.logger import get_logger
import numpy as np
from typing import List, Dict, Any


logger = get_logger(__name__)


def get_all_domains(sess, tenant_name: str) -> List[Dict[str, Any]]:
    """Return all domains for a specific tenant as a list of JSON-serializable dicts.

    Each item contains: name, description, scope, domain_entities, domain_purposes.
    
    Args:
        sess: Database session
        tenant_name: Name of the tenant to filter domains by
    """
    domains = sess.execute(
        select(Domain).where(Domain.tenant_name == tenant_name)
    ).scalars().all()
    return [
        {
            "name": d.name,
            "description": d.description,
            "scope": d.scope,
            "domain_entities": d.domain_entities,
            "domain_purpose": d.domain_purposes,
        }
        for d in domains
    ]


def get_capabilities_by_domain(sess, domain_name: str, tenant_name: str) -> List[Dict[str, Any]]:
    """Return capabilities for a given domain and tenant as a list of JSON-serializable dicts.

    Uses the DomainCapability relationship table to join domains and capabilities.
    
    Args:
        sess: Database session
        domain_name: Name of the domain
        tenant_name: Name of the tenant to filter by
    """
    capabilities = sess.execute(
        select(Capability)
        .join(DomainCapability, Capability.name == DomainCapability.capability_name)
        .where(
            (DomainCapability.domain_name == domain_name) &
            (DomainCapability.tenant_name == tenant_name) &
            (Capability.tenant_name == tenant_name)
        )
    ).scalars().all()

    return [
        {
            "name": c.name,
            "label": c.label,
            "description": c.description,
            "business_context": c.business_context,
            "business_processes": c.business_processes,
            "outcome": c.outcome,
            "business_intent": c.business_intent,
        }
        for c in capabilities
    ]


def upsert_domain(sess, emb, domain_data, tenant_name: str):
    """Upsert a domain record for a specific tenant.
    
    Args:
        sess: Database session
        emb: Embedder instance for generating embeddings
        domain_data: Dictionary containing domain attributes
        tenant_name: Name of the tenant
    """
    name = domain_data["name"]
    label = domain_data["label"]
    description = domain_data.get("description", "")
    scope = domain_data.get("scope", "")
    domain_purposes = domain_data.get("domain_purposes", "")
    domain_entities = domain_data.get("domain_entities", [])
    value_metrics = domain_data.get("value_metrics", [])

    emb_input_parts = [
        label or "",
        description or "",
        scope or "",
        domain_purposes or "",
        " ".join(json.dumps(domain_entities)),
        " ".join(json.dumps(value_metrics)),
    ]
    emb_input = " ".join(part for part in emb_input_parts if part).strip()
    emb_vector = emb.encode(emb_input)

    domain = sess.execute(
        select(Domain).where(
            (Domain.name == name) & 
            (Domain.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not domain:
        domain = Domain(
            name=name,
            tenant_name=tenant_name,
            label=label,
            description=description,
            scope=scope,
            domain_entities=domain_entities,
            domain_purposes=domain_purposes,
            value_metrics=value_metrics,
            emb=emb_vector
        )
        sess.add(domain)
        logger.info(f"Inserted new domain {domain.name} for tenant {tenant_name}")
    else:
        domain.label = label
        domain.description = description
        domain.scope = scope
        domain.domain_entities = domain_entities
        domain.domain_purposes = domain_purposes
        domain.value_metrics = value_metrics
        domain.emb = emb_vector
        logger.info(f"Updated existing domain {domain.name} for tenant {tenant_name}")


def upsert_capability(sess, emb, cap_data, tenant_name: str):
    """Upsert a capability record for a specific tenant.
    
    Args:
        sess: Database session
        emb: Embedder instance for generating embeddings
        cap_data: Dictionary containing capability attributes
        tenant_name: Name of the tenant
    """
    name = cap_data.get("name")
    label = cap_data.get("label", "")
    description = cap_data.get("description", "")
    business_context = cap_data.get("business_context", [])
    business_processes = cap_data.get("business_processes", [])
    outcome = cap_data.get("outcome", "")
    business_intent = cap_data.get("business_intent", [])

    emb_input_parts = [
        label or "",
        description or "",
        outcome or "",
        " ".join(json.dumps(business_context)),
        " ".join(json.dumps(business_processes)),
        " ".join(json.dumps(business_intent)),
    ]
    emb_input = " ".join(part for part in emb_input_parts if part).strip()
    emb_vector = emb.encode(emb_input)

    capability = sess.execute(
        select(Capability).where(
            (Capability.name == name) &
            (Capability.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not capability:
        capability = Capability(
            name=name,
            tenant_name=tenant_name,
            label=label,
            description=description,
            business_context=business_context,
            business_processes=business_processes,
            outcome=outcome,
            business_intent=business_intent,
            emb=emb_vector
        )
        sess.add(capability)
        logger.info(f"Inserted new capability {capability.name} for tenant {tenant_name}")
    else:
        capability.label = label
        capability.description = description
        capability.business_context = business_context
        capability.business_processes = business_processes
        capability.outcome = outcome
        capability.business_intent = business_intent
        capability.emb = emb_vector
        logger.info(f"Updated existing capability {capability.name} for tenant {tenant_name}")

def insert_domain_capability(sess, domain_name, capability_name, tenant_name: str):
    """Create a domain↔capability relationship for a specific tenant.
    
    Args:
        sess: Database session
        domain_name: Name of the domain
        capability_name: Name of the capability
        tenant_name: Name of the tenant
    """
    dom_cap = sess.execute(
        select(DomainCapability).where(
            (DomainCapability.capability_name == capability_name) &
            (DomainCapability.domain_name == domain_name) &
            (DomainCapability.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not dom_cap:
        dom_cap = DomainCapability(
            domain_name=domain_name,
            capability_name=capability_name,
            tenant_name=tenant_name
        )
        sess.add(dom_cap)
        logger.info(f"Inserted new domain and capability relation for tenant {tenant_name}, domain_name={domain_name} and cap_name={capability_name}")
    else:
        logger.info(f"Domain and capability relation already exists for tenant {tenant_name}, domain_name={domain_name} and cap_name={capability_name}")


def insert_capability_operation(sess, capability_name, operation_name):
    """Create a capability↔operation mapping only if the corresponding Skill exists.

    Historically, this table stored capability→operation names without a dedicated
    skills table. Now that `capability_skill.skill_name` has an FK to `skills.name`,
    we must ensure a Skill row exists first to avoid FK violations.
    """
    # Ensure the referenced Skill row exists; otherwise skip creating the relation
    skill = sess.execute(
        select(Skill).where(Skill.name == operation_name)
    ).scalar_one_or_none()
    if not skill:
        logger.warning(
            "Skipping capability/operation relation because Skill does not exist: "
            "capability_name=%s, operation_name=%s",
            capability_name,
            operation_name,
        )
        return

    cap_op = sess.execute(
        select(CapabilitySkill).where(
            (CapabilitySkill.capability_name == capability_name) &
            (CapabilitySkill.skill_name == operation_name)
        )
    ).scalar_one_or_none()
    if not cap_op:
        cap_op = CapabilitySkill(
            skill_name=operation_name,
            capability_name=capability_name,
        )
        sess.add(cap_op)
        logger.info(
            "Inserted new capability and operation relation, op_name=%s and cap_name=%s",
            operation_name,
            capability_name,
        )
    else:
        logger.info(
            "Capability and operation relation already exists, op_name=%s and cap_name=%s",
            operation_name,
            capability_name,
        )


def upsert_canonical_skill(sess, skill_data, tenant_name: str):
    """Upsert a canonical skill record for a specific tenant.
    
    Args:
        sess: Database session
        skill_data: Dictionary containing skill attributes:
            - name (required): Unique skill identifier
            - label (required): Display name
            - skill_kind: Type of skill (e.g., 'core')
            - intent: Skill intent (e.g., 'get_details')
            - entity: List of entities (e.g., ['campaigns'])
            - criticality: Criticality level (e.g., 'core')
            - description: Detailed description
        tenant_name: Name of the tenant
    """
    name = skill_data.get("name")
    label = skill_data.get("label", "")
    skill_kind = skill_data.get("skill_kind", "")
    intent = skill_data.get("intent", "")
    entity = skill_data.get("entity", [])
    criticality = skill_data.get("criticality", "")
    description = skill_data.get("description", "")

    canonical_skill = sess.execute(
        select(CanonicalSkill).where(
            (CanonicalSkill.name == name) &
            (CanonicalSkill.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not canonical_skill:
        canonical_skill = CanonicalSkill(
            name=name,
            tenant_name=tenant_name,
            label=label,
            skill_kind=skill_kind,
            intent=intent,
            entity=entity,
            criticality=criticality,
            description=description
        )
        sess.add(canonical_skill)
        logger.info(f"Inserted new canonical skill {canonical_skill.name} for tenant {tenant_name}")
    else:
        canonical_skill.label = label
        canonical_skill.skill_kind = skill_kind
        canonical_skill.intent = intent
        canonical_skill.entity = entity
        canonical_skill.criticality = criticality
        canonical_skill.description = description
        logger.info(f"Updated existing canonical skill {canonical_skill.name} for tenant {tenant_name}")


def insert_capability_canonical_skill(sess, capability_name, canonical_skill_name, tenant_name: str):
    """Create a capability↔canonical_skill relationship for a specific tenant.
    
    Args:
        sess: Database session
        capability_name: Name of the capability
        canonical_skill_name: Name of the canonical skill
        tenant_name: Name of the tenant
    """
    cap_skill = sess.execute(
        select(CapabilityCanonicalSkill).where(
            (CapabilityCanonicalSkill.capability_name == capability_name) &
            (CapabilityCanonicalSkill.canonical_skill_name == canonical_skill_name) &
            (CapabilityCanonicalSkill.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not cap_skill:
        cap_skill = CapabilityCanonicalSkill(
            capability_name=capability_name,
            canonical_skill_name=canonical_skill_name,
            tenant_name=tenant_name
        )
        sess.add(cap_skill)
        logger.info(
            f"Inserted new capability and canonical skill relation for tenant {tenant_name}, "
            f"capability_name={capability_name} and canonical_skill_name={canonical_skill_name}"
        )
    else:
        logger.info(
            f"Capability and canonical skill relation already exists for tenant {tenant_name}, "
            f"capability_name={capability_name} and canonical_skill_name={canonical_skill_name}"
        )


def upsert_workflow(sess, workflow_data, tenant_name: str):
    """Upsert a workflow record for a specific tenant.
    
    Args:
        sess: Database session
        workflow_data: Dictionary containing workflow attributes:
            - name (required): Unique workflow identifier
            - label (required): Display name
            - description: Detailed description
            - value_metrics: List of value metrics
        tenant_name: Name of the tenant
    """
    name = workflow_data.get("name")
    label = workflow_data.get("label", "")
    description = workflow_data.get("description", "")
    value_metrics = workflow_data.get("value_metrics", [])

    workflow = sess.execute(
        select(Workflow).where(
            (Workflow.name == name) &
            (Workflow.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not workflow:
        workflow = Workflow(
            name=name,
            tenant_name=tenant_name,
            label=label,
            description=description,
            value_metrics=value_metrics
        )
        sess.add(workflow)
        logger.info(f"Inserted new workflow {workflow.name} for tenant {tenant_name}")
    else:
        workflow.label = label
        workflow.description = description
        workflow.value_metrics = value_metrics
        logger.info(f"Updated existing workflow {workflow.name} for tenant {tenant_name}")


def upsert_workflow_step(sess, workflow_step_data, tenant_name: str):
    """Upsert a workflow step record for a specific tenant.
    
    Args:
        sess: Database session
        workflow_step_data: Dictionary containing workflow step attributes:
            - name (required): Unique workflow step identifier
            - label (required): Display name
            - step_order (required): Order of the step in the workflow
            - intent: Intent of the step
            - description: Detailed description
            - workflow_name (required): Name of the parent workflow
        tenant_name: Name of the tenant
    """
    name = workflow_step_data.get("name")
    label = workflow_step_data.get("label", "")
    step_order = workflow_step_data.get("order", 0)
    intent = workflow_step_data.get("intent", "")
    description = workflow_step_data.get("description", "")
    workflow_name = workflow_step_data.get("workflow_name")

    workflow_step = sess.execute(
        select(WorkflowStep).where(
            (WorkflowStep.name == name) &
            (WorkflowStep.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not workflow_step:
        workflow_step = WorkflowStep(
            name=name,
            tenant_name=tenant_name,
            label=label,
            step_order=step_order,
            intent=intent,
            description=description,
            workflow_name=workflow_name
        )
        sess.add(workflow_step)
        logger.info(f"Inserted new workflow step {workflow_step.name} for tenant {tenant_name}")
    else:
        workflow_step.label = label
        workflow_step.step_order = step_order
        workflow_step.intent = intent
        workflow_step.description = description
        workflow_step.workflow_name = workflow_name
        logger.info(f"Updated existing workflow step {workflow_step.name} for tenant {tenant_name}")


def insert_workflow_step_domain(sess, workflow_step_name, domain_name, tenant_name: str):
    """Create a workflow_step↔domain relationship for a specific tenant.
    
    Args:
        sess: Database session
        workflow_step_name: Name of the workflow step
        domain_name: Name of the domain
        tenant_name: Name of the tenant
    """
    ws_domain = sess.execute(
        select(WorkflowStepDomain).where(
            (WorkflowStepDomain.workflow_step_name == workflow_step_name) &
            (WorkflowStepDomain.domain_name == domain_name) &
            (WorkflowStepDomain.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not ws_domain:
        ws_domain = WorkflowStepDomain(
            workflow_step_name=workflow_step_name,
            domain_name=domain_name,
            tenant_name=tenant_name
        )
        sess.add(ws_domain)
        logger.info(
            f"Inserted new workflow step and domain relation for tenant {tenant_name}, "
            f"workflow_step_name={workflow_step_name} and domain_name={domain_name}"
        )
    else:
        logger.info(
            f"Workflow step and domain relation already exists for tenant {tenant_name}, "
            f"workflow_step_name={workflow_step_name} and domain_name={domain_name}"
        )


def insert_workflow_step_capability(sess, workflow_step_name, capability_name, tenant_name: str):
    """Create a workflow_step↔capability relationship for a specific tenant.
    
    Args:
        sess: Database session
        workflow_step_name: Name of the workflow step
        capability_name: Name of the capability
        tenant_name: Name of the tenant
    """
    ws_capability = sess.execute(
        select(WorkflowStepCapability).where(
            (WorkflowStepCapability.workflow_step_name == workflow_step_name) &
            (WorkflowStepCapability.capability_name == capability_name) &
            (WorkflowStepCapability.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    if not ws_capability:
        ws_capability = WorkflowStepCapability(
            workflow_step_name=workflow_step_name,
            capability_name=capability_name,
            tenant_name=tenant_name
        )
        sess.add(ws_capability)
        logger.info(
            f"Inserted new workflow step and capability relation for tenant {tenant_name}, "
            f"workflow_step_name={workflow_step_name} and capability_name={capability_name}"
        )
    else:
        logger.info(
            f"Workflow step and capability relation already exists for tenant {tenant_name}, "
            f"workflow_step_name={workflow_step_name} and capability_name={capability_name}"
        )


def get_all_workflow_steps_grouped_by_workflow(sess, tenant_name: str) -> Dict[str, List[Dict[str, Any]]]:
    """Get all workflow steps grouped by workflows and ordered by step_order for a specific tenant.
    
    Returns a dictionary where keys are workflow names and values are lists of 
    workflow steps ordered by their step_order attribute (from small to large).
    
    Args:
        sess: Database session
        tenant_name: Name of the tenant to filter by
        
    Returns:
        Dict[str, List[Dict[str, Any]]]: Dictionary with workflow names as keys and 
        lists of workflow step dictionaries as values. Each workflow step dict contains:
            - id: UUID of the workflow step
            - name: Unique workflow step identifier
            - label: Display name
            - step_order: Order of the step in the workflow
            - intent: Intent of the step
            - description: Detailed description
            - workflow_name: Name of the parent workflow
            - created_at: Creation timestamp
    
    Example:
        {
            "campaign_management_workflow": [
                {
                    "id": "uuid-1",
                    "name": "step_1",
                    "label": "Create Campaign",
                    "step_order": "1",
                    "intent": "create",
                    "description": "...",
                    "workflow_name": "campaign_management_workflow",
                    "created_at": "..."
                },
                {
                    "id": "uuid-2",
                    "name": "step_2",
                    "label": "Configure Campaign",
                    "step_order": "2",
                    ...
                }
            ],
            "another_workflow": [...]
        }
    """
    # Query all workflow steps joined with workflows, filtered by tenant, ordered by workflow_name and step_order
    workflow_steps = sess.execute(
        select(WorkflowStep)
        .join(Workflow, (WorkflowStep.workflow_name == Workflow.name) & (WorkflowStep.tenant_name == Workflow.tenant_name))
        .where(WorkflowStep.tenant_name == tenant_name)
        .order_by(WorkflowStep.workflow_name, WorkflowStep.step_order)
    ).scalars().all()
    
    # Group workflow steps by workflow name
    grouped_steps = {}
    for step in workflow_steps:
        workflow_name = step.workflow_name
        if workflow_name not in grouped_steps:
            grouped_steps[workflow_name] = []
        
        grouped_steps[workflow_name].append({
            "id": str(step.id),
            "name": step.name,
            "label": step.label,
            "step_order": step.step_order,
            "intent": step.intent,
            "description": step.description,
            "workflow_name": step.workflow_name,
            "created_at": step.created_at,
        })
    
    return grouped_steps


def get_domains_by_workflow_step(sess, workflow_step_name: str, tenant_name: str) -> List[str]:
    """Get all domain names associated with a workflow step for a specific tenant.
    
    Args:
        sess: Database session
        workflow_step_name: Name of the workflow step
        tenant_name: Name of the tenant
        
    Returns:
        List[str]: List of domain names associated with the workflow step
    """
    domains = sess.execute(
        select(WorkflowStepDomain.domain_name)
        .where(
            (WorkflowStepDomain.workflow_step_name == workflow_step_name) &
            (WorkflowStepDomain.tenant_name == tenant_name)
        )
    ).scalars().all()
    
    return list(domains)


def get_capabilities_by_workflow_step(sess, workflow_step_name: str, tenant_name: str) -> List[str]:
    """Get all capability names associated with a workflow step for a specific tenant.
    
    Args:
        sess: Database session
        workflow_step_name: Name of the workflow step
        tenant_name: Name of the tenant
        
    Returns:
        List[str]: List of capability names associated with the workflow step
    """
    capabilities = sess.execute(
        select(WorkflowStepCapability.capability_name)
        .where(
            (WorkflowStepCapability.workflow_step_name == workflow_step_name) &
            (WorkflowStepCapability.tenant_name == tenant_name)
        )
    ).scalars().all()
    
    return list(capabilities)


def get_avg_vector(emb, ins_outs):
    """
    Given an embedding model and a list of input/output elements,
    encode each element and return the average vector.
    Each element should have 'name' and 'description' attributes or keys.
    """
    # Support both list of objects and list of dicts
    texts = []
    for element in ins_outs:
        if hasattr(element, "name"):
            texts.append(f"{element.name}")
        elif isinstance(element, dict) and "name" in element :
            texts.append(f"{element['name']}")
        elif isinstance(element, str):
            texts.append(element)
        else:
            continue
    if not texts:
        return None
    vs = np.array(emb.encode(texts), float)
    avg_vec = np.mean(vs, axis=0)
    return avg_vec.tolist()


def get_domains_with_tool_count(sess, tenant_name: str, agent_id: str = None) -> List[Dict[str, Any]]:
    """Get domain names and total count of tools in each domain for a specific tenant.
    
    This function retrieves domains for a tenant and counts the total number of tools associated
    with each domain through the following relationship chain:
    - Domain -> Capability (via domain_capability)
    - Capability -> Tool (via capability_tool)
    - Capability -> Skill (via capability_skill)
    - Skill -> Tool (via tool_skills)
    
    Domains with no tools will have a tool_count of 0.
    
    If agent_id is provided, only domains associated with the agent are returned
    (through role_agent -> role_domain relationships).
    
    Args:
        sess: Database session
        tenant_name: Name of the tenant to filter by
        agent_id: Optional agent ID to filter domains by agent association
        
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing:
            - name: Name of the domain
            - label: Label of the domain
            - description: Description of the domain
            - tool_count: Total count of unique tools in the domain (0 if no tools)
        Sorted by tool_count in descending order (largest to smallest)
    
    Example:
        [
            {"name": "marketing", "label": "Marketing", "description": "Marketing domain", "tool_count": 25},
            {"name": "sales", "label": "Sales", "description": "Sales domain", "tool_count": 18},
            {"name": "finance", "label": "Finance", "description": "Finance domain", "tool_count": 0}
        ]
    """
    from integrator.iam.iam_db_model import RoleAgent, RoleDomain
    from integrator.tools.tool_db_model import CapabilityTool, CapabilitySkill, ToolSkill
    from sqlalchemy import func, distinct, union, outerjoin
    
    # Build the base query for tools through capabilities
    # Path 1: Domain -> Capability -> Tool (direct)
    tools_via_capability = (
        select(
            DomainCapability.domain_name,
            CapabilityTool.tool_id
        )
        .join(CapabilityTool, DomainCapability.capability_name == CapabilityTool.capability_name)
        .where(DomainCapability.tenant_name == tenant_name)
    )
    
    # Path 2: Domain -> Capability -> Skill -> Tool
    tools_via_skill = (
        select(
            DomainCapability.domain_name,
            ToolSkill.tool_id
        )
        .join(CapabilitySkill, DomainCapability.capability_name == CapabilitySkill.capability_name)
        .join(ToolSkill, CapabilitySkill.skill_name == ToolSkill.skill_name)
        .where(DomainCapability.tenant_name == tenant_name)
    )
    
    # Combine both paths using UNION to get all unique domain-tool pairs
    combined_tools = union(tools_via_capability, tools_via_skill).subquery()
    
    # If agent_id is provided, start with agent's domains
    if agent_id:
        # Get domains associated with the agent through roles
        base_domains = (
            select(
                Domain.name.label('name'),
                Domain.label.label('label'),
                Domain.description.label('description')
            )
            .join(RoleDomain, Domain.name == RoleDomain.domain_name)
            .join(RoleAgent, RoleDomain.role_name == RoleAgent.role_name)
            .where(
                (RoleAgent.agent_id == agent_id) &
                (Domain.tenant_name == tenant_name)
            )
        ).subquery()
    else:
        # Get all domains for the tenant
        base_domains = (
            select(
                Domain.name.label('name'),
                Domain.label.label('label'),
                Domain.description.label('description')
            )
            .where(Domain.tenant_name == tenant_name)
        ).subquery()
    
    # Left join domains with tool counts to include domains with 0 tools
    query = (
        select(
            base_domains.c.name,
            base_domains.c.label,
            base_domains.c.description,
            func.coalesce(func.count(distinct(combined_tools.c.tool_id)), 0).label('tool_count')
        )
        .outerjoin(combined_tools, base_domains.c.name == combined_tools.c.domain_name)
        .group_by(base_domains.c.name, base_domains.c.label, base_domains.c.description)
        .order_by(func.coalesce(func.count(distinct(combined_tools.c.tool_id)), 0).desc())
    )
    
    results = sess.execute(query).all()
    
    return [
        {
            "name": row.name,
            "label": row.label,
            "description": row.description,
            "tool_count": row.tool_count
        }
        for row in results
    ]


def get_capabilities_with_tool_and_skill_count(sess, domain_name: str, tenant_name: str) -> List[Dict[str, Any]]:
    """Get all capabilities for a domain and tenant with their tool and skill counts.
    
    This function retrieves all capabilities associated with a domain and tenant, and counts:
    - Total number of unique tools (via capability_tool and capability_skill -> tool_skills)
    - Total number of unique skills (via capability_skill)
    
    Args:
        sess: Database session
        domain_name: Name of the domain to get capabilities for
        tenant_name: Name of the tenant to filter by
        
    Returns:
        List[Dict[str, Any]]: List of dictionaries containing:
            - name: Name of the capability
            - label: Label of the capability
            - description: Description of the capability
            - tool_count: Total count of unique tools for the capability
            - skill_count: Total count of unique skills for the capability
        Sorted by tool_count in descending order (largest to smallest)
    
    Example:
        [
            {"name": "campaign_management", "label": "Campaign Management", "description": "...", "tool_count": 15, "skill_count": 8},
            {"name": "analytics", "label": "Analytics", "description": "...", "tool_count": 10, "skill_count": 5},
            {"name": "reporting", "label": "Reporting", "description": "...", "tool_count": 3, "skill_count": 2}
        ]
    """
    from integrator.tools.tool_db_model import CapabilityTool, CapabilitySkill, ToolSkill
    from sqlalchemy import func, distinct, union, outerjoin
    
    # Get all capabilities for the domain and tenant with name, label, description
    base_capabilities = (
        select(
            Capability.name.label('name'),
            Capability.label.label('label'),
            Capability.description.label('description')
        )
        .join(DomainCapability, Capability.name == DomainCapability.capability_name)
        .where(
            (DomainCapability.domain_name == domain_name) &
            (DomainCapability.tenant_name == tenant_name) &
            (Capability.tenant_name == tenant_name)
        )
    ).subquery()
    
    # Path 1: Capability -> Tool (direct via capability_tool)
    tools_via_capability = (
        select(
            CapabilityTool.capability_name,
            CapabilityTool.tool_id
        )
    )
    
    # Path 2: Capability -> Skill -> Tool (via capability_skill and tool_skills)
    tools_via_skill = (
        select(
            CapabilitySkill.capability_name,
            ToolSkill.tool_id
        )
        .join(ToolSkill, CapabilitySkill.skill_name == ToolSkill.skill_name)
    )
    
    # Combine both tool paths
    combined_tools = union(tools_via_capability, tools_via_skill).subquery()
    
    # Count tools per capability
    tool_counts = (
        select(
            combined_tools.c.capability_name,
            func.count(distinct(combined_tools.c.tool_id)).label('tool_count')
        )
        .group_by(combined_tools.c.capability_name)
    ).subquery()
    
    # Count skills per capability
    skill_counts = (
        select(
            CapabilitySkill.capability_name,
            func.count(distinct(CapabilitySkill.skill_name)).label('skill_count')
        )
        .group_by(CapabilitySkill.capability_name)
    ).subquery()
    
    # Join capabilities with tool and skill counts
    query = (
        select(
            base_capabilities.c.name,
            base_capabilities.c.label,
            base_capabilities.c.description,
            func.coalesce(tool_counts.c.tool_count, 0).label('tool_count'),
            func.coalesce(skill_counts.c.skill_count, 0).label('skill_count')
        )
        .outerjoin(tool_counts, base_capabilities.c.name == tool_counts.c.capability_name)
        .outerjoin(skill_counts, base_capabilities.c.name == skill_counts.c.capability_name)
        .order_by(func.coalesce(tool_counts.c.tool_count, 0).desc())
    )
    
    results = sess.execute(query).all()
    
    return [
        {
            "name": row.name,
            "label": row.label,
            "description": row.description,
            "tool_count": row.tool_count,
            "skill_count": row.skill_count
        }
        for row in results
    ]


def get_workflows_with_tool_count(sess, tenant_name: str) -> Dict[str, Any]:
    """Get all workflows with tool counts and their workflow steps with tool counts for a specific tenant.
    
    This function retrieves workflows for a tenant and for each workflow:
    - Counts total unique MCP tools from the mcp_tools table
    - Lists all workflow steps with their individual tool counts
    
    The relationship chain used:
    - Workflow -> WorkflowStep (via workflow_name FK)
    - WorkflowStep -> Domain (via workflow_step_domain)
    - Domain -> Capability (via domain_capability)
    - Capability -> Tool (via capability_tool and capability_skill -> tool_skills)
    - Tool IDs are then used to count actual MCP tools in mcp_tools table
    
    Additionally uses:
    - WorkflowStep -> Capability (via workflow_step_capability) for direct capability associations
    
    Args:
        sess: Database session
        tenant_name: Name of the tenant to filter by
        
    Returns:
        Dict[str, Any]: Dictionary containing:
            - total_mcp_tool_count: Total count of all MCP tools in the mcp_tools table
            - workflows: List of workflow dictionaries, each containing:
                - id: UUID of the workflow
                - name: Name of the workflow
                - label: Label of the workflow
                - description: Description of the workflow
                - tool_count: Total count of unique tools for this workflow
                - workflow_steps: List of workflow steps with tool counts and domains
        
    Example:
        {
            "total_mcp_tool_count": 52,
            "workflows": [
                {
                    "id": "uuid-1",
                    "name": "campaign_management_workflow",
                    "label": "Campaign Management Workflow",
                    "description": "...",
                    "tool_count": 25,
                    "workflow_steps": [...]
                }
            ]
        }
    """
    from integrator.tools.tool_db_model import CapabilityTool, CapabilitySkill, ToolSkill, McpTool
    from sqlalchemy import func, distinct, union
    
    # Get total count of MCP tools in the mcp_tools table
    total_mcp_tool_count = sess.execute(
        select(func.count(distinct(McpTool.id)))
    ).scalar() or 0
    
    # Get all workflows for the tenant
    workflows = sess.execute(
        select(Workflow)
        .where(Workflow.tenant_name == tenant_name)
        .order_by(Workflow.name)
    ).scalars().all()
    
    workflows_list = []
    
    for workflow in workflows:
        # Get all workflow steps for this workflow
        workflow_steps = sess.execute(
            select(WorkflowStep)
            .where(WorkflowStep.workflow_name == workflow.name)
            .order_by(WorkflowStep.step_order)
        ).scalars().all()
        
        workflow_steps_data = []
        all_workflow_tools = set()
        
        for step in workflow_steps:
            # Get domains associated with this workflow step
            step_domains = sess.execute(
                select(WorkflowStepDomain.domain_name)
                .where(WorkflowStepDomain.workflow_step_name == step.name)
            ).scalars().all()
            
            # For each domain, get tool count
            domains_with_tools = []
            for domain_name in step_domains:
                # Path A1: Domain -> Capability -> Tool (direct via capability_tool)
                tools_via_domain_capability = (
                    select(CapabilityTool.tool_id)
                    .join(DomainCapability, CapabilityTool.capability_name == DomainCapability.capability_name)
                    .where(DomainCapability.domain_name == domain_name)
                )
                
                # Path A2: Domain -> Capability -> Skill -> Tool
                tools_via_domain_skill = (
                    select(ToolSkill.tool_id)
                    .join(CapabilitySkill, ToolSkill.skill_name == CapabilitySkill.skill_name)
                    .join(DomainCapability, CapabilitySkill.capability_name == DomainCapability.capability_name)
                    .where(DomainCapability.domain_name == domain_name)
                )
                
                # Combine both paths for this domain
                domain_tools = union(tools_via_domain_capability, tools_via_domain_skill).subquery()
                
                # Count unique tools for this domain
                domain_tool_count = sess.execute(
                    select(func.count(distinct(domain_tools.c.tool_id)))
                ).scalar()
                
                # Get domain label
                domain = sess.execute(
                    select(Domain).where(Domain.name == domain_name)
                ).scalar_one_or_none()
                
                domains_with_tools.append({
                    "name": domain_name,
                    "label": domain.label if domain else domain_name,
                    "tool_count": domain_tool_count or 0
                })
            
            # Get tools for this workflow step through all paths
            # Path A1: WorkflowStep -> Domain -> Capability -> Tool (direct via capability_tool)
            tools_via_domain_capability = (
                select(CapabilityTool.tool_id)
                .join(DomainCapability, CapabilityTool.capability_name == DomainCapability.capability_name)
                .join(WorkflowStepDomain, DomainCapability.domain_name == WorkflowStepDomain.domain_name)
                .where(WorkflowStepDomain.workflow_step_name == step.name)
            )
            
            # Path A2: WorkflowStep -> Domain -> Capability -> Skill -> Tool
            tools_via_domain_skill = (
                select(ToolSkill.tool_id)
                .join(CapabilitySkill, ToolSkill.skill_name == CapabilitySkill.skill_name)
                .join(DomainCapability, CapabilitySkill.capability_name == DomainCapability.capability_name)
                .join(WorkflowStepDomain, DomainCapability.domain_name == WorkflowStepDomain.domain_name)
                .where(WorkflowStepDomain.workflow_step_name == step.name)
            )
            
            # Path B1: WorkflowStep -> Capability -> Tool (direct via capability_tool)
            tools_via_step_capability = (
                select(CapabilityTool.tool_id)
                .join(WorkflowStepCapability, CapabilityTool.capability_name == WorkflowStepCapability.capability_name)
                .where(WorkflowStepCapability.workflow_step_name == step.name)
            )
            
            # Path B2: WorkflowStep -> Capability -> Skill -> Tool
            tools_via_step_skill = (
                select(ToolSkill.tool_id)
                .join(CapabilitySkill, ToolSkill.skill_name == CapabilitySkill.skill_name)
                .join(WorkflowStepCapability, CapabilitySkill.capability_name == WorkflowStepCapability.capability_name)
                .where(WorkflowStepCapability.workflow_step_name == step.name)
            )
            
            # Combine all paths using UNION to get unique tool IDs
            combined_tools = union(
                tools_via_domain_capability,
                tools_via_domain_skill,
                tools_via_step_capability,
                tools_via_step_skill
            ).subquery()
            
            # Count unique tools for this workflow step
            tool_count_result = sess.execute(
                select(func.count(distinct(combined_tools.c.tool_id)))
            ).scalar()
            
            # Get the actual tool IDs to add to the workflow's total
            step_tool_ids = sess.execute(
                select(distinct(combined_tools.c.tool_id))
            ).scalars().all()
            
            all_workflow_tools.update(step_tool_ids)
            
            workflow_steps_data.append({
                "id": str(step.id),
                "name": step.name,
                "label": step.label,
                "step_order": step.step_order,
                "intent": step.intent,
                "description": step.description,
                "tool_count": tool_count_result or 0,
                "domains": domains_with_tools
            })
        
        workflows_list.append({
            "id": str(workflow.id),
            "name": workflow.name,
            "label": workflow.label,
            "description": workflow.description,
            "tool_count": len(all_workflow_tools),
            "workflow_steps": workflow_steps_data
        })
    
    return {
        "total_mcp_tool_count": total_mcp_tool_count,
        "workflows": workflows_list
    }
