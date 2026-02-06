from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from integrator.iam.iam_db_crud import upsert_tenant
from integrator.iam.iam_keycloak_crud import get_admin_token, create_realm, get_realm, KC_CONFIG
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger

logger = get_logger(__name__)

def restore_tenants_from_backup(sess, kc_config, tenant_backup_file, keycloak_backup_file):
    """Restore tenant database data and Keycloak realms from backup files"""
    try:
        # Get Keycloak admin token
        access_token = get_admin_token(kc_config)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        
        # Load tenant table backup
        with open(tenant_backup_file, "r") as f:
            tenant_data = json.load(f)
        
        # Load Keycloak realm backup
        with open(keycloak_backup_file, "r") as f:
            keycloak_data = json.load(f)
        
        restored_tenants = []
        
        # Restore each tenant
        for tenant_info in tenant_data.get("tenants", []):
            tenant_name = tenant_info.get("name")
            if not tenant_name:
                logger.warning("Skipping tenant with no name.")
                continue
                
            logger.info(f"Restoring tenant: {tenant_name}")
            
            # Step 1: Restore tenant table data
            try:
                upsert_tenant(sess, tenant_info)
                logger.info(f"Successfully restored tenant table data for: {tenant_name}")
            except Exception as e:
                logger.error(f"Failed to restore tenant table data for {tenant_name}: {str(e)}")
                continue
            
            # Step 2: Restore Keycloak realm
            if tenant_name in keycloak_data:
                realm_info = keycloak_data[tenant_name].get("realm", {})
                try:
                    # Check if realm already exists
                    existing_realm = get_realm(headers, tenant_name, kc_config)
                    
                    if not existing_realm:
                        # Create new realm if it doesn't exist
                        realm_created = create_realm(headers, tenant_name, kc_config)
                        if realm_created:
                            logger.info(f"Created new Keycloak realm for tenant: {tenant_name}")
                        else:
                            logger.warning(f"Failed to create Keycloak realm for tenant: {tenant_name}")
                            continue
                    else:
                        logger.info(f"Keycloak realm already exists for tenant: {tenant_name}")
                    
                    # Update realm settings if needed
                    if realm_info:
                        realm_url = f"{kc_config['KEYCLOAK_BASE']}/admin/realms/{tenant_name}"
                        realm_update_data = {
                            "enabled": realm_info.get("enabled", True),
                            "sslRequired": realm_info.get("sslRequired", "none"),
                            "accessTokenLifespan": realm_info.get("accessTokenLifespan", 1800),
                            "ssoSessionIdleTimeout": realm_info.get("ssoSessionIdleTimeout", 3600),
                            "ssoSessionMaxLifespan": realm_info.get("ssoSessionMaxLifespan", 28800)
                        }
                        
                        response = requests.put(realm_url, headers=headers, json=realm_update_data)
                        if response.status_code == 204:
                            logger.info(f"Updated Keycloak realm settings for tenant: {tenant_name}")
                        else:
                            logger.warning(f"Failed to update realm settings for {tenant_name}: {response.status_code}")
                    
                except Exception as e:
                    logger.error(f"Failed to restore Keycloak realm for {tenant_name}: {str(e)}")
                    continue
            else:
                logger.warning(f"No Keycloak backup data found for tenant: {tenant_name}")
            
            restored_tenants.append(tenant_name)
        
        # Commit database changes
        sess.commit()
        logger.info(f"Successfully restored {len(restored_tenants)} tenants: {restored_tenants}")
        return restored_tenants
        
    except Exception as e:
        logger.error(f"Failed to restore tenants from backup: {str(e)}")
        sess.rollback()
        return []

def main():
    """Main import function for tenant data"""
    import sys

    if len(sys.argv) != 2:
        print("Usage: python 01_tenant_import.py <backup_directory>")
        print("Example: python 01_tenant_import.py ../../backup_data/tenants_20251102_193429")
        sys.exit(1)
        #backup_dir="../data/backup_data/tenants_20260126_142445"
    else:
        backup_dir = sys.argv[1]
    
    # Construct full paths if relative path provided
    if not os.path.isabs(backup_dir):
        # Get the project root directory (two levels up from ops/import/)
        project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        backup_dir = os.path.join(project_root, backup_dir)
    
    tenant_backup_file = os.path.join(backup_dir, "tenant_table_backup.json")
    keycloak_backup_file = os.path.join(backup_dir, "keycloak_realm_backup.json")
    
    # Verify backup files exist
    if not os.path.exists(tenant_backup_file):
        logger.error(f"Tenant backup file not found: {tenant_backup_file}")
        sys.exit(1)
    
    if not os.path.exists(keycloak_backup_file):
        logger.error(f"Keycloak backup file not found: {keycloak_backup_file}")
        sys.exit(1)
    
    logger.info(f"Starting tenant import from {backup_dir}")
    logger.info(f"Tenant backup file: {tenant_backup_file}")
    logger.info(f"Keycloak backup file: {keycloak_backup_file}")
    
    with get_db_cm() as sess:
        restored_tenants = restore_tenants_from_backup(
            sess, KC_CONFIG, tenant_backup_file, keycloak_backup_file
        )
    
    if restored_tenants:
        logger.info(f"Tenant import completed successfully. Restored tenants: {restored_tenants}")
    else:
        logger.error("Tenant import failed or no tenants were restored.")
        sys.exit(1)

if __name__ == "__main__":
    main()
