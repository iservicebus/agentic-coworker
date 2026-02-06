from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
from pathlib import Path
from integrator.utils.logger import get_logger
from agent_ops.update.app_key import update_app_keys
from agent_ops.update.auth_provider import update_auth_providers

logger = get_logger(__name__)


def is_app_key_file(file_path: str) -> bool:
    """
    Check if the file contains app key data.
    App key data should have 'app_url' field in the data objects.

    Args:
        file_path: Path to the JSON file

    Returns:
        True if file contains app key data, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Check if data structure matches {'<tenant_name>': [<data_object>]}
        if not isinstance(data, dict):
            return False

        # Check first data object in any tenant
        for tenant_name, data_list in data.items():
            if isinstance(data_list, list) and len(data_list) > 0:
                first_obj = data_list[0]
                if isinstance(first_obj, dict) and 'app_url' in first_obj:
                    return True

        return False
    except Exception as e:
        logger.error(f"Error checking file type for {file_path}: {e}")
        return False


def is_auth_provider_file(file_path: str) -> bool:
    """
    Check if the file contains auth provider data.
    Auth provider data should have 'provider_id', 'name', and 'type' fields.

    Args:
        file_path: Path to the JSON file

    Returns:
        True if file contains auth provider data, False otherwise
    """
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)

        # Check if data structure matches {'<tenant_name>': [<data_object>]}
        if not isinstance(data, dict):
            return False

        # Check first data object in any tenant
        for tenant_name, data_list in data.items():
            if isinstance(data_list, list) and len(data_list) > 0:
                first_obj = data_list[0]
                if isinstance(first_obj, dict):
                    has_provider_id = 'provider_id' in first_obj
                    has_name = 'provider_name' in first_obj
                    has_type = 'provider_type' in first_obj
                    if has_provider_id and has_name and has_type:
                        return True
        return False
    except Exception as e:
        logger.error(f"Error checking file type for {file_path}: {e}")
        return False


def process_update_folder(update_folder_path: str):
    """
    Process all files in the update folder.
    Files are processed in order from oldest to newest.
    Each file is checked to determine if it's for app key or auth provider updates.

    Args:
        update_folder_path: Path to the folder containing update files
    """
    try:
        # Check if folder exists
        folder_path = Path(update_folder_path)
        if not folder_path.exists() or not folder_path.is_dir():
            logger.error(f"Update folder does not exist or is not a directory: {update_folder_path}")
            return

        # Get all .json files in the folder
        all_files = [f for f in folder_path.iterdir() if f.is_file() and f.suffix.lower() == '.json']

        if not all_files:
            logger.info(f"No .json files found in update folder: {update_folder_path}")
            return

        # Sort files by modification time (oldest first)
        sorted_files = sorted(all_files, key=lambda f: f.stat().st_mtime)

        logger.info(f"Found {len(sorted_files)} .json file(s) in update folder: {update_folder_path}")
        logger.info(f"Processing files from oldest to newest...")

        # Process each file
        for file_path in sorted_files:
            file_path_str = str(file_path)
            logger.info(f"\n{'='*60}")
            logger.info(f"Processing file: {file_path.name}")
            logger.info(f"{'='*60}")

            # Determine file type and call appropriate function
            if is_app_key_file(file_path_str):
                logger.info(f"Detected as APP KEY update file")
                update_app_keys(file_path_str)
                logger.info(f"✓ Completed app key update for: {file_path.name}")
            elif is_auth_provider_file(file_path_str):
                logger.info(f"Detected as AUTH PROVIDER update file")
                update_auth_providers(file_path_str)
                logger.info(f"✓ Completed auth provider update for: {file_path.name}")
            else:
                logger.warning(f"⚠️ Could not determine file type for: {file_path.name}")
                logger.warning(f"   File must be either app key (with 'app_url') or auth provider (with 'provider_id', 'name', 'type')")

        logger.info(f"\n{'='*60}")
        logger.info(f"✓ Completed processing all files in update folder")
        logger.info(f"{'='*60}\n")

    except Exception as e:
        logger.error(f"Error processing update folder {update_folder_path}: {e}")


if __name__ == "__main__":
    import sys

    # Default update folder path
    default_update_folder = "/Users/jingnan.zhou/workspace/agentic-coworker/data/update_data"

    # Get folder path from command line argument or use default
    update_folder = sys.argv[1] if len(sys.argv) > 1 else default_update_folder

    logger.info(f"Starting update process...")
    logger.info(f"Update folder: {update_folder}")

    process_update_folder(update_folder)

    logger.info(f"Update process finished.")
