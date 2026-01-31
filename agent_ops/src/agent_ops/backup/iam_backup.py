from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from datetime import datetime
from integrator.iam.iam_db_model import Agent, User, Role, RoleDomain, RoleUser, RoleAgent, UserAgent, AuthProvider, Tenant, AgentProfile
from integrator.iam.iam_keycloak_crud import get_admin_token, get_user, get_client, KC_CONFIG
import requests
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from sqlalchemy import select
import numpy as np

logger = get_logger(__name__)

def backup_users_agents(sess, kc_config, backup_dir, tenant_names):
    """Backup users and agents data with Keycloak data"""
    try:
        access_token = get_admin_token(kc_config)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        tenant_users = {}
        tenant_agents = {}
        keycloak_users = {}
        keycloak_agents = {}
        
        for tenant_name in tenant_names:
            # Get users for this tenant
            users_stmt = select(User).where(User.tenant_name == tenant_name)
            users = sess.execute(users_stmt).scalars().all()
            users_data = []
            
            logger.info(f"Backing up {len(users)} users in tenant={tenant_name}")
            for user in users:
                user_data = {
                    "id": str(user.id),
                    "username": user.username,
                    "tenant_name": user.tenant_name,
                    "email": user.email,
                    "encrypted_credentials": user.encrypted_credentials,
                    "iv": user.iv
                }
                users_data.append(user_data)
                
                # Get Keycloak user data from the user's tenant
                try:
                    realm_user = get_user(headers, tenant_name, user.username, kc_config)
                    if realm_user:
                        if tenant_name not in keycloak_users:
                            keycloak_users[tenant_name] = []
                        keycloak_users[tenant_name].append(realm_user)
                except Exception as e:
                    logger.warning(f"Failed to get Keycloak data for user {user.username} in tenant {tenant_name}: {str(e)}")
            
            tenant_users[tenant_name] = users_data
            
            # Get agents for this tenant
            agents_stmt = select(Agent).where(Agent.tenant_name == tenant_name)
            agents = sess.execute(agents_stmt).scalars().all()
            agents_data = []
            
            logger.info(f"Backing up {len(agents)} agents in tenant={tenant_name}")
            for agent in agents:
                agent_data = {
                    "id": str(agent.id),
                    "name": agent.name if agent.name else agent.agent_id,
                    "agent_id": agent.agent_id,
                    "tenant_name": agent.tenant_name,
                    "encrypted_secret": agent.encrypted_secret,
                    "iv": agent.iv
                }
                agents_data.append(agent_data)
                
                # Get Keycloak agent data
                try:
                    realm_agent = get_user(headers, tenant_name, agent.agent_id, kc_config)
                    if realm_agent:
                        if tenant_name not in keycloak_agents:
                            keycloak_agents[tenant_name] = []
                        keycloak_agents[tenant_name].append(realm_agent)
                except Exception as e:
                    logger.warning(f"Failed to get Keycloak data for agent {agent.agent_id} in tenant {tenant_name}: {str(e)}")
            
            tenant_agents[tenant_name] = agents_data
        
        # Save users backup
        users_backup_file = os.path.join(backup_dir, "users_backup.json")
        with open(users_backup_file, "w") as f:
            json.dump(tenant_users, f, indent=2)
        logger.info(f"Backed up users to {users_backup_file}")
        
        # Save agents backup
        agents_backup_file = os.path.join(backup_dir, "agents_backup.json")
        with open(agents_backup_file, "w") as f:
            json.dump(tenant_agents, f, indent=2)
        logger.info(f"Backed up agents to {agents_backup_file}")
        
        # Save Keycloak users backup
        backup_files = [users_backup_file, agents_backup_file]
        if keycloak_users:
            keycloak_users_file = os.path.join(backup_dir, "keycloak_users_backup.json")
            with open(keycloak_users_file, "w") as f:
                json.dump(keycloak_users, f, indent=2)
            logger.info(f"Backed up Keycloak users to {keycloak_users_file}")
            backup_files.append(keycloak_users_file)
        
        # Save Keycloak agents backup
        if keycloak_agents:
            keycloak_agents_file = os.path.join(backup_dir, "keycloak_agents_backup.json")
            with open(keycloak_agents_file, "w") as f:
                json.dump(keycloak_agents, f, indent=2)
            logger.info(f"Backed up Keycloak agents to {keycloak_agents_file}")
            backup_files.append(keycloak_agents_file)
        
        return backup_files
        
    except Exception as e:
        logger.error(f"Failed to backup users and agents: {str(e)}")
        return []

