"""CRUD helpers for creating Domain, Capability, and Tool nodes in Neo4j with tenant isolation.

These helpers are intended to be used by higher-level services that keep the
relational (PostgreSQL) models in sync with the Neo4j knowledge graph.

They rely on the shared Neo4j driver from ``integrator.utils.graph`` so that
connection management is centralized.

This version includes tenant isolation - all nodes include tenant_name property
and all queries filter by tenant_name to ensure complete data isolation.
"""

from __future__ import annotations

from typing import Any, Mapping, Union

from integrator.domains.domain_db_model import Domain, Capability
from integrator.utils.logger import get_logger

from integrator.domains.domain_db_crud import (
    get_all_workflow_steps_grouped_by_workflow,
    get_domains_by_workflow_step,
    get_capabilities_by_workflow_step,
    get_capabilities_by_domain
)
from sqlalchemy import select
from integrator.domains.domain_db_model import Workflow

logger = get_logger(__name__)

DomainLike = Union[Domain, Mapping[str, Any]]
CapabilityLike = Union[Capability, Mapping[str, Any]]


def _extract_domain_props(domain: DomainLike) -> dict:
    """Normalize a Domain ORM instance or dict into Neo4j properties.

    The resulting dict will contain the keys expected on the Domain node:
    - name
    - tenant_name
    - label
    - description
    - scope
    - domain_entities
    - domain_purpose
    """

    if isinstance(domain, Domain):
        # ORM object
        name = domain.name
        tenant_name = domain.tenant_name
        label = domain.label
        description = domain.description or ""
        scope = domain.scope or ""
        domain_entities = domain.domain_entities or []
        # In the relational model the column is ``domain_purposes``.
        domain_purpose = getattr(domain, "domain_purposes", "") or ""
    else:
        # Mapping / dict
        name = domain["name"]
        tenant_name = domain.get("tenant_name", "default")
        label = domain.get("label", "")
        description = domain.get("description", "")
        scope = domain.get("scope", "")
        domain_entities = domain.get("domain_entities", [])
        domain_purpose = (
            domain.get("domain_purpose")
            or domain.get("domain_purposes", "")
            or ""
        )

    return {
        "name": name,
        "tenant_name": tenant_name,
        "label": label,
        "description": description,
        "scope": scope,
        "domain_entities": domain_entities,
        "domain_purpose": domain_purpose,
    }


def _extract_capability_props(capability: CapabilityLike) -> dict:
    """Normalize a Capability ORM instance or dict into Neo4j properties.

    The resulting dict will contain the keys expected on the Capability node:
    - name
    - tenant_name
    - label
    - description
    - business_context
    - business_processes
    - outcome
    - business_intent
    """

    if isinstance(capability, Capability):
        name = capability.name
        tenant_name = capability.tenant_name
        label = capability.label
        description = capability.description or ""
        business_context = capability.business_context or []
        business_processes = capability.business_processes or []
        outcome = capability.outcome or ""
        business_intent = capability.business_intent or []
    else:
        name = capability["name"]
        tenant_name = capability.get("tenant_name", "default")
        label = capability.get("label", "")
        description = capability.get("description", "")
        business_context = capability.get("business_context", [])
        business_processes = capability.get("business_processes", [])
        outcome = capability.get("outcome", "")
        business_intent = capability.get("business_intent", [])

    return {
        "name": name,
        "tenant_name": tenant_name,
        "label": label,
        "description": description,
        "business_context": business_context,
        "business_processes": business_processes,
        "outcome": outcome,
        "business_intent": business_intent,
    }


def create_domain_node(gsess, domain: DomainLike) -> None:
    """Create or update a Domain node in Neo4j with tenant isolation.

    Uses the ``name`` and ``tenant_name`` as the composite identifier of the node.

    Node label: ``Domain``
    Properties: name, tenant_name, label, description, scope, domain_entities, domain_purpose
    """

    props = _extract_domain_props(domain)

    cypher = """
    MERGE (d:Domain {name: $name, tenant_name: $tenant_name})
    SET d.label = $label,
        d.description = $description,
        d.scope = $scope,
        d.domain_entities = $domain_entities,
        d.domain_purpose = $domain_purpose
    """

    gsess.run(cypher, **props)

    logger.info("Upserted Domain node in Neo4j: %s (tenant: %s)", props["name"], props["tenant_name"])


