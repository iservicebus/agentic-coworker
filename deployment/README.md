# AIntegrator Deployment Guide

This directory contains deployment configurations for the AIntegrator platform.

## Deployment Options

Choose the deployment method that best fits your needs:

### 1. [Support Platform](./support-platform/) - Infrastructure Services
Required infrastructure services (PostgreSQL, Keycloak, Neo4j, ETCD, etc.)
- **Use for**: All deployment scenarios
- **Start first**: Before any application services
- **Quick start**: `cd support-platform && ./start.sh`

### 2. [Local Development](./local/) - Native Processes
Run services locally in separate terminal windows (macOS only)
- **Use for**: Active development and debugging
- **Best for**: Fast iteration, hot reload, debugging
- **Quick start**: `cd local && ./start.sh`

### 3. [Docker Compose](./docker/) - Containerized Services
Run all application services in Docker containers
- **Use for**: Testing, consistent environments
- **Best for**: Integration testing, multi-service testing
- **Quick start**: `cd docker && ./docker-compose-up.sh`

### 4. [Kubernetes](./kubernetes/) - Orchestrated Deployment
Deploy to Kubernetes (Docker Desktop or cloud)
- **Use for**: Production-like environments, scaling
- **Best for**: Production deployments, high availability
- **Quick start**: `cd kubernetes && ./deploy.sh`

## Application Services

The AIntegrator platform consists of four main application services:

1. **Portal** (port 3000) - Next.js frontend application
2. **Integrator** (port 6060) - Main integration service
3. **MCP Services** (port 6666) - Model Context Protocol services
4. **Support Services** (port 5000) - Supporting API services

## Infrastructure Services

All deployments require the support platform infrastructure:

1. **Keycloak** (port 8888) - Identity and Access Management
2. **PostgreSQL** (port 5432) - Database with pgvector
3. **Neo4j** (ports 7474, 7687) - Graph database
4. **ETCD** (port 12379) - Configuration management
5. **Traefik** (ports 80, 8080) - Reverse proxy
6. **NATS** (ports 4222, 8222) - Message broker

## Quick Start Guide

### Step 1: Start Support Platform

**Always start this first**, regardless of which deployment method you choose:

```bash
cd deployment/support-platform
./start.sh
```

Wait for all services to be ready (30-60 seconds), then follow the initialization steps in `support-platform/README.md`.

### Step 2: Choose Your Deployment Method

#### Option A: Local Development (macOS)
```bash
cd deployment/local
./start.sh
```

#### Option B: Docker Compose
```bash
cd deployment/docker
./docker-compose-up.sh
```

#### Option C: Kubernetes
```bash
cd deployment/kubernetes
./deploy.sh
```

## Prerequisites

### For All Deployments
- Support platform running (see Step 1 above)
- Each service configured with environment files

### For Docker Compose
- Docker Desktop installed
- Built Docker images for all services

### For Kubernetes
- Docker Desktop with Kubernetes enabled
- Built Docker images for all services

### For Local Development
- macOS (uses Terminal.app with AppleScript)
- All service dependencies installed locally
- Each service has a `start.sh` script

## Deployment Details

### Support Platform Deployment

See [support-platform/README.md](./support-platform/README.md) for detailed documentation.

### Local Development Deployment

See [local/README.md](./local/README.md) for detailed documentation.

**Note**: Local deployment is macOS-only and requires Terminal.app.

### Building Docker Images

Before using Docker Compose or Kubernetes, build all Docker images:

```bash
# From the project root directory

# Build Portal
cd portal
docker build -t portal:latest .

# Build Integrator
cd ../integrator
docker build -t integrator:latest .

# Build MCP Services
cd ../mcp_services
docker build -t mcp-services:latest .

# Build Support Services
cd ../support_services
docker build -t support-services:latest .

cd ..
```

## Docker Compose Deployment

### Setup

The Docker Compose configuration uses the **existing `.env.docker` files** from each project:
- `portal/scripts/.env.docker`
- `integrator/.env.docker`
- `mcp_services/.env.docker`
- `support_services/.env.docker`

**Steps:**

1. Ensure each project has its `.env.docker` file configured:
```bash
# Check existing .env.docker files
ls -la portal/scripts/.env.docker
ls -la integrator/.env.docker
ls -la mcp_services/.env.docker
ls -la support_services/.env.docker
```

2. Edit the `.env.docker` files if needed:
```bash
# Edit each service's environment file
vim portal/scripts/.env.docker
vim integrator/.env.docker
vim mcp_services/.env.docker
vim support_services/.env.docker
```

Key values to update in each file:
- `SECRET_KEY` - Generate a random secret key
- `NEXTAUTH_SECRET` - Generate a random secret for NextAuth (portal)
- `DATABASE_URL` - Your PostgreSQL connection string
- `AZURE_API_KEY` - Your Azure OpenAI API key
- `AZURE_API_BASE` / `AZURE_ENDPOINT` - Your Azure OpenAI endpoint
- `NEO4J_PASSWORD` - Your Neo4j password
- `IAM_URL` - Your IAM service URL
- Other service-specific credentials

