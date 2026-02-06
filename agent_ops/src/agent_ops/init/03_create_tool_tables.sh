#!/bin/bash

# Script to create tables, triggers, functions, and indexes in the agent-portal database (PostgreSQL in Docker)

DB_NAME="agent-portal"
DB_USER="user"
CONTAINER_NAME="postgres" # Adjust if your container name is different

SQL_FILE="/tmp/create_tables.sql"

cat > "$SQL_FILE" <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;



-- 3. APPLICATIONS 
CREATE TABLE IF NOT EXISTS applications (
    app_name TEXT NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    app_note TEXT,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (app_name, tenant_name)
);

-- 4. API Keys PER APPLICATIONS 
CREATE TABLE IF NOT EXISTS app_keys (
    app_name TEXT NOT NULL,
    agent_id TEXT NOT NULL,
    tenant_name TEXT NOT NULL,
    secrets JSONB NOT NULL,       -- Store tokens, headers, config
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (app_name, agent_id, tenant_name),
    FOREIGN KEY (app_name, tenant_name) REFERENCES applications(app_name, tenant_name) ON DELETE CASCADE,
    FOREIGN KEY (agent_id, tenant_name) REFERENCES agents(agent_id, tenant_name) ON DELETE CASCADE
);



-- 6. STAGING SERVICES
CREATE TABLE IF NOT EXISTS staging_services (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL,
    tenant VARCHAR(255) NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    service_data JSONB NOT NULL, -- The entire service JSON object
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Trigger to update 'updated_at' on staging_services
CREATE OR REPLACE FUNCTION update_staging_services_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_staging_services_modtime ON staging_services;
CREATE TRIGGER update_staging_services_modtime
BEFORE UPDATE ON staging_services
FOR EACH ROW
EXECUTE FUNCTION update_staging_services_modified_column();



-- MCP TOOLs
CREATE TABLE IF NOT EXISTS mcp_tools (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    embedding vector(1536),
    document jsonb,
    canonical_data jsonb,
    tenant VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    tool_type VARCHAR(255) DEFAULT 'domain',
    created_by VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_by VARCHAR(255),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, tenant)
);

-- Trigger to update 'updated_at' on mcp_tools
CREATE OR REPLACE FUNCTION update_mcp_tools_modified_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS update_mcp_tools_modtime ON mcp_tools;
CREATE TRIGGER update_mcp_tools_modtime
BEFORE UPDATE ON mcp_tools
FOR EACH ROW
EXECUTE FUNCTION update_mcp_tools_modified_column();

-- 3. Skills table
CREATE TABLE IF NOT EXISTS skills (
    name VARCHAR(255) NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    label VARCHAR(255) NOT NULL,
    description TEXT,
    operational_entities JSONB DEFAULT '[]'::jsonb,
    operational_procedures JSONB DEFAULT '[]'::jsonb,
    operational_intent TEXT DEFAULT '',
    preconditions JSONB DEFAULT '[]'::jsonb,
    postconditions JSONB DEFAULT '[]'::jsonb,
    proficiency VARCHAR(50) DEFAULT '',
    emb vector(1536),
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (name, tenant_name)
);

-- Relationship between MCP Tools and Skills
CREATE TABLE IF NOT EXISTS tool_skills (
    tool_id UUID NOT NULL REFERENCES mcp_tools(id),
    skill_name VARCHAR(255) NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    step_index INTEGER,
    step_intent TEXT,
    PRIMARY KEY (tool_id, skill_name, tenant_name),
    FOREIGN KEY (skill_name, tenant_name) REFERENCES skills(name, tenant_name)
);

-- Relationship between Capability and Skill
CREATE TABLE IF NOT EXISTS capability_skill (
    capability_name VARCHAR(255) NOT NULL,
    skill_name VARCHAR(255) NOT NULL,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    PRIMARY KEY (capability_name, skill_name, tenant_name),
    FOREIGN KEY (capability_name, tenant_name) REFERENCES capabilities(name, tenant_name),
    FOREIGN KEY (skill_name, tenant_name) REFERENCES skills(name, tenant_name)
);

-- Relationship between Capability and MCP Tool
CREATE TABLE IF NOT EXISTS capability_tool (
    capability_name VARCHAR(255) NOT NULL,
    tool_id UUID NOT NULL REFERENCES mcp_tools(id),
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    PRIMARY KEY (capability_name, tool_id, tenant_name),
    FOREIGN KEY (capability_name, tenant_name) REFERENCES capabilities(name, tenant_name)
);

-- Relationship between MCP tools (tool flows)
CREATE TABLE IF NOT EXISTS tool_rels (
    source_tool_id UUID NOT NULL REFERENCES mcp_tools(id),
    target_tool_id UUID NOT NULL REFERENCES mcp_tools(id),
    composite_intent TEXT,
    field_mapping JSONB,
    PRIMARY KEY (source_tool_id, target_tool_id)
);

-- Relationship between Application and MCP Tool
CREATE TABLE IF NOT EXISTS application_mcp_tool (
    app_name TEXT NOT NULL,
    tenant_name TEXT NOT NULL,
    tool_id UUID NOT NULL REFERENCES mcp_tools(id) ON DELETE CASCADE,
    created_at TIMESTAMPTZ DEFAULT now(),
    PRIMARY KEY (app_name, tenant_name, tool_id),
    FOREIGN KEY (app_name, tenant_name) REFERENCES applications(app_name, tenant_name) ON DELETE CASCADE
);

EOF

# Copy the SQL file into the container and execute it
docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/create_tables.sql"
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_tables.sql

echo "Finished creating tables, triggers, functions, and indexes."