def create_capability_node(gsess, capability: CapabilityLike) -> None:
    """Create or update a Capability node in Neo4j with tenant isolation.

    Uses the ``name`` and ``tenant_name`` as the composite identifier of the node.

    Node label: ``Capability``
    Properties: name, tenant_name, label, description, business_context,
                business_processes, outcome, business_intent
    """

    props = _extract_capability_props(capability)

    cypher = """
    MERGE (c:Capability {name: $name, tenant_name: $tenant_name})
    SET c.label = $label,
        c.description = $description,
        c.business_context = $business_context,
        c.business_processes = $business_processes,
        c.outcome = $outcome,
        c.business_intent = $business_intent
    """

    gsess.run(cypher, **props)

    logger.info("Upserted Capability node in Neo4j: %s (tenant: %s)", props["name"], props["tenant_name"])


def create_domain_capability_edge(gsess, domain_name: str, capability_name: str, tenant_name: str) -> None:
    """Create or update the HAS_CAPABILITY edge between a Domain and a Capability within the same tenant.

    This assumes that the corresponding Domain and Capability nodes already
    exist (for example, created via ``create_domain_node`` and
    ``create_capability_node``).
    
    Both nodes must belong to the same tenant.
    """

    cypher = """
    MATCH (d:Domain {name: $domain_name, tenant_name: $tenant_name})
    MATCH (c:Capability {name: $capability_name, tenant_name: $tenant_name})
    MERGE (d)-[:HAS_CAPABILITY]->(c)
    """

    gsess.run(cypher, domain_name=domain_name, capability_name=capability_name, tenant_name=tenant_name)

    logger.info(
        "Upserted HAS_CAPABILITY edge in Neo4j: %s -> %s (tenant: %s)",
        domain_name,
        capability_name,
        tenant_name,
    )


def create_workflow_node(gsess, workflow: Mapping[str, Any]) -> None:
    """Create or update a Workflow node in Neo4j with tenant isolation.

    Uses the ``name`` and ``tenant_name`` as the composite identifier of the node.

    Node label: ``Workflow``
    Properties: name, tenant_name, label, description, value_metrics
    
    Args:
        gsess: Neo4j session
        workflow: Dictionary containing workflow attributes:
            - name (required): Unique workflow identifier
            - tenant_name (required): Tenant identifier
            - label: Display name
            - description: Detailed description
            - value_metrics: List of value metrics
    """
    name = workflow.get("name")
    tenant_name = workflow.get("tenant_name", "default")
    label = workflow.get("label", "")
    description = workflow.get("description", "")
    value_metrics = workflow.get("value_metrics", [])

    cypher = """
    MERGE (w:Workflow {name: $name, tenant_name: $tenant_name})
    SET w.label = $label,
        w.description = $description,
        w.value_metrics = $value_metrics
    """

    gsess.run(
        cypher,
        name=name,
        tenant_name=tenant_name,
        label=label,
        description=description,
        value_metrics=value_metrics,
    )

    logger.info("Upserted Workflow node in Neo4j: %s (tenant: %s)", name, tenant_name)


def create_workflow_step_node(gsess, workflow_step: Mapping[str, Any]) -> None:
    """Create or update a WorkflowStep node in Neo4j with tenant isolation.

    Uses the ``name`` and ``tenant_name`` as the composite identifier of the node.

    Node label: ``WorkflowStep``
    Properties: name, tenant_name, label, step_order, intent, description, workflow_name
    
    Args:
        gsess: Neo4j session
        workflow_step: Dictionary containing workflow step attributes:
            - name (required): Unique workflow step identifier
            - tenant_name (required): Tenant identifier
            - label: Display name
            - step_order: Order of the step in the workflow
            - intent: Intent of the step
            - description: Detailed description
            - workflow_name: Name of the parent workflow
    """
    name = workflow_step.get("name")
    tenant_name = workflow_step.get("tenant_name", "default")
    label = workflow_step.get("label", "")
    step_order = workflow_step.get("step_order", "")
    intent = workflow_step.get("intent", "")
    description = workflow_step.get("description", "")
    workflow_name = workflow_step.get("workflow_name")

    cypher = """
    MERGE (ws:WorkflowStep {name: $name, tenant_name: $tenant_name})
    SET ws.label = $label,
        ws.step_order = $step_order,
        ws.intent = $intent,
        ws.description = $description,
        ws.workflow_name = $workflow_name
    """

    gsess.run(
        cypher,
        name=name,
        tenant_name=tenant_name,
        label=label,
        step_order=step_order,
        intent=intent,
        description=description,
        workflow_name=workflow_name,
    )

    logger.info("Upserted WorkflowStep node in Neo4j: %s (tenant: %s)", name, tenant_name)