**Note**: Docker Compose automatically overrides inter-service URLs to use Docker network names (e.g., `http://mcp-services:6666` instead of `http://host.docker.internal:6666`)

### Running with Docker Compose

```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# View logs for specific service
docker-compose logs -f portal
docker-compose logs -f integrator
docker-compose logs -f mcp-services
docker-compose logs -f support-services

# Stop all services
docker-compose down

# Stop and remove volumes
docker-compose down -v
```

### Accessing Services

Once running, services are available at:
- Portal: http://localhost:3000
- Integrator: http://localhost:6060
- MCP Services: http://localhost:6666
- Support Services: http://localhost:5000

### Troubleshooting Docker Compose

1. **Services can't connect to each other**
   - Check that all services are on the same network
   - Verify service names in environment variables

2. **Services can't connect to external dependencies**
   - Ensure `host.docker.internal` resolves correctly
   - On Linux, you may need to add `--add-host=host.docker.internal:host-gateway`

3. **Health checks failing**
   - Check service logs: `docker-compose logs <service-name>`
   - Verify environment variables are set correctly

## Kubernetes Deployment

### Setup

1. Ensure Docker Desktop Kubernetes is enabled:
   - Docker Desktop → Settings → Kubernetes → Enable Kubernetes

2. Verify Kubernetes is running:
```bash
kubectl cluster-info
kubectl get nodes
```

3. Navigate to Kubernetes deployment directory:
```bash
cd deployment/kubernetes
```

4. Create secrets file from template:
```bash
cp secret.yaml.template secret.yaml
```

5. Edit `secret.yaml` and fill in your actual secrets:
```bash
# Use your preferred editor
nano secret.yaml
# or
vim secret.yaml
```

**IMPORTANT**: Do not commit `secret.yaml` to version control!

6. Review and update `configmap.yaml` if needed:
   - Update external service URLs
   - Adjust model configurations
   - Modify other non-sensitive settings

### Deploying to Kubernetes

```bash
# Create namespace
kubectl apply -f namespace.yaml

# Create ConfigMap
kubectl apply -f configmap.yaml

# Create Secrets (ensure you've edited secret.yaml first!)
kubectl apply -f secret.yaml

# Deploy all services
kubectl apply -f portal-deployment.yaml
kubectl apply -f integrator-deployment.yaml
kubectl apply -f mcp-services-deployment.yaml
kubectl apply -f support-services-deployment.yaml
```

### Verifying Deployment

```bash
# Check all resources in the namespace
kubectl get all -n aintegrator

# Check pod status
kubectl get pods -n aintegrator

# Check services
kubectl get services -n aintegrator

# View logs for a specific pod
kubectl logs -n aintegrator <pod-name>

# Follow logs
kubectl logs -n aintegrator <pod-name> -f

# Describe a pod for troubleshooting
kubectl describe pod -n aintegrator <pod-name>
```

### Accessing Services

Services are exposed via NodePort:
- Portal: http://localhost:30000
- Integrator: http://localhost:30060
- MCP Services: http://localhost:30666
- Support Services: http://localhost:30500

### Updating Deployments

```bash
# After updating ConfigMap or Secrets
kubectl apply -f configmap.yaml
kubectl apply -f secret.yaml

# Restart deployments to pick up changes
kubectl rollout restart deployment/portal -n aintegrator
kubectl rollout restart deployment/integrator -n aintegrator
kubectl rollout restart deployment/mcp-services -n aintegrator
kubectl rollout restart deployment/support-services -n aintegrator

# Check rollout status
kubectl rollout status deployment/portal -n aintegrator
```

### Scaling Services

```bash
# Scale a deployment
kubectl scale deployment/integrator --replicas=3 -n aintegrator

# Verify scaling
kubectl get pods -n aintegrator
```

### Troubleshooting Kubernetes

1. **Pods not starting**
   ```bash
   kubectl describe pod -n aintegrator <pod-name>
   kubectl logs -n aintegrator <pod-name>
   ```

2. **ImagePullBackOff error**
   - Ensure Docker images are built and available locally
   - For Docker Desktop, images should be in the local Docker registry

3. **Services can't reach external dependencies**
   - Update `host.docker.internal` references in `configmap.yaml`
   - For Linux, may need to use actual host IP address

4. **Configuration issues**
   - Verify ConfigMap: `kubectl get configmap aintegrator-config -n aintegrator -o yaml`
   - Verify Secrets exist: `kubectl get secrets -n aintegrator`
   - Check environment variables in pods: `kubectl exec -n aintegrator <pod-name> -- env`

### Cleaning Up

```bash
# Delete all resources in the namespace
kubectl delete namespace aintegrator

# Or delete individual resources
kubectl delete -f portal-deployment.yaml
kubectl delete -f integrator-deployment.yaml
kubectl delete -f mcp-services-deployment.yaml
kubectl delete -f support-services-deployment.yaml
kubectl delete -f configmap.yaml
kubectl delete -f secret.yaml
kubectl delete -f namespace.yaml
```

