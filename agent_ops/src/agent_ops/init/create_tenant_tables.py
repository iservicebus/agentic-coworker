#!/usr/bin/env python3
"""
Script to create tenant tables in the agent-portal database (PostgreSQL)
Converted from shell script to Python for better integration
"""

from integrator.utils.env import load_env
load_env()

from integrator.utils.db import get_db_cm
from integrator.utils.logger import get_logger
from sqlalchemy import text

logger = get_logger(__name__)

SQL_STATEMENTS = """
CREATE EXTENSION IF NOT EXISTS vector;


-- 1. TENANTS
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);
"""

def create_tenant_tables():
    """Create tenant tables in the database"""
    try:
        logger.info("Starting tenant tables creation...")

        with get_db_cm() as session:
            # Execute the SQL statements
            session.execute(text(SQL_STATEMENTS))
            session.commit()

        logger.info("Successfully created tenant tables, triggers, functions, and indexes.")

    except Exception as e:
        logger.error(f"Failed to create tenant tables: {str(e)}")
        raise

if __name__ == "__main__":
    create_tenant_tables()