def create_workflow_has_step_edge(gsess, workflow_name: str, workflow_step_name: str, tenant_name: str) -> None:
    """Create or update the HAS_STEP edge between a Workflow and a WorkflowStep within the same tenant.

    This assumes that the corresponding Workflow and WorkflowStep nodes already
    exist (for example, created via ``create_workflow_node`` and
    ``create_workflow_step_node``).
    
    Both nodes must belong to the same tenant.
    
    Args:
        gsess: Neo4j session
        workflow_name: Name of the workflow
        workflow_step_name: Name of the workflow step
        tenant_name: Tenant identifier
    """
    cypher = """
    MATCH (w:Workflow {name: $workflow_name, tenant_name: $tenant_name})
    MATCH (ws:WorkflowStep {name: $workflow_step_name, tenant_name: $tenant_name})
    MERGE (w)-[:HAS_STEP]->(ws)
    """

    gsess.run(cypher, workflow_name=workflow_name, workflow_step_name=workflow_step_name, tenant_name=tenant_name)

    logger.info(
        "Upserted HAS_STEP edge in Neo4j: %s -> %s (tenant: %s)",
        workflow_name,
        workflow_step_name,
        tenant_name,
    )


def create_workflow_step_next_edge(gsess, from_step_name: str, to_step_name: str, workflow_name: str, tenant_name: str) -> None:
    """Create or update the NEXT_STEP edge between two WorkflowSteps in the same workflow and tenant.

    This edge represents the sequential order of steps within a workflow.
    
    Args:
        gsess: Neo4j session
        from_step_name: Name of the source workflow step
        to_step_name: Name of the target workflow step
        workflow_name: Name of the workflow (stored as edge property for context)
        tenant_name: Tenant identifier
    """
    cypher = """
    MATCH (ws1:WorkflowStep {name: $from_step_name, tenant_name: $tenant_name})
    MATCH (ws2:WorkflowStep {name: $to_step_name, tenant_name: $tenant_name})
    MERGE (ws1)-[r:NEXT_STEP]->(ws2)
    SET r.workflow_name = $workflow_name
    """

    gsess.run(
        cypher,
        from_step_name=from_step_name,
        to_step_name=to_step_name,
        workflow_name=workflow_name,
        tenant_name=tenant_name,
    )

    logger.info(
        "Upserted NEXT_STEP edge in Neo4j: %s -> %s (workflow: %s, tenant: %s)",
        from_step_name,
        to_step_name,
        workflow_name,
        tenant_name,
    )


def create_workflow_step_domain_edge(gsess, workflow_step_name: str, domain_name: str, tenant_name: str) -> None:
    """Create or update the USES_DOMAIN edge between a WorkflowStep and a Domain within the same tenant.

    This edge represents that a workflow step operates within or uses a specific domain.
    
    Args:
        gsess: Neo4j session
        workflow_step_name: Name of the workflow step
        domain_name: Name of the domain
        tenant_name: Tenant identifier
    """
    cypher = """
    MATCH (ws:WorkflowStep {name: $workflow_step_name, tenant_name: $tenant_name})
    MATCH (d:Domain {name: $domain_name, tenant_name: $tenant_name})
    MERGE (ws)-[:USES_DOMAIN]->(d)
    """

    gsess.run(cypher, workflow_step_name=workflow_step_name, domain_name=domain_name, tenant_name=tenant_name)

    logger.info(
        "Upserted USES_DOMAIN edge in Neo4j: %s -> %s (tenant: %s)",
        workflow_step_name,
        domain_name,
        tenant_name,
    )


