from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from datetime import datetime
from integrator.utils.logger import get_logger

from agent_ops.backup.tenant_backup import backup_tenant

from agent_ops.backup.domain_backup import backup_all_domains
from agent_ops.backup.iam_backup import backup_all_iam
from agent_ops.backup.tools_backup import backup_all_tools

logger = get_logger(__name__)


def backup_all():
    """Main backup function for domain data"""
    import sys

    # Get backup_path and tenant_name from command line arguments
    # Default to /app/data/backup_data for container environment
    backup_path = sys.argv[1] if len(sys.argv) > 1 else "/app/data/backup_data"
    tenant_name = sys.argv[2] if len(sys.argv) > 2 else None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_dir = os.path.join(backup_path, f".secure.{timestamp}")
    backup_tenant(backup_dir)
    backup_all_domains(backup_dir, tenant_name)

    backup_all_iam(backup_dir, tenant_name)
    backup_all_tools(backup_dir, tenant_name)
    
    
if __name__ == "__main__":
    backup_all()
