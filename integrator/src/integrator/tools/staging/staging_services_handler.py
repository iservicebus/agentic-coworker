import json
import uuid # Added for UUID type
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from fastapi import HTTPException

from integrator.tools.tool_db_model import StagingService # Relative import from parent directory

# Helper to extract name, ensuring it exists
def _extract_service_name(service_json_object: Dict[str, Any]) -> str:
    service_name = service_json_object.get("name")
    if not service_name or not isinstance(service_name, str):
        raise HTTPException(status_code=422, detail="Service data must contain a 'name' field of type string.")
    return service_name

def create_staging_service(db: Session, tenant: str,  service_json_object: Dict[str, Any], username: str) -> StagingService:
    service_name = _extract_service_name(service_json_object)
    
    db_service = StagingService(
        tenant=tenant,
        name=service_name,
        service_data=service_json_object,
        created_by=username,
        updated_by=username # Also set updated_by on creation
    )
    try:
        db.add(db_service)
        db.commit()
        db.refresh(db_service)
        return db_service
    except Exception as e:
        db.rollback()
        # Log the exception e
        raise HTTPException(status_code=500, detail="An unexpected error occurred while creating the staging service.")

def get_staging_service(db: Session, service_id: uuid.UUID) -> Optional[StagingService]:
    return db.query(StagingService).filter(StagingService.id == service_id).first()

def get_staging_service_by_name(db: Session, tenant: str, name: str) -> Optional[StagingService]:
    """
    Get a staging service by name and tenant.
    Note: Since unique constraint was removed, this returns the first match if multiple exist.
    """
    return db.query(StagingService).filter(StagingService.tenant == tenant, StagingService.name == name).first()

def list_staging_services(db: Session, tenant: str, skip: int = 0, limit: int = 100) -> List[StagingService]:
    return db.query(StagingService).filter(StagingService.tenant == tenant).offset(skip).limit(limit).all()

def update_staging_service(db: Session, service_id: uuid.UUID, service_json_object: Dict[str, Any], username: str) -> Optional[StagingService]:
    db_service = get_staging_service(db, service_id)
    if not db_service:
        return None

    new_service_name = _extract_service_name(service_json_object)
    
    db_service.name = new_service_name
    db_service.service_data = service_json_object
    db_service.updated_by = username
    
    try:
        db.commit()
        db.refresh(db_service)
        return db_service
    except Exception as e:
        db.rollback()
        # Log the exception e
        raise HTTPException(status_code=500, detail="An unexpected error occurred while updating the staging service.")


def delete_staging_service(db: Session, service_id: uuid.UUID) -> Optional[StagingService]:
    db_service = get_staging_service(db, service_id)
    if not db_service:
        return None
    
    try:
        db.delete(db_service)
        db.commit()
        return db_service # Return the deleted object (now detached from session)
    except Exception as e:
        db.rollback()
        # Log the exception e
        raise HTTPException(status_code=500, detail="An unexpected error occurred while deleting the staging service.")

def populate_services_from_config(db: Session, tenant: str = "default",  username: str = "system_populate") -> List[StagingService]:
    """
    Populates staging services from the config/split_services.json file for the specified tenant.
    Note: Since unique constraint was removed, this will create services even if duplicates exist.
    """
    created_services = []
    
    # The import 'from config.split_services import default as default_services_config'
    # directly gives the list of services for the "default" tenant.
    # If you need to read the file dynamically or handle other tenants from the file,
    # this part would need to change to actually load and parse the JSON file.
    # For now, assuming 'default_services_config' is the list of service dicts.

    services_to_load = []
    try:
        # Attempt to load services from the imported config.
        # This assumes config.split_services.json has a structure like: {"default": [...services...]}
        # and the import system makes `default_services_config` be that list.
        
        # Dynamically load config/split_services.json
        # This is more robust than relying on a direct import if the file path is fixed.
        # Construct the path relative to the current file or use an absolute path if available.
        # For simplicity, if direct import `from config.split_services import default` works, use it.
        # If not, we need a way to locate `config/split_services.json`.
        # Let's assume the direct import `default_services_config` works as intended by the user's structure.
        # If `config.split_services.json` is not a Python module, this import will fail.
        # It's more likely a JSON file to be read.

        # Correct way to load from a JSON file:
        config_file_path = "config/split_services.json" # Relative to project root
        try:
            with open(config_file_path, 'r') as f:
                all_config_data = json.load(f)
            services_to_load = all_config_data.get(tenant, []) # Get services for the specified tenant
        except FileNotFoundError:
            raise HTTPException(status_code=500, detail=f"Configuration file {config_file_path} not found.")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail=f"Error decoding JSON from {config_file_path}.")

    except ImportError:
         raise HTTPException(status_code=500, detail="Could not import default services configuration. Ensure config/split_services.json is structured correctly or accessible.")


    for service_data_item in services_to_load:
        service_name = service_data_item.get("name")
        if not service_name:
            # Log or handle services in config without a name
            print(f"Skipping service in config due to missing name: {service_data_item}")
            continue

        # Since unique constraint was removed, we no longer check for existing services
        # and allow duplicates to be created
        try:
            created_service = create_staging_service(
                db=db,
                tenant=tenant,
                service_json_object=service_data_item,
                username=username
            )
            created_services.append(created_service)
        except HTTPException as e:
            # Log this error, e.g., if create_staging_service raises 422
            print(f"Error creating service '{service_name}' from config: {e.detail}")
            # Decide if one failure should stop the whole process or just skip this item
        except Exception as e:
            print(f"Unexpected error creating service '{service_name}' from config: {str(e)}")


    return created_services
