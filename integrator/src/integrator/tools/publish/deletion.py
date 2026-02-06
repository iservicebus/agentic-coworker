import json
import argparse
import sys
import os

# SQLAlchemy imports for DB session
from sqlalchemy.orm import Session
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Import utilities from the project
from integrator.utils.etcd import get_etcd_client # Corrected relative import
from integrator.utils.db import get_db # Assuming db.py is also in utils
from integrator.utils.logger import get_logger # Import the logger
# Import the centralized delete_service_metadata function
from integrator.tools.tool_etcd_crud import delete_service_metadata as centralized_delete_service_metadata # Corrected relative import
from integrator.tools.publish.retrieve import retrieve_all_services, backup_services_to_json # Added for backup functionality

logger = get_logger(__name__) # Initialize logger for this module

def delete_services_from_config(etcd_client, db: Session, config_path: str, agent_id: str, username: str):
    """
    Loads service definitions from a JSON configuration file and deletes them
    using the centralized delete_service_metadata function.
    """
    logger.info(f"Starting service deletion using config: {config_path}")

    loaded_tenants_data = {}
    try:
        with open(config_path, 'r') as f:
            loaded_tenants_data = json.load(f) # Expects a dict like {"tenant_name": [services]}
        logger.info(f"Successfully loaded {len(loaded_tenants_data)} tenant(s) definitions from {config_path}")
    except FileNotFoundError:
        logger.error(f"Services configuration file not found at {config_path}", exc_info=True)
        sys.exit(1) # Or handle error differently
    except json.JSONDecodeError as e:
        logger.error(f"Could not parse JSON from {config_path}: {e}", exc_info=True)
        sys.exit(1) # Or handle error differently
    except Exception as e:
        logger.error(f"An unexpected error occurred while loading {config_path}: {e}", exc_info=True)
        sys.exit(1) # Or handle error differently

    if not loaded_tenants_data:
        logger.info("No tenants found in the configuration file to delete.")
        return

    deletion_count = 0
    for tenant_name, services_list in loaded_tenants_data.items():
        logger.info(f"Processing tenant: {tenant_name}")
        if not isinstance(services_list, list):
            logger.warning(f"Skipping tenant '{tenant_name}': services data is not a list.")
            continue
        for service_data_item in services_list:
            service_name = service_data_item.get("name")

            if not service_name:
                logger.warning(f"Skipping service deletion in tenant '{tenant_name}': 'name' is missing: {service_data_item}")
                continue
            
            logger.info(f"Processing deletion for service: {service_name} (tenant: {tenant_name})")
            # Call the imported and updated delete_service_metadata function
            centralized_delete_service_metadata(
                etcd_client,
                db, # Pass the db session
                service_name,
                tenant_name, # Pass the tenant name
                agent_id,
                username # Pass the username
            )
            deletion_count += 1
            logger.debug("-" * 20) # Separator, changed to debug

    logger.info(f"Finished processing {deletion_count} services from {config_path} for deletion.")


if __name__ == "__main__":
    from integrator.utils.env import load_env
    load_env()


    parser = argparse.ArgumentParser(
        description="Backs up all services to a JSON file and then deletes them from etcd and the database using that backup file."
    )
    parser.add_argument(
        "-p", "--path",
        default=None,
        help="Optional path for the backup JSON file. Defaults to 'backup/deleted_services.json' relative to the project root."
    )
    args = parser.parse_args()

    script_dir = os.path.dirname(__file__)
    project_root = os.path.abspath(os.path.join(script_dir, "../../../"))

    if args.path:
        effective_backup_path = args.path
        if not os.path.isabs(effective_backup_path):
            effective_backup_path = os.path.join(project_root, effective_backup_path)
        logger.info(f"Using provided path for backup and deletion: {effective_backup_path}")
    else:
        default_relative_path = "backup/deleted_services.json"
        effective_backup_path = os.path.join(project_root, default_relative_path)
        logger.info(f"Using default path for backup and deletion: {effective_backup_path}")

    effective_backup_dir = os.path.dirname(effective_backup_path)
    if effective_backup_dir and not os.path.exists(effective_backup_dir):
        try:
            logger.info(f"Creating directory: {effective_backup_dir}")
            os.makedirs(effective_backup_dir, exist_ok=True)
        except OSError as e:
            logger.error(f"Could not create directory {effective_backup_dir}: {e}", exc_info=True)
            sys.exit(1)


    etcd = None
    db_session = None
    try:
        etcd = get_etcd_client()
    except Exception as e:
        logger.critical(f"Exiting due to etcd connection failure: {e}", exc_info=True)
        sys.exit(1)

    try:
        db_session = next(get_db())
        agent_user = "agent_user" # Define a username for script operations
        agent_id = "agent-client" # Define an agent"
        # --- Backup Phase ---
        logger.info("Attempting to retrieve all services for backup...")
        all_services_data = retrieve_all_services(etcd)

        if not all_services_data:
            logger.info("No services found to backup. Exiting.")
            sys.exit(0) # Successful exit as there's nothing to do

        logger.info(f"Backing up retrieved services to {effective_backup_path}...")
        backup_successful = backup_services_to_json(all_services_data, effective_backup_path)

        if not backup_successful:
            logger.error(f"Failed to backup services to {effective_backup_path}. Aborting deletion.")
            sys.exit(1)
        
        logger.info(f"Services successfully backed up to {effective_backup_path}.")

        # --- Deletion Phase ---
        logger.info(f"Proceeding to delete services using the backup file: {effective_backup_path}")
        delete_services_from_config(etcd, db_session, effective_backup_path, agent_id, agent_user)
        
        logger.info("Service backup and deletion script complete!")

    except Exception as e:
        logger.error(f"An error occurred during service backup/deletion: {e}", exc_info=True)
        if db_session: # Ensure session is closed even on outer try/except
            db_session.close()
        sys.exit(1) # Exit with error status
    finally:
        if db_session:
            db_session.close() # Ensure session is closed
