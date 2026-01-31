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
from integrator.iam.iam_db_model import Tenant
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from sqlalchemy import select
import numpy as np
BACKUP_DIR="../../../data/backup_data"

logger = get_logger(__name__)

def serialize_datetime(obj):
    """Helper to serialize datetime objects"""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    return str(obj)

def backup_domains(sess, backup_dir, tenant_names):
    """Backup all domains from database to JSON format with complete metadata"""
    try:
        tenant_domains={}
        for tenant_name in tenant_names:
            stmt = select(Domain)
            if tenant_name:
                stmt = stmt.where(Domain.tenant_name == tenant_name)
            domains = sess.execute(stmt).scalars().all()
            
            domains_data = []
            for domain in domains:
                domain_dict = {
                    "id": str(domain.id),
                    "name": domain.name,
                    "tenant_name": domain.tenant_name,
                    "label": domain.label,
                    "description": domain.description,
                    "scope": domain.scope,
                    "domain_entities": domain.domain_entities if domain.domain_entities else [],
                    "domain_purposes": domain.domain_purposes,
                    "value_metrics": domain.value_metrics if domain.value_metrics else [],
                    "created_at": domain.created_at
                }
                
                # Convert embedding vector to list for JSON serialization
                if domain.emb is not None:
                    if isinstance(domain.emb, np.ndarray):
                        domain_dict["emb"] = domain.emb.tolist()
                    elif hasattr(domain.emb, '__iter__'):
                        domain_dict["emb"] = list(domain.emb)
                    else:
                        domain_dict["emb"] = domain.emb
                else:
                    domain_dict["emb"] = None
                    
                domains_data.append(domain_dict)
            logger.info(f"Backing up {len(domains_data)} domains in tenant={tenant_name}")
 
            tenant_domains[tenant_name]=domains_data
        backup_file = os.path.join(backup_dir, "domains.json")
        logger.info(f"Backed up domains in tenant={tenant_name} to {backup_file}")

        with open(backup_file, "w") as f:
            json.dump(tenant_domains, f, indent=2)
        
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup domains: {str(e)}")
        return None

