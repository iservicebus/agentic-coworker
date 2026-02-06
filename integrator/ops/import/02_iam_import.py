from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import sys
import uuid
from integrator.iam.iam_db_crud import (
    upsert_user, upsert_agent, upsert_role, insert_role_domain, 
    insert_role_user, insert_role_agent, upsert_auth_provider, 
    upsert_tenant, insert_user_agent
)
from integrator.iam.iam_keycloak_crud import get_admin_token, create_user, create_client, create_client_mapper, KC_CONFIG
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from integrator.utils.crypto_utils import decrypt
from integrator.utils.llm import Embedder
from sqlalchemy import select, delete
from integrator.iam.iam_db_model import Tenant, User, Agent, Role, RoleDomain, RoleUser, RoleAgent, UserAgent, AgentProfile
import numpy as np

logger = get_logger(__name__)


def restore_users_from_backup(sess, headers, kc_config, users_backup_file, keycloak_users_backup_file=None):
    """Restore users from backup files to database and Keycloak"""
    try:
        # Load users backup
        with open(users_backup_file, "r") as f:
            tenant_users = json.load(f)
        
        # Load Keycloak users backup if provided
        keycloak_users_data = {}
        if keycloak_users_backup_file and os.path.exists(keycloak_users_backup_file):
            with open(keycloak_users_backup_file, "r") as f:
                keycloak_users_data = json.load(f)
        
        restored_users = []
        
        # Loop through tenants
        for tenant_name, users_data in tenant_users.items():
            logger.info(f"Restoring {len(users_data)} users for tenant: {tenant_name}")
            
            # Restore each user
            for user_info in users_data:
                username = user_info.get("username")
                if not username:
                    logger.warning("Skipping user with no username.")
                    continue
                
                logger.info(f"Restoring user: {username}")
                
                # Step 1: Restore user table data
                try:
                    # Decrypt credentials if available
                    decrypted_credentials = None
                    if user_info.get("encrypted_credentials") and user_info.get("iv"):
                        try:
                            decrypted_credentials_json = decrypt(user_info["encrypted_credentials"], user_info["iv"])
                            decrypted_credentials = json.loads(decrypted_credentials_json)
                            logger.info(f"Successfully decrypted credentials for user: {username}")
                        except Exception as e:
                            logger.warning(f"Failed to decrypt credentials for user {username}: {str(e)}")
                    
                    # Prepare user data for database insertion
                    user_data_for_db = {
                        "id": user_info.get("id"),  # Preserve UUID from backup
                        "username": user_info.get("username"),
                        "email": user_info.get("email"),
                        "tenant_name": tenant_name,
                        "credentials": decrypted_credentials  # This will be re-encrypted by upsert_user
                    }
                    
                    upsert_user(sess, user_data_for_db, tenant_name)
                    logger.info(f"Successfully restored user table data for: {username}")
                except Exception as e:
                    logger.error(f"Failed to restore user table data for {username}: {str(e)}")
                    continue
                
                # Step 2: Restore Keycloak user (only if headers available)
                if headers and tenant_name and tenant_name in keycloak_users_data:
                    # Find the user in Keycloak backup data
                    keycloak_user_data = None
                    for kc_user in keycloak_users_data[tenant_name]:
                        if kc_user.get("username") == username:
                            keycloak_user_data = kc_user
                            break
                    
                    if keycloak_user_data:
                        try:
                            # Prepare user data for Keycloak creation
                            user_data_for_kc = {
                                "username": keycloak_user_data.get("username"),
                                "email": keycloak_user_data.get("email", ""),
                                "enabled": keycloak_user_data.get("enabled", True)
                            }
                            
                            # Include custom attributes (like user_type)
                            if keycloak_user_data.get("attributes"):
                                user_data_for_kc["attributes"] = keycloak_user_data["attributes"]
                            
                            # Use decrypted credentials if available
                            if decrypted_credentials:
                                user_data_for_kc["credentials"] = decrypted_credentials
                            
                            create_user(headers, tenant_name, user_data_for_kc, kc_config)
                            logger.info(f"Successfully restored Keycloak user for: {username}")
                        except Exception as e:
                            logger.error(f"Failed to restore Keycloak user for {username}: {str(e)}")
                            continue
                    else:
                        logger.warning(f"No Keycloak backup data found for user: {username}")
                else:
                    logger.warning(f"No tenant or Keycloak data available for user: {username}")
                
                restored_users.append(username)
        
        logger.info(f"Successfully restored {len(restored_users)} users: {restored_users}")
        return restored_users
        
    except Exception as e:
        logger.error(f"Failed to restore users from backup: {str(e)}")
        return []

