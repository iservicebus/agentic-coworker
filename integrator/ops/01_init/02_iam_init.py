from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()
import json
import os
from integrator.iam.iam_db_crud import upsert_role, insert_role_domain, insert_role_user, insert_role_agent, insert_user_agent
import os
from integrator.utils.db import get_db_cm
from integrator.utils.llm import Embedder
from integrator.utils.logger import get_logger
from integrator.iam.iam_keycloak_crud import (
    get_admin_token,
    create_realm, create_realm_roles, create_client, create_user, KC_CONFIG, create_client_mapper,
    create_client_scope,
    assign_scope_to_client
)
import numpy as np


logger = get_logger(__name__)

ROLES_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_roles_v1.json")
ROLE_CAT_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_role_domain_v1.json")
ROLE_USER_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_role_user_v1.json")


def load_roles(sess, emb, json_path):
    """
    Load roles from JSON file with embedding generation and domain relationships.
    Automatically reads tenant name from the JSON structure.
    
    Args:
        sess: SQLAlchemy session
        emb: Embedder instance for generating embeddings
        json_path: Path to the roles JSON file
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
            
            # Iterate through each tenant in the data
            for tenant_name, roles in data.items():
                logger.info(f"Loading roles for tenant: {tenant_name}")
                for role_data in roles:
                    # Upsert the role
                    upsert_role(sess, role_data, tenant_name, emb)
                    sess.flush()
                    # Create role-domain relationships if domains are present
                    domains = role_data.get("domains", [])
                    if domains:
                        role_name = role_data["name"]
                        for domain_name in domains:
                            insert_role_domain(sess, role_name, domain_name, tenant_name)
                
                sess.commit()
                logger.info(f"Inserted/updated {len(roles)} roles with their domain relationships for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to insert roles from file: {json_path}, error:{str(e)}")
        sess.rollback()


def load_role_domains(sess, json_path):
    """
    Load role-domain relationships from JSON file.
    Automatically reads tenant name from the JSON structure.
    
    Args:
        sess: SQLAlchemy session
        json_path: Path to the role-domain JSON file
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        
        # Iterate through each tenant in the data
        for tenant_name, role_domains in data.items():
            logger.info(f"Loading role-domains for tenant: {tenant_name}")
            for entry in role_domains:
                # JSON still uses the key "category" but this now represents a domain
                domain_name = entry["domain"]
                for role_name in entry["roles"]:
                    insert_role_domain(sess, role_name, domain_name, tenant_name)
            sess.commit()
            logger.info(f"Inserted total role-domains {len(role_domains)} successfully for tenant: {tenant_name}.")
    except Exception as e:
        sess.rollback()
        logger.error(f"Error inserting role-domain relationships for file: {json_path}, error: {str(e)}")


# New IAM init loaders

INIT_IAM_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_users_v1.json")
INIT_AUTH_PROVIDERS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_oauth_providers_v1.json")

from integrator.iam.iam_db_crud import (
    upsert_tenant, upsert_agent, upsert_user,  upsert_auth_provider
)
from integrator.utils.host import generate_host_id