def create_workflow_step_capability_edge(gsess, workflow_step_name: str, capability_name: str, tenant_name: str) -> None:
    """Create or update the USES_CAPABILITY edge between a WorkflowStep and a Capability within the same tenant.

    This edge represents that a workflow step utilizes a specific capability.
    
    Args:
        gsess: Neo4j session
        workflow_step_name: Name of the workflow step
        capability_name: Name of the capability
        tenant_name: Tenant identifier
    """
    cypher = """
    MATCH (ws:WorkflowStep {name: $workflow_step_name, tenant_name: $tenant_name})
    MATCH (c:Capability {name: $capability_name, tenant_name: $tenant_name})
    MERGE (ws)-[:USES_CAPABILITY]->(c)
    """

    gsess.run(cypher, workflow_step_name=workflow_step_name, capability_name=capability_name, tenant_name=tenant_name)

    logger.info(
        "Upserted USES_CAPABILITY edge in Neo4j: %s -> %s (tenant: %s)",
        workflow_step_name,
        capability_name,
        tenant_name,
    )


def cleanup_domain_graph(gsess, domain_name: str | None = None, tenant_name: str | None = None) -> None:
    """Delete Domain/Capability/Tool/Skill nodes and their edges from Neo4j with tenant isolation.

    This is a graph-only cleanup helper that does **not** modify the
    relational database.

    - If both ``domain_name`` and ``tenant_name`` are provided, only that specific Domain 
      and its connected nodes within that tenant are deleted.
    - If only ``tenant_name`` is provided, all domain-related nodes for that tenant are deleted.
    - If neither is provided, all domain-related nodes across all tenants are deleted.

    Parameters
    ----------
    gsess:
        An active Neo4j session (e.g. from ``get_graph_driver().session()``).
    domain_name:
        Optional logical name of the Domain whose subgraph should be removed.
    tenant_name:
        Optional tenant identifier to limit deletion to a specific tenant.
    """

    if domain_name is not None and tenant_name is not None:
        cypher = """
        MATCH (d:Domain {name: $domain_name, tenant_name: $tenant_name})
        OPTIONAL MATCH (d)-[:HAS_CAPABILITY]->(c:Capability {tenant_name: $tenant_name})
        OPTIONAL MATCH (c)-[:HAS_TOOL]->(t:Tool {tenant_name: $tenant_name})
        OPTIONAL MATCH (c)-[:HAS_SKILL]->(s:Skill {tenant_name: $tenant_name})
        DETACH DELETE d, c, t, s
        """
        gsess.run(cypher, domain_name=domain_name, tenant_name=tenant_name)
        logger.info(
            "Deleted Neo4j subgraph for domain %s in tenant %s",
            domain_name,
            tenant_name,
        )
    elif tenant_name is not None:
        cypher = """
        MATCH (n {tenant_name: $tenant_name})
        WHERE n:Domain OR n:Capability OR n:Tool OR n:Skill
        DETACH DELETE n
        """
        gsess.run(cypher, tenant_name=tenant_name)
        logger.info(
            "Deleted all Neo4j domain-related nodes for tenant %s",
            tenant_name,
        )
    else:
        cypher = """
        MATCH (n)
        WHERE n:Domain OR n:Capability OR n:Tool OR n:Skill
        DETACH DELETE n
        """
        gsess.run(cypher)
        logger.info(
            "Deleted entire Neo4j Domain/Capability/Tool/Skill subgraph (all tenants)",
        )


def cleanup_all_domains_graph(gsess, tenant_name: str | None = None) -> None:
    """Convenience helper to remove all domain-related nodes from Neo4j.

    If tenant_name is provided, only removes nodes for that tenant.
    Otherwise, removes all domain-related nodes across all tenants.
    """
    cleanup_domain_graph(gsess, domain_name=None, tenant_name=tenant_name)