def restore_agents_from_backup(sess, headers, kc_config, agents_backup_file, keycloak_agents_backup_file=None):
    """Restore agents from backup files to database and Keycloak (agents are Keycloak users)"""
    try:
        # Load agents backup
        with open(agents_backup_file, "r") as f:
            tenant_agents = json.load(f)
        
        # Load Keycloak agents backup if provided (agents are Keycloak users)
        keycloak_agents_data = {}
        if keycloak_agents_backup_file and os.path.exists(keycloak_agents_backup_file):
            with open(keycloak_agents_backup_file, "r") as f:
                keycloak_agents_data = json.load(f)
        
        restored_agents = []
        
        # Loop through tenants
        for tenant_name, agents_data in tenant_agents.items():
            logger.info(f"Restoring {len(agents_data)} agents for tenant: {tenant_name}")
            
            # Restore each agent
            for agent_info in agents_data:
                agent_id = agent_info.get("agent_id")
                if not agent_id:
                    logger.warning("Skipping agent with no agent_id.")
                    continue
                    
                logger.info(f"Restoring agent: {agent_id}")
                
                # Step 1: Restore agent table data
                try:
                    # Decrypt the secret if available
                    decrypted_secret = None
                    if agent_info.get("encrypted_secret") and agent_info.get("iv"):
                        try:
                            decrypted_secret = decrypt(agent_info["encrypted_secret"], agent_info["iv"])
                            logger.info(f"Successfully decrypted secret for agent: {agent_id}")
                        except Exception as e:
                            logger.warning(f"Failed to decrypt secret for agent {agent_id}: {str(e)}")
                    
                    # Prepare agent data for database insertion
                    agent_data_for_db = {
                        "agent_id": agent_info.get("agent_id"),
                        "name": agent_info.get("name"),
                        "secret": decrypted_secret,  # This will be re-encrypted by upsert_agent
                        "tenant_name": tenant_name
                    }
                    
                    upsert_agent(sess, agent_data_for_db, tenant_name)
                    logger.info(f"Successfully restored agent table data for: {agent_id}")
                except Exception as e:
                    logger.error(f"Failed to restore agent table data for {agent_id}: {str(e)}")
                    continue
                
                # Step 2: Restore Keycloak agent (agents are Keycloak users, not clients) - only if headers available
                if headers and tenant_name and tenant_name in keycloak_agents_data:
                    # Find the agent in Keycloak backup data
                    keycloak_agent_data = None
                    for kc_agent in keycloak_agents_data[tenant_name]:
                        if kc_agent.get("username") == agent_id:
                            keycloak_agent_data = kc_agent
                            break
                    
                    if keycloak_agent_data:
                        try:
                            # Prepare agent data for Keycloak creation (as a user)
                            agent_data_for_kc = {
                                "username": keycloak_agent_data.get("username"),
                                "email": keycloak_agent_data.get("email", ""),
                                "enabled": keycloak_agent_data.get("enabled", True)
                            }
                            
                            # Include custom attributes (like user_type="agent")
                            if keycloak_agent_data.get("attributes"):
                                agent_data_for_kc["attributes"] = keycloak_agent_data["attributes"]
                            
                            # Use decrypted credentials if available
                            if decrypted_secret:
                                # Try to parse as JSON first, if it fails, treat as plain password
                                try:
                                    if isinstance(decrypted_secret, str):
                                        # Try to parse as JSON
                                        try:
                                            agent_data_for_kc["credentials"] = json.loads(decrypted_secret)
                                        except json.JSONDecodeError:
                                            # If not JSON, treat as plain password and create credentials array
                                            agent_data_for_kc["credentials"] = [{
                                                "type": "password",
                                                "value": decrypted_secret,
                                                "temporary": False
                                            }]
                                    else:
                                        agent_data_for_kc["credentials"] = decrypted_secret
                                except Exception as e:
                                    logger.warning(f"Failed to process credentials for agent {agent_id}: {str(e)}")
                            
                            create_user(headers, tenant_name, agent_data_for_kc, kc_config)
                            logger.info(f"Successfully restored Keycloak agent (as user) for: {agent_id}")
                        except Exception as e:
                            logger.error(f"Failed to restore Keycloak agent for {agent_id}: {str(e)}")
                            continue
                    else:
                        logger.warning(f"No Keycloak backup data found for agent: {agent_id}")
                else:
                    logger.warning(f"No tenant or Keycloak data available for agent: {agent_id}")
                
                restored_agents.append(agent_id)
        
        logger.info(f"Successfully restored {len(restored_agents)} agents: {restored_agents}")
        return restored_agents
        
    except Exception as e:
        logger.error(f"Failed to restore agents from backup: {str(e)}")
        return []

