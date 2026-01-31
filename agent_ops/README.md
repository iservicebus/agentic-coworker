# Agent Operations (agent-ops)

Agent Operations CLI tool for managing database initialization, backup, restore, and seed data operations.

## Features

- **Database Initialization**: Three initialization modes (schema-only, with defaults, with seed data)
- **Backup & Restore**: Create timestamped backups and restore from any backup
- **Seed Data Management**: Load and process raw seed data into database
- **Update Operations**: Update app keys and auth providers from JSON files
- **Docker Support**: Persistent utility container for fast, reliable operations
- **Idempotent Operations**: Safe to run multiple times without side effects
- **CLI Interface**: Simple command-line interface with clear subcommands

## Quick Start

All commands run through the utility container which starts automatically with docker-compose:

```bash
# Initialize database with seed data
docker exec agent-ops python -m agent_ops init-seed

# Create a backup
docker exec agent-ops python -m agent_ops backup

# Restore from backup
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/TIMESTAMP
```

## Documentation

📚 **[Quick Reference Guide](./QUICK_REFERENCE.md)** - Complete usage documentation with:
- Prerequisites and setup
- All available commands
- Usage examples and workflows
- Troubleshooting guide
- Data directory structure

## Available Commands

| Command | Description |
|---------|-------------|
| `init-db` | Initialize database schema only |
| `init-defaults` | Initialize DB + restore default data |
| `init-seed` | Initialize DB + load seed data |
| `load-seed` | Load seed data into existing DB |
| `restore` | Restore from backup |
| `backup` | Create timestamped backup |
| `update` | Update app keys and auth providers |

Run `docker exec agent-ops python -m agent_ops --help` to see all commands and options.

## Installation

### Local Installation

```bash
# Install in development mode
pip install -e .

# Run the CLI
agent-ops --help
```

### Using Python Module

```bash
python -m agent_ops --help
```

## Docker Usage

### Utility Container

The agent-ops utility container runs continuously and is always available for operations. It starts automatically with docker-compose and connects to the `aintegrator-backend` network.

```bash
# Check if container is running
docker ps | grep agent-ops

# Run commands (works from any directory)
docker exec agent-ops python -m agent_ops [COMMAND] [OPTIONS]

# Interactive shell access
docker exec -it agent-ops bash
```

### Prerequisites

1. **Platform services running** (postgres, keycloak, neo4j, etcd, nats):
   ```bash
   cd /path/to/deployment/docker-platform
   docker-compose up -d
   ```

2. **Keycloak SSL disabled** (one-time setup):
   ```bash
   docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
     --server http://localhost:8080 --realm master --user admin --password admin
   docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
   ```

### Building the Image

```bash
cd /path/to/agent_ops
./build_docker.sh
```

The utility container is configured in `docker-compose.yml` with:
- Pre-configured environment from `../integrator/.env.docker`
- Volume mounts for `/app/data` directory
- Connected to `aintegrator-backend` network

## Command Examples

```bash
# Initialize database with seed data
docker exec agent-ops python -m agent_ops init-seed

# Initialize with default data (pre-processed backup)
docker exec agent-ops python -m agent_ops init-defaults

# Create backup
docker exec agent-ops python -m agent_ops backup

# Restore from specific backup
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/20260128_023013

# Update app keys and auth providers
docker exec agent-ops python -m agent_ops update

# Load seed data
docker exec agent-ops python -m agent_ops load-seed
```

📖 For detailed documentation, see **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)**

## Development

### Project Structure

```
agent_ops/
├── src/
│   └── agent_ops/
│       ├── __init__.py
│       ├── __main__.py          # CLI entry point
│       ├── backup/
│       │   ├── main.py          # Backup orchestration
│       │   ├── tenant_backup.py
│       │   ├── domain_backup.py
│       │   ├── iam_backup.py
│       │   └── tools_backup.py
│       └── utils/
├── Dockerfile
├── docker-compose.yml
├── .dockerignore
├── pyproject.toml
└── README.md
```

### Dependencies

This package depends on:
- `integrator`: Core integration utilities and models
- `requests`: HTTP client
- `numpy`: Numerical operations

See `pyproject.toml` for full dependency list.

### Testing

```bash
# Install test dependencies
pip install -e ".[test]"

# Run tests
pytest
```

## Troubleshooting

### Container Not Running

```bash
# Check if container is running
docker ps | grep agent-ops

# Start if stopped
docker start agent-ops

# Or restart with docker-compose
cd /path/to/deployment/docker-apps
docker-compose restart agent-ops
```

### Database Connection Errors

```bash
# Check PostgreSQL is running
docker ps | grep postgres

# Test connection
docker exec postgres psql -U user -d agent-studio -c "SELECT 1;"
```

### Keycloak SSL Required Error

```bash
# Configure and disable SSL (one-time setup)
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
```

### Network Not Found

```bash
# Start platform services to create network
cd /path/to/deployment/docker-platform
docker-compose up -d
```

For more troubleshooting tips, see **[QUICK_REFERENCE.md](./QUICK_REFERENCE.md)**

## License

See LICENSE file in the root directory.
