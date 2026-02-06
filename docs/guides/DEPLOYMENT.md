# Agentic Coworker - Deployment Guide

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Environment Setup](#environment-setup)
- [Local Development Deployment](#local-development-deployment)
- [Staging Deployment](#staging-deployment)
- [Production Deployment](#production-deployment)
- [Docker Deployment](#docker-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Database Setup and Migrations](#database-setup-and-migrations)
- [Configuration Management](#configuration-management)
- [Monitoring and Logging](#monitoring-and-logging)
- [Backup and Disaster Recovery](#backup-and-disaster-recovery)
- [Troubleshooting](#troubleshooting)

## Overview

This guide provides comprehensive instructions for deploying the Agentic Coworker platform across different environments, from local development to production-grade deployments.

### Deployment Options

| Option | Use Case | Complexity | Scalability |
|--------|----------|------------|-------------|
| Docker Compose | Development, Testing | Low | Limited |
| Docker Swarm | Small Production | Medium | Moderate |
| Kubernetes | Enterprise Production | High | Excellent |
| Cloud Managed | Fully Managed | Medium | Excellent |

## Prerequisites

### System Requirements

#### Minimum Requirements (Development)
- **CPU**: 4 cores
- **RAM**: 8 GB
- **Storage**: 50 GB SSD
- **OS**: Linux (Ubuntu 22.04+), macOS 12+, Windows 11 (with WSL2)

#### Recommended Requirements (Production)
- **CPU**: 16 cores
- **RAM**: 32 GB
- **Storage**: 500 GB SSD (NVMe preferred)
- **OS**: Linux (Ubuntu 22.04 LTS recommended)
- **Network**: 1 Gbps

### Software Requirements

| Software | Minimum Version | Purpose |
|----------|-----------------|---------|
| Docker | 24.0+ | Containerization |
| Docker Compose | 2.20+ | Multi-container orchestration |
| Git | 2.30+ | Version control |
| Python | 3.11+ | Backend development |
| Node.js | 18+ | Frontend development |
| npm/yarn | 9+/1.22+ | Package management |

### Network Requirements

**Ports to Expose**:
```
3000    # Agent Studio (Web UI)
6060    # Integrator API
6666    # MCP Services
5000    # Support Services
8888    # Keycloak (IAM)
5432    # PostgreSQL (if external access needed)
7474    # Neo4j Browser
7687    # Neo4j Bolt
2379    # ETCD Client
4222    # NATS
80/443  # Traefik HTTP/HTTPS
```

**Domain Configuration**:
- Add `127.0.0.1 host.docker.internal` to `/etc/hosts` (Linux/macOS) or `C:\Windows\System32\drivers\etc\hosts` (Windows)

## Environment Setup

### 1. Clone Repository

```bash
git clone https://github.com/YOUR_USERNAME/agentic-coworker.git
cd agentic-coworker
```

### 2. Configure Environment Variables

```bash
# Copy sample environment file
cp .env.docker.sample .env.docker

# Edit with your configuration
nano .env.docker  # or use your preferred editor
```

### 3. Configure AI Provider

Choose one of the supported LLM providers:

#### Azure OpenAI (Default)
```bash
MODEL_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_MODEL=gpt-5
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

#### OpenAI
```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### Google AI
```bash
MODEL_PROVIDER=google_genai
GOOGLE_API_KEY=your-google-api-key
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-001
```

#### Anthropic Claude
```bash
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
LOCAL_EMBEDDING_MODEL=rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
LOCAL_EMBEDDING_BASE_URL=http://host.docker.internal:11434
```

#### Local OpenAI/MLX (On-Premises)
```bash
MODEL_PROVIDER=local_openai
LOCAL_OPENAI_BASE_URL=http://host.docker.internal:5555/v1
LOCAL_OPENAI_API_KEY="local"
LOCAL_OPENAI_MODEL=gpt-oss-20b  # or gpt-oss-120b
LOCAL_EMBEDDING_MODEL=rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
LOCAL_EMBEDDING_BASE_URL=http://host.docker.internal:11434
```

## Local Development Deployment

### Quick Start

```bash
# Start all services
docker-compose up -d

# Check status
docker-compose ps

# View logs
docker-compose logs -f

# Access services
open http://localhost:3000        # Agent Studio
open http://localhost:8888        # Keycloak (admin/admin)
open http://localhost:6060/docs   # Integrator API Docs
```

### First-Time Setup

1. **Wait for Services to Initialize** (2-3 minutes)
   ```bash
   # Monitor initialization
   docker-compose logs -f postgres keycloak
   ```

2. **Verify Database Seeding**
   ```bash
   docker exec postgres psql -U user -d agent-studio -c "SELECT COUNT(*) FROM tenants;"
   ```

3. **Check Keycloak Configuration**
   ```bash
   # Access Keycloak admin console
   # URL: http://localhost:8888
   # Credentials: admin / admin
   ```

4. **Login to Agent Studio**
   ```bash
   # Navigate to http://localhost:3000
   # Use Keycloak credentials or configure OAuth providers
   ```

### Development Workflow

```bash
# Make code changes
# Rebuild specific service
docker-compose build agent-studio
docker-compose up -d agent-studio

# View specific service logs
docker-compose logs -f agent-studio

# Restart all services
docker-compose restart

# Stop services
docker-compose stop

# Clean up (removes containers and volumes)
docker-compose down -v
```

## Staging Deployment

Staging environment mirrors production with test data.

### Configuration

```bash
# Create staging environment file
cp .env.docker .env.staging

# Update staging-specific values
nano .env.staging
```

**Key Staging Settings**:
```bash
# Use staging credentials
AZURE_OPENAI_API_KEY=staging-key
DATABASE_URL=postgresql://user:password@staging-db:5432/agent-studio-staging

# Enable debug logging
LOG_LEVEL=DEBUG

# Use staging OAuth providers
# (configure separate OAuth apps for staging)
```

### Deploy to Staging

```bash
# Use staging environment
docker-compose --env-file .env.staging up -d

# Run smoke tests
./scripts/smoke-tests.sh staging

# Verify deployments
curl http://staging.yourdomain.com/health
```

## Production Deployment

### Pre-Production Checklist

- [ ] SSL/TLS certificates configured
- [ ] Production database backups enabled
- [ ] Monitoring and alerting configured
- [ ] Rate limiting configured
- [ ] OAuth providers configured with production URLs
- [ ] API keys rotated and secured
- [ ] Security hardening applied
- [ ] Load testing completed
- [ ] Disaster recovery plan documented
- [ ] Team trained on operations

### Production Environment Setup

#### 1. Secure Configuration

```bash
# Use production environment file
cp .env.docker .env.production

# Set production values
nano .env.production
```

**Critical Production Settings**:
```bash
# Use production credentials
AZURE_OPENAI_API_KEY=prod-key

# Production database
DATABASE_URL=postgresql://user:strong-password@prod-db:5432/agent-studio

# Production URLs
NEXTAUTH_URL=https://yourdomain.com
NEXTAUTH_SECRET=generate-strong-secret-here

# Disable debug
LOG_LEVEL=INFO

# Enable production mode
NODE_ENV=production
PYTHON_ENV=production

# Security settings
ISSUER_VALIDATION=true
AUTHORIZATION_ENABLED=true
```

#### 2. SSL/TLS Configuration

**Using Traefik with Let's Encrypt**:

```yaml
# docker-compose.prod.yml
services:
  traefik:
    command:
      - "--certificatesresolvers.letsencrypt.acme.email=admin@yourdomain.com"
      - "--certificatesresolvers.letsencrypt.acme.storage=/letsencrypt/acme.json"
      - "--certificatesresolvers.letsencrypt.acme.tlschallenge=true"
    volumes:
      - "./letsencrypt:/letsencrypt"
    labels:
      - "traefik.http.routers.agent-studio.tls.certresolver=letsencrypt"
```

#### 3. Database Configuration

**External PostgreSQL** (Recommended):
```bash
# Managed database (RDS, Cloud SQL, etc.)
DATABASE_URL=postgresql://user:password@prod-db.example.com:5432/agent-studio?sslmode=require

# Connection pooling
DB_POOL_SIZE=20
DB_MAX_OVERFLOW=10
DB_POOL_TIMEOUT=30
```

**Database Optimization**:
```sql
-- PostgreSQL configuration (postgresql.conf)
shared_buffers = 4GB
effective_cache_size = 12GB
maintenance_work_mem = 1GB
checkpoint_completion_target = 0.9
wal_buffers = 16MB
default_statistics_target = 100
random_page_cost = 1.1
effective_io_concurrency = 200
work_mem = 10MB
min_wal_size = 1GB
max_wal_size = 4GB
max_worker_processes = 8
max_parallel_workers_per_gather = 4
max_parallel_workers = 8
```

#### 4. Deploy to Production

```bash
# Pull latest images
docker-compose -f docker-compose.yml -f docker-compose.prod.yml pull

# Start services
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d

# Verify health
curl https://yourdomain.com/api/health

# Monitor logs
docker-compose -f docker-compose.yml -f docker-compose.prod.yml logs -f
```

## Docker Deployment

### Multi-Stage Builds

**Optimized Dockerfile for Agent Studio**:
```dockerfile
# Build stage
FROM node:18-alpine AS builder
WORKDIR /app
COPY package*.json ./
RUN npm ci --only=production
COPY . .
RUN npm run build

# Production stage
FROM node:18-alpine
WORKDIR /app
COPY --from=builder /app/.next ./.next
COPY --from=builder /app/node_modules ./node_modules
COPY --from=builder /app/package.json ./
EXPOSE 3000
CMD ["npm", "start"]
```

### Docker Compose Production Configuration

```yaml
version: '3.8'

services:
  agent-studio:
    image: agentic-coworker/agent-studio:latest
    restart: always
    environment:
      - NODE_ENV=production
    deploy:
      resources:
        limits:
          cpus: '2'
          memory: 4G
        reservations:
          cpus: '1'
          memory: 2G
      replicas: 2
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/api/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s

  integrator:
    image: agentic-coworker/integrator:latest
    restart: always
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G
      replicas: 3
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:6060/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  postgres:
    image: pgvector/pgvector:pg15
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: agent-studio
    volumes:
      - postgres-data:/var/lib/postgresql/data
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G

volumes:
  postgres-data:
    driver: local
```

### Docker Swarm Deployment

```bash
# Initialize swarm
docker swarm init

# Deploy stack
docker stack deploy -c docker-compose.yml -c docker-compose.prod.yml agentic-coworker

# Check services
docker stack services agentic-coworker

# Scale services
docker service scale agentic-coworker_integrator=5

# Update service
docker service update --image agentic-coworker/integrator:v2.0 agentic-coworker_integrator

# Remove stack
docker stack rm agentic-coworker
```

## Kubernetes Deployment

### Prerequisites

```bash
# Install kubectl
curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"
chmod +x kubectl
sudo mv kubectl /usr/local/bin/

# Verify installation
kubectl version --client
```

### Kubernetes Manifests

#### Namespace

```yaml
# k8s/namespace.yaml
apiVersion: v1
kind: Namespace
metadata:
  name: agentic-coworker
```

#### ConfigMap

```yaml
# k8s/configmap.yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: agentic-coworker-config
  namespace: agentic-coworker
data:
  MODEL_PROVIDER: "azure_openai"
  INTEGRATOR_PORT: "6060"
  MCP_PORT: "6666"
  SUPPORT_PORT: "5000"
```

#### Secrets

```yaml
# k8s/secrets.yaml
apiVersion: v1
kind: Secret
metadata:
  name: agentic-coworker-secrets
  namespace: agentic-coworker
type: Opaque
stringData:
  AZURE_OPENAI_API_KEY: "your-api-key"
  DATABASE_URL: "postgresql://user:password@postgres:5432/agent-studio"
  NEXTAUTH_SECRET: "generate-strong-secret"
```

#### Deployment - Agent Studio

```yaml
# k8s/agent-studio-deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: agent-studio
  namespace: agentic-coworker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: agent-studio
  template:
    metadata:
      labels:
        app: agent-studio
    spec:
      containers:
      - name: agent-studio
        image: agentic-coworker/agent-studio:latest
        ports:
        - containerPort: 3000
        envFrom:
        - configMapRef:
            name: agentic-coworker-config
        - secretRef:
            name: agentic-coworker-secrets
        resources:
          requests:
            memory: "2Gi"
            cpu: "1"
          limits:
            memory: "4Gi"
            cpu: "2"
        livenessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /api/health
            port: 3000
          initialDelaySeconds: 10
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: agent-studio
  namespace: agentic-coworker
spec:
  selector:
    app: agent-studio
  ports:
  - protocol: TCP
    port: 3000
    targetPort: 3000
  type: ClusterIP
```

#### Ingress

```yaml
# k8s/ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: agentic-coworker-ingress
  namespace: agentic-coworker
  annotations:
    cert-manager.io/cluster-issuer: "letsencrypt-prod"
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - yourdomain.com
    secretName: agentic-coworker-tls
  rules:
  - host: yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: agent-studio
            port:
              number: 3000
      - path: /api/integrator
        pathType: Prefix
        backend:
          service:
            name: integrator
            port:
              number: 6060
```

#### Deploy to Kubernetes

```bash
# Apply all manifests
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secrets.yaml
kubectl apply -f k8s/agent-studio-deployment.yaml
kubectl apply -f k8s/ingress.yaml

# Check deployment status
kubectl get pods -n agentic-coworker
kubectl get services -n agentic-coworker
kubectl get ingress -n agentic-coworker

# View logs
kubectl logs -f deployment/agent-studio -n agentic-coworker

# Scale deployment
kubectl scale deployment agent-studio --replicas=5 -n agentic-coworker

# Rolling update
kubectl set image deployment/agent-studio agent-studio=agentic-coworker/agent-studio:v2.0 -n agentic-coworker
```

### Helm Chart (Recommended)

```bash
# Create Helm chart
helm create agentic-coworker

# Install chart
helm install agentic-coworker ./agentic-coworker \
  --namespace agentic-coworker \
  --create-namespace \
  --values values.production.yaml

# Upgrade
helm upgrade agentic-coworker ./agentic-coworker \
  --namespace agentic-coworker \
  --values values.production.yaml

# Rollback
helm rollback agentic-coworker -n agentic-coworker

# Uninstall
helm uninstall agentic-coworker -n agentic-coworker
```

## Database Setup and Migrations

### Initialize Database

```bash
# Run database initialization
docker exec agent-ops python -m agent_ops seed

# Verify tables created
docker exec postgres psql -U user -d agent-studio -c "\dt"
```

### Run Migrations

```bash
# Apply migrations
docker exec agent-ops python -m agent_ops migrate

# Check migration status
docker exec agent-ops python -m agent_ops migrate --status
```

### Seed Data

```bash
# Load sample data
docker exec agent-ops python -m agent_ops seed --sample

# Load production data
docker exec agent-ops python -m agent_ops seed --production
```

## Configuration Management

### OAuth Providers

```bash
cd data/update_data

# Configure OAuth providers
cp update_oauth_providers.json.template update_oauth_providers.json
nano update_oauth_providers.json

# Apply configuration
docker exec agent-ops python -m agent_ops update
```

### API Keys

```bash
# Configure API keys
cp update_app_keys.json.template update_app_keys.json
nano update_app_keys.json

# Apply configuration
docker exec agent-ops python -m agent_ops update
```

## Monitoring and Logging

### Health Checks

```bash
# Check service health
curl http://localhost:3000/api/health
curl http://localhost:6060/health
curl http://localhost:6666/health

# Database health
docker exec postgres pg_isready -U user

# Check all services
docker-compose ps
```

### Centralized Logging

**Log Aggregation** (ELK Stack):

```yaml
# docker-compose.monitoring.yml
services:
  elasticsearch:
    image: docker.elastic.co/elasticsearch/elasticsearch:8.8.0
    environment:
      - discovery.type=single-node
    ports:
      - "9200:9200"

  logstash:
    image: docker.elastic.co/logstash/logstash:8.8.0
    volumes:
      - ./logstash/config:/usr/share/logstash/pipeline

  kibana:
    image: docker.elastic.co/kibana/kibana:8.8.0
    ports:
      - "5601:5601"
    depends_on:
      - elasticsearch
```

### Metrics Collection

**Prometheus + Grafana**:

```yaml
# docker-compose.monitoring.yml (continued)
  prometheus:
    image: prom/prometheus:latest
    volumes:
      - ./prometheus/prometheus.yml:/etc/prometheus/prometheus.yml
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    ports:
      - "3001:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
    volumes:
      - grafana-data:/var/lib/grafana

volumes:
  grafana-data:
```

## Backup and Disaster Recovery

### Database Backup

```bash
# Manual backup
docker exec agent-ops python -m agent_ops backup

# Automated backup (cron)
0 2 * * * docker exec agent-ops python -m agent_ops backup
```

### Restore from Backup

```bash
# List backups
ls -la data/backup_data/

# Restore from specific backup
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/backup_2026-02-05_02-00-00
```

### Disaster Recovery Plan

1. **Daily automated backups** to remote storage (S3, GCS, Azure Blob)
2. **Backup retention**: 30 days for daily, 12 months for monthly
3. **Recovery Time Objective (RTO)**: 4 hours
4. **Recovery Point Objective (RPO)**: 24 hours
5. **Test restores** monthly to verify backup integrity

## Troubleshooting

### Common Issues

#### Services Won't Start

```bash
# Check logs
docker-compose logs

# Verify environment variables
docker-compose config

# Check port conflicts
sudo netstat -tulpn | grep LISTEN

# Clean up and restart
docker-compose down -v
docker-compose up -d
```

#### Database Connection Errors

```bash
# Check PostgreSQL status
docker-compose ps postgres

# Verify database is ready
docker exec postgres pg_isready -U user

# Check connection string
docker exec agent-studio env | grep DATABASE_URL

# Test connection
docker exec postgres psql -U user -d agent-studio -c "SELECT 1;"
```

#### OAuth Authentication Failures

```bash
# Check Keycloak status
docker-compose logs keycloak

# Verify OAuth configuration
docker exec agent-ops python -m agent_ops config --show-oauth

# Check redirect URIs match
# Provider: http://localhost:3000/api/auth/callback/[provider]
```

#### Performance Issues

```bash
# Check resource usage
docker stats

# Identify slow queries
docker exec postgres psql -U user -d agent-studio -c "
  SELECT query, mean_exec_time, calls
  FROM pg_stat_statements
  ORDER BY mean_exec_time DESC
  LIMIT 10;"

# Check connection pool
docker-compose logs integrator | grep "connection pool"
```

### Debug Mode

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG

# Restart services
docker-compose restart

# View detailed logs
docker-compose logs -f --tail=100
```

### Get Support

- **Documentation**: [Architecture Guide](ARCHITECTURE.md), [Developer Guide](DEVELOPER_GUIDE.md)
- **Issue Tracker**: GitHub Issues
- **Community**: Discord/Slack channel

---

## Appendix

### A. Production Deployment Checklist

```markdown
## Pre-Deployment
- [ ] Code reviewed and tested
- [ ] Database migrations prepared
- [ ] Configuration updated for production
- [ ] SSL certificates obtained
- [ ] DNS configured
- [ ] Monitoring configured
- [ ] Backup strategy implemented

## Deployment
- [ ] Maintenance window scheduled
- [ ] Users notified
- [ ] Database backup created
- [ ] New version deployed
- [ ] Smoke tests passed
- [ ] Rollback plan ready

## Post-Deployment
- [ ] Health checks passing
- [ ] Monitoring alerts configured
- [ ] Performance metrics baseline
- [ ] Documentation updated
- [ ] Team notified
- [ ] Post-mortem if issues
```

### B. Environment Variables Reference

See [Configuration Management](#configuration-management) section and `.env.docker.sample` for complete reference.

### C. Network Diagram

```
Internet
    ↓
[Traefik Reverse Proxy]
    ↓
    ├──→ [Agent Studio:3000]
    ├──→ [Integrator API:6060]
    ├──→ [MCP Services:6666]
    └──→ [Keycloak:8888]
         ↓
    [Internal Network]
         ↓
    ├──→ [PostgreSQL:5432]
    ├──→ [Neo4j:7687]
    ├──→ [ETCD:2379]
    └──→ [NATS:4222]
```

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Maintained By**: Agentic Coworker Team
