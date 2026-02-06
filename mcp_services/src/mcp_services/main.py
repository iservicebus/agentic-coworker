from dotenv import load_dotenv
import uvicorn
import os
from mcp_services.utils.env import load_env
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()

# Now that env vars are loaded, we can safely import other modules.
from mcp_services.servers.refactored_mcp_provider import main


if __name__ == "__main__":
    main()
