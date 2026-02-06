#!/bin/bash

# Script to delete MCP session tables, triggers, functions, and indexes from the agent-portal database (PostgreSQL in Docker)

DB_NAME="agent-portal"
DB_USER="user"
CONTAINER_NAME="postgres" # Adjust if your container name is different

SQL_FILE="/tmp/delete_mcp_session_tables.sql"

cat > "$SQL_FILE" <<'EOF'

-- Drop indexes first
DROP INDEX IF EXISTS idx_ctx_hist_session_hash;
DROP INDEX IF EXISTS idx_ctx_hist_session_seq_desc;

-- Drop triggers
DROP TRIGGER IF EXISTS trg_update_mcp_session_updated_at ON mcp_session;

-- Drop functions
DROP FUNCTION IF EXISTS update_mcp_session_updated_at();

-- Drop the foreign key constraint first (to avoid dependency issues)
ALTER TABLE IF EXISTS mcp_session 
    DROP CONSTRAINT IF EXISTS mcp_session_current_context_fk;

-- Drop tables (order matters due to foreign keys)
-- Drop session_context_history first since it references mcp_session
DROP TABLE IF EXISTS session_context_history CASCADE;

-- Drop mcp_session table
DROP TABLE IF EXISTS mcp_session CASCADE;

-- Note: We don't drop the pgcrypto extension as it might be used by other tables

EOF

# Copy the SQL file into the container and execute it
docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/delete_mcp_session_tables.sql"
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/delete_mcp_session_tables.sql

echo "Finished deleting MCP session tables, triggers, functions, and indexes."
