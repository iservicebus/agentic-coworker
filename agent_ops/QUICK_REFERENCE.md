# Agent-Ops Quick Reference

## Prerequisites Check

```bash
# 1. Platform services running?
docker ps | grep -E "postgres|keycloak|neo4j|etcd|nats"

# 2. Network exists?
docker network inspect aintegrator-backend

# 3. Keycloak SSL disabled? (one-time setup)
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
```

## Execution Method

### Utility Container

All commands are executed using the persistent utility container. The container runs continuously in the background and is always available.

```bash
# The utility container starts automatically with docker-compose up
# Run commands from ANY directory (no need to cd to docker-compose location)

docker exec agent-ops python -m agent_ops update
docker exec agent-ops python -m agent_ops load-seed
docker exec agent-ops python -m agent_ops backup
docker exec agent-ops python -m agent_ops init-seed

# Interactive shell access
docker exec -it agent-ops bash

# Check if container is running
docker ps | grep agent-ops

# Stop when done (optional - uses minimal resources ~1MB)
docker stop agent-ops

# Restart if needed
docker start agent-ops
```

**Advantages:**
- ⚡ Fast execution (no container startup overhead)
- 📂 Works from any directory (no need to be in docker-compose location)
- 🔄 Always available and ready
- 🛠️ Interactive shell access
- 💻 Perfect for development and operations
- 🪶 Minimal resource usage (~1MB memory)

## Common Commands

### Fresh Setup (Most Common)

```bash
# The utility container is always running - run from any directory

# Option A: With seed data (raw configuration)
docker exec agent-ops python -m agent_ops init-seed

# Option B: With default data (pre-processed backup)
docker exec agent-ops python -m agent_ops init-defaults

# Option C: Schema only (manual data loading)
docker exec agent-ops python -m agent_ops init-db
```

### Regular Operations

```bash
# Run from any directory

# Update app keys and auth providers
docker exec agent-ops python -m agent_ops update

# Reload seed data
docker exec agent-ops python -m agent_ops load-seed

# Create backup
docker exec agent-ops python -m agent_ops backup

# Restore from specific backup
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/20260128_023013
```

## Command Patterns

### Base Command
```bash
docker exec agent-ops python -m agent_ops [COMMAND] [OPTIONS]
```

### All Commands

| Command | Purpose | Requires Data Mount |
|---------|---------|---------------------|
| `init-db` | Schema only | No |
| `init-defaults` | Schema + defaults | Yes (read-only) |
| `init-seed` | Schema + seed | Yes (read-only) |
| `load-seed` | Load seed data | Yes (read-only) |
| `restore` | Restore backup | Yes (read-only) |
| `backup` | Create backup | Yes (read-write) |
| `update` | Update app keys/auth providers | Yes (read-only) |

### Command Options

```bash
# init-seed / load-seed
--seed-path PATH          # Custom seed data path

# restore
--restore-from PATH       # Backup directory to restore from
--tenant-name NAME       # Filter by tenant

# backup
--backup-path PATH       # Where to save backup
--tenant-name NAME       # Filter by tenant

# update
--update-folder PATH     # Folder containing update .json files (default: ../data/update_data)
```

## Troubleshooting Quick Fixes

### SSL Required Error
```bash
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
```

### Network Not Found
```bash
cd /path/to/deployment/docker-platform
docker-compose up -d
```

### Database Connection Failed
```bash
# Check Postgres is running
docker ps | grep postgres

# Test connection
docker exec postgres psql -U user -d agent-studio -c "SELECT 1;"
```

### Tenant Missing Error
```bash
# Manually create tenant
docker exec postgres psql -U user -d agent-studio -c \
  "INSERT INTO tenants (name, description) VALUES ('default', 'Default tenant') ON CONFLICT DO NOTHING;"
```

## Typical Workflows

### First-Time Setup
```bash
# Build the Docker image
cd /path/to/agent_ops
./build_docker.sh

# Configure Keycloak SSL (one-time)
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none

# Start services (utility container starts automatically)
cd /path/to/deployment/docker-apps
docker-compose up -d

# Initialize database using the utility container
docker exec agent-ops python -m agent_ops init-seed
```

### Before/After Changes
```bash
# Before: Create backup
docker exec agent-ops python -m agent_ops backup
# Returns: backup_data/20260128_023013

# Make changes...

# After: Restore if needed
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/20260128_023013
```

### Reset to Fresh State
```bash
# Drop all tables
docker exec postgres psql -U user -d agent-studio -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Reinitialize
docker exec agent-ops python -m agent_ops init-seed
```

## Direct Python Execution (Development)

```bash
# Install
pip install -e .

# Run
python -m agent_ops init-db
python -m agent_ops init-seed
python -m agent_ops backup --backup-path /path/to/backup
python -m agent_ops update --update-folder /path/to/update_data
```

## Environment Variables

Environment variables are configured in the `.env` file mounted to the utility container. To override variables:

```bash
# Edit the .env file used by the container
# Usually located at ../integrator/.env.docker

# Or pass environment variables directly to docker exec
docker exec -e DATABASE_URL=postgresql://user:pass@postgres:5432/db \
  -e AZURE_OPENAI_API_KEY=your-key \
  agent-ops python -m agent_ops init-seed
```

## File Locations

### Seed Data (Raw)
```
/data/seed_data/
├── tenants/seed_tenants.json
├── domains/seed_domains.json
├── iam/seed_users.json
└── tools/seed_mcp_tools.json
```

### Backup Data (Processed)
```
/data/backup_data/
├── default_restore/          # Default state
└── 20260128_023013/         # Timestamped backups
```

### Update Data (App Keys & Auth Providers)
```
/data/update_data/
├── app_keys_update.json      # App key updates
└── auth_providers_update.json # Auth provider updates
```
**Note:** Only .json files are processed. Files starting with `.secure.*` are excluded from git.

## Getting Help

```bash
# Show all commands
docker exec agent-ops python -m agent_ops --help

# Show command-specific help
docker exec agent-ops python -m agent_ops init-seed --help
docker exec agent-ops python -m agent_ops backup --help
```

---

**Quick tip:** All operations are idempotent - safe to run multiple times!
