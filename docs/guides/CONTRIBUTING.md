# Contributing to Agentic Coworker

Thank you for your interest in contributing to Agentic Coworker! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Process](#development-process)
- [Coding Standards](#coding-standards)
- [Commit Guidelines](#commit-guidelines)
- [Pull Request Process](#pull-request-process)
- [Testing Guidelines](#testing-guidelines)
- [Documentation](#documentation)
- [Community](#community)

## Code of Conduct

### Our Pledge

We as members, contributors, and leaders pledge to make participation in our community a harassment-free experience for everyone, regardless of age, body size, visible or invisible disability, ethnicity, sex characteristics, gender identity and expression, level of experience, education, socio-economic status, nationality, personal appearance, race, religion, or sexual identity and orientation.

### Our Standards

**Positive behavior includes**:
- Using welcoming and inclusive language
- Being respectful of differing viewpoints and experiences
- Gracefully accepting constructive criticism
- Focusing on what is best for the community
- Showing empathy towards other community members

**Unacceptable behavior includes**:
- The use of sexualized language or imagery
- Trolling, insulting/derogatory comments, and personal or political attacks
- Public or private harassment
- Publishing others' private information without explicit permission
- Other conduct which could reasonably be considered inappropriate

### Enforcement

Instances of abusive, harassing, or otherwise unacceptable behavior may be reported to the project team at conduct@yourproject.com. All complaints will be reviewed and investigated promptly and fairly.

## Getting Started

### Prerequisites

Before contributing, ensure you have:

1. **GitHub Account**: [Sign up](https://github.com/signup) if you don't have one
2. **Development Environment**: Set up per [Developer Guide](DEVELOPER_GUIDE.md)
3. **Read Documentation**: Familiarize yourself with:
   - [README.md](../../README.md) - Project overview
   - [ARCHITECTURE.md](ARCHITECTURE.md) - System architecture
   - [DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md) - Development setup

### Finding Issues to Work On

1. Browse [Issues](https://github.com/YOUR_USERNAME/agentic-coworker/issues)
2. Look for labels:
   - `good first issue` - Great for newcomers
   - `help wanted` - Community help needed
   - `bug` - Bug fixes
   - `enhancement` - New features
   - `documentation` - Documentation improvements

3. Comment on the issue to express interest
4. Wait for maintainer assignment before starting work

## How to Contribute

### Types of Contributions

#### 🐛 Bug Reports

Found a bug? Help us fix it!

**Before submitting**:
- Search [existing issues](https://github.com/YOUR_USERNAME/agentic-coworker/issues) to avoid duplicates
- Try to reproduce on the latest version
- Gather relevant information (OS, versions, error logs)

**Creating a bug report**:
1. Use the bug report template
2. Provide a clear, descriptive title
3. Include steps to reproduce
4. Describe expected vs actual behavior
5. Add screenshots if applicable
6. Include environment details
7. Add relevant logs or error messages

#### ✨ Feature Requests

Have an idea? We'd love to hear it!

**Before submitting**:
- Check if the feature already exists
- Search [existing feature requests](https://github.com/YOUR_USERNAME/agentic-coworker/issues?q=is%3Aissue+label%3Aenhancement)
- Consider if it fits the project's scope

**Creating a feature request**:
1. Use the feature request template
2. Describe the problem you're solving
3. Explain your proposed solution
4. List alternatives you've considered
5. Add mockups or examples if helpful

#### 💻 Code Contributions

Ready to code? Follow these steps:

1. **Discuss first**: Comment on the issue or create one
2. **Fork and clone**: Fork the repository and clone it locally
3. **Create a branch**: Create a feature branch from `develop`
4. **Make changes**: Implement your changes following coding standards
5. **Test thoroughly**: Add and run tests
6. **Document**: Update relevant documentation
7. **Submit PR**: Create a pull request for review

#### 📚 Documentation Contributions

Documentation is as important as code!

**Documentation improvements**:
- Fix typos and grammar
- Clarify confusing sections
- Add examples and tutorials
- Create diagrams and visuals
- Translate documentation

**Where documentation lives**:
- `README.md` - Project overview
- `docs/` - Setup guides
- `ARCHITECTURE.md` - Technical architecture
- `DEPLOYMENT.md` - Deployment instructions
- `USER_GUIDE.md` - User documentation
- `DEVELOPER_GUIDE.md` - Developer documentation
- Inline code comments
- API documentation (docstrings, JSDoc)

## Development Process

### 1. Fork the Repository

```bash
# Click "Fork" on GitHub, then clone your fork
git clone https://github.com/YOUR_USERNAME/agentic-coworker.git
cd agentic-coworker

# Add upstream remote
git remote add upstream https://github.com/ORIGINAL_OWNER/agentic-coworker.git
```

### 2. Create a Branch

```bash
# Update your fork
git checkout develop
git pull upstream develop

# Create a feature branch
git checkout -b feature/your-feature-name

# Or for bug fixes
git checkout -b fix/bug-description
```

### 3. Make Changes

Follow the [Developer Guide](DEVELOPER_GUIDE.md) for:
- Setting up development environment
- Running services locally
- Code organization
- Testing approach

### 4. Commit Your Changes

Follow [Commit Guidelines](#commit-guidelines):

```bash
git add .
git commit -m "feat: add new feature description"
```

### 5. Keep Your Branch Updated

```bash
# Fetch latest changes
git fetch upstream

# Rebase onto develop
git rebase upstream/develop

# Resolve conflicts if any
```

### 6. Push to Your Fork

```bash
git push origin feature/your-feature-name
```

### 7. Create Pull Request

1. Go to your fork on GitHub
2. Click "Compare & pull request"
3. Fill in the PR template
4. Link related issues
5. Request review from maintainers

## Coding Standards

### General Principles

1. **Write Clean Code**:
   - Self-documenting variable and function names
   - Small, focused functions (single responsibility)
   - Clear comments for complex logic
   - Consistent formatting

2. **Follow DRY** (Don't Repeat Yourself):
   - Extract repeated code into functions
   - Use composition over duplication

3. **Handle Errors Gracefully**:
   - Validate inputs
   - Provide meaningful error messages
   - Log errors appropriately

4. **Write Tests**:
   - Unit tests for individual functions
   - Integration tests for component interaction
   - E2E tests for critical user flows

### Python Style Guide

Follow [PEP 8](https://pep8.org/):

```python
# Good: Clear, descriptive names
def calculate_agent_success_rate(agent_id: str, time_period: str) -> float:
    """
    Calculate the success rate of an agent over a time period.

    Args:
        agent_id: The unique identifier of the agent
        time_period: The time period for calculation (e.g., "7d", "30d")

    Returns:
        Success rate as a float between 0.0 and 1.0

    Raises:
        ValueError: If agent_id is invalid or time_period is malformed
    """
    # Implementation
    pass

# Bad: Unclear names, no documentation
def calc(a, t):
    # Implementation
    pass
```

**Python Tools**:
```bash
# Format code
black src/

# Sort imports
isort src/

# Type checking
mypy src/

# Linting
flake8 src/
pylint src/
```

### TypeScript/JavaScript Style Guide

Follow [Airbnb Style Guide](https://github.com/airbnb/javascript):

```typescript
// Good: Type safety, clear names
interface Agent {
  id: string;
  name: string;
  status: 'active' | 'inactive' | 'error';
}

async function fetchAgentById(agentId: string): Promise<Agent> {
  const response = await fetch(`/api/agents/${agentId}`);

  if (!response.ok) {
    throw new Error(`Failed to fetch agent: ${response.statusText}`);
  }

  return response.json();
}

// Bad: No types, unclear names
async function get(id) {
  const res = await fetch(`/api/agents/${id}`);
  return res.json();
}
```

**TypeScript Tools**:
```bash
# Format code
npm run format

# Lint code
npm run lint

# Type checking
npm run type-check
```

### Database Migrations

```python
# Good: Descriptive name, proper up/down
"""add_agent_metrics_table

Revision ID: 001
Create Date: 2026-02-05
"""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.create_table(
        'agent_metrics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.String(), nullable=False),
        sa.Column('success_count', sa.Integer(), default=0),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['agent_id'], ['agents.id'])
    )
    op.create_index('ix_agent_metrics_agent_id', 'agent_metrics', ['agent_id'])

def downgrade():
    op.drop_index('ix_agent_metrics_agent_id', table_name='agent_metrics')
    op.drop_table('agent_metrics')
```

## Commit Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/).

### Commit Message Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, semicolons, etc.)
- `refactor`: Code change that neither fixes a bug nor adds a feature
- `perf`: Performance improvement
- `test`: Adding or updating tests
- `build`: Build system or dependencies
- `ci`: CI configuration
- `chore`: Other changes that don't modify src or test files

### Examples

```bash
# Feature
git commit -m "feat(agent-studio): add agent cloning functionality"

# Bug fix
git commit -m "fix(integrator): resolve token refresh race condition"

# Documentation
git commit -m "docs(readme): update installation instructions"

# With body and footer
git commit -m "feat(mcp): add support for streaming responses

Implement Server-Sent Events (SSE) for real-time agent responses.
This improves user experience by showing progress updates.

Closes #123"
```

### Commit Best Practices

1. **One logical change per commit**: Don't mix unrelated changes
2. **Write clear messages**: Explain what and why, not how
3. **Reference issues**: Use "Closes #123" or "Fixes #456"
4. **Keep commits atomic**: Each commit should leave the code in a working state

## Pull Request Process

### Before Submitting

- [ ] Code follows style guidelines
- [ ] All tests pass locally
- [ ] New tests added for new features
- [ ] Documentation updated
- [ ] Commit messages follow conventions
- [ ] Branch is up to date with `develop`
- [ ] No merge conflicts

### PR Description

Use the PR template and include:

1. **Description**: What does this PR do?
2. **Motivation**: Why is this change needed?
3. **Related Issues**: Link to issues (e.g., "Closes #123")
4. **Type of Change**:
   - [ ] Bug fix (non-breaking)
   - [ ] New feature (non-breaking)
   - [ ] Breaking change
   - [ ] Documentation update

5. **Testing**: How was this tested?
6. **Screenshots**: If UI changes
7. **Checklist**: Complete the checklist

### Review Process

1. **Automated Checks**: CI/CD runs tests and linting
2. **Maintainer Review**: At least one maintainer must approve
3. **Address Feedback**: Make requested changes
4. **Final Approval**: Maintainer merges when ready

### After Your PR is Merged

1. Delete your feature branch
2. Update your local repository:
   ```bash
   git checkout develop
   git pull upstream develop
   ```
3. Celebrate! 🎉 Your contribution is now part of the project!

## Testing Guidelines

### Test Coverage Goals

- **Unit Tests**: 80%+ coverage
- **Integration Tests**: Critical paths
- **E2E Tests**: Key user workflows

### Writing Tests

#### Backend Tests (Python)

```python
# tests/test_agent.py
import pytest
from integrator.models.agent import Agent
from integrator.utils.database import get_test_db

@pytest.fixture
def test_agent(test_db):
    """Fixture providing a test agent."""
    agent = Agent(
        name="Test Agent",
        tenant_id="test-tenant",
        role="assistant"
    )
    test_db.add(agent)
    test_db.commit()
    return agent

def test_create_agent(test_db):
    """Test creating a new agent."""
    agent = Agent(name="New Agent", tenant_id="tenant-1")
    test_db.add(agent)
    test_db.commit()

    assert agent.id is not None
    assert agent.name == "New Agent"

def test_agent_permissions(test_agent):
    """Test agent permission checking."""
    assert test_agent.has_permission("read:tools") == True
    assert test_agent.has_permission("admin:*") == False
```

#### Frontend Tests (TypeScript)

```typescript
// components/__tests__/AgentCard.test.tsx
import { render, screen, fireEvent } from '@testing-library/react';
import AgentCard from '../AgentCard';

describe('AgentCard', () => {
  const mockAgent = {
    id: '1',
    name: 'Test Agent',
    status: 'active',
  };

  it('renders agent information', () => {
    render(<AgentCard agent={mockAgent} />);

    expect(screen.getByText('Test Agent')).toBeInTheDocument();
    expect(screen.getByText('active')).toBeInTheDocument();
  });

  it('calls onStart when start button clicked', () => {
    const onStart = jest.fn();
    render(<AgentCard agent={mockAgent} onStart={onStart} />);

    fireEvent.click(screen.getByText('Start'));
    expect(onStart).toHaveBeenCalledWith('1');
  });
});
```

### Running Tests

```bash
# Backend
cd integrator
pytest                        # Run all tests
pytest tests/test_agent.py   # Run specific test file
pytest -v                     # Verbose output
pytest --cov                  # With coverage

# Frontend
cd agent-studio
npm test                      # Run all tests
npm test -- AgentCard        # Run specific test
npm test -- --coverage        # With coverage
```

## Documentation

### Documentation Standards

1. **Code Comments**:
   - Explain *why*, not *what* (code should be self-explanatory)
   - Document complex algorithms
   - Add TODOs with GitHub issue references

2. **Docstrings** (Python):
   ```python
   def process_agent_task(agent_id: str, task: dict) -> dict:
       """
       Process a task assigned to an agent.

       Args:
           agent_id: The unique identifier of the agent
           task: Task dictionary containing:
               - type: Task type (e.g., "query", "action")
               - payload: Task-specific data

       Returns:
           Result dictionary containing:
               - success: Boolean indicating completion
               - result: Task output
               - error: Error message if failed

       Raises:
           ValueError: If agent_id is invalid
           TaskExecutionError: If task fails to execute

       Example:
           >>> process_agent_task("agent-123", {"type": "query", "payload": {...}})
           {"success": True, "result": {...}}
       """
   ```

3. **JSDoc** (TypeScript):
   ```typescript
   /**
    * Fetches an agent by ID from the API
    *
    * @param agentId - The unique identifier of the agent
    * @returns Promise resolving to the Agent object
    * @throws {Error} If the agent is not found or network error occurs
    *
    * @example
    * ```typescript
    * const agent = await fetchAgent('agent-123');
    * console.log(agent.name);
    * ```
    */
   async function fetchAgent(agentId: string): Promise<Agent> {
     // Implementation
   }
   ```

### Updating Documentation

When making changes:

1. **Update README.md** if changing:
   - Installation steps
   - Configuration
   - Quick start guide

2. **Update relevant guides**:
   - ARCHITECTURE.md for architectural changes
   - DEPLOYMENT.md for deployment changes
   - USER_GUIDE.md for user-facing features
   - DEVELOPER_GUIDE.md for development changes

3. **Update inline documentation**:
   - Docstrings for new functions/classes
   - JSDoc for new components/functions
   - Comments for complex logic

4. **Add examples**:
   - Usage examples in docstrings
   - Code snippets in guides
   - Screenshots for UI changes

## Community

### Communication Channels

- **GitHub Issues**: Bug reports and feature requests
- **GitHub Discussions**: General questions and ideas
- **Discord/Slack**: Real-time chat (link)
- **Email**: contact@yourproject.com

### Getting Help

- Search existing issues and documentation
- Ask in Discord/Slack
- Create a GitHub Discussion
- Email for private matters

### Recognition

Contributors are recognized in:
- [CONTRIBUTORS.md](CONTRIBUTORS.md) file
- Release notes
- Annual contributor spotlight

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

## Quick Reference

### Contribution Checklist

- [ ] Issue discussed with maintainers
- [ ] Fork and branch created
- [ ] Code follows style guidelines
- [ ] Tests added and passing
- [ ] Documentation updated
- [ ] Commits follow conventions
- [ ] PR description completed
- [ ] CI checks passing

### Need Help?

- 📖 [Developer Guide](DEVELOPER_GUIDE.md)
- 💬 [Discord/Slack](LINK)
- 📧 Email: dev@yourproject.com

---

**Thank you for contributing to Agentic Coworker!** 🎉

Your contributions make this project better for everyone.

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Maintained By**: Agentic Coworker Team
