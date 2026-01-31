from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
load_env()

from agent_ops.init.create_tenant_tables import create_tenant_tables
from agent_ops.init.create_domain_tables import create_domain_tables
from agent_ops.init.create_iam_tables import create_iam_tables
from agent_ops.init.create_tool_tables import create_tool_tables
from agent_ops.init.create_mcp_session import create_mcp_session_tables

from integrator.utils.logger import get_logger

logger = get_logger(__name__)

def init_db():
    create_tenant_tables()
    create_domain_tables()
    create_iam_tables()
    create_tool_tables()
    create_mcp_session_tables()


def init_with_defaults():
    """Initialize DB schema and restore default data"""
    logger.info("Starting initialization with defaults...")
    init_db()
    logger.info("Database schema created. Loading default data...")

    import sys
    import os
    original_argv = sys.argv.copy()
    # Use /app/data for Docker, fallback to local path for direct Python execution
    data_dir = '/app/data' if os.path.exists('/app/data') else '/Users/jingnan.zhou/workspace/agentic-coworker/data'
    sys.argv = ['restore', f'{data_dir}/backup_data/default_restore']
    try:
        from agent_ops.restore.main import restore_all
        restore_all()
    finally:
        sys.argv = original_argv

    logger.info("Initialization with defaults completed successfully.")


def init_with_seed():
    """Initialize DB schema and load seed data"""
    logger.info("Starting initialization with seed data...")
    init_db()
    logger.info("Database schema created. Loading seed data...")

    import sys
    import os
    original_argv = sys.argv.copy()
    # Use /app/data for Docker, fallback to local path for direct Python execution
    data_dir = '/app/data' if os.path.exists('/app/data') else '/Users/jingnan.zhou/workspace/agentic-coworker/data'
    sys.argv = ['seed', f'{data_dir}/seed_data']
    try:
        from agent_ops.seed.main import seed_all
        seed_all()
    finally:
        sys.argv = original_argv

    logger.info("Initialization with seed data completed successfully.")

if __name__ == "__main__":
    init_db()