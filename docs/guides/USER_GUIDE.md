# Agentic Coworker - User Guide

## Table of Contents

- [Introduction](#introduction)
- [Getting Started](#getting-started)
- [Dashboard](#dashboard)
- [Managing Agents](#managing-agents)
- [Working with Tools](#working-with-tools)
- [Configuring Integrations](#configuring-integrations)
- [Chat with Agents](#chat-with-agents)
- [Domains and Capabilities](#domains-and-capabilities)
- [User Management](#user-management)
- [Best Practices](#best-practices)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

## Introduction

Welcome to Agentic Coworker! This guide will help you navigate the platform and make the most of your AI agents.

### What is Agentic Coworker?

Agentic Coworker is a governed AI agent platform that enables you to create autonomous agents that work across your entire business ecosystem—from social platforms to enterprise systems—with enterprise-grade security and governance.

### Key Concepts

**Agent**: An autonomous AI entity that can perform tasks, access tools, and interact with external systems on your behalf.

**Tool**: An API endpoint or capability that an agent can use to perform actions (e.g., send email, create ticket, query data).

**Domain**: A business area or category (e.g., "Sales", "IT Support", "Marketing") that organizes related capabilities.

**Role**: A collection of permissions that define what an agent can do within specific domains.

**Tenant**: Your organization's isolated workspace within the platform.

## Getting Started

### Accessing the Platform

1. Navigate to your Agentic Coworker instance (e.g., `https://yourdomain.com` or `http://localhost:3000`)
2. Click **"Sign In"**
3. Choose your authentication method:
   - **Keycloak** (default)
   - **Google**
   - **GitHub**
   - **LinkedIn**

### First-Time Setup

After logging in for the first time:

1. **Select or Create Tenant**
   - Choose your organization from the dropdown
   - Or create a new tenant if you have permissions

2. **Review Dashboard**
   - Overview of your agents and their activities
   - Recent events and notifications
   - System status

3. **Configure Integrations** (Optional)
   - Set up OAuth providers for external services
   - Add API keys for third-party services

## Dashboard

The dashboard provides an at-a-glance view of your agentic ecosystem.

### Dashboard Sections

#### Overview Metrics
- **Active Agents**: Number of agents currently running
- **Tools Available**: Total tools your agents can access
- **Recent Activities**: Latest agent actions and events
- **System Health**: Status of platform services

#### Agent Status
- View all agents with their current status
- Quick actions: Start, Stop, Configure
- Performance metrics per agent

#### Recent Events
- Agent task completions
- Tool executions
- Errors and warnings
- User actions

### Customizing Your Dashboard

1. Click **"Customize Dashboard"** button
2. Drag and drop widgets to rearrange
3. Show/hide specific metrics
4. Save your layout

## Managing Agents

### Creating a New Agent

1. Navigate to **"Agent Management"**
2. Click **"Create Agent"** button
3. Fill in agent details:
   - **Name**: Descriptive name (e.g., "Sales Assistant")
   - **Description**: What the agent does
   - **Role**: Select from available roles (affects permissions)
   - **Model**: Choose LLM provider (GPT-5, Gemini, Claude, etc.)

4. Configure agent settings:
   - **System Prompt**: Instructions for agent behavior
   - **Temperature**: Creativity level (0.0 - 1.0)
   - **Max Tokens**: Response length limit
   - **Tools**: Select which tools agent can access

5. Click **"Create"**

### Agent Profile

View and edit agent configuration:

#### Basic Information
- Name, description, status
- Creation date and last activity
- Assigned role and permissions

#### Tool Access
- View tools the agent can use
- Organized by domain and capability
- Add or remove tool access

#### Performance Metrics
- Tasks completed
- Success rate
- Average execution time
- Token usage

### Starting and Stopping Agents

**Start Agent**:
1. Navigate to agent profile
2. Click **"Start Agent"** button
3. Agent status changes to "Active"

**Stop Agent**:
1. Navigate to agent profile
2. Click **"Stop Agent"** button
3. Confirm action
4. Agent completes current task then stops

### Editing Agent Configuration

1. Navigate to agent profile
2. Click **"Edit"** button
3. Modify settings
4. Click **"Save Changes"**
5. Restart agent if required

### Deleting an Agent

⚠️ **Warning**: This action cannot be undone.

1. Navigate to agent profile
2. Click **"Delete Agent"** button
3. Type agent name to confirm
4. Click **"Delete Permanently"**

## Working with Tools

Tools are the capabilities that agents use to perform actions.

### Tool Library

View all available tools in **"MCP Tools"**:

#### Tool Organization

Tools are organized hierarchically:
```
Domain (e.g., "Sales")
  └── Capability (e.g., "Contact Management")
      └── Skill (e.g., "Create Contact")
          └── Tool (specific API endpoint)
```

#### Tool Details

For each tool:
- **Name and Description**: What the tool does
- **Provider**: Source system (e.g., Salesforce, Gmail)
- **Parameters**: Required inputs
- **Authentication**: How the tool authenticates
- **Usage Count**: How many times it's been used
- **Success Rate**: Reliability metric

### Importing New Tools

#### From API Documentation

1. Navigate to **"Tool Importer"**
2. Select import source:
   - **URL**: Paste API documentation URL
   - **OpenAPI/Swagger**: Upload specification file
   - **Postman**: Import Postman collection

3. Click **"Import"**
4. Review detected endpoints
5. Select endpoints to import
6. Configure authentication
7. Click **"Add to Staging"**

#### Testing in Staging

1. Navigate to **"Staging Services"**
2. Select imported tool
3. Fill in test parameters
4. Click **"Test Tool"**
5. Review response
6. If successful, click **"Publish"**

### Tool Testing

Before agents use tools, test them manually:

1. Navigate to tool detail page
2. Click **"Test Tool"** tab
3. Fill in required parameters
4. Select authentication method
5. Click **"Execute Test"**
6. Review results:
   - ✅ Success: Tool works correctly
   - ❌ Error: Review error message and fix

### Publishing Tools

After testing in staging:

1. Navigate to staging tool
2. Review test results
3. Click **"Publish to Production"**
4. Tool becomes available to agents

## Configuring Integrations

### OAuth Providers

Connect external services for agent access.

#### Setting Up OAuth

1. Navigate to **"Auth Providers"**
2. Click **"Add Provider"**
3. Select provider type:
   - Google
   - GitHub
   - LinkedIn
   - ServiceNow

4. Enter credentials:
   - **Client ID**: From provider's developer console
   - **Client Secret**: From provider's developer console
   - **Redirect URL**: Provided by platform

5. Click **"Save"**

**Setup Guides**:
- [Google OAuth Setup](../setup-guides/google-oauth-setup.md)
- [GitHub OAuth Setup](../setup-guides/github-oauth-setup.md)
- [LinkedIn OAuth Setup](../setup-guides/linkedin-oauth-setup.md)
- [ServiceNow Setup](../setup-guides/servicenow-api-setup.md)

#### Managing OAuth Tokens

1. Navigate to **"Provider Tokens"**
2. View connected accounts
3. Actions:
   - **Refresh Token**: Manually refresh authentication
   - **Revoke Access**: Disconnect account
   - **Re-authorize**: Fix authentication issues

### API Keys

Configure API keys for services that don't use OAuth.

#### Adding API Keys

1. Navigate to **"Service Secrets"**
2. Click **"Add Secret"**
3. Enter details:
   - **Service Name**: (e.g., "SAP API")
   - **Service URL**: Base URL of the API
   - **Secret Type**: Headers, Query Parameters, or Body
   - **Secret Key**: Parameter name (e.g., "APIKey", "api_key")
   - **Secret Value**: Your API key

4. Click **"Save"**

**Setup Guides**:
- [SAP API Key Setup](../setup-guides/sap-api-key-setup.md)
- [FRED API Key Setup](../setup-guides/fred-api-key-setup.md)
- [SEC API Key Setup](../setup-guides/sec-api-key-setup.md)
- [Alpha Vantage API Key Setup](../setup-guides/alphavantage-api-key-setup.md)

## Chat with Agents

Interact with your agents through natural language conversation.

### Starting a Chat

1. Navigate to **"Agent Chat"**
2. Select an agent from the sidebar
3. Type your message in the chat input
4. Press **Enter** or click **Send**

### Chat Features

#### Message Types

**User Message**:
```
You: Create a sales report for Q1 2024
```

**Agent Response**:
```
Agent: I'll create that report for you.
I'm accessing the sales data...
[Tool: Query Sales Database]
Report generated successfully!
[Attachment: Q1_2024_Sales_Report.pdf]
```

**System Message**:
```
System: Agent has completed the task.
```

#### Rich Interactions

- **Attachments**: View files generated by agents
- **Links**: Click to open external resources
- **Code Blocks**: Formatted code snippets
- **Tables**: Structured data display
- **Action Buttons**: Quick actions suggested by agent

### Chat Best Practices

1. **Be Specific**: Clearly state what you need
   - ❌ "Send email"
   - ✅ "Send email to john@example.com with subject 'Meeting Reminder' about tomorrow's 2pm meeting"

2. **Provide Context**: Give relevant background
   - "Using data from last month, calculate the growth rate"

3. **Confirm Critical Actions**: Review before agent executes
   - "Before sending, show me the draft email"

4. **Break Down Complex Tasks**: Split into smaller steps
   - Instead of: "Analyze entire business"
   - Do: "First, show me Q1 revenue. Then, compare with last year."

## Domains and Capabilities

Organize your business processes and agent capabilities.

### Managing Domains

Domains represent business areas (Sales, IT, Marketing, etc.)

#### Creating a Domain

1. Navigate to **"Domains"**
2. Click **"Create Domain"**
3. Enter details:
   - **Name**: (e.g., "Customer Support")
   - **Description**: Purpose of this domain
   - **Owner**: Responsible person

4. Click **"Create"**

#### Adding Capabilities to Domains

1. Select a domain
2. Click **"Add Capability"**
3. Enter capability details:
   - **Name**: (e.g., "Ticket Management")
   - **Description**: What this capability does

4. Link skills and tools to the capability
5. Click **"Save"**

### Permission Management

Control what agents can do in each domain:

1. Navigate to agent profile
2. Go to **"Permissions"** tab
3. Select domains the agent can access
4. For each domain, grant specific capabilities
5. Click **"Save Permissions"**

## User Management

Manage users and their access to the platform (Admin only).

### Adding Users

1. Navigate to **"User Management"**
2. Click **"Add User"**
3. Enter user details:
   - **Email**: User's email address
   - **Name**: Full name
   - **Role**: Owner, Member, or Viewer

4. Click **"Send Invitation"**
5. User receives email with login instructions

### User Roles

| Role | Permissions |
|------|-------------|
| **Owner** | Full control: manage agents, tools, users, settings |
| **Member** | Create and manage agents, use tools, view reports |
| **Viewer** | Read-only access: view agents, tools, reports |

### Managing User Access

**Edit User**:
1. Find user in list
2. Click **"Edit"**
3. Modify role or details
4. Click **"Save"**

**Deactivate User**:
1. Find user in list
2. Click **"Deactivate"**
3. Confirm action
4. User can no longer access platform

**Reactivate User**:
1. Find deactivated user
2. Click **"Reactivate"**
3. User can access platform again

## Best Practices

### Agent Design

1. **Single Responsibility**: Each agent should have a clear, focused purpose
   - ✅ "Email Assistant" for handling emails
   - ❌ "Do Everything Agent"

2. **Appropriate Permissions**: Grant only necessary tool access
   - Use role-based access control
   - Review permissions regularly

3. **Clear Instructions**: Write detailed system prompts
   - Define agent's role and constraints
   - Provide examples of good responses

4. **Regular Monitoring**: Check agent performance
   - Review success rates
   - Investigate failures
   - Update instructions as needed

### Security Best Practices

1. **Credential Management**:
   - Rotate API keys regularly
   - Use strong, unique passwords
   - Don't share credentials

2. **Access Control**:
   - Follow principle of least privilege
   - Review user access periodically
   - Remove access for departing users

3. **Data Protection**:
   - Don't include sensitive data in prompts
   - Review agent logs for PII
   - Use encrypted connections

4. **OAuth Best Practices**:
   - Revoke unused tokens
   - Re-authorize when changing scopes
   - Monitor authorization logs

### Performance Optimization

1. **Tool Selection**:
   - Use specific tools rather than general ones
   - Cache frequently accessed data
   - Batch operations when possible

2. **Prompt Engineering**:
   - Keep prompts concise and clear
   - Provide structured output format
   - Use examples for complex tasks

3. **Resource Management**:
   - Monitor token usage
   - Set appropriate rate limits
   - Scale agents based on demand

## Troubleshooting

### Common Issues and Solutions

#### Agent Not Responding

**Symptoms**: Agent doesn't reply to messages

**Solutions**:
1. Check agent status (should be "Active")
2. Verify LLM provider credentials
3. Check API quota limits
4. Review agent logs for errors

#### Authentication Failures

**Symptoms**: "Unauthorized" or "Token expired" errors

**Solutions**:
1. Navigate to **"Provider Tokens"**
2. Click **"Refresh Token"** for the provider
3. If refresh fails, click **"Re-authorize"**
4. Grant permissions again

#### Tool Execution Errors

**Symptoms**: Agent reports tool failed

**Solutions**:
1. Navigate to tool detail page
2. Click **"Test Tool"** to manually verify
3. Check API key/OAuth token is valid
4. Review error message for specific issue
5. Verify required parameters are correct

#### Slow Performance

**Symptoms**: Agents take long time to respond

**Solutions**:
1. Check system status on dashboard
2. Reduce number of tools agent must choose from
3. Use more specific prompts
4. Consider upgrading LLM model
5. Check network connectivity

#### Rate Limit Errors

**Symptoms**: "Too many requests" errors

**Solutions**:
1. Check API provider rate limits
2. Reduce agent request frequency
3. Implement caching for repeated queries
4. Upgrade API plan if needed

### Getting Help

1. **Check Documentation**:
   - This user guide
   - [Architecture Documentation](ARCHITECTURE.md)
   - [Setup Guides](../)

2. **View Logs**:
   - Agent execution logs
   - System logs
   - API logs

3. **Contact Support**:
   - Email: support@yourcompany.com
   - GitHub Issues: [Link]
   - Community Forum: [Link]

## FAQ

### General Questions

**Q: How many agents can I create?**
A: Depends on your plan. Check with your administrator for limits.

**Q: Can agents work together?**
A: Yes! Agents can be configured to collaborate on complex tasks.

**Q: What happens if an agent makes a mistake?**
A: Agents can be configured with human-in-the-loop approval for critical actions. You can also review and rollback changes.

**Q: How is my data secured?**
A: All credentials are encrypted (AES-256-GCM), data is tenant-isolated, and communications use TLS.

### Technical Questions

**Q: What LLM models are supported?**
A: GPT-5 (Azure OpenAI), GPT-4o (OpenAI), Gemini 2.5 Flash (Google), Claude Sonnet 4.5 (Anthropic), and local models (MLX).

**Q: Can I use my own custom APIs?**
A: Yes! Use the Tool Importer to add any REST API.

**Q: How do I integrate with on-premises systems?**
A: You can deploy the platform on-premises and configure direct network access to internal APIs.

**Q: What's the difference between staging and production tools?**
A: Staging is for testing new tools safely. Production tools are verified and available to all agents.

### Troubleshooting Questions

**Q: Why can't my agent access certain tools?**
A: Check the agent's role and permissions. The agent must have explicit access to the domain containing the tool.

**Q: My OAuth token keeps expiring. What should I do?**
A: This is normal. Tokens are automatically refreshed. If auto-refresh fails, manually re-authorize in "Provider Tokens".

**Q: How do I report a bug?**
A: Create an issue on GitHub or contact support with detailed steps to reproduce.

## Glossary

**API**: Application Programming Interface - allows software to communicate

**Domain**: Business area or category organizing related capabilities

**LLM**: Large Language Model - the AI powering agents

**MCP**: Model Context Protocol - standard for agent-tool communication

**OAuth**: Open Authorization - secure authentication protocol

**Role**: Collection of permissions defining what an agent can do

**Tenant**: Isolated workspace for your organization

**Token**: Authentication credential with expiration time

**Tool**: Capability or API endpoint an agent can use

---

## Additional Resources

- [Setup Guides](../) - OAuth and API key configuration
- [Architecture Documentation](ARCHITECTURE.md) - Technical details
- [Deployment Guide](DEPLOYMENT.md) - Installation and setup
- [Developer Guide](DEVELOPER_GUIDE.md) - For customization
- [API Reference](API_REFERENCE.md) - API documentation

---

**Need Help?**

- 📧 Email: support@yourcompany.com
- 💬 Community: [Discord/Slack Link]
- 📝 Issues: [GitHub Issues](https://github.com/YOUR_USERNAME/agentic-coworker/issues)

---

**Document Version**: 1.0
**Last Updated**: February 2026
**Maintained By**: Agentic Coworker Team
