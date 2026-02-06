from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os

from integrator.utils.env import load_env
# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()

# === .env ===
# DATABASE_URL = "postgresql://user:password@localhost:5432/agent-portal"

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


from contextlib import contextmanager

get_db_cm = contextmanager(get_db)

import os # Added for environment variables
from sqlalchemy.engine.url import URL as SQLAlchemyURL # For constructing DB URL

def get_db_url():
    """
    Constructs a SQLAlchemy database URL from environment variables.
    Assumes the following environment variables are set:
    DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME
    """
    try:
        db_user = os.environ['DB_USER']
        db_password = os.environ['DB_PASSWORD']
        db_host = os.environ['DB_HOST']
        db_port = os.environ['DB_PORT']
        db_name = os.environ['DB_NAME']

        # Using PostgreSQL as an example, adjust 'drivername' if using a different DB
        db_url = SQLAlchemyURL.create(
            drivername="postgresql+psycopg2", # Or "mysql+mysqlconnector", "sqlite", etc.
            username=db_user,
            password=db_password,
            host=db_host,
            port=int(db_port),
            database=db_name,
        )
        print(f"Database URL constructed: {db_url.render_as_string(hide_password=True)}")
        return str(db_url)
    except KeyError as e:
        print(f"❌ FATAL: Missing database configuration environment variable: {e}. Please set DB_USER, DB_PASSWORD, DB_HOST, DB_PORT, DB_NAME.")
        raise
    except ValueError as e:
        print(f"❌ FATAL: DB_PORT must be an integer. Error: {e}")
        raise
    except Exception as e:
        print(f"❌ FATAL: An unexpected error occurred while constructing DB URL: {e}")
        raise