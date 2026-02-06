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
    assign_scope_to_client,
    disable_keycloak_ssl
)
import numpy as np


logger = get_logger(__name__)

INIT_TENANT_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/00_tenants/seed_tenants_v1.json")

from integrator.iam.iam_db_crud import (
    upsert_tenant
)

def load_init_tenants(sess, kc_config, tenant_json_path):


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


 
        with open(tenant_json_path, "r") as f:
            tenant_config = json.load(f)
        for tenant_data in tenant_config.get("tenants", []):
            tenant_name = tenant_data.get("name")
            if not tenant_name:
                logger.warning("Skipping tenant with no name.")
                continue
            logger.info(f"--- Creating realm for tenant: {tenant_name} ---")
            if create_realm( headers, tenant_name, kc_config):
                disable_keycloak_ssl("master", headers,  kc_config)
                logger.info(f"Realm created. Please run the script again to process roles, users, and agents.")
                import time
                time.sleep(10)
                #return False

            upsert_tenant(sess, tenant_data)
   

            for scope in tenant_data.get("scopes", []):
                create_client_scope(headers, tenant_name, scope, kc_config)

            if "roles" in tenant_data:
                create_realm_roles( headers, tenant_name, tenant_data["roles"], kc_config)

            for client_data in tenant_data.get("clients", []):
                create_client( headers, tenant_name, client_data, kc_config)
                logger.info(f"created client with client id: {client_data.get('name') or client_data.get('agent_id')}")
                mappers=client_data.get("mapper", {})
                if mappers:
                    create_client_mapper(headers,tenant_name,client_data.get("name"),mappers, kc_config )
                scopes=client_data.get("scopes",[])

                for scope in scopes:
                    assign_scope_to_client(headers, tenant_name, client_data.get("name"),scope, kc_config)

            sess.flush()    
        sess.commit()
        logger.info(f"Inserted/updated tenants, agents, and users from {tenant_json_path}.")
        return True
    except Exception as e:
        logger.error(f"Failed to load IAM config from {tenant_json_path}: {e}")
        sess.rollback()
def seed_tenants(seed_dir: str):
    tenant_path = os.path.join( seed_dir, "tenants", "seed_tenants.json")
    with get_db_cm() as sess:
        if not load_init_tenants(sess, KC_CONFIG, tenant_path):
            return

if __name__ == "__main__":
    
    seed_tenants("/Users/jingnan.zhou/workspace/agentic-coworker/data/seed_data")