def load_init_auth_providers(sess, json_path):
    """
    Load auth providers from JSON file.
    Automatically reads tenant name from the JSON structure.
    
    Args:
        sess: SQLAlchemy session
        json_path: Path to the auth providers JSON file
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        
        # Iterate through each tenant in the data
        for tenant_name, auth_providers_data in data.items():
            logger.info(f"Loading auth providers for tenant: {tenant_name}")
            for provider in auth_providers_data:
                upsert_auth_provider(sess, provider, tenant_name)
            sess.commit()
            logger.info(f"Processed {len(auth_providers_data)} auth providers for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to load auth providers from {json_path}: {e}")
        sess.rollback()

def load_init_iam(sess, kc_config, iam_json_path, auth_provider_json_path):
    """
    Load IAM configuration from JSON file.
    Automatically reads tenant name from the JSON structure: {"tenant_name": {"users": [...], "agents": [...]}}
    
    Args:
        sess: SQLAlchemy session
        kc_config: Keycloak configuration
        iam_json_path: Path to the IAM JSON file
        auth_provider_json_path: Path to the auth providers JSON file (not used in this function anymore)
    """
    try:
        access_token = get_admin_token(kc_config)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
    except Exception as e:
        logger.error(f"failed to get KeyCloak access token")
        return False

    try:
        with open(iam_json_path, "r") as f:
            iam_config = json.load(f)
        
        # Iterate through each tenant in the data structure
        for tenant_name, tenant_data in iam_config.items():
            logger.info(f"--- Processing tenant: {tenant_name} ---")
            
            # Process agents
            for agent_data in tenant_data.get("agents", []):
                upsert_agent(sess, agent_data, tenant_name)
                create_user(headers, tenant_name, agent_data, kc_config)
                
                logger.info(f"created agent with agent id: {agent_data.get('name') or agent_data.get('agent_id')}")
                sess.flush()
                
            # Process users
            for user_data in tenant_data.get("users", []):
                upsert_user(sess, user_data, tenant_name)
                create_user(headers, tenant_name, user_data, kc_config)
                sess.flush()
                logger.info(f"created user with user name: {user_data.get('username')}")
                agents = user_data.get("agents", [])
                for agent in agents:
                    insert_user_agent(sess, user_data.get("username"), agent.get("agent_id"), tenant_name, agent.get("role"), agent.get("context", {}))

            sess.flush()
            
        sess.commit()
        logger.info(f"Inserted/updated tenants, agents, and users from {iam_json_path}.")
        return True

    except Exception as e:
        logger.error(f"Failed to load IAM config from {iam_json_path}: {e}")
        sess.rollback()
        return False

def load_role_users(sess, json_path):
    """
    Loads role-user and role-agent relationships from a JSON file and inserts them into the database.
    Automatically reads tenant name from the JSON structure.
    Each entry in the JSON should have either a 'user' or 'agent' key and a list of 'roles'.
    
    Args:
        sess: SQLAlchemy session
        json_path: Path to the role-user JSON file
    """
    try:
        with open(json_path, "r") as f:
            data = json.load(f)
        
        # Iterate through each tenant in the data
        for tenant_name, role_user_data in data.items():
            logger.info(f"Loading role-users for tenant: {tenant_name}")
            user_count = 0
            agent_count = 0
            for entry in role_user_data:
                if "user" in entry:
                    username = entry["user"]
                    for role_name in entry["roles"]:
                        insert_role_user(sess, role_name, username, tenant_name)
                    user_count += 1
                elif "agent" in entry:
                    agent_id = entry["agent"]
                    for role_name in entry["roles"]:
                        insert_role_agent(sess, role_name, agent_id, tenant_name)
                    agent_count += 1
            sess.commit()
            logger.info(f"Inserted/updated {user_count} users and {agent_count} agents from {json_path} for tenant: {tenant_name}.")
    except Exception as e:
        logger.error(f"Failed to load role users from {json_path}: {e}")
        sess.rollback()


def main():
    emb = Embedder()
    with get_db_cm() as sess:
        if not load_init_iam(sess, KC_CONFIG, INIT_IAM_JSON_PATH, INIT_AUTH_PROVIDERS_JSON_PATH):
            return
        
        # Load auth providers (automatically reads tenant names from JSON)
        load_init_auth_providers(sess, INIT_AUTH_PROVIDERS_JSON_PATH)
        
        # Load roles with their domain relationships from roles.json (automatically reads tenant names from JSON)
        load_roles(sess, emb, ROLES_JSON_PATH)
        
        # Load role-user and role-agent relationships (automatically reads tenant names from JSON)
        load_role_users(sess, ROLE_USER_JSON_PATH)

if __name__ == "__main__":
    main()