def backup_keycloak_clients(kc_config, backup_dir):
    """Backup Keycloak clients (separate from agents/users)"""
    try:
        access_token = get_admin_token(kc_config)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Get all tenants to iterate through realms
        from integrator.utils.db import get_db_cm
        keycloak_clients = {}
        
        with get_db_cm() as sess:
            tenants_stmt = select(Tenant)
            tenants = sess.execute(tenants_stmt).scalars().all()
            
            for tenant in tenants:
                tenant_name = tenant.name
                logger.info(f"Backing up Keycloak clients for tenant: {tenant_name}")
                
                try:
                    # Get all clients for this realm
                    clients_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients'
                    clients_resp = requests.get(clients_url, headers=headers)
                    
                    if clients_resp.status_code == 200:
                        all_clients = clients_resp.json()
                        
                        # Filter out built-in Keycloak clients (keep only custom clients)
                        custom_clients = []
                        for client in all_clients:
                            client_id = client.get("clientId", "")
                            # Skip built-in Keycloak clients
                            if not any(client_id.startswith(prefix) for prefix in ["realm-", "account", "admin-cli", "broker", "security-admin-console"]):
                                # Get mappers for this client
                                try:
                                    client_uuid = client["id"]
                                    mappers_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients/{client_uuid}/protocol-mappers/models'
                                    mappers_resp = requests.get(mappers_url, headers=headers)
                                    
                                    if mappers_resp.status_code == 200:
                                        mappers_data = mappers_resp.json()
                                        if mappers_data:
                                            client["mappers"] = mappers_data
                                            logger.info(f"Retrieved {len(mappers_data)} mappers for client {client_id}")
                                except Exception as mapper_error:
                                    logger.warning(f"Failed to get mappers for client {client_id}: {str(mapper_error)}")
                                
                                custom_clients.append(client)
                        
                        if custom_clients:
                            keycloak_clients[tenant_name] = custom_clients
                            logger.info(f"Backed up {len(custom_clients)} custom clients for tenant {tenant_name}")
                    else:
                        logger.warning(f"Failed to get clients for tenant {tenant_name}: {clients_resp.text}")
                        
                except Exception as e:
                    logger.warning(f"Failed to backup clients for tenant {tenant_name}: {str(e)}")
        
        # Save Keycloak clients backup
        if keycloak_clients:
            keycloak_clients_file = os.path.join(backup_dir, "keycloak_clients_backup.json")
            with open(keycloak_clients_file, "w") as f:
                json.dump(keycloak_clients, f, indent=2)
            logger.info(f"Backed up Keycloak clients to {keycloak_clients_file}")
            return keycloak_clients_file
        
        return None
        
    except Exception as e:
        logger.error(f"Failed to backup Keycloak clients: {str(e)}")
        return None

def backup_agent_profiles(sess, backup_dir, tenant_names):
    """Backup agent profiles"""
    try:
        tenant_profiles = {}
        for tenant_name in tenant_names:
            profiles_stmt = select(AgentProfile).where(AgentProfile.tenant_name == tenant_name)
            profiles = sess.execute(profiles_stmt).scalars().all()
            
            profiles_data = []
            for profile in profiles:
                profile_data = {
                    "agent_id": profile.agent_id,
                    "tenant_name": profile.tenant_name,
                    "context": profile.context,
                    "created_at": profile.created_at.isoformat() if profile.created_at else None,
                    "updated_at": profile.updated_at.isoformat() if profile.updated_at else None
                }
                profiles_data.append(profile_data)
            
            logger.info(f"Backing up {len(profiles_data)} agent profiles in tenant={tenant_name}")
            tenant_profiles[tenant_name] = profiles_data
        
        profiles_file = os.path.join(backup_dir, "agent_profiles_backup.json")
        with open(profiles_file, "w") as f:
            json.dump(tenant_profiles, f, indent=2)
        
        logger.info(f"Backed up agent profiles to {profiles_file}")
        return profiles_file
        
    except Exception as e:
        logger.error(f"Failed to backup agent profiles: {str(e)}")
        return None

