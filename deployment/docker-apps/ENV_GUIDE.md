# Docker Compose Environment Variables Guide

## How Docker Compose Reads `.env` Files

Docker Compose has **two ways** to use environment variables:

### 1. `.env` File (Automatic Loading)
Docker Compose **automatically** reads a `.env` file from the same directory as `docker-compose.yml`.

**Location**: `deployment/docker/.env`

This file is used for:
- **Variable substitution** in the `docker-compose.yml` itself (e.g., `${HOME}`)
- Does NOT automatically pass variables to containers

### 2. `env_file` Directive (Direct Container Environment)
The `env_file` directive passes environment variables **directly to containers**.

```yaml
services:
  portal:
    env_file:
      - .env  # All variables from .env are loaded into the container
```

## Our Implementation

We use **both approaches** for maximum flexibility:

```yaml
services:
  portal:
    env_file:
      - .env           # Load ALL variables from .env into the container
    environment:
      - CUSTOM_VAR=value  # Override or add specific variables
```

### Benefits

✅ **Simple Configuration**: Just one `.env` file for all services
✅ **Easy Maintenance**: Update variables in one place
✅ **Override Capability**: Can override specific variables per service
✅ **Clean YAML**: No need to list every variable in docker-compose.yml

## How It Works

1. **Copy template to .env**:
   ```bash
   cp .env.template .env
   ```

2. **Edit .env** with your actual values:
   ```bash
   vim .env
   ```

3. **Run Docker Compose**:
   ```bash
   docker-compose up -d
   ```

4. **Docker Compose automatically**:
   - Reads `.env` file
   - Passes ALL variables from `.env` to each container (via `env_file`)
   - Overrides with any `environment` values in docker-compose.yml

## Service-Specific Overrides

For inter-service communication, we override URLs in docker-compose.yml:

```yaml
integrator:
  env_file:
    - .env
  environment:
    # Override to use Docker network names instead of localhost
    - MCP_URL=http://mcp-services:6666/sse
```

This allows:
- `.env` to have external/localhost URLs (e.g., for debugging)
- Docker Compose to override with internal Docker network URLs

## Variable Priority (Highest to Lowest)

1. **`environment` in docker-compose.yml** (highest priority)
2. **`env_file` directive** (.env file)
3. **Container's Dockerfile ENV** (lowest priority)

## Example

**.env file**:
```bash
DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/db
MCP_URL=http://localhost:6666/sse
```

**docker-compose.yml**:
```yaml
integrator:
  env_file:
    - .env
  environment:
    - MCP_URL=http://mcp-services:6666/sse  # Overrides .env value
```

**Result in container**:
- `DATABASE_URL=postgresql://user:pass@host.docker.internal:5432/db` (from .env)
- `MCP_URL=http://mcp-services:6666/sse` (from environment, overrides .env)

## Multiple .env Files (Alternative Approach)

You can also use multiple env files:

```yaml
services:
  portal:
    env_file:
      - .env.common     # Shared variables
      - .env.portal     # Portal-specific variables
```

## Checking Environment Variables

To see what variables are loaded in a running container:

```bash
# List all environment variables
docker exec portal-container env

# Check a specific variable
docker exec portal-container printenv DATABASE_URL
```

## Best Practices

1. **Never commit `.env` to Git** (already in .gitignore)
2. **Use `.env.template`** as documentation
3. **Group related variables** with comments
4. **Use descriptive names** for clarity
5. **Document required vs optional** variables
6. **Use defaults** where sensible (via `${VAR:-default}`)

## Troubleshooting

### Variables not loading?
1. Check `.env` file exists: `ls -la .env`
2. Check file format: No spaces around `=`, one variable per line
3. Restart services: `docker-compose restart`

### Wrong values?
1. Check override in docker-compose.yml `environment` section
2. Check variable priority (see above)
3. Verify with: `docker exec <container> env | grep VAR_NAME`

### Changes not taking effect?
```bash
# Recreate containers to reload environment
docker-compose up -d --force-recreate
```
