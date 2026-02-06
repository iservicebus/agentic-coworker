# Agentic Coworker — Governed AI Agents for Social and Enterprise

> Empower AI agents to work autonomously across your entire business ecosystem—from social platforms like LinkedIn, to productivity tools like Google Workspace (Gmail, Calendar, Drive) and GitHub, to enterprise systems like SAP and ServiceNow. Agents automatically acquire skills and integrate with any REST API, while enterprise governance ensures they have the right permissions, access the right tools, and operate within your security boundaries. Built for organizations that want powerful agents with human oversight.



[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)

## ✨ What Your Agents Can Do


### Agents Work Across Your Entire Business

- 🔌 **Connect to Any API Instantly** - Agents automatically acquire new skills from REST APIs using multiple sources: API documentation websites, OpenAPI specs, and Postman collections. They validate and test new capabilities before using them in production workflows.

- 🏢 **Understand Your Business Context** - Agents organize their capabilities by your business structure: Role → Domain → Capability → Skill → Tool. They know which tools to use for which job, matching their actions to your organization's responsibilities and workflows.

- 🔐 **Operate Securely Within Boundaries** - Agents authenticate using OAuth 2.0 across Google, GitHub, LinkedIn, ServiceNow, and more. Their credentials are encrypted (AES-256-GCM), automatically refreshed, and completely isolated per tenant. They never cross security boundaries.

- 👥 **Work Under Human Governance** - Agents operate with fine-grained permissions based on their assigned roles. They only access tools they're authorized to use, work within resource limits, and maintain audit trails of all actions. Humans stay in control through owner/member/viewer relationships.

### How Agents Evolve and Learn

1. **Acquire Skills** - Agents import new capabilities from various API formats, understand them through semantic metadata, and validate them with built-in testing before deployment.

2. **Organize Knowledge** - Agents structure their tools hierarchically by business domains, making intelligent decisions about which capabilities to use for each task.

3. **Execute Autonomously** - Agents run workflows across multiple services, manage OAuth credentials automatically, and operate at scale across isolated tenants.

### Agent Intelligence Features

- ✅ **Self-Testing Capabilities** - Agents validate their tools with sample data and schema verification before using them
- 🏗️ **Tenant-Aware Operations** - Agents maintain complete isolation of data, tools, and credentials across organizational boundaries
- 🔍 **Semantic Tool Discovery** - Agents find the right tools using vector embeddings and similarity matching
- 🔑 **Autonomous Credential Management** - Agents handle OAuth tokens, refresh cycles, and encryption automatically
- 🤝 **Human Collaboration** - Agents work with multiple humans in owner, member, or viewer capacities
- 📊 **Business Process Awareness** - Agents map their actions to business workflows and domain-specific metrics
- 🤖 **Multi-Agent Coordination** - Multiple agents orchestrate together, each with specialized capabilities
- 🎯 **Standardized Communication** - Agents use Model Context Protocol (MCP) for consistent tool interaction
- 📈 **Knowledge Graph Navigation** - Agents leverage relationship mapping to understand complex connections
- 🚀 **Cloud-Native Deployment** - Agents run in containerized environments with automatic scaling
- 🔄 **Event-Driven Coordination** - Agents communicate and coordinate through real-time messaging

### Measure Your Agentic Readiness

- 📊 **AI Integration Readiness Dashboard** - Visualize your organization's readiness for AI agents by measuring MCP tool availability across business workflows. See which processes have automation potential, identify integration gaps, and track coverage metrics across workflow steps. Understand your path to full agent deployment with clear metrics on tool availability and workflow readiness.


## 🚀 Quick Start

### Prerequisites

