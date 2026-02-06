from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from datetime import datetime
from integrator.utils.logger import get_logger

from agent_ops.restore.tenant_import import restore_tenant

from agent_ops.restore.domain_import import restore_all_domains
from agent_ops.restore.iam_import import restore_all_iam
from agent_ops.restore.tools_import import restore_all_tools

logger = get_logger(__name__)


def restore_all():
    """Main backup function for domain data"""
    import sys

    # Get backup_path and tenant_name from command line arguments
    backup_dir = sys.argv[1] if len(sys.argv) > 1 else "/Users/jingnan.zhou/workspace/agentic-coworker/data/backup_data/default_restore"
    tenant_name = sys.argv[2] if len(sys.argv) > 2 else None

    restore_tenant(backup_dir)
    restore_all_domains(backup_dir, tenant_name)
    
    restore_all_iam(backup_dir, tenant_name)
    restore_all_tools(backup_dir, tenant_name)
    
if __name__ == "__main__":
    restore_all()
