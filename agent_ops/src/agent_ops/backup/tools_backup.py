from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
from datetime import datetime
from integrator.tools.tool_db_model import Application, AppKey, StagingService, McpTool, ToolSkill, CapabilitySkill, CapabilityTool, Skill, ToolRel, ApplicationMcpTool
from integrator.iam.iam_db_model import Tenant
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from integrator.utils.etcd import get_etcd_client
from integrator.utils.host import generate_host_id
from sqlalchemy import select
import numpy as np

logger = get_logger(__name__)

def backup_staging_tables(sess, backup_dir, tenant_names):
    """Backup tools and services from database in init format"""
    try:
        stagings_by_tenant = {}
        for tenant_name in tenant_names:
            staging_stmt = select(StagingService).where(StagingService.tenant == tenant_name)
            stagings = sess.execute(staging_stmt).scalars().all()
            
            stagings_data = []
            for staging in stagings:
                service_data = {
                    "name": staging.name,
                    "tenant": staging.tenant,
                    "service_data": staging.service_data
                }
                stagings_data.append(service_data)
            
            logger.info(f"Backing up {len(stagings_data)} staging services in tenant={tenant_name}")
            stagings_by_tenant[tenant_name] = stagings_data
        
        # Save in initial_services.json format
        staging_backup = os.path.join(backup_dir, "staging_services.json")
        with open(staging_backup, "w") as f:
            json.dump(stagings_by_tenant, f, indent=2)
        
        logger.info(f"Backed up staging services to {staging_backup}")
        return staging_backup
        
    except Exception as e:
        logger.error(f"Failed to backup staging database: {str(e)}")
        return None


def backup_tools_database(sess, backup_dir, tenant_names):
    """Backup tools and services from database in init format"""
    try:
        tools_by_tenant = {}
        for tenant_name in tenant_names:
            tools_stmt = select(McpTool).where(McpTool.tenant == tenant_name)
            tools = sess.execute(tools_stmt).scalars().all()
            
            tools_data = []
            for tool in tools:
                service_data = {
                    "name": tool.name,
                    "description": tool.description,
                    "document": tool.document,
                    "canonical_data": tool.canonical_data,
                    "tenant": tool.tenant,
                    "tool_type": tool.tool_type
                }
                tools_data.append(service_data)
            
            logger.info(f"Backing up {len(tools_data)} MCP tools in tenant={tenant_name}")
            tools_by_tenant[tenant_name] = tools_data
        
        # Save in initial_services.json format
        mcp_tool_backup = os.path.join(backup_dir, "mcp_tools.json")
        with open(mcp_tool_backup, "w") as f:
            json.dump(tools_by_tenant, f, indent=2)
        
        logger.info(f"Backed up MCP tools to {mcp_tool_backup}")
        return mcp_tool_backup
        
    except Exception as e:
        logger.error(f"Failed to backup tools database: {str(e)}")
        return None

