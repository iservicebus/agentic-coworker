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

ROLES_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/domains/roles.json")
ROLE_CAT_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/domains/role_domain.json")
ROLE_USER_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/domains/role_user.json")


def load_roles(sess, emb, json_path):
    """
    Load roles from JSON file with embedding generation and domain relationships.
    
    Args:
        sess: SQLAlchemy session
        emb: Embedder instance for generating embeddings
        json_path: Path to the roles JSON file
    """
    try:
        with open(json_path, "r") as f:
            roles = json.load(f)
            for role_data in roles:
                # Upsert the role
                upsert_role(sess, role_data, emb)
                sess.flush()
                # Create role-domain relationships if domains are present
                domains = role_data.get("domains", [])
                if domains:
                    role_name = role_data["name"]
                    for domain_name in domains:
                        insert_role_domain(sess, role_name, domain_name)
            
            sess.commit()
            logger.info(f"Inserted/updated {len(roles)} roles with their domain relationships.")
    except Exception as e:
        logger.error(f"Failed to insert roles from file: {json_path}, error:{str(e)}")
        sess.rollback()


def load_role_domains(sess, json_path):

    try:
        with open(json_path, "r") as f:
            role_domains = json.load(f)
        for entry in role_domains:
            # JSON still uses the key "category" but this now represents a domain
            domain_name = entry["domain"]
            for role_name in entry["roles"]:
                insert_role_domain(sess, role_name, domain_name)
        sess.commit()
        logger.info(f"Inserted total role-domains {len(role_domains)} successfully.")
    except Exception as e:
        sess.rollback()
        logger.error(f"Error inserting role-domain relationships for file: {json_path}, error: {str(e)}")


# New IAM init loaders

INIT_IAM_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/init_iam.json")
#INITIAL_SERVICES_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/initial_services.json")
#INIT_APP_KEYS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/init_app_keys.json")
INIT_AUTH_PROVIDERS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../init/init_auth_providers_v2.json")

from integrator.iam.iam_db_crud import (
    upsert_tenant, upsert_agent, upsert_user,  upsert_auth_provider
)
from integrator.utils.host import generate_host_id

def load_init_auth_providers(sess, json_path, tenant_name=None):
    try:
        with open(json_path, "r") as f:
            auth_providers_data = json.load(f)
        for provider in auth_providers_data:
            if tenant_name:
                upsert_auth_provider(sess, provider, tenant_name)
        sess.commit()
        logger.info(f"Processed auth providers from {json_path}.")
    except Exception as e:
        logger.error(f"Failed to load auth providers from {json_path}: {e}")
        sess.rollback()

def load_init_iam(sess, kc_config, iam_json_path, auth_provider_json_path):


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
        for tenant_data in iam_config.get("tenants", []):
            tenant_name = tenant_data.get("name")
            if not tenant_name:
                logger.warning("Skipping tenant with no name.")
                continue
            logger.info(f"--- Creating realm for tenant: {tenant_name} ---")
            if create_realm( headers, tenant_name, kc_config):
                logger.info(f"Realm created. Please run the script again to process roles, users, and agents.")
                return False

            upsert_tenant(sess, tenant_data)

            for scope in tenant_data.get("scopes", []):
                create_client_scope(headers, tenant_name, scope, kc_config)

            if "roles" in tenant_data:
                create_realm_roles( headers, tenant_name, tenant_data["roles"], kc_config)

            for client_data in tenant_data.get("clients", []):
                create_client( headers, tenant_name, client_data, kc_config)
                logger.info(f"created client with client id: {client_data.get("name") or client_data.get("agent_id")}")
                mappers=client_data.get("mapper", {})
                if mappers:
                    create_client_mapper(headers,tenant_name,client_data.get("name"),mappers, kc_config )
                scopes=client_data.get("scopes",[])

                for scope in scopes:
                    assign_scope_to_client(headers, tenant_name, client_data.get("name"),scope, kc_config)

                    
            for agent_data in tenant_data.get("agents", []):
                upsert_agent(sess, agent_data, tenant_name)
                create_user( headers, tenant_name, agent_data, kc_config)
                
                #create_client( headers, tenant_name, agent_data, kc_config)
                logger.info(f"created agent with agent id: {agent_data.get("name") or agent_data.get("agent_id")}")
                sess.flush()
            for user_data in tenant_data.get("users", []):
                upsert_user(sess, user_data, tenant_name)
                create_user( headers, tenant_name, user_data, kc_config)
                sess.flush()
                logger.info(f"created user with user name: {user_data.get("username")}")
                agents=user_data.get("agents", [])
                for agent in agents:

                    insert_user_agent(sess, user_data.get("username"), agent.get("agent_id"), agent.get("role"), agent.get("context", {}))
                    

            sess.flush()    
            load_init_auth_providers(sess, auth_provider_json_path, tenant_name)
        sess.commit()
        logger.info(f"Inserted/updated tenants, agents, and users from {iam_json_path}.")
        return True



    except Exception as e:
        logger.error(f"Failed to load IAM config from {iam_json_path}: {e}")
        sess.rollback()

def load_role_users(sess, json_path):
    """
    Loads role-user and role-agent relationships from a JSON file and inserts them into the database.
    Each entry in the JSON should have either a 'user' or 'agent' key and a list of 'roles'.
    """
    try:
        with open(json_path, "r") as f:
            role_user_data = json.load(f)
        user_count = 0
        agent_count = 0
        for entry in role_user_data:
            if "user" in entry:
                username = entry["user"]
                for role_name in entry["roles"]:
                    insert_role_user(sess, role_name, username)
                user_count += 1
            elif "agent" in entry:
                agent_id = entry["agent"]
                for role_name in entry["roles"]:
                    insert_role_agent(sess, role_name, agent_id)
                agent_count += 1
        sess.commit()
        logger.info(f"Inserted/updated {user_count} users and {agent_count} agents from {json_path}.")
    except Exception as e:
        logger.error(f"Failed to load role users from {json_path}: {e}")
        sess.rollback()


def main():
    emb = Embedder()
    with get_db_cm() as sess:
        if not load_init_iam(sess, KC_CONFIG, INIT_IAM_JSON_PATH, INIT_AUTH_PROVIDERS_JSON_PATH):
            return
        
        # Load roles with their domain relationships from roles.json
        load_roles(sess, emb, ROLES_JSON_PATH)
        
        # Load role-user and role-agent relationships
        load_role_users(sess, ROLE_USER_JSON_PATH)

if __name__ == "__main__":
    main()
