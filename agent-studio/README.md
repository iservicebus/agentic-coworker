# Agent Studio

**Build, govern, and empower AI agents with enterprise-grade tools and security**

Agent Studio is a comprehensive platform for creating, managing, and governing AI agents with seamless API integration, hierarchical capability modeling, and enterprise-grade security.

## Overview

Agent Studio transforms REST APIs into AI-ready tools and provides complete lifecycle management for AI agents - from tool creation to governance and deployment.

### Key Capabilities

#### 🔄 Universal API Integration
- **Multi-Format Import**: Convert REST APIs to MCP tools from multiple sources:
  - Published API documentation websites
  - OpenAPI specifications (URL or file upload)
  - Postman collections
- **Tool Refinement**: Annotate, validate, and test tools before deployment
- **Staging Workflow**: Three-stage lifecycle (import → stage → register)

#### 🏗️ Bottom-Up Capability Modeling
Organize tools using a hierarchical business-aligned structure:
```
Role (RBAC)
  └── Domain (Business Area)
       └── Capability (Business Function)
            └── Skill (Technical Implementation)
                 └── MCP Tool (Executable)
```

#### 🔒 Enterprise-Grade Security
- **OAuth 2.0 Integration**: Dynamic provider configuration for:
  - Google, GitHub, LinkedIn
  - Keycloak, ServiceNow
  - Custom OAuth providers
- **Credential Management**: AES-256-GCM encryption for secrets
- **Multi-Tenant Architecture**: Complete data isolation per tenant
- **Token Management**: Automatic refresh and secure storage

#### 🤖 Agent Governance
- **Role-Based Access Control**: Hierarchical permissions (Role → Domain → Capability → Tool)
- **Agent Lifecycle Management**: Create, configure, and manage AI agents
- **Human-Agent Collaboration**: Multi-user per agent with role assignments
- **Resource Allocation**: Fine-grained capability and tool access control

#### ✅ Runtime Validation
- **Tool Testing**: Built-in test interface with sample data generation
- **Schema Validation**: Automatic input/output validation
- **Integration Testing**: Validate tools before production deployment

## Technology Stack

### Frontend
- **Framework**: Next.js 15.3.3 with App Router
- **UI Library**: React 19 with Server Components
- **Styling**: Tailwind CSS 4
- **Type Safety**: TypeScript (strict mode)
- **Authentication**: NextAuth.js 4.24.11

### Backend
- **Runtime**: Node.js via Next.js API routes
- **Database**: PostgreSQL with connection pooling
- **Encryption**: AES-256-GCM for credential storage
- **API Design**: RESTful endpoints with centralized client

## Getting Started

### Prerequisites
- Node.js 20 or higher
- PostgreSQL database
- OAuth provider credentials (optional, for external integrations)

### Installation

```bash
# Install dependencies
npm install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
npm run dev
```

### Environment Variables

```env
# Database
DATABASE_URL=postgresql://user:password@localhost:5432/agentstudio

# Authentication
NEXTAUTH_URL=http://localhost:3000
NEXTAUTH_SECRET=your-secret-key

# Encryption
SECRET_KEY=your-32-byte-encryption-key

# Backend API
NEXT_PUBLIC_INTEGRATOR_API_URL=http://localhost:6060
```

### Docker Deployment

```bash
# Build image
docker build -t agent-studio .

# Run container
docker run -p 3000:3000 \
  -e DATABASE_URL=postgresql://... \
  -e NEXTAUTH_SECRET=... \
  -e SECRET_KEY=... \
  agent-studio
```

## Project Structure

```
src/
├── app/                          # Next.js App Router
│   ├── api/                      # Backend API routes
│   │   └── auth/                 # NextAuth OAuth handlers
│   ├── portal/                   # Protected portal pages
│   │   ├── mcp-tools/            # Tool explorer
│   │   ├── tool-importer/        # API import interface
│   │   ├── agent-mngt/           # Agent management
│   │   ├── domains/              # Business capability navigation
│   │   └── dashboard/            # Main dashboard
│   └── token/                    # OAuth token flows
├── components/                   # Reusable React components
│   ├── ToolDefinitionUI/         # Tool editor
│   ├── HierarchicalNavigation/   # Domain navigator
│   └── ToolTestUI/               # Tool validation
├── lib/                          # Utilities & infrastructure
│   ├── apiClient.ts              # Centralized API client
│   ├── crypto.ts                 # Encryption utilities
│   ├── db.ts                     # Database connection
│   └── providers/                # OAuth provider implementations
└── types/                        # TypeScript definitions
```

## Core Features

### Tool Import & Management
Import APIs from multiple sources and convert them to MCP tools with semantic annotations:

```typescript
// Convert from OpenAPI
await convertOpenApiByLink(openapiUrl);

// Convert from Postman
await convertPostmanToTool(postmanFile);

// Convert from API docs
await convertDocToTool(apiDocUrl);
```

### Agent Management
Create and configure AI agents with role-based access:

```typescript
// Create agent
await createAgentByUser(tenant, username, {
  name: "CustomerServiceBot",
  description: "Handles customer inquiries"
});

// Assign roles
await updateAgentRoles(tenant, agentId, ["CustomerSupport"]);

// Get accessible tools
await searchMcpTools(tenant, {
  agent_id: agentId,
  filter: { roles: [...] }
});
```

### Security & OAuth
Configure OAuth providers dynamically without redeployment:

```typescript
// Store encrypted provider credentials
await createAuthProvider({
  provider_name: "github",
  client_id: "...",
  client_secret: "...",  // Automatically encrypted
  tenant_name: "acme"
});

// Generate agent tokens
// Navigate to /portal/provider-tokens
// Click "Get Token" to initiate OAuth flow
```

## Development Scripts

```bash
npm run dev          # Start development server with Turbopack
npm run build        # Build for production
npm run build:ts     # TypeScript compilation check
npm run start        # Start production server
npm run lint         # Run ESLint
npm run test         # Run tests
```

## Architecture Highlights

### Multi-Tenant Architecture
- Cookie-based tenant selection
- Per-tenant data isolation
- Tenant-scoped OAuth providers and credentials

### Hierarchical RBAC
- Role → Domain → Capability → Skill → Tool
- Fine-grained access control
- Business process alignment

### Security-First Design
- AES-256-GCM encryption at rest
- JWT-based session management
- Automatic token refresh
- HTTPS enforcement

### Extensible Provider System
- Factory pattern for OAuth providers
- Easy addition of custom providers
- Runtime provider configuration

## Contributing

Contributions are welcome! Please follow these guidelines:

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## License

[Add your license here]

## Support

For issues and questions:
- GitHub Issues: [Add your repo URL]
- Documentation: [Add docs URL]
- Contact: [Add contact info]
