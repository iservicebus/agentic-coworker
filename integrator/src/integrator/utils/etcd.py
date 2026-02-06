import etcd3
from integrator.utils.logger import get_logger # Import the logger
import os
logger = get_logger(__name__) # Initialize logger for this module

def get_etcd_client( ):

    """
    Initializes and returns an etcd3 client, checking the connection.

    Args:
        host (str): The etcd host.
        port (int): The etcd port.

    Returns:
        etcd3.client: An initialized etcd3 client instance.

    Raises:
        etcd3.exceptions.ConnectionFailedError: If the connection to etcd fails.
        Exception: For other potential errors during client initialization or status check.
    """
    host=os.getenv("ETCD_HOST")
    port=os.getenv("ETCD_PORT")


    logger.info(f"Attempting to connect to etcd at {host}:{port}...")
    try:


        client = etcd3.client(host=host, port=port)
        # Check status to confirm connection - this might raise exceptions
        client.status()
        logger.info("Successfully connected to etcd.")
        return client
    except etcd3.exceptions.ConnectionFailedError as e:
        logger.error(f"Connection to etcd ({host}:{port}) failed. Please ensure etcd is running and accessible.", exc_info=True)
        raise  # Re-raise the specific connection error
    except Exception as e:
        logger.error(f"An unexpected error occurred while connecting to etcd: {e}", exc_info=True)
        raise # Re-raise any other unexpected exception
