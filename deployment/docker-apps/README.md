# Docker Apps Deployment

This directory contains the Docker Compose configuration for deploying all application containers with automatic database initialization.

## Overview

The deployment includes:
- **Automatic DB Initialization** - Database is initialized before any app starts
- **Agent Studio** - Next.js frontend (port 3000)
- **Integrator Service** - Main integration service (port 6060)
- **MCP Services** - Model Context Protocol services (port 6666)
- **Support Services** - Supporting API services (port 5000)

## Prerequisites

### 1. Platform Services Must Be Running

The app containers require platform services (PostgreSQL, Keycloak, Neo4j, ETCD, NATS):

```bash
cd ../docker-platform
docker-compose up -d

# Verify platform services are running
docker ps | grep -E "postgres|keycloak|neo4j|etcd|nats"
```

### 2. Agent-Ops Image Must Be Built

The db-init service uses the `agent-ops:latest` image:

```bash
cd ../../agent_ops
./build.sh

# Verify image exists
docker images | grep agent-ops
```

### 3. Keycloak SSL Must Be Disabled (One-Time Setup)

```bash
# Configure Keycloak admin CLI
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin

# Disable SSL requirement
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none

# Verify
docker exec keycloak /opt/keycloak/bin/kcadm.sh get realms/master | grep sslRequired
# Should show: "sslRequired" : "none",
```

### 4. Data Directory Must Exist

```bash
# Verify data directory structure
ls -la ../../data/
# Should contain: backup_data/default_restore/
```

## How It Works

### Automatic Database Initialization

The docker-compose.yml includes a special `db-init` service that:

1. **Runs First** - Executes before any app container starts
2. **Initializes Database** - Runs `agent-ops init-defaults` to:
   - Create all database tables, triggers, functions, indexes
   - Restore default data from `/data/backup_data/default_restore/`
   - Create Keycloak realms and users
   - Populate all domain, IAM, and tool data
