from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.
load_env()

import json
import os, sys
from integrator.tools.tool_db_crud import upsert_app_key, upsert_application,upsert_staging_service, delete_staging_service_by_id, get_app_by_app_name_and_tenant_name
from integrator.tools.tool_ingestion import ingest_tool
from integrator.utils.db import get_db_cm
from integrator.utils.graph import get_graph_driver, close_graph_driver
from integrator.utils.llm import Embedder, LLM
from integrator.utils.logger import get_logger
from integrator.utils.etcd import get_etcd_client
import numpy as np

logger = get_logger(__name__)

INITIAL_SERVICES_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/03_tools/seed_mcp_tools_v1.json")
INIT_APP_KEYS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../data/seed_data/03_tools/seed_app_keys_v1.json")

from integrator.utils.host import generate_host_id_from_url,generate_host_id



def load_app_keys(sess, init_app_key_path):
    """
    Loads app keys from a JSON configuration file and registers them.
    Expected format: {"<tenant_name>": [<app_key_data>]}
    """
    try:
        with open(init_app_key_path, 'r') as f:
            loaded_tenants_data = json.load(f)

        logger.info(f"Successfully loaded app keys for {len(loaded_tenants_data)} tenant(s) from {init_app_key_path}")

        # Iterate through tenants and their app keys
        for tenant_name, app_key_list in loaded_tenants_data.items():
            logger.info(f"\nProcessing app keys for tenant: {tenant_name}")
            
            if not isinstance(app_key_list, list):
                logger.warning(f"⚠️ Skipping tenant '{tenant_name}': app keys data is not a list.")
                continue

            for key_info in app_key_list:
                app_name, _, _ = generate_host_id_from_url(key_info.get("app_url"))
                agent_id = key_info.get("agent_id")

                # Check if application exists
                if not get_app_by_app_name_and_tenant_name(sess, app_name, tenant_name):
                    logger.info(f"Service secret can not be inserted or updated due to app is not created yet: {app_name}, tenant: {tenant_name}")
                    continue
                
                # Check if agent exists before inserting app_key
                from integrator.iam.iam_db_crud import get_agent_by_agent_id
                agent = get_agent_by_agent_id(sess, agent_id, tenant_name)
                if not agent:
                    logger.warning(f"⚠️ Skipping app_key for app '{app_name}': agent '{agent_id}' does not exist in tenant '{tenant_name}'")
                    continue
                
                upsert_app_key(sess, key_info, app_name, agent_id, tenant_name)
                sess.flush()
                logger.info(f"Service secret for app name inserted or updated. app name: {app_name}, tenant: {tenant_name}")
                        
            sess.commit()
            logger.info(f"Completed processing app keys for tenant: {tenant_name}")
            
    except Exception as e:
        logger.error(f"Could not load or parse service secrets file: {init_app_key_path}. error: {str(e)}")
        sess.rollback()



def update_app_keys(app_key_path: str):

    with get_db_cm() as sess:
        load_app_keys(sess, app_key_path)
