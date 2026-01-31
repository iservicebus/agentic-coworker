# Environment Files Reference

## Overview

Docker Compose uses the **existing `.env.docker` files** from each project directory, eliminating the need for a separate consolidated environment file.

## File Locations

```
aintegrator/
├── agent-studio/.env.docker             ← Agent Studio environment
├── integrator/.env.docker               ← Integrator environment
├── mcp_services/.env.docker             ← MCP Services environment
└── support_services/.env.docker         ← Support Services environment
```

## How It Works

The `docker-compose.yml` references each project's `.env.docker` file:

```yaml
services:
  agent-studio:
    env_file:
      - ../../agent-studio/.env.docker

  integrator:
    env_file:
      - ../../integrator/.env.docker

  mcp-services:
    env_file:
      - ../../mcp_services/.env.docker

  support-services:
    env_file:
      - ../../support_services/.env.docker
```

## Service URL Overrides

Docker Compose automatically overrides inter-service URLs to use Docker network names:

| Service | Variable | Original (.env.docker) | Override (Docker Compose) |
|---------|----------|----------------------|---------------------------|
| integrator | MCP_URL | `http://host.docker.internal:6666/sse` | `http://mcp-services:6666/sse` |
| mcp-services | AUTHORIZATION_HOST | `http://host.docker.internal:3000` | `http://agent-studio:3000` |
| mcp-services | INTEGRATOR_URL | `http://host.docker.internal:6060` | `http://integrator:6060` |
| support-services | INTEGRATOR_URL | `http://localhost:3000` | `http://agent-studio:3000` |

This allows:
- **Standalone mode**: Each service can run independently using `host.docker.internal`
- **Compose mode**: Services communicate via Docker network names automatically

## Configuration Files by Service

### Agent Studio (`agent-studio/.env.docker`)
```bash
# Authentication
LOGIN_PROVIDER=keycloak
AUTH_HOST_ID=agent-host
AUTH_HOST_SECRET=host-secret
AUTH_ISSUER=http://host.docker.internal:8888/realms/default
NEXTAUTH_SECRET=your-secret
NEXTAUTH_URL=http://localhost:3000

# Backend
INTEGRATOR_BASE_URL=http://host.docker.internal:6060

# Database
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/agent-studio

SECRET_KEY=your-secret-key
```

### Integrator (`integrator/.env.docker`)
```bash
ENV_LOADED=true
PORT=6060

# Model Configuration
VLLM_MODEL=azure/gpt-5
MAX_TEXT_EXTRACTION_LENGTH=20000

# Azure OpenAI
AZURE_API_VERSION=2024-12-01-preview
AZURE_API_BASE=https://your-resource.cognitiveservices.azure.com/
AZURE_API_KEY=your-api-key

# LangChain
LC_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_OPENAI_MODEL=gpt-5

# Services
IAM_URL=http://host.docker.internal:8888
MCP_URL=http://host.docker.internal:6666/sse  # Overridden by docker-compose

# Database & Storage
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/agent-studio
ETCD_HOST=host.docker.internal
ETCD_PORT=12379
NEO4J_URI=neo4j://host.docker.internal:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

SECRET_KEY=your-secret-key
```

### MCP Services (`mcp_services/.env.docker`)
```bash
PORT=6666

# IAM
IAM_URL=http://host.docker.internal:8888
REALM=default

# Transport
TRANSPORT=sse
AUTHORIZATION_ENABLED=true
AUTHORIZATION_HOST=http://host.docker.internal:3000  # Overridden by docker-compose
INTEGRATOR_URL=http://host.docker.internal:6060      # Overridden by docker-compose
PROXY_URL=http://host.docker.internal

# Database
DATABASE_URL=postgresql://user:password@host.docker.internal:5432/agent-studio

# Graphiti (optional)
GRAPHITI_ENABLED=false
GRAPHITI_URI=bolt://host.docker.internal:7687
GRAPHITI_USER=neo4j
GRAPHITI_PASSWORD=password

# Azure OpenAI
AZURE_ENDPOINT=https://your-resource.cognitiveservices.azure.com/
AZURE_API_KEY=your-api-key
AZURE_API_VERSION=2024-12-01-preview
AZURE_LLM_DEPLOYMENT=gpt-5
AZURE_EMBEDDING_DEPLOYMENT=text-embedding-3-small
```

### Support Services (`support_services/.env.docker`)
```bash
# Model
VLLM_MODEL=vertex_ai/gemini-2.0-flash
MAX_TEXT_EXTRACTION_LENGTH=20000

# Services
INTEGRATOR_URL=http://localhost:3000  # Overridden by docker-compose
PORT=6666

# IAM
IAM_URL=http://host.docker.internal:8888
REALM=default
```

## Benefits of This Approach

✅ **No duplication**: Each project maintains its own configuration
✅ **Consistency**: Same `.env.docker` files used for standalone and composed deployments
✅ **Flexibility**: Each service can be deployed independently
✅ **Simplicity**: No need to sync multiple environment files
✅ **Smart overrides**: Docker Compose handles inter-service URLs automatically

## Editing Environment Files

To edit a service's environment:

```bash
# Edit portal environment
vim agent-studio/.env.docker

# Edit integrator environment
vim integrator/.env.docker

# Edit MCP services environment
vim mcp_services/.env.docker

# Edit support services environment
vim support_services/.env.docker
```

After editing, restart the services:

```bash
cd deployment/docker
docker-compose restart
# or
docker-compose up -d --force-recreate
```

## Checking Current Configuration

View environment variables in a running container:

```bash
# View all variables
docker exec portal-container env

# View specific variable
docker exec portal-container printenv DATABASE_URL

# View variables for other services
docker exec integrator-app env
docker exec mcp-services-app env
docker exec support-services-app env
```

## Variable Priority

When the same variable is defined in multiple places:

1. **`environment` in docker-compose.yml** (highest priority - used for overrides)
2. **`env_file` (.env.docker)** (service defaults)
3. **Dockerfile ENV** (lowest priority - build-time defaults)

## Common Configuration Tasks

### Update Azure OpenAI Keys
Edit these files:
- `integrator/.env.docker`: Update `AZURE_API_KEY` and `AZURE_OPENAI_API_KEY`
- `mcp_services/.env.docker`: Update `AZURE_API_KEY`

### Update Database Connection
Edit all four `.env.docker` files (services that use database):
- `agent-studio/.env.docker`: Update `DATABASE_URL`
- `integrator/.env.docker`: Update `DATABASE_URL`
- `mcp_services/.env.docker`: Update `DATABASE_URL`

### Update IAM Service URL
Edit all four `.env.docker` files:
- Update `IAM_URL` in each file

### Change Model Configuration
- **Integrator**: Edit `integrator/.env.docker` → `VLLM_MODEL`
- **Support Services**: Edit `support_services/.env.docker` → `VLLM_MODEL`

## Troubleshooting

### Services can't communicate?
Check if Docker Compose overrides are working:
```bash
docker exec integrator-app printenv MCP_URL
# Should show: http://mcp-services:6666/sse (not host.docker.internal)
```

### Changes not taking effect?
```bash
# Recreate containers to reload environment
cd deployment/docker
docker-compose up -d --force-recreate
```

### Missing environment files?
Run the startup script to check:
```bash
cd deployment/docker
./docker-compose-up.sh
# It will report any missing .env.docker files
```