def backup_roles_and_relationships(sess, backup_dir, tenant_names):
    """Backup roles and their relationships"""
    try:
        backup_files = []
        
        # Backup roles
        tenant_roles = {}
        for tenant_name in tenant_names:
            roles_stmt = select(Role).where(Role.tenant_name == tenant_name)
            roles = sess.execute(roles_stmt).scalars().all()
            roles_data = []
            for role in roles:
                role_dict = {
                    "id": str(role.id),
                    "name": role.name,
                    "tenant_name": role.tenant_name,
                    "type": role.type,
                    "label": role.label,
                    "description": role.description,
                    "job_roles": role.job_roles,
                    "constraints": role.constraints
                }
                
                # Convert embedding vector to list for JSON serialization
                if role.emb is not None:
                    if isinstance(role.emb, np.ndarray):
                        role_dict["emb"] = role.emb.tolist()
                    elif hasattr(role.emb, '__iter__'):
                        role_dict["emb"] = list(role.emb)
                    else:
                        role_dict["emb"] = role.emb
                else:
                    role_dict["emb"] = None
                
                roles_data.append(role_dict)
            
            logger.info(f"Backing up {len(roles_data)} roles in tenant={tenant_name}")
            tenant_roles[tenant_name] = roles_data
        
        roles_file = os.path.join(backup_dir, "roles.json")
        with open(roles_file, "w") as f:
            json.dump(tenant_roles, f, indent=2)
        backup_files.append(roles_file)
        logger.info(f"Backed up roles to {roles_file}")
        
        # Backup role-domain relationships
        tenant_role_domains = {}
        for tenant_name in tenant_names:
            role_domain_stmt = select(RoleDomain).where(RoleDomain.tenant_name == tenant_name)
            role_domains = sess.execute(role_domain_stmt).scalars().all()
            role_domain_data = {}
            for role_domain in role_domains:
                if role_domain.domain_name not in role_domain_data:
                    role_domain_data[role_domain.domain_name] = []
                role_domain_data[role_domain.domain_name].append(role_domain.role_name)
            
            # Format as expected by init
            role_domain_formatted = []
            for domain_name, role_names in role_domain_data.items():
                role_domain_formatted.append({
                    "domain": domain_name,
                    "roles": role_names
                })
            
            logger.info(f"Backing up {len(role_domain_formatted)} role-domain relationships in tenant={tenant_name}")
            tenant_role_domains[tenant_name] = role_domain_formatted
        
        role_domain_file = os.path.join(backup_dir, "role_domain.json")
        with open(role_domain_file, "w") as f:
            json.dump(tenant_role_domains, f, indent=2)
        backup_files.append(role_domain_file)
        logger.info(f"Backed up role-domain relationships to {role_domain_file}")
        
        # Backup role-user and role-agent relationships
        tenant_role_users = {}
        for tenant_name in tenant_names:
            role_user_data = []
            
            # Get user roles
            role_user_stmt = select(RoleUser).where(RoleUser.tenant_name == tenant_name)
            role_users = sess.execute(role_user_stmt).scalars().all()
            user_roles = {}
            for role_user in role_users:
                if role_user.username not in user_roles:
                    user_roles[role_user.username] = []
                user_roles[role_user.username].append(role_user.role_name)
            
            for username, roles in user_roles.items():
                role_user_data.append({
                    "user": username,
                    "roles": roles
                })
            
            # Get agent roles
            role_agent_stmt = select(RoleAgent).where(RoleAgent.tenant_name == tenant_name)
            role_agents = sess.execute(role_agent_stmt).scalars().all()
            agent_roles = {}
            for role_agent in role_agents:
                if role_agent.agent_id not in agent_roles:
                    agent_roles[role_agent.agent_id] = []
                agent_roles[role_agent.agent_id].append(role_agent.role_name)
            
            for agent_id, roles in agent_roles.items():
                role_user_data.append({
                    "agent": agent_id,
                    "roles": roles
                })
            
            logger.info(f"Backing up {len(role_user_data)} role-user/agent relationships in tenant={tenant_name}")
            tenant_role_users[tenant_name] = role_user_data
        
        role_user_file = os.path.join(backup_dir, "role_user.json")
        with open(role_user_file, "w") as f:
            json.dump(tenant_role_users, f, indent=2)
        backup_files.append(role_user_file)
        logger.info(f"Backed up role-user/agent relationships to {role_user_file}")
        
        # Backup user-agent relationships
        tenant_user_agents = {}
        for tenant_name in tenant_names:
            user_agent_stmt = select(UserAgent).where(UserAgent.tenant_name == tenant_name)
            user_agents = sess.execute(user_agent_stmt).scalars().all()
            user_agent_data = []
            for user_agent in user_agents:
                user_agent_data.append({
                    "username": user_agent.username,
                    "agent_id": user_agent.agent_id,
                    "role": user_agent.role,
                    "context": user_agent.context
                })
            
            logger.info(f"Backing up {len(user_agent_data)} user-agent relationships in tenant={tenant_name}")
            tenant_user_agents[tenant_name] = user_agent_data
        
        user_agent_file = os.path.join(backup_dir, "user_agent.json")
        with open(user_agent_file, "w") as f:
            json.dump(tenant_user_agents, f, indent=2)
        backup_files.append(user_agent_file)
        logger.info(f"Backed up user-agent relationships to {user_agent_file}")
        
        # Backup auth providers
        tenant_auth_providers = {}
        for tenant_name in tenant_names:
            auth_providers_stmt = select(AuthProvider).where(AuthProvider.tenant_name == tenant_name)
            auth_providers = sess.execute(auth_providers_stmt).scalars().all()
            auth_providers_data = []
            for provider in auth_providers:
                provider_data = {
                    "provider_id": provider.provider_id,
                    "type": provider.type,
                    "client_id": provider.client_id,
                    "tenant_name": provider.tenant_name,
                    "provider_type": provider.provider_type,
                    "provider_name": provider.provider_name,
                    "encrypted_secret": provider.encrypted_secret,
                    "is_built_in": provider.is_built_in,
                    "iv": provider.iv
                }
                if provider.options:
                    provider_data["options"] = provider.options
                auth_providers_data.append(provider_data)
            
            logger.info(f"Backing up {len(auth_providers_data)} auth providers in tenant={tenant_name}")
            tenant_auth_providers[tenant_name] = auth_providers_data
        
        auth_providers_file = os.path.join(backup_dir, "init_auth_providers.json")
        with open(auth_providers_file, "w") as f:
            json.dump(tenant_auth_providers, f, indent=2)
        backup_files.append(auth_providers_file)
        logger.info(f"Backed up auth providers to {auth_providers_file}")
        
        logger.info(f"Backed up roles and relationships to {len(backup_files)} files")
        return backup_files
        
    except Exception as e:
        logger.error(f"Failed to backup roles and relationships: {str(e)}")
        return []

