from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
from datetime import datetime
from integrator.domains.domain_db_model import (
    Domain, Capability, DomainCapability, CanonicalSkill, CapabilityCanonicalSkill,
    Workflow, WorkflowStep, WorkflowStepDomain, WorkflowStepCapability
)

from integrator.domains.domain_db_model import Domain
from integrator.domains.domain_graph_crud import (
    sync_domains_from_db_to_graph, sync_workflows_from_db_to_graph
)
from integrator.utils.graph import get_graph_driver, close_graph_driver

from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
import uuid
import numpy as np





logger = get_logger(__name__)

def import_domains(sess, backup_dir, clear_existing=False):
    """Import domains from JSON backup with complete metadata"""
    try:
        backup_file = os.path.join(backup_dir, "domains.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Domains backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_domains = json.load(f)
        
        if clear_existing:
            # Clear existing domains
            sess.execute(delete(DomainCapability))
            sess.execute(delete(Domain))
            logger.info("Cleared existing domains and relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, domains_data in tenant_domains.items():
            logger.info(f"Importing {len(domains_data)} domains for tenant: {tenant_name}")
            
            for domain_data in domains_data:
                # Extract tenant_name from data
                import_tenant = domain_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue
                # Check if domain already exists for this tenant
                existing = sess.execute(
                    select(Domain).where(
                        (Domain.name == domain_data["name"]) &
                        (Domain.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Domain {domain_data['name']} already exists, skipping")
                    continue
                
                # Convert embedding back to numpy array if present
                emb_vector = None
                if domain_data.get("emb"):
                    emb_vector = np.array(domain_data["emb"], dtype=np.float32)
                
                if existing:
                    # Update existing domain
                    existing.label = domain_data["label"]
                    existing.description = domain_data["description"]
                    existing.scope = domain_data.get("scope", "")
                    existing.domain_entities = domain_data.get("domain_entities", [])
                    existing.domain_purposes = domain_data.get("domain_purposes", "")
                    existing.value_metrics = domain_data.get("value_metrics", [])
                    existing.emb = emb_vector
                    existing.created_at = domain_data.get("created_at")
                    logger.info(f"Updated domain: {domain_data['name']}")
                else:
                    # Create new domain
                    domain = Domain(
                        id=uuid.UUID(domain_data["id"]) if domain_data.get("id") else None,
                        name=domain_data["name"],
                        tenant_name=tenant_name,
                        label=domain_data["label"],
                        description=domain_data["description"],
                        scope=domain_data.get("scope", ""),
                        domain_entities=domain_data.get("domain_entities", []),
                        domain_purposes=domain_data.get("domain_purposes", ""),
                        value_metrics=domain_data.get("value_metrics", []),
                        emb=emb_vector,
                        created_at=domain_data.get("created_at")
                    )
                    sess.add(domain)
                    logger.info(f"Imported domain: {domain_data['name']}")
                
                imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} domains")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import domains: {str(e)}")
        sess.rollback()
        return False

def import_capabilities(sess, backup_dir, clear_existing=False):
    """Import capabilities from JSON backup with complete metadata"""
    try:
        backup_file = os.path.join(backup_dir, "capabilities.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Capabilities backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_capabilities = json.load(f)
        
        if clear_existing:
            # Clear existing capabilities
            sess.execute(delete(DomainCapability))
            sess.execute(delete(Capability))
            logger.info("Cleared existing capabilities and relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, capabilities_data in tenant_capabilities.items():
            logger.info(f"Importing {len(capabilities_data)} capabilities for tenant: {tenant_name}")
            
            for capability_data in capabilities_data:
                # Extract tenant_name from data
                import_tenant = capability_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue
                # Check if capability already exists for this tenant
                existing = sess.execute(
                    select(Capability).where(
                        (Capability.name == capability_data["name"]) &
                        (Capability.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Capability {capability_data['name']} already exists, skipping")
                    continue
                
                # Convert embedding back to numpy array if present
                emb_vector = None
                if capability_data.get("emb"):
                    emb_vector = np.array(capability_data["emb"], dtype=np.float32)
                
                if existing:
                    # Update existing capability
                    existing.label = capability_data["label"]
                    existing.description = capability_data["description"]
                    existing.business_context = capability_data.get("business_context", [])
                    existing.business_processes = capability_data.get("business_processes", [])
                    existing.outcome = capability_data.get("outcome", "")
                    existing.business_intent = capability_data.get("business_intent", [])
                    existing.emb = emb_vector
                    existing.created_at = capability_data.get("created_at")
                    logger.info(f"Updated capability: {capability_data['name']}")
                else:
                    # Create new capability
                    capability = Capability(
                        id=uuid.UUID(capability_data["id"]) if capability_data.get("id") else None,
                        name=capability_data["name"],
                        tenant_name=tenant_name,
                        label=capability_data["label"],
                        description=capability_data["description"],
                        business_context=capability_data.get("business_context", []),
                        business_processes=capability_data.get("business_processes", []),
                        outcome=capability_data.get("outcome", ""),
                        business_intent=capability_data.get("business_intent", []),
                        emb=emb_vector,
                        created_at=capability_data.get("created_at")
                    )
                    sess.add(capability)
                    logger.info(f"Imported capability: {capability_data['name']}")
                
                imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} capabilities")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import capabilities: {str(e)}")
        sess.rollback()
        return False

def import_domain_capability_relationships(sess, backup_dir, clear_existing=False):
    """Import domain-capability relationships from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "domain_capability.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Domain-capability relationships backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(DomainCapability))
            logger.info("Cleared existing domain-capability relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Importing {len(relationships_data)} domain-capability relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                # Extract tenant_name from data
                import_tenant = rel_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue                
                # Check if relationship already exists
                existing = sess.execute(
                    select(DomainCapability).where(
                        (DomainCapability.domain_name == rel_data["domain_name"]) &
                        (DomainCapability.capability_name == rel_data["capability_name"]) &
                        (DomainCapability.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {rel_data['domain_name']} -> {rel_data['capability_name']} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = DomainCapability(
                        domain_name=rel_data["domain_name"],
                        capability_name=rel_data["capability_name"],
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} domain-capability relationships")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import domain-capability relationships: {str(e)}")
        sess.rollback()
        return False


def import_canonical_skills(sess, backup_dir, clear_existing=False):
    """Import canonical skills from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "canonical_skills.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Canonical skills backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_skills = json.load(f)
        
        if clear_existing:
            # Clear existing canonical skills
            sess.execute(delete(CapabilityCanonicalSkill))
            sess.execute(delete(CanonicalSkill))
            logger.info("Cleared existing canonical skills and relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, skills_data in tenant_skills.items():
            logger.info(f"Importing {len(skills_data)} canonical skills for tenant: {tenant_name}")
            
            for skill_data in skills_data:
                # Extract tenant_name from data
                import_tenant = skill_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue                
                # Check if skill already exists for this tenant
                existing = sess.execute(
                    select(CanonicalSkill).where(
                        (CanonicalSkill.name == skill_data["name"]) &
                        (CanonicalSkill.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Canonical skill {skill_data['name']} already exists, skipping")
                    continue
                
                if existing:
                    # Update existing skill
                    existing.label = skill_data["label"]
                    existing.skill_kind = skill_data["skill_kind"]
                    existing.intent = skill_data["intent"]
                    existing.entity = skill_data.get("entity", [])
                    existing.criticality = skill_data["criticality"]
                    existing.description = skill_data["description"]
                    existing.created_at = skill_data.get("created_at")
                    logger.info(f"Updated canonical skill: {skill_data['name']}")
                else:
                    # Create new skill
                    skill = CanonicalSkill(
                        id=uuid.UUID(skill_data["id"]) if skill_data.get("id") else None,
                        name=skill_data["name"],
                        tenant_name=tenant_name,
                        label=skill_data["label"],
                        skill_kind=skill_data["skill_kind"],
                        intent=skill_data["intent"],
                        entity=skill_data.get("entity", []),
                        criticality=skill_data["criticality"],
                        description=skill_data["description"],
                        created_at=skill_data.get("created_at")
                    )
                    sess.add(skill)
                    logger.info(f"Imported canonical skill: {skill_data['name']}")
                
                imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} canonical skills")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import canonical skills: {str(e)}")
        sess.rollback()
        return False


def import_capability_canonical_skill_relationships(sess, backup_dir, clear_existing=False):
    """Import capability-canonical skill relationships from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "capability_canonical_skill.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Capability-canonical skill relationships backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(CapabilityCanonicalSkill))
            logger.info("Cleared existing capability-canonical skill relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Importing {len(relationships_data)} capability-canonical skill relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                # Extract tenant_name from data
                import_tenant = rel_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue               
                # Check if relationship already exists
                existing = sess.execute(
                    select(CapabilityCanonicalSkill).where(
                        (CapabilityCanonicalSkill.capability_name == rel_data["capability_name"]) &
                        (CapabilityCanonicalSkill.canonical_skill_name == rel_data["canonical_skill_name"]) &
                        (CapabilityCanonicalSkill.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {rel_data['capability_name']} -> {rel_data['canonical_skill_name']} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = CapabilityCanonicalSkill(
                        capability_name=rel_data["capability_name"],
                        canonical_skill_name=rel_data["canonical_skill_name"],
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} capability-canonical skill relationships")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import capability-canonical skill relationships: {str(e)}")
        sess.rollback()
        return False


def import_workflows(sess, backup_dir, clear_existing=False):
    """Import workflows from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "workflows.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Workflows backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_workflows = json.load(f)
        
        if clear_existing:
            # Clear existing workflows and related data
            sess.execute(delete(WorkflowStepDomain))
            sess.execute(delete(WorkflowStepCapability))
            sess.execute(delete(WorkflowStep))
            sess.execute(delete(Workflow))
            logger.info("Cleared existing workflows and relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, workflows_data in tenant_workflows.items():
            logger.info(f"Importing {len(workflows_data)} workflows for tenant: {tenant_name}")
            
            for workflow_data in workflows_data:
                # Extract tenant_name from data
                import_tenant = workflow_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue                
                # Check if workflow already exists for this tenant
                existing = sess.execute(
                    select(Workflow).where(
                        (Workflow.name == workflow_data["name"]) &
                        (Workflow.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Workflow {workflow_data['name']} already exists, skipping")
                    continue
                
                if existing:
                    # Update existing workflow
                    existing.label = workflow_data["label"]
                    existing.description = workflow_data["description"]
                    existing.value_metrics = workflow_data.get("value_metrics", [])
                    existing.created_at = workflow_data.get("created_at")
                    logger.info(f"Updated workflow: {workflow_data['name']}")
                else:
                    # Create new workflow
                    workflow = Workflow(
                        id=uuid.UUID(workflow_data["id"]) if workflow_data.get("id") else None,
                        name=workflow_data["name"],
                        tenant_name=tenant_name,
                        label=workflow_data["label"],
                        description=workflow_data["description"],
                        value_metrics=workflow_data.get("value_metrics", []),
                        created_at=workflow_data.get("created_at")
                    )
                    sess.add(workflow)
                    logger.info(f"Imported workflow: {workflow_data['name']}")
                
                imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} workflows")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import workflows: {str(e)}")
        sess.rollback()
        return False


def import_workflow_steps(sess, backup_dir, clear_existing=False):
    """Import workflow steps from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "workflow_steps.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Workflow steps backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_steps = json.load(f)
        
        if clear_existing:
            # Clear existing workflow steps
            sess.execute(delete(WorkflowStepDomain))
            sess.execute(delete(WorkflowStepCapability))
            sess.execute(delete(WorkflowStep))
            logger.info("Cleared existing workflow steps and relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, steps_data in tenant_steps.items():
            logger.info(f"Importing {len(steps_data)} workflow steps for tenant: {tenant_name}")
            
            for step_data in steps_data:
                # Extract tenant_name from data
                tenant_name = step_data.get("tenant_name", tenant_name)
                
                # Check if step already exists for this tenant
                existing = sess.execute(
                    select(WorkflowStep).where(
                        (WorkflowStep.name == step_data["name"]) &
                        (WorkflowStep.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Workflow step {step_data['name']} already exists, skipping")
                    continue
                
                if existing:
                    # Update existing step
                    existing.label = step_data["label"]
                    existing.step_order = step_data["step_order"]
                    existing.intent = step_data["intent"]
                    existing.description = step_data["description"]
                    existing.workflow_name = step_data["workflow_name"]
                    existing.created_at = step_data.get("created_at")
                    logger.info(f"Updated workflow step: {step_data['name']}")
                else:
                    # Create new step
                    step = WorkflowStep(
                        id=uuid.UUID(step_data["id"]) if step_data.get("id") else None,
                        name=step_data["name"],
                        tenant_name=tenant_name,
                        label=step_data["label"],
                        step_order=step_data["step_order"],
                        intent=step_data["intent"],
                        description=step_data["description"],
                        workflow_name=step_data["workflow_name"],
                        created_at=step_data.get("created_at")
                    )
                    sess.add(step)
                    logger.info(f"Imported workflow step: {step_data['name']}")
                
                imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} workflow steps")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import workflow steps: {str(e)}")
        sess.rollback()
        return False


def import_workflow_step_domain_relationships(sess, backup_dir, clear_existing=False):
    """Import workflow step-domain relationships from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "workflow_step_domain.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Workflow step-domain relationships backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(WorkflowStepDomain))
            logger.info("Cleared existing workflow step-domain relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Importing {len(relationships_data)} workflow step-domain relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                # Extract tenant_name from data
                tenant_name = rel_data.get("tenant_name", tenant_name)
                
                # Check if relationship already exists
                existing = sess.execute(
                    select(WorkflowStepDomain).where(
                        (WorkflowStepDomain.workflow_step_name == rel_data["workflow_step_name"]) &
                        (WorkflowStepDomain.domain_name == rel_data["domain_name"]) &
                        (WorkflowStepDomain.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {rel_data['workflow_step_name']} -> {rel_data['domain_name']} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = WorkflowStepDomain(
                        workflow_step_name=rel_data["workflow_step_name"],
                        domain_name=rel_data["domain_name"],
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} workflow step-domain relationships")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import workflow step-domain relationships: {str(e)}")
        sess.rollback()
        return False


def import_workflow_step_capability_relationships(sess, backup_dir, clear_existing=False):
    """Import workflow step-capability relationships from JSON backup"""
    try:
        backup_file = os.path.join(backup_dir, "workflow_step_capability.json")
        if not os.path.exists(backup_file):
            logger.warning(f"Workflow step-capability relationships backup file not found: {backup_file}")
            return False
        
        with open(backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(WorkflowStepCapability))
            logger.info("Cleared existing workflow step-capability relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Importing {len(relationships_data)} workflow step-capability relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                # Extract tenant_name from data
                import_tenant = rel_data.get("tenant_name", tenant_name)
                if import_tenant != tenant_name:
                    continue                
                # Check if relationship already exists
                existing = sess.execute(
                    select(WorkflowStepCapability).where(
                        (WorkflowStepCapability.workflow_step_name == rel_data["workflow_step_name"]) &
                        (WorkflowStepCapability.capability_name == rel_data["capability_name"]) &
                        (WorkflowStepCapability.tenant_name == tenant_name)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {rel_data['workflow_step_name']} -> {rel_data['capability_name']} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = WorkflowStepCapability(
                        workflow_step_name=rel_data["workflow_step_name"],
                        capability_name=rel_data["capability_name"],
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully imported {imported_count} workflow step-capability relationships")
        return True
        
    except Exception as e:
        logger.error(f"Failed to import workflow step-capability relationships: {str(e)}")
        sess.rollback()
        return False


def load_graph(sess):
    driver = get_graph_driver()
    with driver.session() as gsess:  
        #cleanup_all_domains_graph(gsess)
        #cleanup_all_workflow_graph(gsess)
        sync_domains_from_db_to_graph(sess, gsess)
        sync_workflows_from_db_to_graph(sess, gsess)


    close_graph_driver()
    print("domain and workflow graph are loaded.")


def restore_all_domains(backup_dir, tenant_name:str=None, clear_existing=False):

    tenant_suffix = f"_{tenant_name}" if tenant_name else "_all"
    backup_dir = os.path.join( backup_dir, f"domains{tenant_suffix}")

    if not os.path.exists(backup_dir):
        logger.error(f"Backup directory not found: {backup_dir}")
        return False
    
    logger.info(f"Starting domain import from {backup_dir}")
    
    try:
        with get_db_cm() as sess:
            success = True
            
            # Import in dependency order
            logger.info("Importing domains...")
            if not import_domains(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing capabilities...")
            if not import_capabilities(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing canonical skills...")
            if not import_canonical_skills(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing domain-capability relationships...")
            if not import_domain_capability_relationships(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing capability-canonical skill relationships...")
            if not import_capability_canonical_skill_relationships(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing workflows...")
            if not import_workflows(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing workflow steps...")
            if not import_workflow_steps(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing workflow step-domain relationships...")
            if not import_workflow_step_domain_relationships(sess, backup_dir, clear_existing):
                success = False
            
            logger.info("Importing workflow step-capability relationships...")
            if not import_workflow_step_capability_relationships(sess, backup_dir, clear_existing):
                success = False

            # Commit database changes first before attempting graph sync
            if success:
                sess.commit()
                logger.info("Domain import to database completed successfully")
            else:
                sess.rollback()
                logger.error("Domain import failed, rolled back changes")
                return success

            # Sync to graph database (non-fatal - database changes already committed)
            try:
                logger.info("Syncing domains and workflows to graph database...")
                load_graph(sess)
                logger.info("Graph sync completed successfully")
            except Exception as e:
                logger.warning(f"Graph sync failed (database changes were still saved): {str(e)}")

            return success
            
    except Exception as e:
        logger.error(f"Domain import failed with exception: {str(e)}")
        return False