def cleanup_workflow_graph(gsess, workflow_name: str | None = None, tenant_name: str | None = None) -> None:
    """Delete Workflow/WorkflowStep nodes and their edges from Neo4j with tenant isolation.

    This is a graph-only cleanup helper that does **not** modify the
    relational database.

    - If both ``workflow_name`` and ``tenant_name`` are provided, only that specific Workflow 
      and its connected nodes within that tenant are deleted.
    - If only ``tenant_name`` is provided, all workflow-related nodes for that tenant are deleted.
    - If neither is provided, all workflow-related nodes across all tenants are deleted.

    Parameters
    ----------
    gsess:
        An active Neo4j session (e.g. from ``get_graph_driver().session()``).
    workflow_name:
        Optional logical name of the Workflow whose subgraph should be removed.
    tenant_name:
        Optional tenant identifier to limit deletion to a specific tenant.
    """

    if workflow_name is not None and tenant_name is not None:
        cypher = """
        MATCH (w:Workflow {name: $workflow_name, tenant_name: $tenant_name})
        OPTIONAL MATCH (w)-[:HAS_STEP]->(ws:WorkflowStep {tenant_name: $tenant_name})
        DETACH DELETE w, ws
        """
        gsess.run(cypher, workflow_name=workflow_name, tenant_name=tenant_name)
        logger.info(
            "Deleted Neo4j subgraph for workflow %s in tenant %s",
            workflow_name,
            tenant_name,
        )
    elif tenant_name is not None:
        cypher = """
        MATCH (n {tenant_name: $tenant_name})
        WHERE n:Workflow OR n:WorkflowStep
        DETACH DELETE n
        """
        gsess.run(cypher, tenant_name=tenant_name)
        logger.info(
            "Deleted all Neo4j workflow-related nodes for tenant %s",
            tenant_name,
        )
    else:
        cypher = """
        MATCH (n)
        WHERE n:Workflow OR n:WorkflowStep
        DETACH DELETE n
        """
        gsess.run(cypher)
        logger.info(
            "Deleted entire Neo4j Workflow/WorkflowStep subgraph (all tenants)",
        )


def cleanup_all_workflow_graph(gsess, tenant_name: str | None = None) -> None:
    """Convenience helper to remove all workflow-related nodes from Neo4j.

    If tenant_name is provided, only removes nodes for that tenant.
    Otherwise, removes all workflow-related nodes across all tenants.
    """
    cleanup_workflow_graph(gsess, workflow_name=None, tenant_name=tenant_name)


def sync_domains_from_db_to_graph(sess, gsess, tenant_name: str = None) -> None:
    """Sync domains and capabilities from PostgreSQL to Neo4j with tenant isolation.
    
    If tenant_name is provided, only syncs data for that tenant.
    Otherwise, reads all tenants from the tenant table and syncs each one.
    
    Args:
        sess: PostgreSQL session
        gsess: Neo4j session
        tenant_name: Optional tenant identifier to limit sync to specific tenant
    """
    from integrator.iam.iam_db_model import Tenant
    
    if tenant_name:
        # Sync specific tenant only
        tenants_to_sync = [tenant_name]
        logger.info(f"Syncing domains for specific tenant: {tenant_name}")
    else:
        # Read all tenants from tenant table and sync each
        tenants_stmt = select(Tenant.name)
        tenant_results = sess.execute(tenants_stmt).scalars().all()
        tenants_to_sync = list(tenant_results)
        logger.info(f"Syncing domains for all tenants: {tenants_to_sync}")
    
    for current_tenant in tenants_to_sync:
        logger.info(f"Starting domain sync for tenant: {current_tenant}")
        
        stmt = select(Domain).where(Domain.tenant_name == current_tenant)
        domains = sess.execute(stmt).scalars().all()
        
        for domain in domains:
            create_domain_node(gsess, domain)
            capabilities = get_capabilities_by_domain(sess, domain.name, domain.tenant_name)
            for capability in capabilities:
                # Determine capability name whether we received a dict or ORM object
                if isinstance(capability, dict):
                    cap_name = capability["name"]
                else:
                    cap_name = capability.name

                create_capability_node(gsess, capability)
                create_domain_capability_edge(gsess, domain.name, cap_name, domain.tenant_name)
        
        logger.info(f"Completed domain sync for tenant: {current_tenant} ({len(domains)} domains)")
    
    if tenant_name:
        logger.info(f"Domains sync completed successfully for tenant: {tenant_name}")
    else:
        logger.info(f"Domains sync completed successfully for all {len(tenants_to_sync)} tenants")


