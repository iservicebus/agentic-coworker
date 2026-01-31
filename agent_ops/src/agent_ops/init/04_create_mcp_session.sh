#!/bin/bash

# Script to create tables, triggers, functions, and indexes in the agent-portal database (PostgreSQL in Docker)

DB_NAME="agent-portal"
DB_USER="user"
CONTAINER_NAME="postgres" # Adjust if your container name is different

SQL_FILE="/tmp/create_tables.sql"

cat > "$SQL_FILE" <<'EOF'

-- For gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- 1) Live session record (points to latest snapshot)
CREATE TABLE IF NOT EXISTS mcp_session (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    agent_id TEXT NOT NULL,
    
    -- pointer to latest context snapshot (FK added later to avoid circular dependency)
    current_context_id UUID,
    created_at TIMESTAMPTZ DEFAULT now(),
    updated_at TIMESTAMPTZ DEFAULT now(),
    
    -- Ensure one session per agent per tenant
    UNIQUE (agent_id, tenant_name),
    -- Composite FK to agents table
    FOREIGN KEY (agent_id, tenant_name) REFERENCES agents(agent_id, tenant_name) ON DELETE CASCADE
);

-- 2) Append-only context history snapshots
CREATE TABLE IF NOT EXISTS session_context_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES mcp_session(id) ON DELETE CASCADE,
    tenant_name TEXT NOT NULL REFERENCES tenants(name) ON DELETE CASCADE,
    
    -- auto-generated, monotonic per session: 1,2,3...
    seq BIGINT NOT NULL,
    
    -- full context payload: include toolset JSON here (and anything else)
    context JSONB,
    
    -- for change-detection / idempotency
    context_hash TEXT NOT NULL,
    
    created_at TIMESTAMPTZ DEFAULT now(),
    
    UNIQUE (session_id, seq)
);

-- Add FK from session.current_context_id -> history.id
DO $$
BEGIN
  IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'mcp_session_current_context_fk') THEN
    ALTER TABLE mcp_session
      ADD CONSTRAINT mcp_session_current_context_fk
      FOREIGN KEY (current_context_id)
      REFERENCES session_context_history(id);
  END IF;
END $$;

-- updated_at trigger for mcp_session
CREATE OR REPLACE FUNCTION update_mcp_session_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_mcp_session_updated_at ON mcp_session;
CREATE TRIGGER trg_update_mcp_session_updated_at
BEFORE UPDATE ON mcp_session
FOR EACH ROW
EXECUTE FUNCTION update_mcp_session_updated_at();

-- Indexes: fast "latest context for session"
CREATE INDEX IF NOT EXISTS idx_ctx_hist_session_seq_desc
  ON session_context_history(session_id, seq DESC);

-- Optional: fast "has this exact context already been stored?"
CREATE INDEX IF NOT EXISTS idx_ctx_hist_session_hash
  ON session_context_history(session_id, context_hash);

-- Tenant-scoped query performance
CREATE INDEX IF NOT EXISTS idx_mcp_session_tenant
  ON mcp_session(tenant_name);

CREATE INDEX IF NOT EXISTS idx_mcp_session_agent_tenant
  ON mcp_session(agent_id, tenant_name);

CREATE INDEX IF NOT EXISTS idx_ctx_hist_tenant
  ON session_context_history(tenant_name);



EOF

# Copy the SQL file into the container and execute it
docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/create_tables.sql"
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_tables.sql

echo "Finished creating tables, triggers, functions, and indexes."