def backup_all_iam(backup_dir:str, tenant_name:str=None):
    """Main backup function for IAM data"""
    
    tenant_suffix = f"_{tenant_name}" if tenant_name else "_all"
    backup_dir = os.path.join( backup_dir,  f"iam{tenant_suffix}")
    os.makedirs(backup_dir, exist_ok=True)
    
    # Create domains subdirectory for role relationships
    domains_dir = os.path.join(backup_dir, "domains")
    os.makedirs(domains_dir, exist_ok=True)
    
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
        
        logger.info(f"Starting IAM backup to {backup_dir}")
        

        # Backup users and agents with Keycloak data
        user_agent_files = backup_users_agents(sess, KC_CONFIG, backup_dir, tenant_names)
        backup_files.extend(user_agent_files)
        
        # Backup agent profiles
        profiles_file = backup_agent_profiles(sess, backup_dir, tenant_names)
        if profiles_file:
            backup_files.append(profiles_file)
        
        # Backup roles and relationships
        role_files = backup_roles_and_relationships(sess, domains_dir, tenant_names)
        backup_files.extend(role_files)
    
    # Backup Keycloak clients (separate from database)
    clients_file = backup_keycloak_clients(KC_CONFIG, backup_dir)
    if clients_file:
        backup_files.append(clients_file)
    
    logger.info(f"IAM backup completed. Files created: {backup_files}")
    return backup_files