def backup_skills(sess, backup_dir, tenant_names):
    """Backup all skills with complete metadata"""
    try:
        tenant_skills = {}
        for tenant_name in tenant_names:
            stmt = select(Skill).where(Skill.tenant_name == tenant_name)
            skills = sess.execute(stmt).scalars().all()
            
            skills_data = []
            for skill in skills:
                skill_dict = {
                    "name": skill.name,
                    "tenant_name": skill.tenant_name,
                    "label": skill.label,
                    "description": skill.description,
                    "operational_entities": skill.operational_entities if skill.operational_entities else [],
                    "operational_procedures": skill.operational_procedures if skill.operational_procedures else [],
                    "operational_intent": skill.operational_intent if skill.operational_intent else "",
                    "preconditions": skill.preconditions if skill.preconditions else [],
                    "postconditions": skill.postconditions if skill.postconditions else [],
                    "proficiency": skill.proficiency if skill.proficiency else "",
                    "created_at": skill.created_at.isoformat() if skill.created_at else None
                }
                
                # Convert embedding vector to list for JSON serialization
                if skill.emb is not None:
                    if isinstance(skill.emb, np.ndarray):
                        skill_dict["emb"] = skill.emb.tolist()
                    elif hasattr(skill.emb, '__iter__'):
                        skill_dict["emb"] = list(skill.emb)
                    else:
                        skill_dict["emb"] = skill.emb
                else:
                    skill_dict["emb"] = None
                    
                skills_data.append(skill_dict)
            
            logger.info(f"Backing up {len(skills_data)} skills in tenant={tenant_name}")
            tenant_skills[tenant_name] = skills_data
        
        backup_file = os.path.join(backup_dir, "skills.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_skills, f, indent=2)
        
        logger.info(f"Backed up skills to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup skills: {str(e)}")
        return None

def backup_tool_skills(sess, backup_dir, tenant_names):
    """Backup tool skill relationships with joined data from ToolSkill and McpTool tables"""
    try:
        tool_skills_by_tenant = {}
        
        for tenant_name in tenant_names:
            # Join ToolSkill with McpTool to get skill_name, tenant_name, and tool_name
            tool_skills_stmt = select(
                ToolSkill.skill_name,
                ToolSkill.step_index,
                ToolSkill.step_intent,
                McpTool.tenant,
                McpTool.name.label('tool_name')
            ).join(McpTool, ToolSkill.tool_id == McpTool.id).where(McpTool.tenant == tenant_name)
            
            tool_skills = sess.execute(tool_skills_stmt).all()
            
            # Group by tool for better organization
            tools_dict = {}
            for tool_skill in tool_skills:
                tool_name = tool_skill.tool_name
                
                if tool_name not in tools_dict:
                    tools_dict[tool_name] = []
                
                skill_entry = {"skill_name": tool_skill.skill_name}
                if tool_skill.step_index is not None:
                    skill_entry["step_index"] = tool_skill.step_index
                if tool_skill.step_intent is not None:
                    skill_entry["step_intent"] = tool_skill.step_intent
                
                tools_dict[tool_name].append(skill_entry)
            
            logger.info(f"Backing up {len(tool_skills)} tool-skill relationships in tenant={tenant_name}")
            tool_skills_by_tenant[tenant_name] = tools_dict
        
        # Save tool skills backup
        tool_skills_file = os.path.join(backup_dir, "tool_skills.json")
        with open(tool_skills_file, "w") as f:
            json.dump(tool_skills_by_tenant, f, indent=2)
        
        logger.info(f"Backed up tool-skill relationships to {tool_skills_file}")
        return tool_skills_file
        
    except Exception as e:
        logger.error(f"Failed to backup tool skills: {str(e)}")
        return None

def backup_capability_skill_relationships(sess, backup_dir, tenant_names):
    """Backup capability-skill relationships"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            stmt = select(CapabilitySkill).where(CapabilitySkill.tenant_name == tenant_name)
            relationships = sess.execute(stmt).scalars().all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "capability_name": rel.capability_name,
                    "skill_name": rel.skill_name,
                    "tenant_name": rel.tenant_name
                })
            
            logger.info(f"Backing up {len(relationships_data)} capability-skill relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "capability_skill.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up capability-skill relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup capability-skill relationships: {str(e)}")
        return None

def backup_capability_tool_relationships(sess, backup_dir, tenant_names):
    """Backup capability-tool relationships with joined data"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            # Join CapabilityTool with McpTool to get capability_name, tool_name, and tenant
            cap_tool_stmt = select(
                CapabilityTool.capability_name,
                CapabilityTool.tenant_name,
                McpTool.name.label('tool_name'),
                McpTool.tenant
            ).join(McpTool, CapabilityTool.tool_id == McpTool.id).where(CapabilityTool.tenant_name == tenant_name)
            
            relationships = sess.execute(cap_tool_stmt).all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "capability_name": rel.capability_name,
                    "tenant_name": rel.tenant_name,
                    "tool_name": rel.tool_name,
                    "tool_tenant": rel.tenant
                })
            
            logger.info(f"Backing up {len(relationships_data)} capability-tool relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "capability_tool.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up capability-tool relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup capability-tool relationships: {str(e)}")
        return None


def backup_tool_relationships(sess, backup_dir, tenant_names):
    """Backup tool relationships (tool_rel table) with joined data"""
    try:
        tool_rels_by_tenant = {}
        
        for tenant_name in tenant_names:
            tool_rel_stmt = select(
                ToolRel.source_tool_id,
                ToolRel.target_tool_id,
                ToolRel.composite_intent,
                ToolRel.field_mapping,
                ToolRel.tenant_name
            ).where(ToolRel.tenant_name == tenant_name)
            
            tool_rels = sess.execute(tool_rel_stmt).all()
            
            tool_rels_data = []
            for tool_rel in tool_rels:
                # Get source and target tools
                source_tool = sess.execute(
                    select(McpTool).where(McpTool.id == tool_rel.source_tool_id)
                ).scalar_one_or_none()
                
                target_tool = sess.execute(
                    select(McpTool).where(McpTool.id == tool_rel.target_tool_id)
                ).scalar_one_or_none()
                
                if not source_tool or not target_tool:
                    logger.warning(f"Skipping tool relationship with missing source or target tool")
                    continue
                
                rel_data = {
                    "source_tool_name": source_tool.name,
                    "target_tool_name": target_tool.name,
                    "composite_intent": tool_rel.composite_intent,
                    "field_mapping": tool_rel.field_mapping
                }
                
                tool_rels_data.append(rel_data)
            
            logger.info(f"Backing up {len(tool_rels_data)} tool relationships in tenant={tenant_name}")
            tool_rels_by_tenant[tenant_name] = tool_rels_data
        
        # Save tool relationships backup
        tool_rel_file = os.path.join(backup_dir, "tool_relationships.json")
        with open(tool_rel_file, "w") as f:
            json.dump(tool_rels_by_tenant, f, indent=2)
        
        logger.info(f"Backed up tool relationships to {tool_rel_file}")
        return tool_rel_file
        
    except Exception as e:
        logger.error(f"Failed to backup tool relationships: {str(e)}")
        return None


def backup_applications_and_keys(sess, backup_dir, tenant_names):
    """Backup applications and their API keys"""
    try:
        backup_files = []
        
        # Backup applications
        tenant_applications = {}
        for tenant_name in tenant_names:
            apps_stmt = select(Application).where(Application.tenant_name == tenant_name)
            applications = sess.execute(apps_stmt).scalars().all()
            
            applications_data = []
            for app in applications:
                app_data = {
                    "app_name": app.app_name,
                    "tenant_name": app.tenant_name
                }
                if app.app_note:
                    app_data["app_note"] = app.app_note
                
                applications_data.append(app_data)
            
            logger.info(f"Backing up {len(applications_data)} applications in tenant={tenant_name}")
            tenant_applications[tenant_name] = applications_data
        
        apps_file = os.path.join(backup_dir, "applications_backup.json")
        with open(apps_file, "w") as f:
            json.dump(tenant_applications, f, indent=2)
        backup_files.append(apps_file)
        logger.info(f"Backed up applications to {apps_file}")
        
        # Backup app keys
        tenant_app_keys = {}
        for tenant_name in tenant_names:
            keys_stmt = select(AppKey).where(AppKey.tenant_name == tenant_name)
            app_keys = sess.execute(keys_stmt).scalars().all()
            
            app_keys_data = []
            for key in app_keys:
                key_data = {
                    "app_name": key.app_name,
                    "agent_id": key.agent_id,
                    "tenant_name": key.tenant_name
                }
                if key.secrets:
                    key_data["secrets"] = key.secrets
                
                app_keys_data.append(key_data)
            
            logger.info(f"Backing up {len(app_keys_data)} app keys in tenant={tenant_name}")
            tenant_app_keys[tenant_name] = app_keys_data
        
        keys_file = os.path.join(backup_dir, "app_keys.json")
        with open(keys_file, "w") as f:
            json.dump(tenant_app_keys, f, indent=2)
        backup_files.append(keys_file)
        logger.info(f"Backed up app keys to {keys_file}")
        
        return backup_files
        
    except Exception as e:
        logger.error(f"Failed to backup applications and keys: {str(e)}")
        return []


def backup_application_mcp_tool_relationships(sess, backup_dir, tenant_names):
    """Backup application-MCP tool relationships with joined data"""
    try:
        tenant_relationships = {}
        for tenant_name in tenant_names:
            # Join ApplicationMcpTool with McpTool to get app_name, tool_name, and tenant
            app_tool_stmt = select(
                ApplicationMcpTool.app_name,
                ApplicationMcpTool.tenant_name,
                McpTool.name.label('tool_name'),
                McpTool.tenant
            ).join(McpTool, ApplicationMcpTool.tool_id == McpTool.id).where(ApplicationMcpTool.tenant_name == tenant_name)
            
            relationships = sess.execute(app_tool_stmt).all()
            
            relationships_data = []
            for rel in relationships:
                relationships_data.append({
                    "app_name": rel.app_name,
                    "tenant_name": rel.tenant_name,
                    "tool_name": rel.tool_name,
                    "tool_tenant": rel.tenant
                })
            
            logger.info(f"Backing up {len(relationships_data)} application-tool relationships in tenant={tenant_name}")
            tenant_relationships[tenant_name] = relationships_data
        
        backup_file = os.path.join(backup_dir, "application_mcp_tool.json")
        with open(backup_file, "w") as f:
            json.dump(tenant_relationships, f, indent=2)
        
        logger.info(f"Backed up application-tool relationships to {backup_file}")
        return backup_file
        
    except Exception as e:
        logger.error(f"Failed to backup application-tool relationships: {str(e)}")
        return None


def backup_all_tools(backup_dir: str, tenant_name: str=None):
    """Main backup function for tools and services data"""

    tenant_suffix = f"_{tenant_name}" if tenant_name else "_all"
    backup_dir = os.path.join(backup_dir, f"tools{tenant_suffix}")
    os.makedirs(backup_dir, exist_ok=True)
    
    backup_files = []
    
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
        
        logger.info(f"Starting tools and services backup to {backup_dir}")

        # Backup staging tables
        staging_table = backup_staging_tables(sess, backup_dir, tenant_names)
        if staging_table:
            backup_files.append(staging_table)

        # Backup tools database
        tools_file = backup_tools_database(sess, backup_dir, tenant_names)
        if tools_file:
            backup_files.append(tools_file)
        
        # Backup skills
        skills_file = backup_skills(sess, backup_dir, tenant_names)
        if skills_file:
            backup_files.append(skills_file)
        
        # Backup tool skill relationships
        tool_skills_file = backup_tool_skills(sess, backup_dir, tenant_names)
        if tool_skills_file:
            backup_files.append(tool_skills_file)
        
        # Backup capability-skill relationships
        cap_skill_file = backup_capability_skill_relationships(sess, backup_dir, tenant_names)
        if cap_skill_file:
            backup_files.append(cap_skill_file)
        
        # Backup capability-tool relationships
        cap_tool_file = backup_capability_tool_relationships(sess, backup_dir, tenant_names)
        if cap_tool_file:
            backup_files.append(cap_tool_file)
        
        # Backup tool relationships
        tool_rel_file = backup_tool_relationships(sess, backup_dir, tenant_names)
        if tool_rel_file:
            backup_files.append(tool_rel_file)
        
        # Backup applications and keys
        app_files = backup_applications_and_keys(sess, backup_dir, tenant_names)
        backup_files.extend(app_files)
        
        # Backup application-tool relationships
        app_tool_file = backup_application_mcp_tool_relationships(sess, backup_dir, tenant_names)
        if app_tool_file:
            backup_files.append(app_tool_file)
        
    
    logger.info(f"Tools and services backup completed. Files created: {backup_files}")
    return backup_files
