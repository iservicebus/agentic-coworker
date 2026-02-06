# Support Platform Deployment

This directory contains Docker Compose configuration for the infrastructure services that support the AIntegrator platform.

## Services Included

The support platform provides the following infrastructure services:

### 1. **Keycloak** (Port 8888)
- Identity and Access Management (IAM)
- User authentication and authorization
- Admin credentials: `admin/admin`

### 2. **PostgreSQL with pgvector** (Port 5432)
- Main database with vector extension
- Credentials: `user/password`
- Database: `agent-studio`

### 3. **Neo4j** (Ports 7474, 7687)
- Graph database for relationship management
- HTTP UI: http://localhost:7474
- Bolt protocol: bolt://localhost:7687
- Credentials: `neo4j/password`
- Plugins: APOC, Graph Data Science

### 4. **ETCD** (Port 12379)
- Distributed key-value store
- Used for configuration management

### 5. **Traefik** (Ports 80, 8080)
- Reverse proxy and load balancer
- Dashboard: http://localhost:8080
- Configured with ETCD as dynamic provider

### 6. **NATS** (Ports 4222, 8222)
- Message broker with JetStream
- Client port: 4222
- Monitoring: http://localhost:8222

## Quick Start

### Start All Services

```bash
cd deployment/support-platform
docker-compose up -d
```

### Check Status

```bash
docker-compose ps
```

### View Logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f postgres
docker-compose logs -f keycloak
docker-compose logs -f neo4j
```

### Stop All Services

```bash
docker-compose down
```

### Stop and Remove Volumes

```bash
docker-compose down -v
```

## Initial Setup

After starting the services for the first time, you need to initialize the platform:

### 1. Clean Start (if needed)

```bash
# Stop and remove all volumes
docker-compose down
docker volume rm $(docker volume ls -q | grep -E 'keycloak_data|pgdata|neo4j_data|nats-data')

# Start fresh
docker-compose up -d
```

Wait for all services to be ready (30-60 seconds).

### 2. Initialize Keycloak (IAM)

```bash
cd ../../integrator/iam
python keycloak.py
```

### 3. Create Database Tables

```bash
cd ../../integrator/db
./create_tables.sh
```

### 4. Populate Initial Data

```bash
cd ../../integrator/db
./insert_tables.sh
```

### 5. Register Services

```bash
cd ../../integrator/scripts
./register_services.sh
```

### 6. Create Tool Index Tables

```bash
cd ../../tool_index
./create_tables.sh
```

### 7. Enqueue Tools

```bash
cd ../../tool_index
python producer.py --file services_backup.json
```

### 8. Ingest Tools

```bash
cd ../../tool_index
python consumer.py -i
```

## Service Access

Once started, services are available at:

| Service | URL | Credentials |
|---------|-----|-------------|
| Keycloak | http://localhost:8888 | admin/admin |
| PostgreSQL | localhost:5432 | user/password |
| Neo4j UI | http://localhost:7474 | neo4j/password |
| Traefik Dashboard | http://localhost:8080 | - |
| NATS Monitoring | http://localhost:8222 | - |

## Data Persistence

All service data is persisted in Docker volumes:

- `keycloak_data` - Keycloak configuration and realms
- `pgdata` - PostgreSQL database
- `neo4j_data` - Neo4j graph database
- `neo4j_logs` - Neo4j logs
- `neo4j_import` - Neo4j import directory
- `neo4j_plugins` - Neo4j plugins
- `nats-data` - NATS JetStream data

## Configuration

### PostgreSQL Initialization

The `init/` directory contains database initialization scripts that run on first startup.
See `init/init.md` for the complete initialization sequence.

### Keycloak

Default admin credentials are set via environment variables:
- Username: `admin`
- Password: `admin`

**⚠️ Change these in production!**

### Neo4j

Neo4j is configured with:
- Initial heap size: 1G
- Max heap size: 2G
- Page cache: 1G
- APOC and Graph Data Science plugins enabled
- Unrestricted procedures: `apoc.*`, `gds.*`

### ETCD

ETCD is configured to:
- Listen on port 2379 (mapped to 12379 on host)
- Work with Traefik for dynamic configuration

### Traefik

Traefik is configured with:
- HTTP entrypoint: port 80
- HTTPS entrypoint: port 443
- Dashboard enabled on port 8080
- ETCD as dynamic configuration provider

**⚠️ Dashboard is insecure (api.insecure=true) - don't use in production!**

## Networking

All services are connected via the `backend` Docker network, allowing them to communicate using service names as hostnames.

## Troubleshooting

### Services Not Starting

```bash
# Check logs
docker-compose logs

# Check specific service
docker-compose logs keycloak
```

### Port Conflicts

If ports are already in use:
1. Stop conflicting services
2. Or modify ports in docker-compose.yml

### Database Connection Issues

```bash
# Check PostgreSQL is ready
docker exec postgres pg_isready -U user

# Connect to database
docker exec -it postgres psql -U user -d agent-studio
```

### Neo4j Connection Issues

```bash
# Check Neo4j logs
docker-compose logs neo4j

# Verify Neo4j is running
docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1"
```

### Clear All Data and Restart

```bash
# Stop and remove everything
docker-compose down -v

# Remove all volumes
docker volume ls -q | grep -E 'keycloak_data|pgdata|neo4j_data|nats-data' | xargs docker volume rm

# Start fresh
docker-compose up -d

# Re-run initialization steps (see Initial Setup section)
```

## Production Considerations

When deploying to production:

1. **Change all default passwords**
   - Keycloak admin password
   - PostgreSQL password
   - Neo4j password

2. **Secure Traefik**
   - Remove `api.insecure=true`
   - Enable proper authentication
   - Configure TLS/SSL

3. **Resource Limits**
   - Add resource limits to each service
   - Adjust Neo4j memory settings based on workload

4. **Backup Strategy**
   - Regular backups of PostgreSQL
   - Regular backups of Neo4j
   - Backup Keycloak realm configurations

5. **Monitoring**
   - Add proper monitoring and alerting
   - Use NATS monitoring endpoint
   - Monitor Traefik metrics

6. **Network Security**
   - Use proper network policies
   - Don't expose all ports publicly
   - Use TLS for all connections

## Integration with Application Services

These support services are used by the main application services:
- **Agent Studio** uses PostgreSQL and Keycloak for authentication
- **Integrator** uses PostgreSQL, ETCD, and Neo4j
- **MCP Services** uses PostgreSQL and Neo4j (optional)
- All services can use NATS for messaging

Make sure these support services are running before starting the application services.

## Health Checks

Verify all services are healthy:

```bash
# PostgreSQL
docker exec postgres pg_isready -U user

# Neo4j
docker exec neo4j cypher-shell -u neo4j -p password "RETURN 1"

# Keycloak (wait for it to start, can take 30-60 seconds)
curl http://localhost:8888/health

# NATS
curl http://localhost:8222/healthz

# ETCD
docker exec etcd etcdctl endpoint health
```

## Logs Location

Service logs are stored in:
- Neo4j logs: `neo4j_logs` volume
- Other services: Docker container logs (use `docker-compose logs`)

## Support

For initialization sequence details, see `init/init.md`.

For issues with specific services, check their respective documentation:
- [Keycloak](https://www.keycloak.org/documentation)
- [PostgreSQL](https://www.postgresql.org/docs/)
- [Neo4j](https://neo4j.com/docs/)
- [Traefik](https://doc.traefik.io/traefik/)
- [ETCD](https://etcd.io/docs/)
- [NATS](https://docs.nats.io/)