## Environment Variables Reference

### Common Variables
- `SECRET_KEY` - Application secret key
- `REALM` - Authentication realm (default: "default")
- `DATABASE_URL` - PostgreSQL connection string
- `IAM_URL` - IAM service URL
- `ETCD_HOST` / `ETCD_PORT` - ETCD configuration
- `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` - Neo4j configuration

### Azure OpenAI
- `AZURE_API_KEY` - Azure OpenAI API key
- `AZURE_API_BASE` / `AZURE_ENDPOINT` - Azure OpenAI endpoint
- `AZURE_API_VERSION` - API version
- `AZURE_OPENAI_MODEL` - Model deployment name
- `AZURE_LLM_DEPLOYMENT` - LLM deployment name
- `AZURE_EMBEDDING_DEPLOYMENT` - Embedding model deployment name

### Service-Specific

#### Portal
- `NEXTAUTH_URL` - NextAuth callback URL
- `NEXTAUTH_SECRET` - NextAuth secret key

#### Integrator
- `VLLM_MODEL` - LLM model to use
- `MAX_TEXT_EXTRACTION_LENGTH` - Maximum text extraction length
- `MCP_URL` - MCP service URL

#### MCP Services
- `TRANSPORT` - Transport protocol (default: "sse")
- `AUTHORIZATION_ENABLED` - Enable authorization
- `AUTHORIZATION_HOST` - Authorization service URL
- `GRAPHITI_ENABLED` - Enable Graphiti features
- `GRAPHITI_URI` - Graphiti/Neo4j connection

#### Support Services
- `VLLM_MODEL` - LLM model to use
- `INTEGRATOR_URL` - Portal/Integrator service URL

## Security Considerations

1. **Never commit secrets to version control**
   - Add `.env` and `secret.yaml` to `.gitignore`
   - Use secure secret management in production

2. **Use strong secrets**
   - Generate random, complex values for all secret keys
   - Rotate secrets regularly

3. **Network security**
   - In production, use proper ingress controllers
   - Implement TLS/SSL for external access
   - Use network policies to restrict inter-service communication

4. **Container security**
   - Keep base images updated
   - Scan images for vulnerabilities
   - Run containers as non-root users (already configured)

## Deployment Comparison

| Aspect | Local | Docker Compose | Kubernetes |
|--------|-------|----------------|------------|
| **Platform** | macOS only | Cross-platform | Cross-platform |
| **Startup Speed** | Fast | Medium | Slower |
| **Hot Reload** | Yes (Portal) | Possible with volumes | No |
| **Isolation** | Process-level | Container-level | Pod-level |
| **Scaling** | Manual | Limited | Automatic |
| **Resource Usage** | Lower | Medium | Higher |
| **Log Access** | Separate terminals | `docker-compose logs` | `kubectl logs` |
| **Best For** | Development | Testing | Production |
| **Debugging** | Excellent | Good | Moderate |
| **Consistency** | Lower | High | Highest |

## Port Reference

### Application Services

| Service | Port | Access URL |
|---------|------|------------|
| Portal | 3000 | http://localhost:3000 |
| Integrator | 6060 | http://localhost:6060 |
| MCP Services | 6666 | http://localhost:6666 |
| Support Services | 5000 | http://localhost:5000 |

### Infrastructure Services (Support Platform)

| Service | Port | Access URL |
|---------|------|------------|
| Keycloak | 8888 | http://localhost:8888 |
| PostgreSQL | 5432 | localhost:5432 |
| Neo4j UI | 7474 | http://localhost:7474 |
| Neo4j Bolt | 7687 | bolt://localhost:7687 |
| Traefik Dashboard | 8080 | http://localhost:8080 |
| ETCD | 12379 | localhost:12379 |
| NATS Client | 4222 | localhost:4222 |
| NATS Monitoring | 8222 | http://localhost:8222 |

### Kubernetes NodePorts

| Service | NodePort | Access URL |
|---------|----------|------------|
| Portal | 30000 | http://localhost:30000 |
| Integrator | 30060 | http://localhost:30060 |
| MCP Services | 30666 | http://localhost:30666 |
| Support Services | 30500 | http://localhost:30500 |

## Production Considerations

For production deployments:

1. **Use proper orchestration**
   - Consider managed Kubernetes (EKS, GKE, AKS)
   - Implement proper CI/CD pipelines

2. **High availability**
   - Run multiple replicas of each service
   - Use pod disruption budgets
   - Implement proper health checks

3. **Monitoring and logging**
   - Integrate with monitoring tools (Prometheus, Grafana)
   - Set up centralized logging (ELK stack, CloudWatch)
   - Configure alerts for critical issues

4. **Resource management**
   - Set appropriate resource requests and limits
   - Monitor resource usage and adjust as needed
   - Use horizontal pod autoscaling

5. **Database and external services**
   - Use managed database services
   - Implement proper backup strategies
   - Use connection pooling

## Support

For issues or questions:
1. Check service logs first
2. Verify environment configuration
3. Ensure external dependencies are accessible
4. Review this documentation