3. **Exits After Completion** - The init container exits (doesn't restart)
4. **Blocks App Start** - All app services wait for `db-init` to complete successfully

### Important: When Does Init Run?

The `db-init` service has `restart: "no"` which means:

| Scenario | db-init Runs? | Explanation |
|----------|---------------|-------------|
| First `docker-compose up -d` | ✅ Yes | Container doesn't exist yet |
| Second `docker-compose up -d` | ❌ No | Exited container still exists |
| After `docker-compose down` | ✅ Yes | Container was removed |
| After `docker-compose stop` | ❌ No | Container still exists |
| With `--force-recreate` | ✅ Yes | Forces container recreation |

**TL;DR:** Init runs on first deployment, then is skipped on subsequent `docker-compose up -d` commands (unless you remove containers first with `docker-compose down`).

### Service Dependencies

```
db-init (init-defaults)
  ↓ completes successfully
  ├─→ agent-studio (starts)
  ├─→ mcp-services (starts)
  ├─→ support-services (starts)
  └─→ integrator (waits for mcp-services, then starts)
```

## Usage

### Deployment Script (Recommended)

Use the included `deploy.sh` script for easier deployment control:

```bash
# Standard deployment (init runs if needed)
./deploy.sh

# Force database re-initialization
./deploy.sh --init

# Skip initialization (faster, if DB already initialized)
./deploy.sh --skip-init

# Show help
./deploy.sh --help
```

**Benefits of using the script:**
- ✅ Checks prerequisites automatically
- ✅ Clear status messages
- ✅ Waits for init to complete
- ✅ Shows service URLs
- ✅ Handles errors gracefully

### First-Time Deployment

```bash
# 1. Start platform services (if not already running)
cd /path/to/deployment/docker-platform
docker-compose up -d

# 2. Configure Keycloak SSL (one-time, see Prerequisites)
# ... run Keycloak SSL commands ...

# 3. Build agent-ops image (if not already built)
cd /path/to/agent_ops
./build.sh

# 4. Deploy all apps (includes automatic DB initialization)
cd /path/to/deployment/docker-apps
docker-compose up -d
```

**What happens:**
1. `db-init` container starts first
2. Database is initialized with default data (~2-3 minutes)
3. `db-init` exits with success
4. All app containers start in parallel
5. Apps are ready to use

### Subsequent Deployments

For subsequent runs, you have several options:

#### Option A: Standard Restart (Skips Init)

```bash
# Stops and starts services, db-init won't run again
docker-compose stop
docker-compose up -d
```

**When:** Daily restarts, after config changes, etc.

#### Option B: Skip Init Explicitly (Fastest)

```bash
# Start only app services, skip db-init entirely
docker-compose up -d agent-studio integrator mcp-services support-services
```

**When:** You know DB is already initialized and want fastest startup.

#### Option C: Force Re-initialization

```bash
# Remove db-init container, then restart everything
docker-compose rm -f db-init
docker-compose up -d
```

**When:** You want to reload default data, or fix a failed init.

#### Option D: Complete Reset

```bash
# Remove all containers, then recreate (init will run)
docker-compose down
docker-compose up -d
```

**When:** Starting completely fresh.

### Stopping Services

```bash
# Stop all services
docker-compose down

# Stop and remove volumes (CAUTION: removes data)
docker-compose down -v
```

### Viewing Logs

```bash
# View db-init logs
docker-compose logs db-init

# View all logs
docker-compose logs -f

# View specific service logs
docker-compose logs -f integrator
docker-compose logs -f agent-studio
```

### Rebuilding Services

```bash
# Rebuild all services
docker-compose build

# Rebuild specific service
docker-compose build integrator

# Rebuild and restart
docker-compose up -d --build
```

## Configuration

### Database Initialization Service

The `db-init` service configuration:

```yaml
db-init:
  image: agent-ops:latest
  container_name: db-init
  command: init-defaults
  networks:
    - aintegrator-backend
  volumes:
    - ../../integrator/.env.docker:/app/agent_ops/.env:ro
    - ../../data:/app/data:ro
  restart: "no"  # Only run once
```

**Key settings:**
- `image: agent-ops:latest` - Uses the agent-ops Docker image
- `command: init-defaults` - Runs the init-defaults command
- `restart: "no"` - Prevents restart after completion
- Volumes mounted read-only (`:ro`) since init only reads data

### Changing Initialization Mode

You can change from `init-defaults` to other initialization modes:

#### Use Seed Data Instead

```yaml
db-init:
  image: agent-ops:latest
  command: init-seed  # Changed from init-defaults
  # ... rest of config
```

#### Schema Only (Manual Data Loading)

```yaml
db-init:
  image: agent-ops:latest
  command: init-db  # Only creates schema
  # ... rest of config
```

See [agent_ops/OPERATIONS.md](../../agent_ops/OPERATIONS.md) for all initialization modes.

### Environment Variables

Each service uses its own `.env.docker` file:

- `agent-studio/.env.docker` - Frontend configuration
- `integrator/.env.docker` - Integration service config
- `mcp_services/.env.docker` - MCP services config
- `support_services/.env.docker` - Support services config

The db-init service uses `integrator/.env.docker` for database connectivity.

## Troubleshooting

### DB-Init Failed

**Check logs:**
```bash
docker-compose logs db-init
```

**Common issues:**

1. **Keycloak SSL Required Error**
   ```
   403 Client Error: Forbidden
   error=ssl_required
   ```
   **Solution:** Disable SSL in Keycloak (see Prerequisites)

2. **Platform Services Not Running**
   ```
   Connection refused to postgres:5432
   ```
   **Solution:** Start platform services first
   ```bash
   cd ../docker-platform
   docker-compose up -d
   ```

3. **Agent-Ops Image Not Found**
   ```
   Error: No such image: agent-ops:latest
   ```
   **Solution:** Build the agent-ops image
   ```bash
   cd ../../agent_ops
   ./build.sh
   ```

4. **Data Directory Not Found**
   ```
   No such file or directory: /app/data/backup_data/default_restore
   ```
   **Solution:** Verify data directory exists and has default_restore
   ```bash
   ls -la ../../data/backup_data/default_restore/
   ```

### App Container Won't Start

**Check if db-init completed successfully:**
```bash
docker ps -a | grep db-init
# Should show "Exited (0)" - success
# If shows "Exited (1)" - check db-init logs
```

**Manually verify database:**
```bash
docker exec postgres psql -U user -d agent-studio -c "\dt"
# Should show list of tables
```

### Understanding Init Behavior

**Check if db-init has run:**
```bash
# Check db-init status
docker ps -a | grep db-init

# If shows "Exited (0)" - init completed successfully
# If shows "Exited (1)" - init failed, check logs
# If not shown - init hasn't run yet
```

**View db-init logs (even after it exits):**
```bash
docker-compose logs db-init
```

**Force init to run again:**
```bash
# Method 1: Remove container and restart
docker-compose rm -f db-init
docker-compose up -d

# Method 2: Use deploy script
./deploy.sh --init

# Method 3: Full recreate
docker-compose up -d --force-recreate db-init
```

### Re-initialize Database

If you need to start completely fresh:

```bash
# 1. Drop all tables
docker exec postgres psql -U user -d agent-studio -c \
  "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# 2. Remove db-init container
docker-compose rm -f db-init

# 3. Re-run deployment (will recreate db-init)
docker-compose up -d

# Or use the deploy script
./deploy.sh --init
```

### Skip Database Initialization

If database is already initialized and you just want to restart apps:

```bash
# Start specific services without db-init
docker-compose up -d agent-studio integrator mcp-services support-services
```

## Service Ports

| Service | Port | Description |
|---------|------|-------------|
| agent-studio | 3000 | Next.js frontend |
| integrator | 6060 | Main integration service |
| mcp-services | 6666 | Model Context Protocol services |
| support-services | 5000 | Supporting API services |

## Health Checks

All services have health checks configured:

```bash
# Check service health
docker ps --format "table {{.Names}}\t{{.Status}}"

# View health status in detail
docker inspect integrator-app | grep -A 5 Health
```

Health check URLs:
- agent-studio: `http://localhost:3000`
- integrator: `http://localhost:6060`
- mcp-services: `http://localhost:6666`
- support-services: `http://localhost:5000`

## Production Deployment

For production deployments:

1. **Use secrets management** instead of `.env` files
2. **Enable SSL/TLS** for all services
3. **Configure proper health checks** with appropriate timeouts
4. **Set resource limits** (CPU/memory) for each container
5. **Use external networks** instead of default bridge
6. **Configure logging drivers** for centralized logging
7. **Enable restart policies** based on your orchestration needs

## Development Workflow

### Local Development Setup

```bash
# 1. Start platform services
cd ../docker-platform
docker-compose up -d

# 2. Configure Keycloak (one-time)
# ... run Keycloak SSL commands ...

# 3. Build agent-ops
cd ../../agent_ops
./build.sh

# 4. Deploy apps
cd ../deployment/docker-apps
docker-compose up -d

# 5. Verify all services are running
docker ps
curl http://localhost:3000  # Agent Studio
curl http://localhost:6060  # Integrator
curl http://localhost:6666  # MCP Services
curl http://localhost:5000  # Support Services
```

### Making Changes

```bash
# 1. Stop the service you're modifying
docker-compose stop integrator

# 2. Make code changes...

# 3. Rebuild and restart
docker-compose up -d --build integrator
```

### Viewing Real-Time Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f integrator

# Last 100 lines
docker-compose logs --tail=100 integrator
```

## Advanced Usage

### Custom Data Path

To use a custom data directory:

```bash
# Edit docker-compose.yml, change db-init volumes:
volumes:
  - ../../integrator/.env.docker:/app/agent_ops/.env:ro
  - /custom/path/to/data:/app/data:ro  # Changed
```

### Multiple Environments

Create separate compose files for different environments:

```bash
# docker-compose.dev.yml
# docker-compose.staging.yml
# docker-compose.prod.yml

# Deploy specific environment
docker-compose -f docker-compose.dev.yml up -d
```

### Override Initialization Command

You can override the db-init command at runtime:

```bash
# Run with init-seed instead of init-defaults
docker-compose run --rm db-init init-seed
```

## References

- [Agent-Ops Operations Guide](../../agent_ops/OPERATIONS.md) - Complete command documentation
- [Agent-Ops Quick Reference](../../agent_ops/QUICK_REFERENCE.md) - Command cheat sheet
- [Platform Services](../docker-platform/README.md) - PostgreSQL, Keycloak, Neo4j, ETCD, NATS

## Support

For issues:
1. Check logs: `docker-compose logs db-init`
2. Verify prerequisites are met
3. Review [agent_ops/OPERATIONS.md](../../agent_ops/OPERATIONS.md) troubleshooting section
4. Check service health: `docker ps`

---

**Important:** The database initialization runs automatically on `docker-compose up -d`. If database is already initialized, the operation is idempotent (safe to run again).
