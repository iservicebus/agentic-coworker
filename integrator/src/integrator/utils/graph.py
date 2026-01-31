import os
from typing import Optional

from neo4j import GraphDatabase, Driver

from integrator.utils.env import load_env

# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()

# Module-level shared driver instance
__neo4j_driver: Optional[Driver] = None


def get_graph_driver() -> Driver:
    """Return a shared Neo4j driver instance.

    Lazily initializes the driver on first call using environment variables:
    - NEO4J_URI (default: "neo4j://localhost:7687")
    - NEO4J_USER (default: "neo4j")
    - NEO4J_PASSWORD (default: "password")

    The same Driver instance is reused for subsequent calls within this
    process. Call ``close_graph_driver`` on application shutdown if you
    need to explicitly close the connection.
    """
    global __neo4j_driver

    if __neo4j_driver is None:
        # ---------------------------
        # Config
        # ---------------------------
        neo4j_uri = os.environ.get("NEO4J_URI", "neo4j://localhost:7687")
        neo4j_user = os.environ.get("NEO4J_USER", "neo4j")
        neo4j_password = os.environ.get("NEO4J_PASSWORD", "password")

        __neo4j_driver = GraphDatabase.driver(neo4j_uri, auth=(neo4j_user, neo4j_password))

    return __neo4j_driver


def close_graph_driver() -> None:
    """Close the shared Neo4j driver, if it has been initialized."""
    global __neo4j_driver

    if __neo4j_driver is not None:
        __neo4j_driver.close()
        __neo4j_driver = None