def restore_keycloak_clients(headers, kc_config, keycloak_clients_backup_file):
    """Restore Keycloak clients (separate from agents/users)"""
    try:
        if not os.path.exists(keycloak_clients_backup_file):
            logger.warning(f"Keycloak clients backup file not found: {keycloak_clients_backup_file}")
            return []
        
        with open(keycloak_clients_backup_file, "r") as f:
            keycloak_clients_data = json.load(f)
        
        restored_clients = []
        
        # Restore clients for each tenant
        for tenant_name, clients_list in keycloak_clients_data.items():
            logger.info(f"Restoring {len(clients_list)} Keycloak clients for tenant: {tenant_name}")
            
            for client_data in clients_list:
                client_id = client_data.get("clientId")
                if not client_id:
                    logger.warning("Skipping client with no clientId")
                    continue
                
                logger.info(f"Restoring Keycloak client: {client_id}")
                
                try:
                    # Prepare client data for Keycloak creation
                    client_data_for_kc = {
                        "name": client_data.get("name", client_id),
                        "agent_id": client_id,  # Use clientId as agent_id
                        "enabled": client_data.get("enabled", True),
                        "protocol": client_data.get("protocol", "openid-connect"),
                        "publicClient": client_data.get("publicClient", False),
                        "serviceAccountsEnabled": client_data.get("serviceAccountsEnabled", False),
                        "standardFlowEnabled": client_data.get("standardFlowEnabled", True),
                        "directAccessGrantsEnabled": client_data.get("directAccessGrantsEnabled", False),
                        "clientAuthenticatorType": client_data.get("clientAuthenticatorType", "client-secret"),
                        "redirectUris": client_data.get("redirectUris", []),
                        "webOrigins": client_data.get("webOrigins", [])
                    }
                    
                    # Add secret if available
                    if client_data.get("secret"):
                        client_data_for_kc["secret"] = client_data["secret"]
                    
                    create_client(headers, tenant_name, client_data_for_kc, kc_config)
                    logger.info(f"Successfully restored Keycloak client: {client_id}")
                    
                    # Restore client mappers if they exist
                    if client_data.get("mappers"):
                        logger.info(f"Restoring {len(client_data['mappers'])} mappers for client: {client_id}")
                        for mapper in client_data["mappers"]:
                            try:
                                create_client_mapper(headers, tenant_name, client_id, mapper, kc_config)
                                logger.info(f"Successfully restored mapper '{mapper.get('name')}' for client: {client_id}")
                            except Exception as mapper_error:
                                logger.error(f"Failed to restore mapper '{mapper.get('name')}' for client {client_id}: {str(mapper_error)}")
                    
                    restored_clients.append(client_id)
                except Exception as e:
                    logger.error(f"Failed to restore Keycloak client {client_id}: {str(e)}")
                    continue
        
        logger.info(f"Successfully restored {len(restored_clients)} Keycloak clients: {restored_clients}")
        return restored_clients
        
    except Exception as e:
        logger.error(f"Failed to restore Keycloak clients from backup: {str(e)}")
        return []