def sync_workflows_from_db_to_graph(sess, gsess, tenant_name: str = None) -> None:
    """Sync all workflows and their steps from PostgreSQL to Neo4j with tenant isolation.
    
    If tenant_name is provided, only syncs data for that tenant.
    Otherwise, reads all tenants from the tenant table and syncs each one.
    
    This function:
    1. Retrieves all workflow steps grouped by workflow from the database
    2. Creates/updates Workflow nodes in Neo4j
    3. Creates/updates WorkflowStep nodes in Neo4j
    4. Creates HAS_STEP edges from Workflow to each WorkflowStep
    5. Creates NEXT_STEP edges between consecutive steps based on step_order
    
    Args:
        sess: PostgreSQL session
        gsess: Neo4j session for graph operations
        tenant_name: Optional tenant identifier to limit sync to specific tenant
    """
    from integrator.iam.iam_db_model import Tenant
    
    if tenant_name:
        # Sync specific tenant only
        tenants_to_sync = [tenant_name]
        logger.info(f"Syncing workflows for specific tenant: {tenant_name}")
    else:
        # Read all tenants from tenant table and sync each
        tenants_stmt = select(Tenant.name)
        tenant_results = sess.execute(tenants_stmt).scalars().all()
        tenants_to_sync = list(tenant_results)
        logger.info(f"Syncing workflows for all tenants: {tenants_to_sync}")
    
    total_workflows_synced = 0
    
    for current_tenant in tenants_to_sync:
        logger.info(f"Starting workflow sync for tenant: {current_tenant}")

        # Get all workflows from the database for this tenant
        stmt = select(Workflow).where(Workflow.tenant_name == current_tenant)
        workflows = sess.execute(stmt).scalars().all()

        # Get all workflow steps grouped by workflow for this tenant
        grouped_steps = get_all_workflow_steps_grouped_by_workflow(sess, current_tenant)

        logger.info(f"Found {len(workflows)} workflows and {len(grouped_steps)} workflow groups for tenant: {current_tenant}")

        # Process each workflow
        for workflow in workflows:
            workflow_name = workflow.name
            workflow_tenant = workflow.tenant_name

            # Create workflow node
            workflow_data = {
                "name": workflow.name,
                "tenant_name": workflow_tenant,
                "label": workflow.label,
                "description": workflow.description or "",
                "value_metrics": workflow.value_metrics or [],
            }
            create_workflow_node(gsess, workflow_data)

            # Get steps for this workflow
            steps = grouped_steps.get(workflow_name, [])

            if not steps:
                logger.warning(f"No steps found for workflow: {workflow_name}")
                continue

            logger.info(f"Processing {len(steps)} steps for workflow: {workflow_name}")

            # Sort steps by step_order to ensure correct ordering
            try:
                sorted_steps = sorted(steps, key=lambda x: float(x.get("step_order", 0)))
            except (ValueError, TypeError):
                # If conversion fails, sort as strings
                sorted_steps = sorted(steps, key=lambda x: str(x.get("step_order", "")))

            # Create workflow step nodes and HAS_STEP edges
            for step in sorted_steps:
                step_name = step["name"]
                step["tenant_name"] = workflow_tenant  # Ensure tenant_name is set

                # Create workflow step node
                create_workflow_step_node(gsess, step)

                # Create HAS_STEP edge from workflow to step
                create_workflow_has_step_edge(gsess, workflow_name, step_name, workflow_tenant)

                # Get and create domain relationships for this step
                domains = get_domains_by_workflow_step(sess, step_name, workflow_tenant)
                for domain_name in domains:
                    create_workflow_step_domain_edge(gsess, step_name, domain_name, workflow_tenant)
                    logger.info(f"Created USES_DOMAIN edge: {step_name} -> {domain_name} (tenant: {workflow_tenant})")

                # Get and create capability relationships for this step
                capabilities = get_capabilities_by_workflow_step(sess, step_name, workflow_tenant)
                for capability_name in capabilities:
                    create_workflow_step_capability_edge(gsess, step_name, capability_name, workflow_tenant)
                    logger.info(f"Created USES_CAPABILITY edge: {step_name} -> {capability_name} (tenant: {workflow_tenant})")

            # Create NEXT_STEP edges between consecutive steps
            for i in range(len(sorted_steps) - 1):
                current_step = sorted_steps[i]
                next_step = sorted_steps[i + 1]

                create_workflow_step_next_edge(
                    gsess,
                    from_step_name=current_step["name"],
                    to_step_name=next_step["name"],
                    workflow_name=workflow_name,
                    tenant_name=workflow_tenant,
                )

            logger.info(f"Successfully synced workflow: {workflow_name} with {len(sorted_steps)} steps (tenant: {workflow_tenant})")
        
        total_workflows_synced += len(workflows)
        logger.info(f"Completed workflow sync for tenant: {current_tenant} ({len(workflows)} workflows)")
    
    if tenant_name:
        logger.info(f"Workflow sync completed successfully for tenant: {tenant_name}")
    else:
        logger.info(f"Workflow sync completed successfully for all {len(tenants_to_sync)} tenants ({total_workflows_synced} total workflows)")
