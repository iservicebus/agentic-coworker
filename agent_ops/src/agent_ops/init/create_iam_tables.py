#!/usr/bin/env python3
"""
Script to create IAM tables in the agent-portal database (PostgreSQL)
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

-- 2. AGENTS (mapped to Keycloak client_id)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    agent_id TEXT NOT NULL,       -- Keycloak client_id
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    name TEXT,
    encrypted_secret TEXT,
    iv TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (agent_id, tenant_name)
);

CREATE INDEX IF NOT EXISTS idx_agents_tenant_name ON agents(tenant_name);

-- 3. AGENT PROFILE (1:1 relationship with agents)
CREATE TABLE IF NOT EXISTS agent_profile (
    agent_id TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    context JSONB,                   -- JSON filter configuration for agent capabilities
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (agent_id, tenant_name),
    FOREIGN KEY (agent_id, tenant_name) REFERENCES agents(agent_id, tenant_name) ON DELETE CASCADE
);

-- Trigger to update 'updated_at' on agent_profile
CREATE OR REPLACE FUNCTION update_agent_profile_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_agent_profile_modtime ON agent_profile;
CREATE TRIGGER update_agent_profile_modtime
BEFORE UPDATE ON agent_profile
FOR EACH ROW
EXECUTE FUNCTION update_agent_profile_modified_column();

-- 5. USERS (Keycloak users, who manage agents)
CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,              -- Keycloak user ID (sub)
    username TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    email TEXT,
    encrypted_credentials TEXT,
    iv TEXT,
    UNIQUE (username, tenant_name)
);

CREATE INDEX IF NOT EXISTS idx_users_tenant_name ON users(tenant_name);


-- Roles table
CREATE TABLE IF NOT EXISTS roles (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR(255) NOT NULL,
  tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
  type VARCHAR(50),
  label VARCHAR(255) NOT NULL,
  description TEXT DEFAULT '',
  job_roles JSONB,
  constraints TEXT,
  emb vector(1536),
  UNIQUE (name, tenant_name)
);

CREATE INDEX IF NOT EXISTS idx_roles_tenant_name ON roles(tenant_name);


-- Relationship tables (fixed schema)
CREATE TABLE IF NOT EXISTS role_domain (
    role_name VARCHAR(255) NOT NULL,
    domain_name VARCHAR(255) NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    PRIMARY KEY (role_name, domain_name, tenant_name),
    FOREIGN KEY (role_name, tenant_name) REFERENCES roles(name, tenant_name) ON DELETE CASCADE,
    FOREIGN KEY (domain_name, tenant_name) REFERENCES domains(name, tenant_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_role_domain_tenant_name ON role_domain(tenant_name);

CREATE TABLE IF NOT EXISTS role_user (
    role_name VARCHAR(255) NOT NULL,
    username TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    PRIMARY KEY (role_name, username, tenant_name),
    FOREIGN KEY (role_name, tenant_name) REFERENCES roles(name, tenant_name) ON DELETE CASCADE,
    FOREIGN KEY (username, tenant_name) REFERENCES users(username, tenant_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_role_user_tenant_name ON role_user(tenant_name);

CREATE TABLE IF NOT EXISTS role_agent (
    role_name VARCHAR(255) NOT NULL,
    agent_id TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    PRIMARY KEY (role_name, agent_id, tenant_name),
    FOREIGN KEY (role_name, tenant_name) REFERENCES roles(name, tenant_name) ON DELETE CASCADE,
    FOREIGN KEY (agent_id, tenant_name) REFERENCES agents(agent_id, tenant_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_role_agent_tenant_name ON role_agent(tenant_name);

CREATE TABLE IF NOT EXISTS user_agent (
    username TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    role TEXT,
    context JSONB,
    PRIMARY KEY (username, agent_id, tenant_name),
    FOREIGN KEY (username, tenant_name) REFERENCES users(username, tenant_name) ON DELETE CASCADE,
    FOREIGN KEY (agent_id, tenant_name) REFERENCES agents(agent_id, tenant_name) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_user_agent_tenant_name ON user_agent(tenant_name);



-- 7. AUTH PROVIDERS (per tenant)

CREATE TABLE IF NOT EXISTS auth_providers (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name TEXT REFERENCES tenants(name) ON DELETE CASCADE NOT NULL,
    provider_id TEXT NOT NULL,
    provider_name TEXT NOT NULL,
    provider_type TEXT NOT NULL,
    type TEXT NOT NULL,
    client_id TEXT,
    encrypted_secret TEXT,
    is_built_in BOOLEAN DEFAULT TRUE,
    iv TEXT,
    options JSONB,
    created_at TIMESTAMPTZ DEFAULT now(),
    UNIQUE (tenant_name, provider_id)
);

-- 8. PROVIDER TOKENS
CREATE TABLE IF NOT EXISTS provider_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token JSONB NOT NULL,
    username TEXT,
    agent_id TEXT NOT NULL,
    tenant_name TEXT NOT NULL,
    provider_id TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    CONSTRAINT fk_tenant FOREIGN KEY (tenant_name) REFERENCES tenants(name) ON DELETE CASCADE,
    CONSTRAINT fk_auth_provider FOREIGN KEY (tenant_name, provider_id) REFERENCES auth_providers(tenant_name, provider_id) ON DELETE CASCADE,
    CONSTRAINT uq_provider_agent_tenant UNIQUE (provider_id, agent_id, tenant_name)
);

-- Apply alterations to ensure existing provider_tokens table matches the latest schema
ALTER TABLE provider_tokens ALTER COLUMN agent_id SET NOT NULL;
-- Drop and re-add uq_provider_agent_tenant to ensure it's correctly defined as per the latest schema
ALTER TABLE provider_tokens DROP CONSTRAINT IF EXISTS uq_provider_agent_tenant;
ALTER TABLE provider_tokens ADD CONSTRAINT uq_provider_agent_tenant UNIQUE (provider_id, agent_id, tenant_name);

-- Trigger to update 'updated_at' on provider_tokens
CREATE OR REPLACE FUNCTION update_provider_tokens_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_provider_tokens_modtime ON provider_tokens;
CREATE TRIGGER update_provider_tokens_modtime
BEFORE UPDATE ON provider_tokens
FOR EACH ROW
EXECUTE FUNCTION update_provider_tokens_modified_column();
"""

def create_iam_tables():
    """Create IAM tables in the database"""
    try:
        logger.info("Starting IAM tables creation...")

        with get_db_cm() as session:
            # Execute the SQL statements
            session.execute(text(SQL_STATEMENTS))
            session.commit()

        logger.info("Successfully created IAM tables, triggers, functions, and indexes.")

    except Exception as e:
        logger.error(f"Failed to create IAM tables: {str(e)}")
        raise

if __name__ == "__main__":
    create_iam_tables()
