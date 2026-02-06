from dotenv import load_dotenv
import os

# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

def load_env():
    if not os.getenv("ENV_LOADED"):  # Check marker
        cdr=os.path.dirname(__file__)
        env_path=os.path.join(cdr, "../../../.env")
        # load_dotenv moved here to be closer to usage and ensure it's called before logger might be used with env vars
        if os.path.exists(env_path):
            load_dotenv(env_path)

if __name__ == "__main__":
    load_env()