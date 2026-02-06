#!/bin/bash

# Script to create tables, triggers, functions, and indexes in the agent-portal database (PostgreSQL in Docker)

DB_NAME="agent-portal"
DB_USER="user"
CONTAINER_NAME="postgres" # Adjust if your container name is different

SQL_FILE="/tmp/create_tables.sql"

cat > "$SQL_FILE" <<'EOF'
CREATE EXTENSION IF NOT EXISTS vector;


-- 1. TENANTS
CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT now()
);




EOF

# Copy the SQL file into the container and execute it
docker cp "$SQL_FILE" "$CONTAINER_NAME:/tmp/create_tables.sql"
docker exec -i "$CONTAINER_NAME" psql -U "$DB_USER" -d "$DB_NAME" -f /tmp/create_tables.sql

echo "Finished creating tables, triggers, functions, and indexes."