def restore_agent_profiles_from_backup(sess, profiles_backup_file, clear_existing=False):
    """Restore agent profiles from backup file"""
    try:
        if not os.path.exists(profiles_backup_file):
            logger.warning(f"Agent profiles backup file not found: {profiles_backup_file}")
            return []
        
        with open(profiles_backup_file, "r") as f:
            tenant_profiles = json.load(f)
        
        if clear_existing:
            sess.execute(delete(AgentProfile))
            logger.info("Cleared existing agent profiles")
        
        restored_profiles = []
        
        # Loop through tenants
        for tenant_name, profiles_data in tenant_profiles.items():
            logger.info(f"Restoring {len(profiles_data)} agent profiles for tenant: {tenant_name}")
            
            for profile_data in profiles_data:
                agent_id = profile_data.get("agent_id")
                if not agent_id:
                    logger.warning("Skipping profile with no agent_id")
                    continue
                
                # Upsert agent profile directly (no upsert_agent_profile function exists)
                from datetime import datetime, timezone
                agent_profile = sess.execute(
                    select(AgentProfile).where(AgentProfile.agent_id == agent_id)
                ).scalar_one_or_none()
                
                if not agent_profile:
                    agent_profile = AgentProfile(
                        agent_id=agent_id,
                        tenant_name=tenant_name,
                        context=profile_data.get("context"),
                        created_at=datetime.fromisoformat(profile_data["created_at"]) if profile_data.get("created_at") else datetime.now(timezone.utc),
                        updated_at=datetime.fromisoformat(profile_data["updated_at"]) if profile_data.get("updated_at") else datetime.now(timezone.utc)
                    )
                    sess.add(agent_profile)
                    logger.info(f"Created agent profile for: {agent_id}")
                else:
                    agent_profile.context = profile_data.get("context")
                    agent_profile.updated_at = datetime.fromisoformat(profile_data["updated_at"]) if profile_data.get("updated_at") else datetime.now(timezone.utc)
                    logger.info(f"Updated agent profile for: {agent_id}")
                
                restored_profiles.append(agent_id)
        
        sess.flush()
        logger.info(f"Successfully restored {len(restored_profiles)} agent profiles")
        return restored_profiles
        
    except Exception as e:
        logger.error(f"Failed to restore agent profiles from backup: {str(e)}")
        return []

