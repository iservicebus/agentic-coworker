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


# Add etcd_client, db, username as arguments
def load_init_tools(etcd_client, sess, gsess, emb, llm, init_tool_path: str, username: str):
    """
    Loads service definitions from a JSON configuration file and registers them.
    """
    logger.info(f"--- Starting service registration using config: {init_tool_path} ---")

    # --- Load services from the specified JSON config file ---
    loaded_tenants_data = {} # Changed to dict to match json structure
    try:
        with open(init_tool_path, 'r') as f:
            loaded_tenants_data = json.load(f) # Expects a dict like {"tenant_name": [services]}
        logger.info(f"\n✅ Successfully loaded {len(loaded_tenants_data)} tenant(s) definitions from {init_tool_path}")
    except FileNotFoundError:
        logger.error(f"❌ Error: tenant configuration file not found at {init_tool_path}", exc_info=True)
        return # Return from function on error
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error: Could not parse JSON from {init_tool_path}: {e}", exc_info=True)
        return # Return from function on error
    except Exception as e:
        logger.error(f"❌ Error: An unexpected error occurred while loading {init_tool_path}: {e}", exc_info=True)
        return # Return from function on error

    # --- Register services loaded from config file ---
    logger.info("\n--- Registering services from configuration file ---")
    if not loaded_tenants_data:
         logger.info("ℹ️ No tenants found in the configuration file to register.")
         return # Return if no services to register

    registration_count = 0
    # Iterate through tenants and their services
    for tenant_name, services_list in loaded_tenants_data.items():
        logger.info(f"\nProcessing tenant: {tenant_name}")
        if not isinstance(services_list, list):
            logger.warning(f"⚠️ Skipping tenant '{tenant_name}': services data is not a list.")
            continue
        for service_data_item in services_list:
            service_name = service_data_item.get("name")
            # URL is expected to be a dict by generate_host_id and register_routing
            url_dict = service_data_item.get("staticInput", {}).get("url")

            if not service_name:
                logger.warning(f"⚠️ Skipping service in tenant '{tenant_name}' due to missing 'name': {service_data_item}")
                continue
            if not url_dict or not isinstance(url_dict, dict) or not url_dict.get("host"):
                logger.warning(f"⚠️ Skipping service '{service_name}' in tenant '{tenant_name}' due to missing or invalid 'staticInput.url.host': {service_data_item}")
                continue
            
            host_id, base_url, _ = generate_host_id(url_dict)
            if host_id and service_data_item.get("appName") == None:
                service_data_item["appName"] = host_id


            logger.info(f"stage the service for service name: {service_name}")

            staging_service = upsert_staging_service(sess, service_data_item, tenant_name, username)
            service_data_item["id"]=str(staging_service.id)
            
            sess.commit()  # Commit the transaction
            logger.info(f"update or insert application : {host_id} for tenant: {tenant_name}")
            # Pass etcd_client, db, tenant_name, service_data_item, and username
            #upsert_application(sess, url_dict, tenant_name)
            #logger.info(f"inserted or updated application for service name: {service_name}. app_name: {host_id}")

            tool=ingest_tool(etcd_client, sess, gsess, emb, llm, tenant_name, service_data_item, username, routing_overwrite=False, metadata_overwrite=True)
            if not tool:
                delete_staging_service_by_id(sess,service_id=staging_service.id)
            sess.flush()
            sess.commit()
            registration_count += 1
        sess.commit()
    logger.info(f"\n--- Finished registering {registration_count} services from {init_tool_path} ---")




def load_initial_applications(sess, json_path):
    try:

        with open(json_path, 'r') as f:
            loaded_tenants_data = json.load(f)

        # This assumes you have loaded tenants already
        for tenant_name, initial_services in loaded_tenants_data.items():

            for service in initial_services:
                if "staticInput" in service and "url" in service["staticInput"]:
                    url_data = service["staticInput"]["url"]
                    upsert_application(sess, url_data, tenant_name)
            sess.commit()
        logger.info(f"Processed initial services from {json_path}.")
    except Exception as e:
        logger.error(f"Failed to load initial services from {json_path}: {e}")
        sess.rollback()



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



def main():
    user="admin"
    try:
        etcd = get_etcd_client()
        driver=get_graph_driver()
    except Exception as e:
        logger.critical(f"Exiting due to etcd connection failure. error: {str(e)}")
        sys.exit(1)

    emb = Embedder()
    llm =LLM()
    with get_db_cm() as sess, driver.session() as gsess:
        #load_initial_applications(sess, INITIAL_SERVICES_JSON_PATH)
        load_init_tools(etcd,sess, gsess, emb, llm, INITIAL_SERVICES_JSON_PATH,user)
        #load_app_keys(sess, INIT_APP_KEYS_JSON_PATH)
    close_graph_driver()
if __name__ == "__main__":
    main()
