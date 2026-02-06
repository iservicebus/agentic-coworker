# AIntegrator Quick Start Guide

Get AIntegrator up and running in minutes!

## Choose Your Path

### 🚀 Path 1: Local Development (Fastest for Development)

**Best for**: Active development, debugging, fast iteration

```bash
# Step 1: Start infrastructure
cd deployment/support-platform
./start.sh

# Step 2: Wait 30-60 seconds, then start services
cd ../local
./start.sh
```

**Access**:
- Agent Studio: http://localhost:3000
- View logs in separate terminal windows

**Requirements**: macOS only

---

### 🐳 Path 2: Docker Compose (Best for Testing)

**Best for**: Integration testing, consistent environment

```bash
# Step 1: Build images
cd agent-studio && docker build -t portal:latest .
cd ../integrator && docker build -t integrator:latest .
cd ../mcp_services && docker build -t mcp-services:latest .
cd ../support_services && docker build -t support-services:latest .

# Step 2: Start infrastructure
cd ../deployment/support-platform
./start.sh

# Step 3: Wait 30-60 seconds, then start services
cd ../docker
./docker-compose-up.sh
```

**Access**:
- Agent Studio: http://localhost:3000
- View logs: `docker-compose logs -f`

**Requirements**: Docker Desktop

---

### ☸️ Path 3: Kubernetes (Production-like)

**Best for**: Production deployments, scaling, high availability

```bash
# Step 1: Build images (same as Docker Compose)
# ... build all images ...

# Step 2: Start infrastructure
cd deployment/support-platform
./start.sh

# Step 3: Configure secrets
cd ../kubernetes
cp secret.yaml.template secret.yaml
vim secret.yaml  # Edit with your secrets

# Step 4: Deploy to Kubernetes
./deploy.sh
```

**Access**:
- Agent Studio: http://localhost:30000
- View logs: `kubectl logs -n aintegrator <pod-name>`

**Requirements**: Docker Desktop with Kubernetes enabled

---

## Detailed Steps

### First Time Setup

#### 1. Start Support Platform (Required)

```bash
cd deployment/support-platform
./start.sh
```

**Wait for all services to be ready** (30-60 seconds)

Verify:
```bash
docker-compose ps
# All services should show "Up"
```

#### 2. Initialize Support Platform (First Time Only)

Run these initialization steps in order:

```bash
# 2.1 Initialize Keycloak
cd ../../integrator/iam
python keycloak.py

# 2.2 Create database tables
cd ../db
./create_tables.sh

# 2.3 Populate initial data
./insert_tables.sh

# 2.4 Register services
cd ../scripts
./register_services.sh

# 2.5 Create tool index tables
cd ../../tool_index
./create_tables.sh

# 2.6 Enqueue tools
python producer.py --file services_backup.json

# 2.7 Ingest tools
python consumer.py -i
```

#### 3. Configure Environment Files

Each service needs its environment file configured:

```bash
# Check existing .env.docker files
ls -la portal/scripts/.env.docker
ls -la integrator/.env.docker
ls -la mcp_services/.env.docker
ls -la support_services/.env.docker

# Edit if needed
vim portal/scripts/.env.docker
vim integrator/.env.docker
vim mcp_services/.env.docker
vim support_services/.env.docker
```

Update these key values:
- Database URLs
- Azure OpenAI credentials
- Keycloak/IAM settings
- Neo4j password

#### 4. Start Application Services

Choose your deployment method (see paths above).

### Daily Development Workflow

After first-time setup, daily workflow is simpler:

```bash
# Morning: Start everything
cd deployment/support-platform && ./start.sh
cd ../local && ./start.sh  # Or ../docker/docker-compose-up.sh

# Develop...

# Evening: Stop everything
cd deployment/local && ./stop.sh  # Or ../docker/docker-compose down
cd ../support-platform && docker-compose down
```

## Troubleshooting

### Services won't start

1. **Check support platform is running**:
   ```bash
   cd deployment/support-platform
   docker-compose ps
   ```

2. **Check ports aren't in use**:
   ```bash
   lsof -i :3000  # Portal
   lsof -i :6060  # Integrator
   lsof -i :6666  # MCP Services
   lsof -i :5000  # Support Services
   ```

3. **Check environment files exist**:
   ```bash
   ls -la portal/scripts/.env.docker
   ls -la integrator/.env.docker
   ls -la mcp_services/.env.docker
   ls -la support_services/.env.docker
   ```

### Can't connect to database

```bash
# Check PostgreSQL is running
docker exec postgres pg_isready -U user

# Try connecting
docker exec -it postgres psql -U user -d agent-studio
```

### Can't access Keycloak

```bash
# Check Keycloak is running
docker ps | grep keycloak

# Wait for it to fully start (can take 30-60 seconds)
curl http://localhost:8888/health
```

### Docker Compose services can't start

```bash
# Check images are built
docker images | grep -E "portal|integrator|mcp-services|support-services"

# Rebuild if needed
docker-compose build
```

### Kubernetes pods not starting

```bash
# Check pod status
kubectl get pods -n aintegrator

# Check events
kubectl describe pod -n aintegrator <pod-name>

# Check logs
kubectl logs -n aintegrator <pod-name>
```

## Common Commands

### Support Platform

```bash
# Start
cd deployment/support-platform
./start.sh

# Stop
docker-compose down

# View logs
docker-compose logs -f

# Restart single service
docker-compose restart postgres
```

### Local Deployment

```bash
# Start
cd deployment/local
./start.sh

# Stop
./stop.sh

# Restart single service - close its terminal and run manually
cd integrator && ./start.sh
```

### Docker Compose

```bash
# Start
cd deployment/docker
./docker-compose-up.sh

# Stop
docker-compose down

# View logs
docker-compose logs -f agent-studio

# Restart service
docker-compose restart integrator
```

### Kubernetes

```bash
# Deploy
cd deployment/kubernetes
./deploy.sh

# Check status
kubectl get all -n aintegrator

# View logs
kubectl logs -n aintegrator -l app=agent-studio

# Restart deployment
kubectl rollout restart deployment/integrator -n aintegrator

# Delete everything
kubectl delete namespace aintegrator
```

## Next Steps

- Read detailed documentation in each deployment folder
- Configure environment variables for your setup
- Check service health after startup
- Review logs if issues occur

## Getting Help

- **Support Platform**: See `deployment/support-platform/README.md`
- **Local Deployment**: See `deployment/local/README.md`
- **Docker Compose**: See `deployment/docker/README.md` (in main README)
- **Kubernetes**: See `deployment/kubernetes/README.md` (in main README)
- **Environment Files**: See `deployment/docker/ENV_FILES.md`

## Access Points Summary

| Service | Local/Docker | Kubernetes | Support Platform |
|---------|--------------|------------|------------------|
| Agent Studio | :3000 | :30000 | - |
| Integrator | :6060 | :30060 | - |
| MCP Services | :6666 | :30666 | - |
| Support Services | :5000 | :30500 | - |
| Keycloak | :8888 | - | :8888 |
| PostgreSQL | :5432 | - | :5432 |
| Neo4j UI | :7474 | - | :7474 |
| Traefik | :8080 | - | :8080 |

All URLs: `http://localhost:<port>`
