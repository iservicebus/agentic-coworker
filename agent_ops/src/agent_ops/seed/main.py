from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

import json
import os
import requests
from datetime import datetime
from integrator.utils.logger import get_logger

from agent_ops.seed.tenant_init import seed_tenants

from agent_ops.seed.domain_init import seed_all_domains
from agent_ops.seed.iam_init import seed_iam
from agent_ops.seed.tools_init import seed_all_tools

logger = get_logger(__name__)


def seed_all():
    import sys

    # Get backup_path and tenant_name from command line arguments
    seed_dir = sys.argv[1] if len(sys.argv) > 1 else "../data/seed_data"

    seed_tenants(seed_dir)
    seed_all_domains(seed_dir)
    seed_iam(seed_dir)
    seed_all_tools(seed_dir)

if __name__ == "__main__":
    seed_all()