1. **Docker & Docker Compose** - [Install Docker Desktop](https://www.docker.com/products/docker-desktop)
2. **Configure DNS** - Add to `/etc/hosts` (macOS/Linux) or `C:\Windows\System32\drivers\etc\hosts` (Windows):
   ```
   127.0.0.1 host.docker.internal
   ```

### Installation

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/agentic-coworker.git
cd agentic-coworker

# Configure environment
cp .env.docker.sample .env.docker
# Edit .env.docker and add your OpenAI, or Azure OpenAI or Google AI credentials

# Start the platform
docker-compose up -d

# Check status
docker-compose ps
```

**First startup takes 2-3 minutes** to initialize the database and configure services.

### Access the Platform

Once running, access:

- **Agent Studio**: http://localhost:3000
  - **Readiness Dashboard**: View your organization's agentic AI readiness metrics
  - **Tool Importer**: Import and manage API integrations
  - **Agent Management**: Configure agent roles and permissions
  - **Test User Login**: `admin` / `securepass`
  - **Test Agent Login**: `agent-admin` / `securepass`
- **API Services**: http://localhost:6060
- **Admin Dashboard**: http://localhost:8888 (admin/admin)

## 📋 Configuration

### Required: AI Model Setup

Edit `.env.docker` and configure your AI provider. The platform supports multiple LLM providers:

#### Azure OpenAI (Cloud)
```bash
MODEL_PROVIDER=azure_openai
AZURE_OPENAI_API_KEY=your-api-key-here
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_MODEL=gpt-5
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-5
AZURE_OPENAI_EMBEDDING_MODEL=text-embedding-3-small
AZURE_OPENAI_API_VERSION=2024-12-01-preview
```

#### OpenAI (Cloud)
```bash
MODEL_PROVIDER=openai
OPENAI_API_KEY=your-openai-api-key-here
OPENAI_MODEL=gpt-4o
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### Google AI (Cloud)
```bash
MODEL_PROVIDER=google_genai
GOOGLE_API_KEY=your-google-api-key-here
GOOGLE_MODEL=gemini-2.5-flash
GOOGLE_EMBEDDING_MODEL=models/gemini-embedding-001
```

#### Anthropic Claude (Cloud)
```bash
MODEL_PROVIDER=anthropic
ANTHROPIC_API_KEY=your-anthropic-api-key-here
ANTHROPIC_MODEL=claude-sonnet-4-5-20250929
LOCAL_EMBEDDING_MODEL=rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
LOCAL_EMBEDDING_BASE_URL=http://host.docker.internal:11434
```

#### Local OpenAI / MLX (On-Premises)
```bash
MODEL_PROVIDER=local_openai
LOCAL_OPENAI_BASE_URL=http://host.docker.internal:5555/v1
LOCAL_OPENAI_API_KEY="local"
LOCAL_OPENAI_MODEL=gpt-oss-20b  # or gpt-oss-120b for larger model
LOCAL_EMBEDDING_MODEL=rjmalagon/gte-qwen2-1.5b-instruct-embed-f16
LOCAL_EMBEDDING_BASE_URL=http://host.docker.internal:11434  # Ollama server
```

**Local Model Notes**:
- Supports **gpt-oss-20b** (20 billion parameters) and **gpt-oss-120b** (120 billion parameters)
- Embeddings run via **Ollama** with **gte-qwen2** model (port 11434)
- Requires local model server running (MLX or compatible OpenAI-compatible server)
- No API keys or external dependencies
- Full data privacy and control
- Ideal for air-gapped environments or data-sensitive deployments

### Optional: External Service Credentials

Add OAuth and API credentials for external services to enable your agents to access external platforms and data sources.

#### OAuth 2.0 Providers

Follow these guides to obtain OAuth credentials:

- **[Google OAuth Setup](docs/setup-guides/google-oauth-setup.md)** - Gmail, Calendar, Drive, and other Google services
- **[GitHub OAuth Setup](docs/setup-guides/github-oauth-setup.md)** - Repository access, issues, and pull requests
- **[LinkedIn OAuth Setup](docs/setup-guides/linkedin-oauth-setup.md)** - Profile data and social features
- **[ServiceNow OAuth Setup](docs/setup-guides/servicenow-api-setup.md)** - ITSM integration (OAuth or API key)

#### API Key Providers

Follow these guides to obtain API keys:

- **[SAP API Key Setup](docs/setup-guides/sap-api-key-setup.md)** - SAP Business APIs and enterprise data
- **[FRED API Key Setup](docs/setup-guides/fred-api-key-setup.md)** - Federal Reserve economic data
- **[SEC API Key Setup](docs/setup-guides/sec-api-key-setup.md)** - SEC EDGAR filings and financial data
- **[Alpha Vantage API Key Setup](docs/setup-guides/alphavantage-api-key-setup.md)** - Stock market and financial data

#### Apply Configuration

After obtaining credentials, configure them:

```bash
cd data/update_data

# Copy templates
cp update_app_keys.json.template update_app_keys.json
cp update_oauth_providers.json.template update_oauth_providers.json

# Edit with your credentials from the guides above, then apply
docker exec agent-ops python -m agent_ops update
```

## 🏗️ Architecture

### System Overview

The Agentic Coworker platform enables AI agents to work autonomously across your entire business ecosystem with enterprise governance and security.

![Agentic Coworker Architecture](docs/images/agentic-coworker-architecture.png)

**Architecture Layers:**

- **Human Interaction Layer**: Web interface and chat apps (Slack, Discord, Teams) for human-agent collaboration
- **Agentic Coworker Platform**: Core components including Agent Factory, MCP Gateway, Agent Identity, Agent Governance, Agent Skill Acquisition, Agent Tool Annotator, and API Gateway
- **Integration Layer**: Connects to Social Apps (LinkedIn), Workplace Productivity tools (Gmail, Calendar, GitHub), and Enterprise Applications (SAP, ServiceNow)

### Platform Services

| Service | Port | Purpose |
|---------|------|---------|
| **Postgres** | 5432 | Primary database with pgvector |
| **Keycloak** | 8888 | Identity & access management |
| **Neo4j** | 7474, 7687 | Graph database for knowledge mapping |
| **ETCD** | 12379 | Distributed configuration |
| **NATS** | 4222 | Message queue for agent coordination |
| **Traefik** | 80, 8080 | Reverse proxy & load balancer |

### Application Services

| Service | Port | Purpose |
|---------|------|---------|
| **Agent Studio** | 3000 | Web UI for agent management |
| **Integrator** | 6060 | Main integration service |
| **MCP Services** | 6666 | Model Context Protocol server |
| **Support Services** | 5000 | Supporting APIs |
| **Agent Ops** | - | Database operations utility |

## 🛠️ Common Operations

### Managing Services

```bash
# View logs
docker-compose logs -f

# Restart services
docker-compose restart

# Stop all services
docker-compose down

# Rebuild after changes
docker-compose up -d --build
```

### Database Operations

```bash
# Create backup
docker exec agent-ops python -m agent_ops backup

# Restore from backup
docker exec agent-ops python -m agent_ops restore \
  --restore-from /app/data/backup_data/[backup-folder]

# Update credentials
docker exec agent-ops python -m agent_ops update
```

See [agent_ops/QUICK_REFERENCE.md](agent_ops/QUICK_REFERENCE.md) for detailed operations.

## 🔧 Troubleshooting

### Services Won't Start

```bash
# Check service status
docker-compose ps

# View logs for specific service
docker-compose logs [service-name]
```

### Reset Everything

```bash
# Stop and remove all containers and volumes
docker-compose down -v

# Start fresh
docker-compose up -d
```

### Database Connection Issues

```bash
# Verify Postgres is healthy
docker exec postgres psql -U user -d agent-studio -c "SELECT 1;"
```

### Keycloak SSL Errors

The platform auto-configures Keycloak on first start. If you encounter SSL errors:

```bash
docker exec keycloak /opt/keycloak/bin/kcadm.sh config credentials \
  --server http://localhost:8080 --realm master --user admin --password admin
docker exec keycloak /opt/keycloak/bin/kcadm.sh update realms/master -s sslRequired=none
```

### Port Conflicts

Edit `docker-compose.yml` to change host port mappings:

```yaml
ports:
  - "3001:3000"  # Changed from 3000:3000
```

## 📚 Documentation

### Core Documentation

- **[Architecture Documentation](docs/guides/ARCHITECTURE.md)** - Complete system architecture, design patterns, and technical details
- **[Deployment Guide](docs/guides/DEPLOYMENT.md)** - Comprehensive deployment instructions for dev, staging, and production
- **[User Guide](docs/guides/USER_GUIDE.md)** - Complete guide for platform users and administrators
- **[Developer Guide](docs/guides/DEVELOPER_GUIDE.md)** - Development setup, coding standards, and contribution workflow
- **[Contributing Guidelines](docs/guides/CONTRIBUTING.md)** - How to contribute to the project

### Setup Guides

**OAuth 2.0 Configuration:**
- [Google OAuth Setup](docs/setup-guides/google-oauth-setup.md) - Configure Google authentication and API access
- [GitHub OAuth Setup](docs/setup-guides/github-oauth-setup.md) - Configure GitHub authentication and repository access
- [LinkedIn OAuth Setup](docs/setup-guides/linkedin-oauth-setup.md) - Configure LinkedIn authentication and social features
- [ServiceNow Setup](docs/setup-guides/servicenow-api-setup.md) - Configure ServiceNow (OAuth or API key)

**API Key Configuration:**
- [SAP API Key Setup](docs/setup-guides/sap-api-key-setup.md) - Configure SAP Business Hub API access
- [FRED API Key Setup](docs/setup-guides/fred-api-key-setup.md) - Configure Federal Reserve economic data access
- [SEC API Key Setup](docs/setup-guides/sec-api-key-setup.md) - Configure SEC EDGAR filings access
- [Alpha Vantage API Key Setup](docs/setup-guides/alphavantage-api-key-setup.md) - Configure stock market data access

### Operations Guides

- [Quick Reference Guide](agent_ops/QUICK_REFERENCE.md) - Database operations and common tasks
- [Operations Manual](agent_ops/OPERATIONS.md) - Detailed operational procedures
- [Docker Environment Guide](agent_ops/DOCKER-ENV.md) - Docker-specific configuration

## 🗂️ Project Structure

```
agentic-coworker/
├── agent-studio/          # Next.js frontend application
├── integrator/            # Main integration service
├── mcp_services/          # Model Context Protocol services
├── support_services/      # Supporting API services
├── agent_ops/             # Database operations utilities
├── docs/                  # Complete documentation
│   ├── guides/           # Core documentation (Architecture, Deployment, User, Developer, Contributing)
│   ├── setup-guides/     # OAuth and API key setup guides
│   └── images/           # Diagrams and images
├── data/
│   ├── seed_data/        # Initial platform data
│   ├── backup_data/      # Database backups
│   └── update_data/      # Credential templates
├── deployment/           # Deployment configurations
├── docker-compose.yml    # Main orchestration file
└── .env.docker.sample   # Configuration template
```

## 🤝 Contributing

We welcome contributions from the community! Whether you're fixing bugs, adding features, improving documentation, or reporting issues, your help makes this project better.

### How to Contribute

1. Read the [Contributing Guidelines](docs/guides/CONTRIBUTING.md)
2. Fork the repository
3. Create your feature branch (`git checkout -b feature/amazing-feature`)
4. Make your changes following our [coding standards](docs/guides/DEVELOPER_GUIDE.md#coding-standards)
5. Write tests for your changes
6. Commit your changes (`git commit -m 'feat: add amazing feature'`)
7. Push to your branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

### Development Resources

- **[Developer Guide](docs/guides/DEVELOPER_GUIDE.md)** - Setup instructions and development workflow
- **[Contributing Guidelines](docs/guides/CONTRIBUTING.md)** - Detailed contribution process
- **[Architecture Documentation](docs/guides/ARCHITECTURE.md)** - Understand the system design

### Code of Conduct

We are committed to providing a welcoming and inclusive environment. Please read our Code of Conduct in [CONTRIBUTING.md](docs/guides/CONTRIBUTING.md#code-of-conduct).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

Built with modern technologies:
- [Next.js 15](https://nextjs.org/) - React framework
- [React 19](https://react.dev/) - UI library
- [TypeScript](https://www.typescriptlang.org/) - Type-safe development
- [PostgreSQL + pgvector](https://www.postgresql.org/) - Relational database with vector search
- [NextAuth.js](https://next-auth.js.org/) - Authentication for Next.js
- [OAuth 2.0](https://oauth.net/2/) - Industry-standard authorization
- [MCP Protocol](https://modelcontextprotocol.io/) - Model Context Protocol
- [Neo4j](https://neo4j.com/) - Graph database
- [Keycloak](https://www.keycloak.org/) - Identity management
- [Docker](https://www.docker.com/) - Containerization
- [NATS](https://nats.io/) - Message queue
- [Traefik](https://traefik.io/) - Reverse proxy

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/iservicebus/agentic-coworker/issues)
- **Documentation**: [Wiki](https://github.com/iservicebus/agentic-coworker/wiki)

---

**Made with ❤️ by Jingnan Zhou**
