from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from datetime import datetime
from integrator.iam.iam_db_model import Tenant
from integrator.iam.iam_keycloak_crud import get_admin_token, get_realm, KC_CONFIG
from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from sqlalchemy import select

logger = get_logger(__name__)
BACKUP_DIR="../../../data/backup_data"
def backup_tenants_only(sess, kc_config, backup_dir):
    """Backup only tenant database data in init format"""
    try:
        access_token = get_admin_token(kc_config)
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }
        keycloak_backup = {}

        # Get all tenants
        tenants_stmt = select(Tenant)
        tenants = sess.execute(tenants_stmt).scalars().all()
        
        tenant_backup = {"tenants": []}
        
        for tenant in tenants:
            logger.info(f"Backing up tenant: {tenant.name}")

            # Use get_realm function to get realm with KC_CONFIG attributes
            realm_data = get_realm(headers, tenant.name, kc_config)
            if not realm_data:
                logger.warning(f"Could not retrieve realm data for {tenant.name}, skipping")
                continue

            tenant_row = {
                "name": tenant.name,
                "description": tenant.description
            }
            
            tenant_backup["tenants"].append(tenant_row)
            keycloak_backup[tenant.name] = {
                "realm": realm_data
            }

        # Save tenant backup
        tenant_table_backup = os.path.join(backup_dir, "tenant_table_backup.json")
        with open(tenant_table_backup, "w") as f:
            json.dump(tenant_backup, f, indent=2)
        
        logger.info(f"Backed up tenant database to {tenant_table_backup}")
 
        # Save Keycloak realm backup for tenants
        tenant_kc_backup = os.path.join(backup_dir, "keycloak_realm_backup.json")
        with open(tenant_kc_backup, "w") as f:
            json.dump(keycloak_backup, f, indent=2)
        
        logger.info(f"Backed up Keycloak tenant realm data to {tenant_kc_backup}")

        return (tenant_table_backup, tenant_kc_backup)
        
    except Exception as e:
        logger.error(f"Failed to backup tenant database: {str(e)}")
        return None

def main():
    """Main backup function for tenant data only"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(os.path.dirname(__file__), BACKUP_DIR,  f"tenants_{timestamp}")
    os.makedirs(backup_dir, exist_ok=True)
    
    logger.info(f"Starting tenant-only backup to {backup_dir}")
    
    backup_files = []
    
    with get_db_cm() as sess:
        # Backup tenant database only
        tenant_files = backup_tenants_only(sess, KC_CONFIG, backup_dir)
        if tenant_files:
            backup_files.extend(tenant_files)
    
    logger.info(f"Tenant backup completed. Files created: {backup_files}")
    return backup_files

if __name__ == "__main__":
    main()
