from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()
import json
import os
from integrator.domains.domain_db_crud import (
    upsert_domain, upsert_capability, insert_domain_capability, 
    upsert_canonical_skill, insert_capability_canonical_skill,
    upsert_workflow, upsert_workflow_step, insert_workflow_step_domain, insert_workflow_step_capability,
    get_capabilities_by_domain
    
)
from integrator.domains.domain_db_model import Domain
from integrator.domains.domain_graph_crud import (
    sync_domains_from_db_to_graph, sync_workflows_from_db_to_graph,
    create_domain_node, create_capability_node, create_domain_capability_edge, cleanup_all_workflow_graph,
    cleanup_all_domains_graph
)
from integrator.utils.db import get_db_cm
from integrator.utils.llm import Embedder
from integrator.utils.graph import get_graph_driver, close_graph_driver
from sqlalchemy import  select, insert
from integrator.utils.logger import get_logger
import numpy as np


logger = get_logger(__name__)

DOMAINS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/01_domains/seed_domains_v1.json")
CAPABILITIES_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/01_domains/seed_capabilities_v1.json")
CANONICAL_SKILLS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/01_domains/seed_capability_minimum_skills_v1.json")
WORKFLOWS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/01_domains/seed_workflows_v1.json")


def load_domains(sess, emb, json_path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            # Extract tenant name from the JSON structure {"tenant_name": [...]}
            for tenant_name, domains in data.items():
                for domain_data in domains:
                    upsert_domain(sess, emb, domain_data, tenant_name)
                sess.commit()
                logger.info(f"Inserted/updated {len(domains)} domains for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to insert domains, error: {str(e)}")

def load_capabilities(sess, emb, json_path):
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            # Extract tenant name from the JSON structure {"tenant_name": [...]}
            for tenant_name, capabilities in data.items():
                count=0
                for item in capabilities:
                    domain_name=item.get("domain") or item.get("category") or item.get("name")
                    for cap_data in item.get("capabilities", []):
                        Capability_name= cap_data.get("name")
                        upsert_capability(sess, emb, cap_data, tenant_name)
                        sess.flush()
                        if domain_name:
                            insert_domain_capability(sess, domain_name, Capability_name, tenant_name)
                        count += 1
                sess.commit()
                logger.info(f"Inserted/updated {count} capabilities for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to insert capabilities, error: {str(e)}")
        sess.rollback()


def load_canonical_skills(sess, json_path):
    """Load canonical skills from JSON file and create relationships with capabilities.
    
    The JSON file contains skill records with the following structure:
    - name: Unique skill identifier
    - label: Display name
    - skill_kind: Type of skill (e.g., 'core', 'process')
    - intent: Skill intent (e.g., 'get_details', 'discover_list')
    - entity: List of entities
    - criticality: Criticality level (e.g., 'core', 'important')
    - description: Detailed description
    - capability: Name of the capability this skill belongs to
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            # Extract tenant name from the JSON structure {"tenant_name": [...]}
            for tenant_name, skills in data.items():
                count = 0
                for skill_data in skills:
                    # Extract capability name for relationship
                    capability_name = skill_data.get("capability")
                    
                    # Prepare skill data for upsert (exclude capability field)
                    canonical_skill_data = {
                        "name": skill_data.get("name"),
                        "label": skill_data.get("label", ""),
                        "skill_kind": skill_data.get("skill_kind", ""),
                        "intent": skill_data.get("intent", ""),
                        "entity": skill_data.get("entity", []),
                        "criticality": skill_data.get("criticality", ""),
                        "description": skill_data.get("description", "")
                    }
                    
                    # Upsert the canonical skill
                    upsert_canonical_skill(sess, canonical_skill_data, tenant_name)
                    sess.flush()
                    
                    # Create relationship with capability if capability name exists
                    if capability_name:
                        insert_capability_canonical_skill(sess, capability_name, canonical_skill_data["name"], tenant_name)
                    
                    count += 1
                
                sess.commit()
                logger.info(f"Inserted/updated {count} canonical skills for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to insert canonical skills, error: {str(e)}")
        sess.rollback()


def load_workflows(sess, json_path):
    """Load workflows, workflow steps, and their relationships from JSON file.
    
    The JSON file contains workflow records with the following structure:
    - name: Unique workflow identifier
    - label: Display name
    - description: Detailed description
    - value_metrics: List of value metrics
    - steps: List of workflow steps, each containing:
        - name: Unique step identifier
        - label: Display name
        - order: Step order in the workflow
        - intent: Step intent
        - description: Detailed description
        - domains: List of domains with required_capabilities
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            # Extract tenant name from the JSON structure {"tenant_name": [...]}
            for tenant_name, workflows in data.items():
                workflow_count = 0
                step_count = 0
                
                for workflow_data in workflows:
                    # Prepare workflow data
                    workflow_info = {
                        "name": workflow_data.get("name"),
                        "label": workflow_data.get("label", ""),
                        "description": workflow_data.get("description", ""),
                        "value_metrics": workflow_data.get("value_metrics", [])
                    }
                    
                    # Upsert the workflow
                    upsert_workflow(sess, workflow_info, tenant_name)
                    sess.flush()
                    workflow_count += 1
                    
                    # Process workflow steps
                    steps = workflow_data.get("steps", [])
                    for step_data in steps:
                        # Prepare workflow step data
                        step_info = {
                            "name": step_data.get("name"),
                            "label": step_data.get("label", ""),
                            "order": step_data.get("order", 0),
                            "intent": step_data.get("intent", ""),
                            "description": step_data.get("description", ""),
                            "workflow_name": workflow_info["name"]
                        }
                        
                        # Upsert the workflow step
                        upsert_workflow_step(sess, step_info, tenant_name)
                        sess.flush()
                        step_count += 1
                        
                        # Process domains and capabilities for this step
                        domains = step_data.get("domains", [])
                        for domain_data in domains:
                            domain_name = domain_data.get("domain_name")
                            
                            # Create workflow_step -> domain relationship
                            if domain_name:
                                insert_workflow_step_domain(sess, step_info["name"], domain_name, tenant_name)
                            
                            # Process capabilities within this domain
                            capabilities = domain_data.get("required_capabilities", [])
                            for capability_data in capabilities:
                                capability_id = capability_data.get("capability_id")
                                
                                # Create workflow_step -> capability relationship
                                if capability_id:
                                    insert_workflow_step_capability(sess, step_info["name"], capability_id, tenant_name)
                
                sess.commit()
                logger.info(f"Inserted/updated {workflow_count} workflows and {step_count} workflow steps for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to insert workflows, error: {str(e)}")
        sess.rollback()

def load_graph(sess):
    driver = get_graph_driver()
    with driver.session() as gsess:  
        #cleanup_all_domains_graph(gsess)
        #cleanup_all_workflow_graph(gsess)
        sync_domains_from_db_to_graph(sess, gsess)
        sync_workflows_from_db_to_graph(sess, gsess)


    close_graph_driver()
    print("domain and workflow graph are loaded.")



def main():
    emb = Embedder()
    with get_db_cm() as sess:
        load_domains(sess, emb, DOMAINS_JSON_PATH)
        load_capabilities(sess, emb, CAPABILITIES_JSON_PATH)
        load_canonical_skills(sess, CANONICAL_SKILLS_JSON_PATH)
        load_workflows(sess, WORKFLOWS_JSON_PATH)
        load_graph(sess)

if __name__ == "__main__":
    main()
