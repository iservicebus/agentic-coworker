#!/usr/bin/env python3
"""
Script to create domain tables in the agent-portal database (PostgreSQL)
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

-- 1. Domain tables for dynamic, hierarchical, LLM-driven domains
CREATE TABLE IF NOT EXISTS domains (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
  label VARCHAR(255) NOT NULL,
  description TEXT DEFAULT '',
  scope TEXT DEFAULT '',
  domain_entities JSONB DEFAULT '[]'::jsonb,
  domain_purposes TEXT DEFAULT '',
  value_metrics JSONB DEFAULT '[]'::jsonb,
  emb vector(1536),
  created_at TEXT,
  UNIQUE (name, tenant_name)
);

-- 2. Canonical capabilities
CREATE TABLE IF NOT EXISTS capabilities (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
  label VARCHAR(255) NOT NULL,
  description TEXT DEFAULT '',
  business_context JSONB DEFAULT '[]'::jsonb,
  business_processes JSONB DEFAULT '[]'::jsonb,
  outcome TEXT DEFAULT '',
  business_intent JSONB DEFAULT '[]'::jsonb,
  emb vector(1536),
  created_at TEXT,
  UNIQUE (name, tenant_name)
);

-- Vector indexes
CREATE INDEX IF NOT EXISTS cap_emb_ivf  ON capabilities        USING ivfflat (emb vector_cosine_ops) WITH (lists=100);


-- 4. Relationship between Domain and Capability

CREATE TABLE IF NOT EXISTS domain_capability (
    domain_name VARCHAR(255) NOT NULL,
    capability_name VARCHAR(255) NOT NULL,
    tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (domain_name, capability_name, tenant_name),
    FOREIGN KEY (domain_name, tenant_name) REFERENCES domains(name, tenant_name),
    FOREIGN KEY (capability_name, tenant_name) REFERENCES capabilities(name, tenant_name)
);

-- 5. Canonical skills table
CREATE TABLE IF NOT EXISTS canonical_skills (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
  label VARCHAR(255) NOT NULL,
  skill_kind VARCHAR(100) DEFAULT '',
  intent VARCHAR(255) DEFAULT '',
  entity JSONB DEFAULT '[]'::jsonb,
  criticality VARCHAR(100) DEFAULT '',
  description TEXT DEFAULT '',
  created_at TEXT,
  UNIQUE (name, tenant_name)
);

-- 6. Relationship between Capability and Canonical Skills
CREATE TABLE IF NOT EXISTS capability_canonical_skill (
    capability_name VARCHAR(255) NOT NULL,
    canonical_skill_name VARCHAR(255) NOT NULL,
    tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (capability_name, canonical_skill_name, tenant_name),
    FOREIGN KEY (capability_name, tenant_name) REFERENCES capabilities(name, tenant_name),
    FOREIGN KEY (canonical_skill_name, tenant_name) REFERENCES canonical_skills(name, tenant_name)
);

-- 7. Workflows table
CREATE TABLE IF NOT EXISTS workflows (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
  label VARCHAR(255) NOT NULL,
  description TEXT DEFAULT '',
  value_metrics JSONB DEFAULT '[]'::jsonb,
  created_at TEXT,
  UNIQUE (name, tenant_name)
);

-- 8. Workflow steps table
CREATE TABLE IF NOT EXISTS workflow_steps (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
  label VARCHAR(255) NOT NULL,
  step_order INTEGER NOT NULL,
  intent TEXT DEFAULT '',
  description TEXT DEFAULT '',
  workflow_name VARCHAR(255) NOT NULL,
  created_at TEXT,
  UNIQUE (name, tenant_name),
  FOREIGN KEY (workflow_name, tenant_name) REFERENCES workflows(name, tenant_name)
);

-- 9. Relationship between Workflow Step and Domain
CREATE TABLE IF NOT EXISTS workflow_step_domain (
    workflow_step_name VARCHAR(255) NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (workflow_step_name, domain_name, tenant_name),
    FOREIGN KEY (workflow_step_name, tenant_name) REFERENCES workflow_steps(name, tenant_name),
    FOREIGN KEY (domain_name, tenant_name) REFERENCES domains(name, tenant_name)
);

-- 10. Relationship between Workflow Step and Capability
CREATE TABLE IF NOT EXISTS workflow_step_capability (
    workflow_step_name VARCHAR(255) NOT NULL,
    capability_name VARCHAR(255) NOT NULL,
    tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
    PRIMARY KEY (workflow_step_name, capability_name, tenant_name),
    FOREIGN KEY (workflow_step_name, tenant_name) REFERENCES workflow_steps(name, tenant_name),
    FOREIGN KEY (capability_name, tenant_name) REFERENCES capabilities(name, tenant_name)
);
"""

def create_domain_tables():
    """Create domain tables in the database"""
    try:
        logger.info("Starting domain tables creation...")

        with get_db_cm() as session:
            # Execute the SQL statements
            session.execute(text(SQL_STATEMENTS))
            session.commit()

        logger.info("Successfully created domain tables, triggers, functions, and indexes.")

    except Exception as e:
        logger.error(f"Failed to create domain tables: {str(e)}")
        raise

if __name__ == "__main__":
    create_domain_tables()
