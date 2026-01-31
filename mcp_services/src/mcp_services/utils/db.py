"""
Database connection utilities for MCP services.

This module provides SQLAlchemy database connection management,
following the same patterns as the integrator module.
"""

import os
from contextlib import contextmanager
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL as SQLAlchemyURL

from mcp_services.utils.env import load_env

# Load environment variables from .env file
load_env()

# Get DATABASE_URL from environment
DATABASE_URL = os.getenv("DATABASE_URL")

# Create SQLAlchemy engine and session factory
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """
    Get a database session.
    
    This is a generator function that yields a database session
    and ensures it's properly closed after use.
    
    Usage with FastAPI:
        @app.get("/items")
        def read_items(db: Session = Depends(get_db)):
            return db.query(Item).all()
    
    Usage with context manager:
        with get_db_cm() as db:
            items = db.query(Item).all()
    
    Yields:
        Session: SQLAlchemy database session
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Context manager version of get_db for non-FastAPI usage
get_db_cm = contextmanager(get_db)


def get_db_url():
    """
    Construct a SQLAlchemy database URL from environment variables.
    
    Required environment variables:
        - DB_USER: Database username
        - DB_PASSWORD: Database password
        - DB_HOST: Database host
        - DB_PORT: Database port
        - DB_NAME: Database name
    
    Returns:
        str: SQLAlchemy database URL
        
    Raises:
        KeyError: If required environment variable is missing
        ValueError: If DB_PORT is not a valid integer
    """
    try:
        db_user = os.environ['DB_USER']
        db_password = os.environ['DB_PASSWORD']
        db_host = os.environ['DB_HOST']
        db_port = os.environ['DB_PORT']
        db_name = os.environ['DB_NAME']

        # Construct PostgreSQL URL
        db_url = SQLAlchemyURL.create(
            drivername="postgresql+psycopg2",
            username=db_user,
            password=db_password,
            host=db_host,
            port=int(db_port),
            database=db_name,
        )
        
        print(f"Database URL constructed: {db_url.render_as_string(hide_password=True)}")
        return str(db_url)
        
    except KeyError as e:
        print(
            f"❌ FATAL: Missing database configuration environment variable: {e}. "
            f"Please set DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME."
        )
        raise
    except ValueError as e:
        print(f"❌ FATAL: DB_PORT must be an integer. Error: {e}")
        raise
    except Exception as e:
        print(f"❌ FATAL: An unexpected error occurred while constructing DB URL: {e}")
        raise
