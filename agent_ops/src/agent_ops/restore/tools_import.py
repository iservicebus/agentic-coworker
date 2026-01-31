from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import sys
from datetime import datetime, timezone
from integrator.tools.tool_db_crud import upsert_tool, upsert_application, upsert_app_key, upsert_tool_skill, upsert_staging_service, upsert_tool_rel, get_mcp_tool_by_name_tenant
from integrator.tools.tool_etcd_crud import register_single_service
from integrator.tools.tool_db_model import Skill, CapabilitySkill, CapabilityTool, McpTool, ToolRel

from integrator.tools.tool_graph_crud import (
    sync_skills_tools_from_db_to_graph
)
from integrator.utils.graph import get_graph_driver, close_graph_driver


from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from integrator.utils.etcd import get_etcd_client
from integrator.utils.llm import LLM
from integrator.utils.llm import Embedder
from sqlalchemy import select, delete
import numpy as np

logger = get_logger(__name__)


def restore_skills_from_backup(sess, skills_backup_file, clear_existing=False):
    """Restore skills from backup file to database"""
    try:
        if not os.path.exists(skills_backup_file):
            logger.warning(f"Skills backup file not found: {skills_backup_file}")
            return []
        
        with open(skills_backup_file, "r") as f:
            tenant_skills = json.load(f)
        
        if clear_existing:
            # Clear existing skills and relationships
            sess.execute(delete(CapabilitySkill))
            sess.execute(delete(Skill))
            logger.info("Cleared existing skills and relationships")
        
        restored_skills = []
        
        # Loop through tenants
        for tenant_name, skills_data in tenant_skills.items():
            logger.info(f"Restoring {len(skills_data)} skills for tenant: {tenant_name}")
            
            for skill_data in skills_data:
                skill_name = skill_data.get("name")
                
                if not skill_name:
                    logger.warning(f"Skipping skill with missing name: {skill_data}")
                    continue
                
                # Check if skill already exists (need to check both name and tenant_name)
                existing = sess.execute(
                    select(Skill).where(
                        Skill.name == skill_name,
                        Skill.tenant_name == tenant_name
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.info(f"Skill {skill_name} already exists, skipping")
                    continue
                
                # Convert embedding back to numpy array if present
                emb_vector = None
                if skill_data.get("emb"):
                    emb_vector = np.array(skill_data["emb"], dtype=np.float32)
                
                # Parse created_at timestamp
                created_at = None
                if skill_data.get("created_at"):
                    try:
                        created_at = datetime.fromisoformat(skill_data["created_at"])
                    except ValueError:
                        created_at = None
                
                if existing:
                    # Update existing skill
                    existing.label = skill_data["label"]
                    existing.description = skill_data.get("description")
                    existing.operational_entities = skill_data.get("operational_entities", [])
                    existing.operational_procedures = skill_data.get("operational_procedures", [])
                    existing.operational_intent = skill_data.get("operational_intent", "")
                    existing.preconditions = skill_data.get("preconditions", [])
                    existing.postconditions = skill_data.get("postconditions", [])
                    existing.proficiency = skill_data.get("proficiency", "")
                    existing.emb = emb_vector
                    if created_at:
                        existing.created_at = created_at
                    logger.info(f"Updated skill: {skill_name}")
                else:
                    # Create new skill
                    skill = Skill(
                        name=skill_name,
                        tenant_name=tenant_name,
                        label=skill_data["label"],
                        description=skill_data.get("description"),
                        operational_entities=skill_data.get("operational_entities", []),
                        operational_procedures=skill_data.get("operational_procedures", []),
                        operational_intent=skill_data.get("operational_intent", ""),
                        preconditions=skill_data.get("preconditions", []),
                        postconditions=skill_data.get("postconditions", []),
                        proficiency=skill_data.get("proficiency", ""),
                        emb=emb_vector,
                        created_at=created_at or datetime.now()
                    )
                    sess.add(skill)
                    logger.info(f"Imported skill: {skill_name}")
                
                restored_skills.append(skill_name)
        
        sess.flush()
        logger.info(f"Successfully restored {len(restored_skills)} skills: {restored_skills}")
        return restored_skills
        
    except Exception as e:
        logger.error(f"Failed to restore skills from backup: {str(e)}")
        return []


def restore_mcp_tools_from_backup(sess, emb, llm, mcp_tools_backup_file):
    """Restore MCP tools from backup file to database"""
    try:
        # Load MCP tools backup
        with open(mcp_tools_backup_file, "r") as f:
            tools_data = json.load(f)
        
        restored_tools = []
        restored_services = []
        
        # Get etcd client for service registration
        etcd_client = get_etcd_client()
        
        # Restore tools for each tenant
        for tenant_name, tools_list in tools_data.items():
            logger.info(f"Restoring {len(tools_list)} tools for tenant: {tenant_name}")
            
            for tool_data in tools_list:
                tool_name = tool_data.get("name")
                
                if not tool_name:
                    logger.warning(f"Skipping tool with missing name: {tool_data}")
                    continue
                
                logger.info(f"Restoring MCP tool: {tool_name} for tenant: {tenant_name}")
                
                try:
                    # Step 1: Restore MCP tool to database
                    # The document field contains the full MCP tool definition
                    mcp_tool_document = tool_data.get("document", {})
                    mcp_tool_canonical_data = tool_data.get("canonical_data")
                    # Use upsert_tool function to restore the tool
                    update, tool = upsert_tool(etcd_client, sess, emb, llm, mcp_tool_document, tenant_name, mcp_tool_canonical_data)
                    
                    if tool:
                        logger.info(f"Successfully {'updated' if update else 'inserted'} MCP tool: {tool_name}")
                        restored_tools.append(tool_name)
                        
                        # Step 2: Restore etcd service if document contains service data
                        # The document attribute in mcp tool is the same as service data for etcd service
                        if mcp_tool_document and isinstance(mcp_tool_document, dict):
                            # Check if this looks like a service definition (has required fields)
                            if (mcp_tool_document.get("staticInput") and 
                                mcp_tool_document.get("staticInput", {}).get("url")):
                                
                                logger.info(f"Restoring etcd service for tool: {tool_name}")
                                try:
                                    # Use register_single_service to restore the service
                                    register_single_service(
                                        etcd_client=etcd_client,
                                        db=sess,
                                        tenant=tenant_name,
                                        service_id=tool.id,
                                        service_data=mcp_tool_document,
                                        routing_overwrite=True,
                                        metadata_overwrite=True
                                    )
                                    logger.info(f"Successfully restored etcd service for tool: {tool_name}")
                                    restored_services.append(tool_name)
                                except Exception as e:
                                    logger.error(f"Failed to restore etcd service for tool {tool_name}: {str(e)}")
                            else:
                                logger.info(f"Tool {tool_name} document does not contain service data, skipping etcd service restoration")
                    else:
                        logger.error(f"Failed to restore MCP tool: {tool_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to restore MCP tool {tool_name}: {str(e)}")
                    continue
        
        logger.info(f"Successfully restored {len(restored_tools)} MCP tools: {restored_tools}")
        logger.info(f"Successfully restored {len(restored_services)} etcd services: {restored_services}")
        return restored_tools, restored_services
        
    except Exception as e:
        logger.error(f"Failed to restore MCP tools from backup: {str(e)}")
        return [], []


def restore_tool_skills_from_backup(sess, tool_skills_backup_file):
    """Restore tool skill relationships from backup file"""
    try:
        if not os.path.exists(tool_skills_backup_file):
            logger.warning(f"Tool skills backup file not found: {tool_skills_backup_file}")
            return 0
        
        # Load tool skills backup
        with open(tool_skills_backup_file, "r") as f:
            tool_skills_data = json.load(f)
        
        restored_relationships = 0
        
        # Restore tool skills for each tenant
        for tenant_name, tools_dict in tool_skills_data.items():
            logger.info(f"Restoring tool skills for tenant: {tenant_name}")
            
            for tool_name, skill_entries in tools_dict.items():
                logger.info(f"Restoring {len(skill_entries)} skills for tool: {tool_name}")
                
                try:
                    # Get the tool(s) from database
                    tools = sess.execute(
                        select(McpTool).where(
                            McpTool.name == tool_name,
                            McpTool.tenant == tenant_name
                        )
                    ).scalars().all()
                    
                    if not tools:
                        logger.warning(f"No tools found with name '{tool_name}' in tenant '{tenant_name}', skipping skill relationships")
                        continue
                    elif len(tools) > 1:
                        logger.warning(f"Found {len(tools)} tools with name '{tool_name}' in tenant '{tenant_name}', restoring skills for all of them")
                    
                    # Extract skill names from entries (may include step_index and step_intent)
                    skill_names = [entry.get("skill_name") if isinstance(entry, dict) else entry for entry in skill_entries]
                    
                    # Restore skills for each matching tool
                    for tool in tools:
                        try:
                            # Use upsert_tool_skill to restore relationships with step metadata
                            for skill_entry in skill_entries:
                                if isinstance(skill_entry, dict):
                                    skill_name = skill_entry.get("skill_name")
                                    rel_json = {
                                        "step_index": skill_entry.get("step_index"),
                                        "step_intent": skill_entry.get("step_intent")
                                    }
                                else:
                                    # Plain string format (backward compatibility)
                                    skill_name = skill_entry
                                    rel_json = {"step_index": None, "step_intent": None}
                                
                                if skill_name:
                                    upsert_tool_skill(sess, skill_name, tool.id, rel_json, tenant_name)
                                    restored_relationships += 1
                            
                            logger.info(f"Successfully restored {len(skill_entries)} skills for tool: {tool_name} (ID: {tool.id})")
                        except Exception as e:
                            logger.error(f"Failed to restore skills for tool {tool_name} (ID: {tool.id}): {str(e)}")
                            continue
                        
                except Exception as e:
                    logger.error(f"Failed to restore skills for tool {tool_name}: {str(e)}")
                    continue
        
        logger.info(f"Successfully restored {restored_relationships} tool-skill relationships")
        return restored_relationships
        
    except Exception as e:
        logger.error(f"Failed to restore tool skills from backup: {str(e)}")
        return 0


def restore_capability_skill_relationships(sess, cap_skill_backup_file, clear_existing=False):
    """Restore capability-skill relationships from backup file"""
    try:
        if not os.path.exists(cap_skill_backup_file):
            logger.warning(f"Capability-skill relationships backup file not found: {cap_skill_backup_file}")
            return 0
        
        with open(cap_skill_backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(CapabilitySkill))
            logger.info("Cleared existing capability-skill relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Restoring {len(relationships_data)} capability-skill relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                # Check if relationship already exists
                existing = sess.execute(
                    select(CapabilitySkill).where(
                        (CapabilitySkill.capability_name == rel_data["capability_name"]) &
                        (CapabilitySkill.skill_name == rel_data["skill_name"])
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {rel_data['capability_name']} -> {rel_data['skill_name']} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = CapabilitySkill(
                        capability_name=rel_data["capability_name"],
                        skill_name=rel_data["skill_name"],
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully restored {imported_count} capability-skill relationships")
        return imported_count
        
    except Exception as e:
        logger.error(f"Failed to restore capability-skill relationships: {str(e)}")
        return 0


def restore_capability_tool_relationships(sess, cap_tool_backup_file, clear_existing=False):
    """Restore capability-tool relationships from backup file"""
    try:
        if not os.path.exists(cap_tool_backup_file):
            logger.warning(f"Capability-tool relationships backup file not found: {cap_tool_backup_file}")
            return 0
        
        with open(cap_tool_backup_file, "r") as f:
            tenant_relationships = json.load(f)
        
        if clear_existing:
            sess.execute(delete(CapabilityTool))
            logger.info("Cleared existing capability-tool relationships")
        
        imported_count = 0
        # Loop through tenants
        for tenant_name, relationships_data in tenant_relationships.items():
            logger.info(f"Restoring {len(relationships_data)} capability-tool relationships for tenant: {tenant_name}")
            
            for rel_data in relationships_data:
                capability_name = rel_data.get("capability_name")
                tool_name = rel_data.get("tool_name")
                tool_tenant = rel_data.get("tool_tenant", tenant_name)
                
                if not capability_name or not tool_name:
                    logger.warning(f"Skipping relationship with missing fields: {rel_data}")
                    continue
                
                # Get the tool from database
                tool = sess.execute(
                    select(McpTool).where(
                        McpTool.name == tool_name,
                        McpTool.tenant == tool_tenant
                    )
                ).scalar_one_or_none()
                
                if not tool:
                    logger.warning(f"Tool '{tool_name}' in tenant '{tool_tenant}' not found, skipping relationship")
                    continue
                
                # Check if relationship already exists
                existing = sess.execute(
                    select(CapabilityTool).where(
                        (CapabilityTool.capability_name == capability_name) &
                        (CapabilityTool.tool_id == tool.id)
                    )
                ).scalar_one_or_none()
                
                if existing and not clear_existing:
                    logger.debug(f"Relationship {capability_name} -> {tool_name} already exists, skipping")
                    continue
                
                if not existing:
                    # Create new relationship
                    relationship = CapabilityTool(
                        capability_name=capability_name,
                        tool_id=tool.id,
                        tenant_name=tenant_name
                    )
                    sess.add(relationship)
                    imported_count += 1
        
        sess.flush()
        logger.info(f"Successfully restored {imported_count} capability-tool relationships")
        return imported_count
        
    except Exception as e:
        logger.error(f"Failed to restore capability-tool relationships: {str(e)}")
        return 0


def restore_applications_from_backup(sess, applications_backup_file, app_keys_backup_file=None):
    """Restore applications and app keys from backup files"""
    try:
        restored_apps = []
        restored_keys = []
        
        # Load applications backup
        with open(applications_backup_file, "r") as f:
            tenant_apps = json.load(f)
        
        # Restore applications - loop through tenants
        for tenant_name, apps_data in tenant_apps.items():
            logger.info(f"Restoring {len(apps_data)} applications for tenant: {tenant_name}")
            
            for app_data in apps_data:
                app_name = app_data.get("app_name")
                
                if not app_name:
                    logger.warning(f"Skipping application with missing app_name: {app_data}")
                    continue
                
                logger.info(f"Restoring application: {app_name}")
                
                try:
                    upsert_application(sess, app_data, tenant_name)
                    restored_apps.append(app_name)
                    logger.info(f"Successfully restored application: {app_name}")
                except Exception as e:
                    logger.error(f"Failed to restore application {app_name}: {str(e)}")
                    continue
        sess.flush()
        
        # Restore app keys if backup file provided
        if app_keys_backup_file and os.path.exists(app_keys_backup_file):
            with open(app_keys_backup_file, "r") as f:
                tenant_keys = json.load(f)
            
            # Loop through tenants
            for tenant_name, keys_data in tenant_keys.items():
                logger.info(f"Restoring {len(keys_data)} app keys for tenant: {tenant_name}")
                
                for key_data in keys_data:
                    app_name = key_data.get("app_name")
                    agent_id = key_data.get("agent_id")
                    
                    if not app_name or not agent_id:
                        logger.warning(f"Skipping app key with missing required fields: {key_data}")
                        continue
                    
                    logger.info(f"Restoring app key for: {app_name}")
                    
                    try:
                        upsert_app_key(sess, key_data, app_name, agent_id, tenant_name)
                        restored_keys.append(f"{app_name}:{tenant_name}")
                        logger.info(f"Successfully restored app key for: {app_name}")
                    except Exception as e:
                        logger.error(f"Failed to restore app key for {app_name}: {str(e)}")
                        continue
        
        logger.info(f"Successfully restored {len(restored_apps)} applications: {restored_apps}")
        logger.info(f"Successfully restored {len(restored_keys)} app keys: {restored_keys}")
        return restored_apps, restored_keys
        
    except Exception as e:
        logger.error(f"Failed to restore applications from backup: {str(e)}")
        return [], []


def restore_tool_relationships_from_backup(sess, tool_rel_backup_file, clear_existing=False):
    """Restore tool relationships from backup file"""
    try:
        if not os.path.exists(tool_rel_backup_file):
            logger.warning(f"Tool relationships backup file not found: {tool_rel_backup_file}")
            return 0
        
        with open(tool_rel_backup_file, "r") as f:
            tool_rels_data = json.load(f)
        
        if clear_existing:
            sess.execute(delete(ToolRel))
            logger.info("Cleared existing tool relationships")
        
        restored_relationships = 0
        
        # Restore tool relationships for each tenant
        for tenant_name, rels_list in tool_rels_data.items():
            logger.info(f"Restoring {len(rels_list)} tool relationships for tenant: {tenant_name}")
            
            for rel_data in rels_list:
                source_tool_name = rel_data.get("source_tool_name")
                target_tool_name = rel_data.get("target_tool_name")
                composite_intent = rel_data.get("composite_intent")
                field_mapping = rel_data.get("field_mapping")
                
                if not source_tool_name or not target_tool_name:
                    logger.warning(f"Skipping relationship with missing tool names: {rel_data}")
                    continue
                
                try:
                    # Prepare relation data for upsert_tool_rel
                    relation_data = {
                        "tool_flow": [source_tool_name, target_tool_name],
                        "composite_intent": composite_intent,
                        "field_mapping": field_mapping
                    }
                    
                    # Use upsert_tool_rel to restore the relationship
                    upsert_tool_rel(sess, tenant_name, relation_data)
                    restored_relationships += 1
                    logger.info(f"Successfully restored tool relationship: {source_tool_name} -> {target_tool_name}")
                    
                except Exception as e:
                    logger.error(f"Failed to restore tool relationship {source_tool_name} -> {target_tool_name}: {str(e)}")
                    continue
        
        sess.flush()
        logger.info(f"Successfully restored {restored_relationships} tool relationships")
        return restored_relationships
        
    except Exception as e:
        logger.error(f"Failed to restore tool relationships from backup: {str(e)}")
        return 0


def restore_staging_services_from_backup(sess, staging_services_backup_file):
    """Restore staging services from backup file"""
    try:
        # Load staging services backup
        with open(staging_services_backup_file, "r") as f:
            staging_data = json.load(f)
        
        restored_staging = []
        
        # Restore staging services for each tenant
        for tenant_name, services_list in staging_data.items():
            logger.info(f"Restoring {len(services_list)} staging services for tenant: {tenant_name}")
            
            for service_data in services_list:
                service_name = service_data.get("name")
                
                if not service_name:
                    logger.warning(f"Skipping staging service with missing name: {service_data}")
                    continue
                
                logger.info(f"Restoring staging service: {service_name}")
                
                try:
                    # Use upsert_staging_service to restore the staging service
                    staging_service = upsert_staging_service(
                        sess=sess,
                        staging_service_data=service_data.get("service_data", service_data),
                        tenant=tenant_name,
                        username="system"  # Default username for restoration
                    )
                    
                    if staging_service:
                        restored_staging.append(service_name)
                        logger.info(f"Successfully restored staging service: {service_name}")
                    else:
                        logger.error(f"Failed to restore staging service: {service_name}")
                        
                except Exception as e:
                    logger.error(f"Failed to restore staging service {service_name}: {str(e)}")
                    continue
        
        logger.info(f"Successfully restored {len(restored_staging)} staging services: {restored_staging}")
        return restored_staging
        
    except Exception as e:
        logger.error(f"Failed to restore staging services from backup: {str(e)}")
        return []

def load_graph(sess):
    driver = get_graph_driver()
    with driver.session() as gsess:  
        #cleanup_all_domains_graph(gsess)
        #cleanup_all_workflow_graph(gsess)
        sync_skills_tools_from_db_to_graph(sess, gsess)


    close_graph_driver()
    print("domain and workflow graph are loaded.")


def restore_all_tools(backup_dir:str, tenant_name:str=None):

    tenant_suffix = f"_{tenant_name}" if tenant_name else "_all"
    backup_dir = os.path.join(backup_dir, f"tools{tenant_suffix}")

 # Construct full paths if relative path provided
    if not os.path.isabs(backup_dir):

        logger.error(f"Backup directory not found: {backup_dir}")
        return False
    
    # Define backup file paths
    skills_backup_file = os.path.join(backup_dir, "skills.json")
    mcp_tools_backup_file = os.path.join(backup_dir, "mcp_tools.json")
    tool_skills_backup_file = os.path.join(backup_dir, "tool_skills.json")
    tool_rel_backup_file = os.path.join(backup_dir, "tool_relationships.json")
    capability_skill_backup_file = os.path.join(backup_dir, "capability_skill.json")
    capability_tool_backup_file = os.path.join(backup_dir, "capability_tool.json")
    applications_backup_file = os.path.join(backup_dir, "applications_backup.json")
    app_keys_backup_file = os.path.join(backup_dir, "app_keys.json")
    staging_services_backup_file = os.path.join(backup_dir, "staging_services.json")
    
    # Verify required backup files exist
    if not os.path.exists(mcp_tools_backup_file):
        logger.error(f"MCP tools backup file not found: {mcp_tools_backup_file}")
        sys.exit(1)
    
    logger.info(f"Starting tools import from {backup_dir}")
    logger.info(f"Skills backup file: {skills_backup_file}")
    logger.info(f"MCP tools backup file: {mcp_tools_backup_file}")
    logger.info(f"Tool skills backup file: {tool_skills_backup_file}")
    logger.info(f"Tool relationships backup file: {tool_rel_backup_file}")
    logger.info(f"Capability-skill backup file: {capability_skill_backup_file}")
    logger.info(f"Capability-tool backup file: {capability_tool_backup_file}")
    logger.info(f"Applications backup file: {applications_backup_file}")
    logger.info(f"App keys backup file: {app_keys_backup_file}")
    logger.info(f"Staging services backup file: {staging_services_backup_file}")
    
    restored_skills = []
    restored_tools = []
    restored_services = []
    restored_tool_skills = 0
    restored_tool_rels = 0
    restored_cap_skills = 0
    restored_cap_tools = 0
    restored_apps = []
    restored_keys = []
    restored_staging = []
    
    # Initialize LLM and embedding models
    try:
        llm = LLM()
        emb = Embedder()
        logger.info("Successfully initialized LLM and embedding models")
    except Exception as e:
        logger.error(f"Failed to initialize LLM and embedding models: {str(e)}")
        sys.exit(1)
    
    with get_db_cm() as sess:
        # Restore skills first (they are referenced by tool_skills and capability_skill)
        if os.path.exists(skills_backup_file):
            restored_skills = restore_skills_from_backup(sess, skills_backup_file)
        sess.flush()
        
        # Restore staging services if backup file exists
        if os.path.exists(staging_services_backup_file):
            restored_staging = restore_staging_services_from_backup(
                sess, staging_services_backup_file
            )
        sess.flush()

        # Restore MCP tools and etcd services
        restored_tools, restored_services = restore_mcp_tools_from_backup(
            sess, emb, llm, mcp_tools_backup_file
        )
        sess.flush()
        
        # Restore tool skills if backup file exists
        if os.path.exists(tool_skills_backup_file):
            restored_tool_skills = restore_tool_skills_from_backup(
                sess, tool_skills_backup_file
            )
        sess.flush()
        
        # Restore tool relationships if backup file exists
        if os.path.exists(tool_rel_backup_file):
            restored_tool_rels = restore_tool_relationships_from_backup(
                sess, tool_rel_backup_file
            )
        sess.flush()
        
        # Restore capability-skill relationships if backup file exists
        if os.path.exists(capability_skill_backup_file):
            restored_cap_skills = restore_capability_skill_relationships(
                sess, capability_skill_backup_file
            )
        sess.flush()
        
        # Restore capability-tool relationships if backup file exists
        if os.path.exists(capability_tool_backup_file):
            restored_cap_tools = restore_capability_tool_relationships(
                sess, capability_tool_backup_file
            )
        sess.flush()
        
        # Restore applications if backup file exists
        if os.path.exists(applications_backup_file):
            restored_apps, restored_keys = restore_applications_from_backup(
                sess, applications_backup_file, app_keys_backup_file
            )
 
        sess.flush()
        # Commit all changes
        sess.commit()

        load_graph(sess)
    
    # Summary
    total_restored = (len(restored_skills) + len(restored_tools) + len(restored_services) + 
                     restored_tool_skills + restored_tool_rels + restored_cap_skills + restored_cap_tools +
                     len(restored_apps) + len(restored_keys) + len(restored_staging))
    
    if total_restored > 0:
        logger.info(f"Tools import completed successfully.")
        logger.info(f"Restored skills: {len(restored_skills)} - {restored_skills}")
        logger.info(f"Restored MCP tools: {len(restored_tools)} - {restored_tools}")
        logger.info(f"Restored etcd services: {len(restored_services)} - {restored_services}")
        logger.info(f"Restored tool-skill relationships: {restored_tool_skills}")
        logger.info(f"Restored tool relationships: {restored_tool_rels}")
        logger.info(f"Restored capability-skill relationships: {restored_cap_skills}")
        logger.info(f"Restored capability-tool relationships: {restored_cap_tools}")
        logger.info(f"Restored applications: {len(restored_apps)} - {restored_apps}")
        logger.info(f"Restored app keys: {len(restored_keys)} - {restored_keys}")
        logger.info(f"Restored staging services: {len(restored_staging)} - {restored_staging}")
    else:
        logger.error("Tools import failed or no items were restored.")
        sys.exit(1)

