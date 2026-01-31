import json
import argparse
import os
import sys # Added for exit()
import etcd3 # Keep for potential type hinting if needed

# Import the new utility function
from integrator.utils.etcd import get_etcd_client # Corrected relative import
from integrator.utils.logger import get_logger # Import the logger

# Import functions from tool_etcd_crud to avoid code duplication
from integrator.tools.tool_etcd_crud import (
    get_services_by_tenant,
    get_all_services,
    get_service_metadata
)

logger = get_logger(__name__) # Initialize logger for this module

# Wrapper functions to maintain backward compatibility with existing API

def retrieve_services_by_tenant(etcd_client, tenant):
    """
    Retrieves all service metadata for a specific tenant from etcd.
    Returns a list of service definition dictionaries for the given tenant.
    
    This is a wrapper around get_services_by_tenant from tool_etcd_crud.py
    """
    return get_services_by_tenant(etcd_client, tenant)


def retrieve_all_services(etcd_client):
    """
    Retrieves all service metadata from etcd, organized by tenant.
    Returns a dictionary where keys are tenant names and values are lists of service definitions.
    
    This is a wrapper around get_all_services from tool_etcd_crud.py
    """
    return get_all_services(etcd_client)


def retrieve_service_by_name(etcd_client, service_name, tenant="default"):
    """
    Retrieves all metadata for a single service specified by its name and tenant from etcd.

    Args:
        etcd_client: An initialized etcd3 client instance.
        service_name (str): The name of the service to retrieve.
        tenant (str): The tenant of the service. Defaults to "default".

    Returns:
        dict: A dictionary containing all metadata for the service,
              or None if the service is not found or an error occurs.
              
    This is a wrapper around get_service_metadata from tool_etcd_crud.py
    """
    return get_service_metadata(etcd_client, service_name, tenant)


def backup_services_to_json(services_list, output_file_path):
    """
    Writes the list of service definitions to a JSON file.
    """
    if services_list is None:
        logger.error("Cannot backup services, retrieval failed.")
        return False

    try:
        # Ensure the output directory exists
        output_dir = os.path.dirname(output_file_path)
        if output_dir and not os.path.exists(output_dir):
            logger.info(f"Creating directory: {output_dir}")
            os.makedirs(output_dir)

        logger.info(f"Writing backup to: {output_file_path}")
        with open(output_file_path, 'w') as f:
            json.dump(services_list, f, indent=4) # Use indent for readability
        logger.info(f"Backup successfully written to {output_file_path}")
        return True
    except IOError as e:
        logger.error(f"Error writing backup file {output_file_path}: {e}", exc_info=True)
        return False
    except Exception as e:
        logger.error(f"An unexpected error occurred during backup: {e}", exc_info=True)
        return False

# --- Main Execution ---
if __name__ == "__main__":
    from integrator.utils.env import load_env
    load_env()


    # Set up argument parser
    parser = argparse.ArgumentParser(description="Retrieve service definitions from etcd and back them up to a JSON file.")
    parser.add_argument(
        "-o", "--output",
        default="config/services_backup.json", # Default backup location
        help="Path to the output JSON backup file (default: config/services_backup.json)"
    )
    args = parser.parse_args()

    # --- Get etcd client using the utility function ---
    etcd = None # Initialize etcd to None
    try:
        # Use the utility function to get the client and check connection
        etcd = get_etcd_client() # Uses default host/port
    except Exception as e:
        # Error messages are now handled by the logger in get_etcd_client
        logger.critical("Exiting due to etcd connection failure.", exc_info=True)
        sys.exit(1) # Use sys.exit

    # --- Retrieve services using the obtained client ---
    retrieved_services = retrieve_all_services(etcd)

    # Backup services to JSON
    if backup_services_to_json(retrieved_services, args.output):
        logger.info("Service backup script complete!")
        sys.exit(0) # Use sys.exit
    else:
        logger.error("Service backup script failed.")
        sys.exit(1) # Use sys.exit
