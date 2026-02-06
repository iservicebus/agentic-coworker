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



# New IAM init loaders

INIT_AUTH_PROVIDERS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/02_iam/seed_oauth_providers_v1.json")

from integrator.iam.iam_db_crud import (
    upsert_tenant, upsert_agent, upsert_user,  upsert_auth_provider
)
from integrator.utils.host import generate_host_id

def upsert_auth_providers(sess, json_path):
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


def update_auth_providers( auth_provider_path:str):
    emb = Embedder()
    with get_db_cm() as sess:
        # Load auth providers (automatically reads tenant names from JSON)
        upsert_auth_providers(sess, auth_provider_path)

