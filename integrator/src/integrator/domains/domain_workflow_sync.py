"""Sync workflow and workflow steps from PostgreSQL to Neo4j.

This module provides functionality to read workflows and their steps from the
relational database and mirror them into the Neo4j knowledge graph, creating
appropriate nodes and edges to represent the workflow structure.

The sync process:
1. Reads all workflow steps grouped by workflow from PostgreSQL
2. Creates Workflow nodes in Neo4j
3. Creates WorkflowStep nodes in Neo4j
4. Creates HAS_STEP edges from Workflow to WorkflowStep
5. Creates NEXT_STEP edges between consecutive WorkflowSteps based on step_order
"""

from typing import Dict, List, Any

from integrator.utils.db import get_db_cm
from integrator.utils.graph import get_graph_driver, close_graph_driver
from integrator.utils.logger import get_logger
from integrator.domains.domain_db_crud import (
    get_all_workflow_steps_grouped_by_workflow,
    get_domains_by_workflow_step,
    get_capabilities_by_workflow_step,
)
from integrator.domains.domain_graph_crud import (
    create_workflow_node,
    create_workflow_step_node,
    create_workflow_has_step_edge,
    create_workflow_step_next_edge,
    create_workflow_step_domain_edge,
    create_workflow_step_capability_edge,
)
from sqlalchemy import select
from integrator.domains.domain_db_model import Workflow


logger = get_logger(__name__)


def sync_workflows_from_db_to_graph(gsess) -> None:
    """Sync all workflows and their steps from PostgreSQL to Neo4j.
    
    This function:
    1. Retrieves all workflow steps grouped by workflow from the database
    2. Creates/updates Workflow nodes in Neo4j
    3. Creates/updates WorkflowStep nodes in Neo4j
    4. Creates HAS_STEP edges from Workflow to each WorkflowStep
    5. Creates NEXT_STEP edges between consecutive steps based on step_order
    
    Args:
        gsess: Neo4j session for graph operations
    """
    with get_db_cm() as sess:
        # Get all workflows from the database
        workflows = sess.execute(select(Workflow)).scalars().all()
        
        # Get all workflow steps grouped by workflow
        grouped_steps = get_all_workflow_steps_grouped_by_workflow(sess)
        
        logger.info(f"Found {len(workflows)} workflows and {len(grouped_steps)} workflow groups to sync")
        
        # Process each workflow
        for workflow in workflows:
            workflow_name = workflow.name
            
            # Create workflow node
            workflow_data = {
                "name": workflow.name,
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
            # Handle both string and numeric step_order values
            try:
                sorted_steps = sorted(steps, key=lambda x: float(x.get("step_order", 0)))
            except (ValueError, TypeError):
                # If conversion fails, sort as strings
                sorted_steps = sorted(steps, key=lambda x: str(x.get("step_order", "")))
            
            # Create workflow step nodes and HAS_STEP edges
            for step in sorted_steps:
                step_name = step["name"]
                
                # Create workflow step node
                create_workflow_step_node(gsess, step)
                
                # Create HAS_STEP edge from workflow to step
                create_workflow_has_step_edge(gsess, workflow_name, step_name)
                
                # Get and create domain relationships for this step
                domains = get_domains_by_workflow_step(sess, step_name)
                for domain_name in domains:
                    create_workflow_step_domain_edge(gsess, step_name, domain_name)
                    logger.info(f"Created USES_DOMAIN edge: {step_name} -> {domain_name}")
                
                # Get and create capability relationships for this step
                capabilities = get_capabilities_by_workflow_step(sess, step_name)
                for capability_name in capabilities:
                    create_workflow_step_capability_edge(gsess, step_name, capability_name)
                    logger.info(f"Created USES_CAPABILITY edge: {step_name} -> {capability_name}")
            
            # Create NEXT_STEP edges between consecutive steps
            for i in range(len(sorted_steps) - 1):
                current_step = sorted_steps[i]
                next_step = sorted_steps[i + 1]
                
                create_workflow_step_next_edge(
                    gsess,
                    from_step_name=current_step["name"],
                    to_step_name=next_step["name"],
                    workflow_name=workflow_name,
                )
            
            logger.info(f"Successfully synced workflow: {workflow_name} with {len(sorted_steps)} steps")
        
        logger.info("Workflow sync completed successfully")


def main():
    """Main entry point for syncing workflows from database to graph."""
    driver = get_graph_driver()
    try:
        with driver.session() as gsess:
            sync_workflows_from_db_to_graph(gsess)
    finally:
        close_graph_driver()
    
    logger.info("Workflow sync process completed")


if __name__ == "__main__":
    main()