def restore_roles_and_relationships(sess, emb, backup_dir, clear_existing=False):
    """Restore roles and their relationships from backup files"""
    try:
        restored_items = []
        
        # Define backup file paths
        roles_file = os.path.join(backup_dir, "domains", "roles.json")
        role_domain_file = os.path.join(backup_dir, "domains", "role_domain.json")
        role_user_file = os.path.join(backup_dir, "domains", "role_user.json")
        user_agent_file = os.path.join(backup_dir, "domains", "user_agent.json")
        auth_providers_file = os.path.join(backup_dir, "domains", "init_auth_providers.json")
        
        if clear_existing:
            # Clear existing relationships first
            sess.execute(delete(RoleUser))
            sess.execute(delete(RoleAgent))
            sess.execute(delete(RoleDomain))
            sess.execute(delete(UserAgent))
            sess.execute(delete(Role))
            logger.info("Cleared existing roles and relationships")
        
        # Restore roles
        if os.path.exists(roles_file):
            with open(roles_file, "r") as f:
                tenant_roles = json.load(f)
            role_count = 0
            for tenant_name, roles_data in tenant_roles.items():
                logger.info(f"Restoring {len(roles_data)} roles for tenant: {tenant_name}")
                for role_data in roles_data:
                    # Convert embedding back to numpy array if present
                    if role_data.get("emb"):
                        role_data["emb"] = np.array(role_data["emb"], dtype=np.float32)
                    
                    upsert_role(sess, role_data, tenant_name, emb)
                    role_count += 1
            sess.flush()
            logger.info(f"Restored {role_count} roles")
            restored_items.append(f"{role_count} roles")
        
        # Restore role-domain relationships
        if os.path.exists(role_domain_file):
            with open(role_domain_file, "r") as f:
                tenant_role_domains = json.load(f)
            role_domain_count = 0
            for tenant_name, role_domain_data in tenant_role_domains.items():
                logger.info(f"Restoring {len(role_domain_data)} role-domain relationships for tenant: {tenant_name}")
                for entry in role_domain_data:
                    domain_name = entry["domain"]
                    for role_name in entry["roles"]:
                        insert_role_domain(sess, role_name, domain_name, tenant_name)
                        role_domain_count += 1
            sess.flush()
            logger.info(f"Restored {role_domain_count} role-domain relationships")
            restored_items.append(f"{role_domain_count} role-domain relationships")
        
        # Restore role-user and role-agent relationships
        if os.path.exists(role_user_file):
            with open(role_user_file, "r") as f:
                tenant_role_users = json.load(f)
            user_role_count = 0
            agent_role_count = 0
            for tenant_name, role_user_data in tenant_role_users.items():
                logger.info(f"Restoring role-user/agent relationships for tenant: {tenant_name}")
                for entry in role_user_data:
                    if "user" in entry:
                        username = entry["user"]
                        for role_name in entry["roles"]:
                            insert_role_user(sess, role_name, username, tenant_name)
                            user_role_count += 1
                    elif "agent" in entry:
                        agent_id = entry["agent"]
                        for role_name in entry["roles"]:
                            insert_role_agent(sess, role_name, agent_id, tenant_name)
                            agent_role_count += 1
            sess.flush()
            logger.info(f"Restored {user_role_count} user-role and {agent_role_count} agent-role relationships")
            restored_items.append(f"{user_role_count} user-role relationships")
            restored_items.append(f"{agent_role_count} agent-role relationships")
        
        # Restore user-agent relationships
        if os.path.exists(user_agent_file):
            with open(user_agent_file, "r") as f:
                tenant_user_agents = json.load(f)
            user_agent_count = 0
            for tenant_name, user_agent_data in tenant_user_agents.items():
                logger.info(f"Restoring {len(user_agent_data)} user-agent relationships for tenant: {tenant_name}")
                for entry in user_agent_data:
                    username = entry.get("username")
                    agent_id = entry.get("agent_id")
                    if username and agent_id:
                        insert_user_agent(sess, username, agent_id, tenant_name, entry.get("role"), entry.get("context", {}))
                        user_agent_count += 1
            sess.flush()
            logger.info(f"Restored {user_agent_count} user-agent relationships")
            restored_items.append(f"{user_agent_count} user-agent relationships")
        
        # Restore auth providers
        if os.path.exists(auth_providers_file):
            with open(auth_providers_file, "r") as f:
                tenant_auth_providers = json.load(f)
            auth_provider_count = 0
            for tenant_name, auth_providers_data in tenant_auth_providers.items():
                logger.info(f"Restoring {len(auth_providers_data)} auth providers for tenant: {tenant_name}")
                for provider in auth_providers_data:
                    # Decrypt the encrypted_secret and provide as clientSecret
                    if provider.get("encrypted_secret") and provider.get("iv"):
                        try:
                            decrypted_secret = decrypt(provider["encrypted_secret"], provider["iv"])
                            provider["clientSecret"] = decrypted_secret
                            logger.info(f"Successfully decrypted secret for auth provider: {provider.get('provider_id')}")
                        except Exception as e:
                            logger.warning(f"Failed to decrypt secret for auth provider {provider.get('provider_id')}: {str(e)}")
                            continue
                    
                    # Fix field name mismatch: backup has client_id, function expects clientId
                    if provider.get("client_id"):
                        provider["clientId"] = provider["client_id"]
                    
                    upsert_auth_provider(sess, provider, tenant_name)
                    auth_provider_count += 1
            sess.flush()
            logger.info(f"Restored {auth_provider_count} auth providers")
            restored_items.append(f"{auth_provider_count} auth providers")
        
        logger.info(f"Successfully restored roles and relationships: {restored_items}")
        return restored_items
        
    except Exception as e:
        logger.error(f"Failed to restore roles and relationships: {str(e)}")
        return []

