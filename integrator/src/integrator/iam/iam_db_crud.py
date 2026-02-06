import logging
import os
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import select, func
from typing import List, Optional
from integrator.iam.iam_db_model import Tenant, Agent, User, AuthProvider, Role, RoleDomain, AgentProfile, UserAgent, RoleAgent
from integrator.tools.tool_db_crud import upsert_application, upsert_app_key
from integrator.utils.db import get_db_cm
from integrator.utils.crypto_utils import encrypt
from integrator.utils.host import generate_host_id

logger = logging.getLogger(__name__)

def upsert_tenant(sess, tenant_data):
    tenant = sess.execute(
        select(Tenant).where(Tenant.name == tenant_data["name"])
    ).scalar_one_or_none()
    if not tenant:
        tenant = Tenant(
            name=tenant_data["name"],
            description=tenant_data.get("description", "")
        )
        sess.add(tenant)
        logger.info(f"Inserted new tenant. name: {tenant.name}")
    else:
        tenant.description = tenant_data.get("description", "")
        logger.info(f"Updated existing tenant, name: {tenant.name}")

def upsert_agent(sess, agent_data, tenant_name):
    from integrator.iam.iam_db_model import AgentProfile
    
    agent_id = agent_data.get("name") or agent_data.get("agent_id") or agent_data.get("username")
    if not agent_id:
        logger.warning("Skipping agent with no name or agent_id.")
        return
    secret = agent_data.get("secret")
    if not secret and agent_data.get("credentials", []):
        secret=agent_data.get("credentials", [])[0].get("value")

      
    encrypted_secret = None
    iv = None
    if secret:
        try:
            encrypted_info = encrypt(secret)
            encrypted_secret = encrypted_info["encryptedData"]
            iv = encrypted_info["iv"]
        except Exception as e:
            logger.warning(f"Could not encrypt secret for agent '{agent_id}': {e}")

    agent = sess.execute(
        select(Agent).where(
            (Agent.agent_id == agent_id) &
            (Agent.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    is_new_agent = agent is None
    
    if not agent:
        agent = Agent(
            agent_id=agent_id,
            tenant_name=tenant_name,
            name=agent_data.get("name", agent_id),
            encrypted_secret=encrypted_secret,
            iv=iv,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        sess.add(agent)
        logger.info(f"Inserted new agent. agent_id: {agent.agent_id}, tenant: {tenant_name}")
        
        # Create AgentProfile for new agent
        agent_profile = AgentProfile(
            agent_id=agent_id,
            tenant_name=tenant_name,
            context=None,  # Initialize as empty
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc)
        )
        sess.add(agent_profile)
        logger.info(f"Created AgentProfile for new agent. agent_id: {agent_id}, tenant: {tenant_name}")
        
    else:
        agent.name = agent_data.get("name", agent_id)
        agent.encrypted_secret = encrypted_secret
        agent.iv = iv
        agent.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated existing agent, agent_id: {agent.agent_id}, tenant: {tenant_name}")
        
        # Ensure AgentProfile exists for existing agent (in case it was missing)
        existing_profile = sess.execute(
            select(AgentProfile).where(
                (AgentProfile.agent_id == agent_id) &
                (AgentProfile.tenant_name == tenant_name)
            )
        ).scalar_one_or_none()
        
        if not existing_profile:
            agent_profile = AgentProfile(
                agent_id=agent_id,
                tenant_name=tenant_name,
                context=None,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            sess.add(agent_profile)
            logger.info(f"Created missing AgentProfile for existing agent. agent_id: {agent_id}, tenant: {tenant_name}")

def upsert_user(sess, user_data, tenant_name):
    username = user_data.get("username")
    if not username:
        logger.warning("Skipping user with no username.")
        return
    
    if not tenant_name:
        logger.warning(f"Skipping user '{username}' with no tenant_name.")
        return
    
    # Handle credentials encryption
    credentials = user_data.get("credentials")
    encrypted_credentials = None
    iv = None
    if credentials:
        try:
            # Convert credentials to JSON string for encryption
            credentials_json = json.dumps(credentials)
            encrypted_info = encrypt(credentials_json)
            encrypted_credentials = encrypted_info["encryptedData"]
            iv = encrypted_info["iv"]
        except Exception as e:
            logger.warning(f"Could not encrypt credentials for user '{username}': {e}")
    
    user = sess.execute(
        select(User).where(
            (User.username == username) &
            (User.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not user:
        # Generate a temporary UUID for initialization if no ID is provided
        # In production, this ID should come from Keycloak
        user_id = user_data.get("id")
        if not user_id:
            user_id = str(uuid.uuid4())
            logger.info(f"Generated temporary UUID for user '{username}': {user_id}")
        
        user = User(
            id=user_id,
            username=username,
            tenant_name=tenant_name,
            email=user_data.get("email", ""),
            encrypted_credentials=encrypted_credentials,
            iv=iv
        )
        sess.add(user)
        logger.info(f"Inserted new user. username: {user.username}, tenant: {tenant_name}")
    else:
        user.email = user_data.get("email", "")
        user.encrypted_credentials = encrypted_credentials
        user.iv = iv
        logger.info(f"Updated existing user, username: {user.username}, tenant: {tenant_name}")



def upsert_role(sess, role_data, tenant_name, emb=None):
    """
    Upsert a role with all fields including embedding.
    
    Args:
        sess: SQLAlchemy session
        role_data: Dictionary containing role data
        tenant_name: Tenant name for isolation
        emb: Optional Embedder instance for generating embeddings
    
    Note: Domains are managed through the role_domain relationship table,
    not as a column in the roles table.
    """
    role = sess.execute(
        select(Role).where(
            (Role.name == role_data["name"]) &
            (Role.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    
    # Generate embedding from description and job_roles
    # Note: domains are stored in role_domain table, not in the role itself
    emb_vec = None
    if emb:
        emb_input_parts = [role_data.get("description", "")]
        
        # Add job_roles if present
        job_roles = role_data.get("job_roles", [])
        if job_roles:
            emb_input_parts.append(" ".join(job_roles))
        
        # Optionally include domains in embedding even though they're stored separately
        domains = role_data.get("domains", [])
        if domains:
            emb_input_parts.append(" ".join(domains))
        
        emb_input = " ".join(part for part in emb_input_parts if part).strip()
        if emb_input:
            emb_vec = emb.encode(emb_input)
    
    if not role:
        role = Role(
            name=role_data["name"],
            tenant_name=tenant_name,
            type=role_data.get("type"),
            label=role_data["label"],
            description=role_data.get("description", ""),
            job_roles=role_data.get("job_roles"),
            constraints=role_data.get("constraints"),
            emb=emb_vec
        )
        sess.add(role)
        logger.info(f"Inserted new role. name: {role.name}, tenant: {tenant_name}")
    else:
        role.type = role_data.get("type")
        role.label = role_data["label"]
        role.description = role_data.get("description", "")
        role.job_roles = role_data.get("job_roles")
        role.constraints = role_data.get("constraints")
        role.emb = emb_vec
        logger.info(f"Updated existing role, name: {role.name}, tenant: {tenant_name}")

def insert_role_domain(sess, role_name, domain_name, tenant_name):
    """
    Insert or ensure existence of a role-domain relationship.

    Note: This maps to the underlying `role_category` table in the DB.
    """
    role_domain = sess.execute(
        select(RoleDomain).where(
            (RoleDomain.role_name == role_name) &
            (RoleDomain.domain_name == domain_name) &
            (RoleDomain.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not role_domain:
        role_domain = RoleDomain(
            domain_name=domain_name,
            role_name=role_name,
            tenant_name=tenant_name
        )
        sess.add(role_domain)
        sess.flush()
        logger.info(f"Inserted new role-domain relation, domain_name={domain_name}, role_name={role_name}, tenant: {tenant_name}")
    else:
        logger.info(f"role-domain relation already exists, domain_name={domain_name}, role_name={role_name}, tenant: {tenant_name}")

def insert_role_user(sess, role_name, username, tenant_name):
    from integrator.iam.iam_db_model import RoleUser
    role_user = sess.execute(
        select(RoleUser).where(
            (RoleUser.role_name == role_name) &
            (RoleUser.username == username) &
            (RoleUser.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not role_user:
        role_user = RoleUser(
            role_name=role_name,
            username=username,
            tenant_name=tenant_name
        )
        sess.add(role_user)
        sess.flush()
        logger.info(f"Inserted new role_user: role_name={role_name}, username={username}, tenant: {tenant_name}")
    else:
        logger.info(f"role_user relation already exists: role_name={role_name}, username={username}, tenant: {tenant_name}")

def insert_role_agent(sess, role_name, agent_id, tenant_name):
    from integrator.iam.iam_db_model import RoleAgent
    role_agent = sess.execute(
        select(RoleAgent).where(
            (RoleAgent.role_name == role_name) &
            (RoleAgent.agent_id == agent_id) &
            (RoleAgent.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not role_agent:
        role_agent = RoleAgent(
            role_name=role_name,
            agent_id=agent_id,
            tenant_name=tenant_name
        )
        sess.add(role_agent)
        sess.flush()
        logger.info(f"Inserted new role_agent: role_name={role_name}, agent_id={agent_id}, tenant: {tenant_name}")
    else:
        logger.info(f"role_agent relation already exists: role_name={role_name}, agent_id={agent_id}, tenant: {tenant_name}")

def upsert_user_agent(sess, username, agent_id, tenant_name, role=None, context=None):
    """
    Upsert (insert or update) a user-agent relationship.
    
    Args:
        sess: SQLAlchemy session
        username: The username to associate with the agent
        agent_id: The agent_id to associate with the user
        tenant_name: Tenant name for isolation
        role: Optional role string for the user-agent relationship
        context: Optional JSON context for the user-agent relationship
    """
    user_agent = sess.execute(
        select(UserAgent).where(
            (UserAgent.username == username) &
            (UserAgent.agent_id == agent_id) &
            (UserAgent.tenant_name == tenant_name)
        )
    ).scalar_one_or_none()
    if not user_agent:
        user_agent = UserAgent(
            username=username,
            agent_id=agent_id,
            tenant_name=tenant_name,
            role=role,
            context=context
        )
        sess.add(user_agent)
        sess.flush()
        logger.info(f"Inserted new user_agent: username={username}, agent_id={agent_id}, tenant: {tenant_name}, role={role}")
    else:
        # Update role and context if provided
        if role is not None:
            user_agent.role = role
        if context is not None:
            user_agent.context = context
        logger.info(f"Updated user_agent relation: username={username}, agent_id={agent_id}, tenant: {tenant_name}, role={role}")

# Keep the old function name for backward compatibility
def insert_user_agent(sess, username, agent_id, tenant_name, role=None, context=None):
    """
    Deprecated: Use upsert_user_agent instead.
    Insert or update a user-agent relationship.
    """
    return upsert_user_agent(sess, username, agent_id, tenant_name, role, context)

def upsert_auth_provider(sess, provider_data, tenant_name):
    provider_id = provider_data.get("provider_id")
    client_secret = provider_data.get("clientSecret")
    if not provider_id:
        logger.warning("Skipping auth provider with missing provider_id")
        return
    encrypted_info =None
    if client_secret:
        encrypted_info =encrypt(client_secret)
    auth_provider = sess.execute(
        select(AuthProvider).where(
            (AuthProvider.tenant_name == tenant_name) &
            (AuthProvider.provider_id == provider_id)
        )
    ).scalar_one_or_none()
    if not auth_provider:
        auth_provider = AuthProvider(
            tenant_name=tenant_name,
            provider_id=provider_id,
            provider_name=provider_data.get("provider_name", provider_id),
            provider_type=provider_data.get("provider_type", provider_id),
            type=provider_data.get("type"),
            client_id=provider_data.get("clientId", "unknown"),
            is_built_in=provider_data.get("is_built_in", True),
            options=provider_data.get("options"),
            created_at=datetime.now(timezone.utc)
        )
        if not encrypted_info:
            encrypted_info =encrypt("known")

        auth_provider.encrypted_secret=encrypted_info["encryptedData"]
        auth_provider.iv=encrypted_info["iv"]

        sess.add(auth_provider)
        logger.info(f"Inserted new auth provider: {provider_id}")
    else:

        # For existing providers, only update fields that are provided
        if "provider_name" in provider_data:
            auth_provider.provider_name = provider_data["provider_name"]
        if "provider_type" in provider_data:
            auth_provider.provider_type = provider_data["provider_type"]
        if "type" in provider_data:
            auth_provider.type = provider_data["type"]
        if "clientId" in provider_data:
            auth_provider.client_id = provider_data.get("clientId")
                
        if encrypted_info:
            auth_provider.encrypted_secret = encrypted_info["encryptedData"]
            auth_provider.iv = encrypted_info["iv"]
        

        if "is_built_in" in provider_data:
            auth_provider.is_built_in = provider_data["is_built_in"]
        if "options" in provider_data:
            auth_provider.options = provider_data["options"]
        logger.info(f"Updated auth provider: {provider_id}")

def get_roles_by_username(sess, username, tenant_name):
    """
    Returns a list of Role objects for the given username in a specific tenant.
    """
    from integrator.iam.iam_db_model import RoleUser, Role
    roles = (
        sess.query(Role)
        .join(RoleUser, (Role.name == RoleUser.role_name) & (Role.tenant_name == RoleUser.tenant_name))
        .filter((RoleUser.username == username) & (RoleUser.tenant_name == tenant_name))
        .all()
    )
    return roles

def get_roles_by_agent_id(sess, agent_id, tenant_name):
    """
    Returns a list of Role objects for the given agent_id in a specific tenant.
    """
    from integrator.iam.iam_db_model import RoleAgent, Role
    roles = (
        sess.query(Role)
        .join(RoleAgent, (Role.name == RoleAgent.role_name) & (Role.tenant_name == RoleAgent.tenant_name))
        .filter((RoleAgent.agent_id == agent_id) & (RoleAgent.tenant_name == tenant_name))
        .all()
    )
    return roles


def is_admin_user(sess, user:dict, admin_role: str="administrator"):
    """
    get the working agent for the current user.
    """
    username = user["preferred_username"]
    roles =get_roles_by_username(sess,username)
    admin = next((role for role in roles if role.name == admin_role), None)
    if admin:
        return True
    else:
        False


def get_user_by_username(sess, username: str, tenant_name: str) -> Optional[User]:
    """
    Retrieve a single user by username for a specific tenant.
    
    Args:
        sess: SQLAlchemy session
        username: The username to search for
        tenant_name: Tenant name for filtering
        
    Returns:
        Optional[User]: User object if found, None otherwise
    """
    try:
        user = sess.execute(
            select(User).where(
                (User.username == username) &
                (User.tenant_name == tenant_name)
            )
        ).scalar_one_or_none()
        
        if user:
            logger.info(f"Retrieved user '{username}' for tenant: {tenant_name}")
        else:
            logger.info(f"User '{username}' not found for tenant: {tenant_name}")
        
        return user
    except Exception as e:
        logger.error(f"Error retrieving user '{username}' for tenant '{tenant_name}': {str(e)}")
        raise


def get_all_users(sess, tenant_name, skip: int = 0, limit: int = 100) -> List[User]:
    """
    Retrieve all users from the database for a specific tenant with pagination.
    
    Args:
        sess: SQLAlchemy session
        tenant_name: Tenant name for filtering
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        
    Returns:
        List[User]: List of all users in the tenant
    """
    try:
        users = sess.execute(
            select(User).where(User.tenant_name == tenant_name).offset(skip).limit(limit)
        ).scalars().all()
        
        logger.info(f"Retrieved {len(users)} users for tenant: {tenant_name}")
        return users
    except Exception as e:
        logger.error(f"Error retrieving all users for tenant '{tenant_name}': {str(e)}")
        raise


def get_all_agents(sess, tenant_name, skip: int = 0, limit: int = 100) -> List[Agent]:
    """
    Retrieve all agents from the database for a specific tenant with pagination.
    
    Args:
        sess: SQLAlchemy session
        tenant_name: Tenant name for filtering
        skip: Number of records to skip (default: 0)
        limit: Maximum number of records to return (default: 100)
        
    Returns:
        List[Agent]: List of all agents in the tenant
    """
    try:
        agents = sess.execute(
            select(Agent).where(Agent.tenant_name == tenant_name).offset(skip).limit(limit)
        ).scalars().all()
        
        logger.info(f"Retrieved {len(agents)} agents for tenant: {tenant_name}")
        return agents
    except Exception as e:
        logger.error(f"Error retrieving all agents for tenant '{tenant_name}': {str(e)}")
        raise


def get_agents_by_username(sess, username: str, tenant_name: str) -> List[dict]:
    """
    Retrieve all agents associated with a given username through the user_agent relationship,
    including role and context from the user_agent table.
    
    Args:
        sess: SQLAlchemy session
        username: The username to search for
        tenant_name: Tenant name for filtering
        
    Returns:
        List[dict]: List of dictionaries containing agent information with role and context
    """
    try:
        # Join UserAgent and Agent tables to get agents with role and context
        results = sess.execute(
            select(Agent, UserAgent.role, UserAgent.context)
            .join(UserAgent, (UserAgent.agent_id == Agent.agent_id) & (UserAgent.tenant_name == Agent.tenant_name))
            .where((UserAgent.username == username) & (UserAgent.tenant_name == tenant_name))
        ).all()
        
        # Convert results to list of dictionaries
        agents_with_context = []
        for agent, role, context in results:
            agent_dict = {
                "id": str(agent.id),
                "agent_id": agent.agent_id,
                "name": agent.name,
                "tenant_name": agent.tenant_name,
                "created_at": agent.created_at.isoformat() if agent.created_at else None,
                "updated_at": agent.updated_at.isoformat() if agent.updated_at else None,
                "role": role,
                "context": context
            }
            agents_with_context.append(agent_dict)
        
        logger.info(f"Retrieved {len(agents_with_context)} agents for username '{username}', tenant: {tenant_name}")
        return agents_with_context
    except Exception as e:
        logger.error(f"Error retrieving agents for username '{username}', tenant '{tenant_name}': {str(e)}")
        raise


def get_agent_by_agent_id(sess, agent_id: str, tenant_name: str) -> Optional[Agent]:
    """
    Retrieve a single agent by agent_id for a specific tenant.
    
    Args:
        sess: SQLAlchemy session
        agent_id: The agent_id to search for
        tenant_name: Tenant name for filtering
        
    Returns:
        Optional[Agent]: Agent object if found, None otherwise
    """
    try:
        agent = sess.execute(
            select(Agent).where(
                (Agent.agent_id == agent_id) &
                (Agent.tenant_name == tenant_name)
            )
        ).scalar_one_or_none()
        
        if agent:
            logger.info(f"Retrieved agent '{agent_id}' for tenant: {tenant_name}")
        else:
            logger.info(f"Agent '{agent_id}' not found for tenant: {tenant_name}")
        
        return agent
    except Exception as e:
        logger.error(f"Error retrieving agent '{agent_id}' for tenant '{tenant_name}': {str(e)}")
        raise


def get_users_by_agent_id(sess, agent_id: str, tenant_name: str) -> List[UserAgent]:
    """
    Retrieve all users associated with a given agent through the user_agent relationship.
    
    Args:
        sess: SQLAlchemy session
        agent_id: The agent_id to search for
        tenant_name: Tenant name for filtering
        
    Returns:
        List[UserAgent]: List of UserAgent objects
    """
    try:
        user_agents = sess.execute(
            select(UserAgent).where(
                (UserAgent.agent_id == agent_id) &
                (UserAgent.tenant_name == tenant_name)
            )
        ).scalars().all()
        
        logger.info(f"Retrieved {len(user_agents)} users for agent_id '{agent_id}', tenant: {tenant_name}")
        return user_agents
    except Exception as e:
        logger.error(f"Error retrieving users for agent_id '{agent_id}', tenant '{tenant_name}': {str(e)}")
        raise


def delete_user_agent(sess, username: str, agent_id: str, tenant_name: str) -> bool:
    """
    Delete a user-agent relationship.
    
    Args:
        sess: SQLAlchemy session
        username: The username
        agent_id: The agent_id
        tenant_name: Tenant name for filtering
        
    Returns:
        bool: True if deleted, False if not found
    """
    try:
        user_agent = sess.execute(
            select(UserAgent).where(
                (UserAgent.username == username) &
                (UserAgent.agent_id == agent_id) &
                (UserAgent.tenant_name == tenant_name)
            )
        ).scalar_one_or_none()
        
        if not user_agent:
            logger.warning(f"User-agent relationship not found: username={username}, agent_id={agent_id}, tenant: {tenant_name}")
            return False
        
        sess.delete(user_agent)
        sess.flush()
        logger.info(f"Deleted user_agent: username={username}, agent_id={agent_id}, tenant: {tenant_name}")
        return True
    except Exception as e:
        logger.error(f"Error deleting user_agent: {str(e)}")
        raise


def get_roles_with_domains_and_tool_counts(sess, agent_id: Optional[str] = None) -> List[dict]:
    """
    Extract all roles along with domains in the role. Each role includes tool count.
    Each domain in roles also includes tool count.
    
    The relationship chain is:
    - Role -> RoleDomain -> Domain -> DomainCapability -> Capability -> CapabilityTool -> McpTool
    
    Args:
        sess: SQLAlchemy session
        agent_id: Optional agent_id to filter roles for a specific agent.
                  If None, extract all roles.
    
    Returns:
        List[dict]: List of roles with structure:
        [
            {
                "role_name": str,
                "role_label": str,
                "role_description": str,
                "role_type": str,
                "tool_count": int,
                "domains": [
                    {
                        "domain_name": str,
                        "domain_label": str,
                        "domain_description": str,
                        "tool_count": int
                    },
                    ...
                ]
            },
            ...
        ]
    """
    from integrator.domains.domain_db_model import Domain, DomainCapability, Capability
    from integrator.tools.tool_db_model import CapabilityTool, McpTool
    
    try:
        # Build base query for roles
        if agent_id:
            # Filter roles for specific agent
            roles_query = (
                sess.query(Role)
                .join(RoleAgent, Role.name == RoleAgent.role_name)
                .filter(RoleAgent.agent_id == agent_id)
            )
            logger.info(f"Extracting roles for agent_id: {agent_id}")
        else:
            # Get all roles
            roles_query = sess.query(Role)
            logger.info("Extracting all roles")
        
        roles = roles_query.all()
        
        result = []
        
        for role in roles:
            # Get all domains for this role
            role_domains = (
                sess.query(Domain)
                .join(RoleDomain, Domain.name == RoleDomain.domain_name)
                .filter(RoleDomain.role_name == role.name)
                .all()
            )
            
            domains_data = []
            total_role_tool_count = 0
            
            for domain in role_domains:
                # Count tools for this domain through the relationship chain:
                # Domain -> DomainCapability -> Capability -> CapabilityTool -> McpTool
                domain_tool_count = (
                    sess.query(func.count(func.distinct(McpTool.id)))
                    .join(CapabilityTool, McpTool.id == CapabilityTool.tool_id)
                    .join(Capability, CapabilityTool.capability_name == Capability.name)
                    .join(DomainCapability, Capability.name == DomainCapability.capability_name)
                    .filter(DomainCapability.domain_name == domain.name)
                    .scalar()
                ) or 0
                
                domains_data.append({
                    "name": domain.name,
                    "label": domain.label,
                    "description": domain.description,
                    "tool_count": domain_tool_count
                })
                
                total_role_tool_count += domain_tool_count
            
            role_data = {
                "role_name": role.name,
                "role_label": role.label,
                "role_description": role.description,
                "role_type": role.type,
                "tool_count": total_role_tool_count,
                "domains": domains_data
            }
            
            result.append(role_data)
        
        logger.info(f"Successfully extracted {len(result)} roles with domain and tool counts")
        return result
        
    except Exception as e:
        logger.error(f"Error extracting roles with domains and tool counts: {str(e)}")
        raise


def main():
    base_dir = os.path.dirname(__file__)
    iam_config_path = os.path.join(base_dir, "../../../init/init_iam.json")
    initial_services_path = os.path.join(base_dir, "../../../init/initial_services.json")
    app_keys_path = os.path.join(base_dir, "../../../init/init_app_keys.json")
    auth_providers_path = os.path.join(base_dir, "../../../init/init_auth_providers.json")

    try:
        with open(iam_config_path, "r") as f:
            iam_config = json.load(f)
    except Exception as e:
        logger.error(f"Failed to load IAM config: {e}")
        return

    try:
        with open(initial_services_path, "r") as f:
            initial_services = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load initial_services.json: {e}")
        initial_services = {}

    try:
        with open(app_keys_path, "r") as f:
            app_key_list = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load app_keys.json: {e}")
        app_key_list = []

    try:
        with open(auth_providers_path, "r") as f:
            auth_providers_data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load auth_providers.json: {e}")
        auth_providers_data = []

    with get_db_cm() as sess:

        role=is_admin_user(sess, {"preferred_username":"agent-user"})
        for tenant_data in iam_config.get("tenants", []):
            tenant_name = tenant_data.get("name")
            if not tenant_name:
                logger.warning("Skipping tenant with no name.")
                continue

            logger.info(f"--- Processing tenant: {tenant_name} ---")
            upsert_tenant(sess, tenant_data)

            # Agents
            for agent_data in tenant_data.get("agents", []):
                upsert_agent(sess, agent_data, tenant_name)
                agent_id = agent_data.get("name") or agent_data.get("agent_id")

                # Applications (for first agent of first tenant, as in original script)
                if initial_services and agent_id:
                    for service in initial_services.get("default", []):
                        if "staticInput" in service and "url" in service["staticInput"]:
                            url_data = service["staticInput"]["url"]
                            host_id, base_url, _ = generate_host_id(url_data)
                            app_data = {
                                "app_name": host_id,
                                "app_note": base_url
                            }
                            upsert_application(sess, url_data, tenant_name)

            # Users
            for user_data in tenant_data.get("users", []):
                upsert_user(sess, user_data, tenant_name)

            # Service Secrets (for first agent of first tenant, as in original script)
            if tenant_data.get("agents"):
                first_agent_id = tenant_data["agents"][0].get("name") or tenant_data["agents"][0].get("agent_id")
                if initial_services and first_agent_id:
                    service_url_map = {
                        service['name']: service['staticInput']['url']
                        for service in initial_services.get("default", [])
                        if 'staticInput' in service and 'url' in service['staticInput']
                    }
                    for secret_info in app_key_list:
                        service_name = secret_info.get("service_name")
                        if not service_name or service_name not in service_url_map:
                            continue
                        url_data = service_url_map[service_name]
                        host_id, _, _ = generate_host_id(url_data)
                        upsert_app_key(sess, secret_info, host_id, first_agent_id, tenant_name)

            # Auth Providers (for each tenant)
            for provider in auth_providers_data:
                upsert_auth_provider(sess, provider, tenant_name)

            sess.commit()
            logger.info(f"--- Finished processing tenant: {tenant_name} ---\n")

if __name__ == "__main__":
    main()
    print("✅ IAM data initialized successfully.")
