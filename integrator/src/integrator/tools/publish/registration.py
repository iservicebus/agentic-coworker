import json
import argparse
import sys
import etcd3
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import utility functions
from integrator.utils.host import generate_host_id
from integrator.utils.logger import get_logger # Import the logger
from integrator.utils.etcd import get_etcd_client

from integrator.utils.db import get_db
from integrator.tools.tool_etcd_crud import register_single_service


# Initialize logger for this module
logger = get_logger(__name__)


# Add etcd_client, db, username as arguments
def register_services_from_config(etcd_client, db: Session, config_path: str, agent_id: str, username: str):
    """
    Loads service definitions from a JSON configuration file and registers them.
    """
    logger.info(f"--- Starting service registration using config: {config_path} ---")

    # --- Load services from the specified JSON config file ---
    loaded_tenants_data = {} # Changed to dict to match json structure
    try:
        with open(config_path, 'r') as f:
            loaded_tenants_data = json.load(f) # Expects a dict like {"tenant_name": [services]}
        logger.info(f"\n✅ Successfully loaded {len(loaded_tenants_data)} tenant(s) definitions from {config_path}")
    except FileNotFoundError:
        logger.error(f"❌ Error: tenant configuration file not found at {config_path}", exc_info=True)
        return # Return from function on error
    except json.JSONDecodeError as e:
        logger.error(f"❌ Error: Could not parse JSON from {config_path}: {e}", exc_info=True)
        return # Return from function on error
    except Exception as e:
        logger.error(f"❌ Error: An unexpected error occurred while loading {config_path}: {e}", exc_info=True)
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
            
            host_id, _, _ = generate_host_id(url_dict)
            if host_id and service_data_item.get("appName") == None:
                service_data_item["appName"] = host_id


            logger.info(f"Registering service: {service_name} for tenant: {tenant_name}")
            # Pass etcd_client, db, tenant_name, service_data_item, and username
            register_single_service(
                etcd_client,
                db, # Pass the db session
                tenant_name, # Explicitly pass the tenant name from the config structure
                service_data_item,
                routing_overwrite=False, # Default as per original logic
                metadata_overwrite=True  # Default as per original logic
            )
            registration_count += 1

    logger.info(f"\n--- Finished registering {registration_count} services from {config_path} ---")


# --- Main Execution ---
if __name__ == "__main__":
    # Logging is now handled by get_logger on its first call
    from integrator.utils.env import load_env
    load_env()

    import os
    cdir= os.path.dirname(__file__)
    path=os.path.join(cdir, "../../../init/initial_services.json")

    # Set up argument parser
    parser = argparse.ArgumentParser(description="Register services defined in a JSON configuration file.")
    parser.add_argument(
        "-c", "--config",
#        default="config/services_config.json", # Default to new location
        default=path, # Default to new location

        help="Path to the service configuration JSON file (default: config/services_config.json)"
    )
    args = parser.parse_args()

    # --- Get etcd client using the utility function ---
    etcd = None
    try:
        etcd = get_etcd_client()
    except Exception as e:
        logger.critical("Exiting due to etcd connection failure.", exc_info=True)
        sys.exit(1)

    # --- Database Setup ---
    db_session = next(get_db())

    agent_user = "agent_user"
    agent_id = "agent-client"

    try:
        # Call the main registration function with the client, db session, config path, and username
        register_services_from_config(etcd, db_session, args.config, agent_id,  agent_user)
    except Exception as e:
        logger.error(f"An error occurred during service registration: {e}", exc_info=True)
    finally:
        if db_session:
            db_session.close() # Ensure session is closed

    logger.info("\n✨ Service registration script complete!")