def backup_capabilities(sess, backup_dir, tenant_names):
    """Backup all capabilities with complete metadata"""
    try:
        tenant_capabilities = {}
        for tenant_name in tenant_names:
            stmt = select(Capability)
            if tenant_name:
                stmt = stmt.where(Capability.tenant_name == tenant_name)
            capabilities = sess.execute(stmt).scalars().all()
            
            capabilities_data = []
            for capability in capabilities:
                cap_dict = {
                    "id": str(capability.id),
                    "name": capability.name,
                    "tenant_name": capability.tenant_name,
                    "label": capability.label,
                    "description": capability.description,
                    "business_context": capability.business_context if capability.business_context else [],
                    "business_processes": capability.business_processes if capability.business_processes else [],
                    "outcome": capability.outcome if capability.outcome else "",
                    "business_intent": capability.business_intent if capability.business_intent else [],
                    "created_at": capability.created_at
                }
                
                # Convert embedding vector to list for JSON serialization
                if capability.emb is not None:
                    if isinstance(capability.emb, np.ndarray):
                        cap_dict["emb"] = capability.emb.tolist()
                    elif hasattr(capability.emb, '__iter__'):
                        cap_dict["emb"] = list(capability.emb)
                    else:
                        cap_dict["emb"] = capability.emb
                else:
                    cap_dict["emb"] = None
                    
                capabilities_data.append(cap_dict)
            
            logger.info(f"Backing up {len(capabilities_data)} capabilities in tenant={tenant_name}")
            tenant_capabilities[tenant_name] = capabilities_data
        
        backup_file = os.path.join(backup_dir, "capabilities.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_capabilities, f, indent=2)
        
        logger.info(f"Backed up capabilities to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup capabilities: {str(e)}")
        return None

def backup_domain_capability_relationships(sess, backup_dir, tenant_names):
    """Backup domain-capability relationships"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            stmt = select(DomainCapability)
            if tenant_name:
                stmt = stmt.where(DomainCapability.tenant_name == tenant_name)
            relationships = sess.execute(stmt).scalars().all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "domain_name": rel.domain_name,
                    "capability_name": rel.capability_name,
                    "tenant_name": rel.tenant_name
                })
            
            logger.info(f"Backing up {len(relationships_data)} domain-capability relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "domain_capability.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up domain-capability relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup domain-capability relationships: {str(e)}")
        return None


def backup_canonical_skills(sess, backup_dir, tenant_names):
    """Backup all canonical skills"""
    try:
        tenant_skills = {}
        for tenant_name in tenant_names:
            stmt = select(CanonicalSkill)
            if tenant_name:
                stmt = stmt.where(CanonicalSkill.tenant_name == tenant_name)
            skills = sess.execute(stmt).scalars().all()
            
            skills_data = []
            for skill in skills:
                skill_dict = {
                    "id": str(skill.id),
                    "name": skill.name,
                    "tenant_name": skill.tenant_name,
                    "label": skill.label,
                    "skill_kind": skill.skill_kind,
                    "intent": skill.intent,
                    "entity": skill.entity if skill.entity else [],
                    "criticality": skill.criticality,
                    "description": skill.description,
                    "created_at": skill.created_at
                }
                skills_data.append(skill_dict)
            
            logger.info(f"Backing up {len(skills_data)} canonical skills in tenant={tenant_name}")
            tenant_skills[tenant_name] = skills_data
        
        backup_file = os.path.join(backup_dir, "canonical_skills.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_skills, f, indent=2)
        
        logger.info(f"Backed up canonical skills to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup canonical skills: {str(e)}")
        return None


def backup_capability_canonical_skill_relationships(sess, backup_dir, tenant_names):
    """Backup capability-canonical skill relationships"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            stmt = select(CapabilityCanonicalSkill)
            if tenant_name:
                stmt = stmt.where(CapabilityCanonicalSkill.tenant_name == tenant_name)
            relationships = sess.execute(stmt).scalars().all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "capability_name": rel.capability_name,
                    "canonical_skill_name": rel.canonical_skill_name,
                    "tenant_name": rel.tenant_name
                })
            
            logger.info(f"Backing up {len(relationships_data)} capability-canonical skill relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "capability_canonical_skill.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up capability-canonical skill relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup capability-canonical skill relationships: {str(e)}")
        return None


def backup_workflows(sess, backup_dir, tenant_names):
    """Backup all workflows"""
    try:
        tenant_workflows = {}
        for tenant_name in tenant_names:
            stmt = select(Workflow)
            if tenant_name:
                stmt = stmt.where(Workflow.tenant_name == tenant_name)
            workflows = sess.execute(stmt).scalars().all()
            
            workflows_data = []
            for workflow in workflows:
                workflow_dict = {
                    "id": str(workflow.id),
                    "name": workflow.name,
                    "tenant_name": workflow.tenant_name,
                    "label": workflow.label,
                    "description": workflow.description,
                    "value_metrics": workflow.value_metrics if workflow.value_metrics else [],
                    "created_at": workflow.created_at
                }
                workflows_data.append(workflow_dict)
            
            logger.info(f"Backing up {len(workflows_data)} workflows in tenant={tenant_name}")
            tenant_workflows[tenant_name] = workflows_data
        
        backup_file = os.path.join(backup_dir, "workflows.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_workflows, f, indent=2)
        
        logger.info(f"Backed up workflows to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup workflows: {str(e)}")
        return None


def backup_workflow_steps(sess, backup_dir, tenant_names):
    """Backup all workflow steps"""
    try:
        tenant_steps = {}
        for tenant_name in tenant_names:
            stmt = select(WorkflowStep)
            if tenant_name:
                stmt = stmt.where(WorkflowStep.tenant_name == tenant_name)
            steps = sess.execute(stmt).scalars().all()
            
            steps_data = []
            for step in steps:
                step_dict = {
                    "id": str(step.id),
                    "name": step.name,
                    "tenant_name": step.tenant_name,
                    "label": step.label,
                    "step_order": step.step_order,
                    "intent": step.intent,
                    "description": step.description,
                    "workflow_name": step.workflow_name,
                    "created_at": step.created_at
                }
                steps_data.append(step_dict)
            
            logger.info(f"Backing up {len(steps_data)} workflow steps in tenant={tenant_name}")
            tenant_steps[tenant_name] = steps_data
        
        backup_file = os.path.join(backup_dir, "workflow_steps.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_steps, f, indent=2)
        
        logger.info(f"Backed up workflow steps to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup workflow steps: {str(e)}")
        return None


def backup_workflow_step_domain_relationships(sess, backup_dir, tenant_names):
    """Backup workflow step-domain relationships"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            stmt = select(WorkflowStepDomain)
            if tenant_name:
                stmt = stmt.where(WorkflowStepDomain.tenant_name == tenant_name)
            relationships = sess.execute(stmt).scalars().all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "workflow_step_name": rel.workflow_step_name,
                    "domain_name": rel.domain_name,
                    "tenant_name": rel.tenant_name
                })
            
            logger.info(f"Backing up {len(relationships_data)} workflow step-domain relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "workflow_step_domain.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up workflow step-domain relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup workflow step-domain relationships: {str(e)}")
        return None


def backup_workflow_step_capability_relationships(sess, backup_dir, tenant_names):
    """Backup workflow step-capability relationships"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            stmt = select(WorkflowStepCapability)
            if tenant_name:
                stmt = stmt.where(WorkflowStepCapability.tenant_name == tenant_name)
            relationships = sess.execute(stmt).scalars().all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "workflow_step_name": rel.workflow_step_name,
                    "capability_name": rel.capability_name,
                    "tenant_name": rel.tenant_name
                })
            
            logger.info(f"Backing up {len(relationships_data)} workflow step-capability relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "workflow_step_capability.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up workflow step-capability relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup workflow step-capability relationships: {str(e)}")
        return None

def main():
    """Main backup function for domain data"""
    import sys
    
    # Get tenant_name from command line argument or use None for all tenants
    tenant_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    tenant_suffix = f"_{tenant_name}" if tenant_name else "_all"
    backup_dir = os.path.join(os.path.dirname(__file__), BACKUP_DIR, f"{timestamp}/domains{tenant_suffix}")
    os.makedirs(backup_dir, exist_ok=True)
    
    tenant_names=[]
    with get_db_cm() as sess:
        # If no tenant_name provided, get all tenants from tenant table
        if not tenant_name:
            stmt = select(Tenant.name)
            tenant_names = sess.execute(stmt).scalars().all()
            if not tenant_names:
                logger.warning("No tenants found in the database")
                return []
            logger.info(f"Found {len(tenant_names)} tenants: {tenant_names}")
        else:
            tenant_names = [tenant_name]
        
        backup_files = []


        # Single tenant - use existing backup functions
        domains_file = backup_domains(sess, backup_dir, tenant_names)
        if domains_file:
            backup_files.append(domains_file)
        
        capabilities_file = backup_capabilities(sess, backup_dir, tenant_names)
        if capabilities_file:
            backup_files.append(capabilities_file)
        
        canonical_skills_file = backup_canonical_skills(sess, backup_dir, tenant_names)
        if canonical_skills_file:
            backup_files.append(canonical_skills_file)
        
        workflows_file = backup_workflows(sess, backup_dir, tenant_names)
        if workflows_file:
            backup_files.append(workflows_file)
        
        workflow_steps_file = backup_workflow_steps(sess, backup_dir, tenant_names)
        if workflow_steps_file:
            backup_files.append(workflow_steps_file)
        
        domain_cap_file = backup_domain_capability_relationships(sess, backup_dir, tenant_names)
        if domain_cap_file:
            backup_files.append(domain_cap_file)
        
        cap_skill_file = backup_capability_canonical_skill_relationships(sess, backup_dir, tenant_names)
        if cap_skill_file:
            backup_files.append(cap_skill_file)
        
        workflow_step_domain_file = backup_workflow_step_domain_relationships(sess, backup_dir, tenant_names)
        if workflow_step_domain_file:
            backup_files.append(workflow_step_domain_file)
        
        workflow_step_cap_file = backup_workflow_step_capability_relationships(sess, backup_dir, tenant_names)
        if workflow_step_cap_file:
            backup_files.append(workflow_step_cap_file)
        
        logger.info(f"Comprehensive domain backup completed. Files created: {backup_files}")
        return backup_files

if __name__ == "__main__":
    main()