def main(backup_dir=None):
    """Main import function for IAM data"""
    if len(sys.argv) != 2 and backup_dir is None:
        print("Usage: python 02_iam_import.py <backup_directory>")
        print("Example: python 02_iam_import.py ../../backup_data/20251102_195253")
        #sys.exit(1)
        backup_dir="/Users/jingnan.zhou/workspace/aintegrator/data/backup_data/20260126_142613/iam_all"
    elif len(sys.argv) == 2:  
        backup_dir = sys.argv[1]
    
    # Construct full paths if relative path provided
    if not os.path.isabs(backup_dir):
        # Get the project root directory (two levels up from ops/import/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        backup_dir = os.path.join(project_root, backup_dir)
    
    # Define backup file paths
    tenants_backup_file = os.path.join(backup_dir, "tenants_backup.json")
    users_backup_file = os.path.join(backup_dir, "users_backup.json")
    agents_backup_file = os.path.join(backup_dir, "agents_backup.json")
    profiles_backup_file = os.path.join(backup_dir, "agent_profiles_backup.json")
    keycloak_users_backup_file = os.path.join(backup_dir, "keycloak_users_backup.json")
    keycloak_agents_backup_file = os.path.join(backup_dir, "keycloak_agents_backup.json")
    keycloak_clients_backup_file = os.path.join(backup_dir, "keycloak_clients_backup.json")
    
    # Verify required backup files exist
    if not os.path.exists(users_backup_file):
        logger.error(f"Users backup file not found: {users_backup_file}")
        sys.exit(1)
    
    if not os.path.exists(agents_backup_file):
        logger.error(f"Agents backup file not found: {agents_backup_file}")
        sys.exit(1)
    
    logger.info(f"Starting IAM import from {backup_dir}")
    logger.info(f"Tenants backup file: {tenants_backup_file}")
    logger.info(f"Users backup file: {users_backup_file}")
    logger.info(f"Agents backup file: {agents_backup_file}")
    logger.info(f"Agent profiles backup file: {profiles_backup_file}")
    logger.info(f"Keycloak users backup file: {keycloak_users_backup_file}")
    logger.info(f"Keycloak agents backup file: {keycloak_agents_backup_file}")
    
    restored_tenants = []
    restored_users = []
    restored_agents = []
    restored_contexts = []
    restored_roles = []
    
    # Initialize embedder for roles
    try:
        emb = Embedder()
        logger.info("Successfully initialized embedder")
    except Exception as e:
        logger.error(f"Failed to initialize embedder: {str(e)}")
        sys.exit(1)
    
    # Get Keycloak admin token (optional - skip if Keycloak is not available)
    headers = None
    try:
        access_token = get_admin_token(KC_CONFIG)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        logger.info("Successfully obtained Keycloak admin token")
    except Exception as e:
        logger.warning(f"Failed to get Keycloak admin token: {str(e)}")
        logger.warning("Will skip Keycloak user/agent/client restoration")
    
    restored_clients = []
    
    with get_db_cm() as sess:
        
        # Restore users (with or without Keycloak)
        if headers:
            restored_users = restore_users_from_backup(
                sess, headers, KC_CONFIG, users_backup_file, keycloak_users_backup_file
            )
        else:
            # Restore only to database without Keycloak
            logger.info("Restoring users to database only (Keycloak unavailable)")
            restored_users = restore_users_from_backup(
                sess, None, KC_CONFIG, users_backup_file, None
            )
        
        # Restore agents (with or without Keycloak)
        if headers:
            restored_agents = restore_agents_from_backup(
                sess, headers, KC_CONFIG, agents_backup_file, keycloak_agents_backup_file
            )
        else:
            # Restore only to database without Keycloak
            logger.info("Restoring agents to database only (Keycloak unavailable)")
            restored_agents = restore_agents_from_backup(
                sess, None, KC_CONFIG, agents_backup_file, None
            )
        
        # Note: Agent profiles are automatically created by upsert_agent, so we skip restoring them
        # to avoid duplicate key violations. The upsert_agent function in iam_db_crud.py already
        # creates AgentProfile entries for each agent.
        restored_profiles = []
        if os.path.exists(profiles_backup_file):
            logger.info(f"Skipping agent profiles restoration - they are auto-created by upsert_agent")
        
        # Restore roles and relationships
        restored_roles = restore_roles_and_relationships(sess, emb, backup_dir)
        
        # Commit all changes
        sess.commit()
    
    # Restore Keycloak clients (separate from database, after tenants are created)
    if headers and os.path.exists(keycloak_clients_backup_file):
        restored_clients = restore_keycloak_clients(headers, KC_CONFIG, keycloak_clients_backup_file)
    elif not headers:
        logger.info("Skipping Keycloak clients restoration (Keycloak unavailable)")
    
    if restored_tenants or restored_users or restored_agents or restored_roles or restored_clients:
        logger.info(f"IAM import completed successfully.")
        logger.info(f"Restored tenants: {restored_tenants}")
        logger.info(f"Restored users: {restored_users}")
        logger.info(f"Restored agents: {restored_agents}")
        logger.info(f"Restored agent contexts: {len(restored_contexts)}")
        logger.info(f"Restored Keycloak clients: {len(restored_clients)}")
        logger.info(f"Restored roles and relationships: {restored_roles}")
    else:
        logger.error("IAM import failed or no items were restored.")
        sys.exit(1)

if __name__ == "__main__":
    main()
