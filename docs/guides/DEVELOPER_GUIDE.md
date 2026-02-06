# Agentic Coworker - Developer Guide

## Table of Contents

- [Getting Started](#getting-started)
- [Development Environment Setup](#development-environment-setup)
- [Project Structure](#project-structure)
- [Development Workflow](#development-workflow)
- [Frontend Development](#frontend-development)
- [Backend Development](#backend-development)
- [Database Development](#database-development)
- [API Development](#api-development)
- [Testing](#testing)
- [Debugging](#debugging)
- [Code Style and Standards](#code-style-and-standards)
- [Contributing](#contributing)

## Getting Started

This guide helps developers set up their environment, understand the codebase, and contribute to the Agentic Coworker platform.

### Prerequisites

**Required Tools**:
- Git 2.30+
- Docker 24.0+ and Docker Compose 2.20+
- Python 3.11+ (for backend development)
- Node.js 18+ and npm 9+ (for frontend development)
- VS Code or preferred IDE

**Recommended Tools**:
- Postman or Insomnia (API testing)
- pgAdmin or DBeaver (database management)
- Neo4j Browser (graph database)
- Redis Commander (if using Redis)

### Quick Setup

```bash
# Clone repository
git clone https://github.com/YOUR_USERNAME/agentic-coworker.git
cd agentic-coworker

# Start development environment
docker-compose up -d

# Verify services
docker-compose ps
```

## Development Environment Setup

### Backend Development Setup

#### 1. Python Environment

```bash
cd integrator

# Create virtual environment
python -m venv venv

# Activate virtual environment
source venv/bin/activate  # Linux/macOS
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Install development dependencies
pip install -r requirements-dev.txt
```

#### 2. Install Pre-commit Hooks

```bash
pip install pre-commit
pre-commit install

# Run hooks manually
pre-commit run --all-files
```

#### 3. Run Backend Services Locally

```bash
# Start dependencies (database, etc.)
docker-compose up -d postgres neo4j etcd nats keycloak

# Run integrator locally
cd integrator
python src/integrator/apis/api_server.py

# Run MCP services locally
cd mcp_services
python -m src.mcp_services.servers.aint_mcp_provider
```

### Frontend Development Setup

#### 1. Node.js Environment

```bash
cd agent-studio

# Install dependencies
npm install

# or use yarn
yarn install
```

#### 2. Development Server

```bash
# Start Next.js development server
npm run dev

# or
yarn dev

# Access at http://localhost:3000
```

#### 3. Build and Production Preview

```bash
# Build for production
npm run build

# Start production server
npm start

# or preview build
npm run preview
```

### IDE Configuration

#### VS Code Settings

```json
// .vscode/settings.json
{
  "editor.formatOnSave": true,
  "editor.defaultFormatter": "esbenp.prettier-vscode",
  "python.linting.enabled": true,
  "python.linting.pylintEnabled": false,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "[typescript]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  },
  "[typescriptreact]": {
    "editor.defaultFormatter": "esbenp.prettier-vscode"
  }
}
```

#### Recommended VS Code Extensions

```json
// .vscode/extensions.json
{
  "recommendations": [
    "dbaeumer.vscode-eslint",
    "esbenp.prettier-vscode",
    "ms-python.python",
    "ms-python.vscode-pylance",
    "ms-python.black-formatter",
    "bradlc.vscode-tailwindcss",
    "prisma.prisma",
    "rangav.vscode-thunder-client",
    "ms-azuretools.vscode-docker"
  ]
}
```

## Project Structure

### Root Directory

```
agentic-coworker/
├── agent-studio/          # Next.js frontend application
├── integrator/            # Python FastAPI backend service
├── mcp_services/          # Model Context Protocol server
├── support_services/      # Supporting microservices
├── agent_ops/             # Database operations CLI
├── agents/                # Agent definitions and configurations
├── data/                  # Data files and migrations
│   ├── seed_data/        # Initial database data
│   ├── backup_data/      # Database backups
│   └── update_data/      # Configuration update files
├── deployment/           # Deployment configurations
├── docs/                 # Documentation and setup guides
├── vendors/              # Third-party integrations
├── docker-compose.yml    # Docker Compose configuration
├── .env.docker.sample    # Environment variable template
├── ARCHITECTURE.md       # Architecture documentation
├── DEPLOYMENT.md         # Deployment guide
├── DEVELOPER_GUIDE.md    # This file
└── USER_GUIDE.md         # User documentation
```

### Agent Studio Structure

```
agent-studio/
├── src/
│   ├── app/                      # Next.js 15 App Router
│   │   ├── api/                  # API routes
│   │   │   ├── auth/            # NextAuth.js authentication
│   │   │   └── generate-sample/ # Sample data generation
│   │   ├── portal/              # Main application pages
│   │   │   ├── dashboard/       # Overview and metrics
│   │   │   ├── agent-mngt/      # Agent management
│   │   │   ├── agent-profile/   # Agent configuration
│   │   │   ├── agent-chat/      # Chat interface
│   │   │   ├── mcp-tools/       # Tool library
│   │   │   ├── tool-importer/   # Import tools
│   │   │   ├── mcp-services/    # MCP configuration
│   │   │   ├── staging-services/ # Testing environment
│   │   │   ├── auth-providers/  # OAuth setup
│   │   │   ├── provider-tokens/ # Token management
│   │   │   ├── service-secrets/ # API keys
│   │   │   ├── domains/         # Domain management
│   │   │   └── user-mngt/       # User admin
│   │   ├── layout.tsx           # Root layout
│   │   ├── page.tsx             # Home page
│   │   └── globals.css          # Global styles
│   ├── components/              # Reusable React components
│   │   ├── auth/               # Authentication components
│   │   ├── chat/               # Chat UI components
│   │   ├── Layout/             # Layout components
│   │   └── ToolDefinitionUI/   # Tool editor components
│   ├── lib/                    # Utility libraries
│   │   ├── providers/          # OAuth provider configurations
│   │   └── iam.ts              # IAM client
│   ├── hooks/                  # Custom React hooks
│   └── types/                  # TypeScript type definitions
├── public/                     # Static assets
├── package.json               # Dependencies
├── tsconfig.json              # TypeScript configuration
├── next.config.ts             # Next.js configuration
└── tailwind.config.ts         # Tailwind CSS configuration
```

### Integrator Structure

```
integrator/
├── src/integrator/
│   ├── apis/                  # FastAPI application
│   │   ├── api_server.py     # Main server entry point
│   │   └── routes/           # API route handlers
│   ├── iam/                  # Identity and Access Management
│   │   ├── oauth.py          # OAuth client
│   │   └── auth.py           # Authentication logic
│   ├── publish/              # Service publishing
│   │   ├── mcp_publisher.py  # MCP service publisher
│   │   └── registry.py       # Service registry
│   ├── staging/              # Staging environment
│   │   ├── validator.py      # Tool validation
│   │   └── test_runner.py    # Test execution
│   ├── clients/              # API clients
│   │   ├── api_client.py     # Generic API client
│   │   └── mcp_client.py     # MCP client
│   ├── logs/                 # Logging module
│   ├── utils/                # Utility functions
│   │   ├── database.py       # Database connection
│   │   ├── crypto.py         # Encryption/decryption
│   │   └── config.py         # Configuration management
│   └── models/               # Data models
│       ├── agent.py
│       ├── tool.py
│       └── user.py
├── tests/                    # Test suite
├── requirements.txt          # Python dependencies
└── Dockerfile               # Docker image definition
```

## Development Workflow

### Branch Strategy

```
main          # Production-ready code
  ↓
develop       # Integration branch
  ↓
feature/*     # Feature branches
hotfix/*      # Urgent fixes
release/*     # Release preparation
```

### Workflow Steps

1. **Create Feature Branch**
   ```bash
   git checkout develop
   git pull origin develop
   git checkout -b feature/your-feature-name
   ```

2. **Make Changes and Commit**
   ```bash
   git add .
   git commit -m "feat: add new feature description"
   ```

3. **Keep Branch Updated**
   ```bash
   git fetch origin
   git rebase origin/develop
   ```

4. **Run Tests**
   ```bash
   # Backend tests
   cd integrator
   pytest

   # Frontend tests
   cd agent-studio
   npm test
   ```

5. **Push and Create Pull Request**
   ```bash
   git push origin feature/your-feature-name
   # Create PR on GitHub
   ```

### Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types**:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples**:
```
feat(agent-studio): add OAuth provider configuration UI
fix(integrator): resolve token refresh race condition
docs(readme): update installation instructions
test(mcp): add integration tests for tool execution
```

## Frontend Development

### Technology Stack

- **Framework**: Next.js 15 (App Router)
- **Language**: TypeScript 5
- **UI Library**: React 19
- **Styling**: Tailwind CSS
- **State Management**: React hooks, Context API
- **Authentication**: NextAuth.js
- **HTTP Client**: Fetch API, axios (for complex scenarios)
- **Forms**: React Hook Form (optional)
- **Testing**: Jest, React Testing Library

### Creating New Pages

```typescript
// src/app/portal/my-feature/page.tsx
'use client';

import { useState, useEffect } from 'react';

export default function MyFeaturePage() {
  const [data, setData] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    const response = await fetch('/api/my-feature');
    const data = await response.json();
    setData(data);
  };

  return (
    <div className="container mx-auto p-4">
      <h1 className="text-2xl font-bold mb-4">My Feature</h1>
      {/* Your component JSX */}
    </div>
  );
}
```

### Creating API Routes

```typescript
// src/app/api/my-feature/route.ts
import { NextRequest, NextResponse } from 'next/server';
import { getServerSession } from 'next-auth';

export async function GET(request: NextRequest) {
  // Check authentication
  const session = await getServerSession();

  if (!session) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 });
  }

  // Your logic here
  const data = { message: 'Hello from API' };

  return NextResponse.json(data);
}

export async function POST(request: NextRequest) {
  const body = await request.json();

  // Process request

  return NextResponse.json({ success: true });
}
```

### State Management Pattern

```typescript
// Using Context API for global state
// src/contexts/AgentContext.tsx
'use client';

import { createContext, useContext, useState, ReactNode } from 'react';

interface AgentContextType {
  agents: Agent[];
  addAgent: (agent: Agent) => void;
  removeAgent: (id: string) => void;
}

const AgentContext = createContext<AgentContextType | undefined>(undefined);

export function AgentProvider({ children }: { children: ReactNode }) {
  const [agents, setAgents] = useState<Agent[]>([]);

  const addAgent = (agent: Agent) => {
    setAgents([...agents, agent]);
  };

  const removeAgent = (id: string) => {
    setAgents(agents.filter(a => a.id !== id));
  };

  return (
    <AgentContext.Provider value={{ agents, addAgent, removeAgent }}>
      {children}
    </AgentContext.Provider>
  );
}

export function useAgents() {
  const context = useContext(AgentContext);
  if (!context) {
    throw new Error('useAgents must be used within AgentProvider');
  }
  return context;
}
```

### Styling Guidelines

**Tailwind CSS Classes**:
```tsx
// Consistent spacing
<div className="p-4 m-2 space-y-4">

// Responsive design
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">

// Buttons
<button className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition">

// Cards
<div className="bg-white rounded-lg shadow-md p-6">
```

## Backend Development

### Technology Stack

- **Framework**: FastAPI
- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0
- **Database**: PostgreSQL with pgvector
- **Async**: asyncio, httpx
- **Validation**: Pydantic v2
- **Testing**: pytest, pytest-asyncio

### Creating New API Endpoints

```python
# integrator/src/integrator/apis/routes/my_feature.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from integrator.utils.database import get_db
from integrator.models.my_model import MyModel
from integrator.iam.auth import get_current_user

router = APIRouter(prefix="/my-feature", tags=["my-feature"])

@router.get("/", response_model=List[MyModel])
async def get_items(
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get all items for current user."""
    items = db.query(MyModel).filter(
        MyModel.tenant_id == current_user.tenant_id
    ).all()
    return items

@router.post("/", response_model=MyModel)
async def create_item(
    item: MyModel,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create a new item."""
    item.tenant_id = current_user.tenant_id
    db.add(item)
    db.commit()
    db.refresh(item)
    return item
```

### Database Models

```python
# integrator/src/integrator/models/my_model.py
from sqlalchemy import Column, String, Integer, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime

from integrator.utils.database import Base

class MyModel(Base):
    __tablename__ = "my_table"
    __table_args__ = {'schema': 'public'}

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(String, ForeignKey("tenants.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    tenant = relationship("Tenant", back_populates="my_models")
```

### Pydantic Schemas

```python
# integrator/src/integrator/schemas/my_schema.py
from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class MyModelBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None

class MyModelCreate(MyModelBase):
    pass

class MyModelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None

class MyModelResponse(MyModelBase):
    id: int
    tenant_id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
```

### Authentication and Authorization

```python
# integrator/src/integrator/iam/auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from integrator.utils.database import get_db
from integrator.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user from token."""
    # Validate token and get user
    user = validate_token(token, db)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

async def check_permission(
    user: User = Depends(get_current_user),
    required_permission: str = None
):
    """Check if user has required permission."""
    if not user.has_permission(required_permission):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient permissions"
        )
```

## Database Development

### Migrations

```bash
# Create new migration
alembic revision -m "add my_table"

# Apply migrations
alembic upgrade head

# Rollback migration
alembic downgrade -1

# View migration history
alembic history
```

### Writing Migrations

```python
# migrations/versions/001_add_my_table.py
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'my_table',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('tenant_id', sa.String(), nullable=False),
        sa.Column('name', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['tenant_id'], ['tenants.id']),
        schema='public'
    )

    op.create_index('ix_my_table_tenant_id', 'my_table', ['tenant_id'])

def downgrade():
    op.drop_index('ix_my_table_tenant_id', table_name='my_table')
    op.drop_table('my_table', schema='public')
```

### Querying Best Practices

```python
# Use SQLAlchemy ORM efficiently

# ✅ Good: Lazy loading with explicit joins
agents = db.query(Agent)\
    .options(joinedload(Agent.tools))\
    .filter(Agent.tenant_id == tenant_id)\
    .all()

# ❌ Bad: N+1 queries
agents = db.query(Agent).filter(Agent.tenant_id == tenant_id).all()
for agent in agents:
    tools = agent.tools  # Triggers separate query for each agent

# ✅ Good: Pagination
page = 1
page_size = 20
offset = (page - 1) * page_size
items = db.query(MyModel).limit(page_size).offset(offset).all()

# ✅ Good: Use indexes
# Ensure tenant_id is indexed for multi-tenant queries
```

## API Development

### REST API Design Principles

**URL Structure**:
```
GET    /api/agents              # List agents
GET    /api/agents/:id          # Get specific agent
POST   /api/agents              # Create agent
PUT    /api/agents/:id          # Update agent (full)
PATCH  /api/agents/:id          # Update agent (partial)
DELETE /api/agents/:id          # Delete agent

# Nested resources
GET    /api/agents/:id/tools    # List agent's tools
POST   /api/agents/:id/tools    # Add tool to agent
```

**Status Codes**:
- `200 OK`: Successful GET, PUT, PATCH
- `201 Created`: Successful POST
- `204 No Content`: Successful DELETE
- `400 Bad Request`: Validation error
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

**Response Format**:
```json
{
  "success": true,
  "data": { /* resource */ },
  "meta": {
    "page": 1,
    "per_page": 20,
    "total": 100
  }
}

// Error response
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input",
    "details": [
      {
        "field": "email",
        "message": "Invalid email format"
      }
    ]
  }
}
```

### API Documentation

```python
# Use FastAPI's automatic documentation
@router.get(
    "/agents/{agent_id}",
    response_model=AgentResponse,
    summary="Get agent by ID",
    description="Retrieve a specific agent by its ID. Requires authentication.",
    responses={
        200: {"description": "Agent found"},
        404: {"description": "Agent not found"},
        403: {"description": "Insufficient permissions"}
    }
)
async def get_agent(
    agent_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get agent by ID with detailed information."""
    # Implementation
```

## Testing

### Backend Testing

```python
# tests/test_my_feature.py
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from integrator.apis.api_server import app
from integrator.utils.database import Base, get_db

# Test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
TestingSessionLocal = sessionmaker(bind=engine)

@pytest.fixture
def test_db():
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def client(test_db):
    def override_get_db():
        yield test_db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)

def test_create_agent(client):
    response = client.post(
        "/api/agents",
        json={"name": "Test Agent", "role": "assistant"}
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Agent"

def test_get_agents(client):
    response = client.get("/api/agents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
```

### Frontend Testing

```typescript
// agent-studio/src/components/__tests__/MyComponent.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import '@testing-library/jest-dom';
import MyComponent from '../MyComponent';

describe('MyComponent', () => {
  it('renders component', () => {
    render(<MyComponent />);
    expect(screen.getByText('Hello')).toBeInTheDocument();
  });

  it('handles click event', () => {
    const handleClick = jest.fn();
    render(<MyComponent onClick={handleClick} />);

    fireEvent.click(screen.getByRole('button'));
    expect(handleClick).toHaveBeenCalledTimes(1);
  });
});
```

### Integration Testing

```bash
# Run integration tests
pytest tests/integration/ -v

# Run with coverage
pytest --cov=integrator tests/

# Generate coverage report
pytest --cov=integrator --cov-report=html tests/
```

## Debugging

### Backend Debugging

```python
# Add breakpoints
import pdb; pdb.set_trace()

# Or use ipdb for enhanced debugging
import ipdb; ipdb.set_trace()

# Logging
import logging
logger = logging.getLogger(__name__)

logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
```

### Frontend Debugging

```typescript
// Console logging
console.log('Debug:', value);
console.error('Error:', error);
console.table(data);

// React DevTools
// Install React Developer Tools browser extension

// Network inspection
// Use browser DevTools Network tab

// Source maps
// Enable in next.config.ts for production debugging
```

### Docker Debugging

```bash
# View logs
docker-compose logs -f service-name

# Execute commands in container
docker exec -it container-name bash

# Inspect container
docker inspect container-name

# Check resource usage
docker stats
```

## Code Style and Standards

### Python Style Guide

Follow [PEP 8](https://pep8.org/) and use these tools:

```bash
# Format code
black src/

# Sort imports
isort src/

# Lint code
flake8 src/
pylint src/

# Type checking
mypy src/
```

### TypeScript/JavaScript Style Guide

```bash
# Format code
npm run format

# Lint code
npm run lint

# Fix linting issues
npm run lint:fix

# Type checking
npm run type-check
```

### Code Review Checklist

- [ ] Code follows style guidelines
- [ ] All tests pass
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] No sensitive data in code
- [ ] Error handling implemented
- [ ] Logging added appropriately
- [ ] Performance considered
- [ ] Security reviewed
- [ ] Backward compatibility maintained

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for detailed contribution guidelines.

### Pull Request Process

1. Create feature branch from `develop`
2. Implement changes with tests
3. Update documentation
4. Run linting and tests locally
5. Push branch and create PR
6. Address review feedback
7. Squash commits if requested
8. Merge after approval

### Getting Help

- **Documentation**: Check existing docs first
- **Issues**: Search GitHub issues
- **Discussions**: GitHub Discussions
- **Chat**: Discord/Slack community

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Maintained By**: Agentic Coworker Team
