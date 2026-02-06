# ServiceNow API Setup Guide

This guide walks you through configuring ServiceNow API access for the Agentic Coworker platform. ServiceNow supports two authentication methods: **OAuth 2.0** (recommended) and **Basic Authentication with API Keys**. This guide covers both approaches.

## Overview

ServiceNow provides access to:
- IT Service Management (ITSM) data
- Incident, problem, and change management
- Service catalog and requests
- Knowledge base articles
- CMDB (Configuration Management Database)
- User and group management
- Custom applications and workflows

Your agents can use ServiceNow API to:
- Create and update incidents/tickets
- Query and manage service requests
- Access knowledge base
- Automate ITSM workflows
- Generate reports and analytics
- Integrate with IT operations

## Prerequisites

- ServiceNow instance (Developer, Personal Developer Instance, or Production)
- ServiceNow account with appropriate permissions
- Admin access to your Agentic Coworker deployment

## Choose Your Authentication Method

ServiceNow supports two authentication methods:

| Method | Security | Setup Complexity | Use Case |
|--------|----------|-----------------|----------|
| **OAuth 2.0** | High | Medium | Production, user delegation |
| **Basic Auth** | Medium | Low | Development, service accounts |

**Recommendation**:
- **Development/Testing**: Basic Authentication (simpler setup)
- **Production**: OAuth 2.0 (more secure, token-based)

---

## Method 1: OAuth 2.0 Authentication (Recommended for Production)

OAuth 2.0 provides secure, token-based authentication with automatic token refresh.

### Step 1: Get ServiceNow Instance

If you don't have a ServiceNow instance:

1. Navigate to [ServiceNow Developer Program](https://developer.servicenow.com/)
2. Click **"Sign up and Start Building"**
3. Create an account or sign in
4. Request a **Personal Developer Instance (PDI)**:
   - Go to **"Manage" > "Instance"**
   - Click **"Request Instance"**
   - Select the latest release
   - Wait for provisioning (usually a few minutes)
5. You'll receive an instance URL like: `https://devXXXXX.service-now.com`

### Step 2: Create OAuth Application in ServiceNow

1. Log in to your ServiceNow instance as an admin
2. Navigate to **System OAuth > Application Registry**
3. Click **"New"** to create a new OAuth application
4. Select **"Create an OAuth API endpoint for external clients"**

5. Fill in the OAuth application details:
   - **Name**: `Agentic Coworker`
   - **Client ID**: Auto-generated (copy this)
   - **Client Secret**: Auto-generated (copy this - you won't see it again)
   - **Redirect URL**: `http://localhost:3000/api/auth/callback/servicenow`
     - For production: `https://yourdomain.com/api/auth/callback/servicenow`
   - **Refresh Token Lifespan**: `31536000` (1 year in seconds)
   - **Access Token Lifespan**: `1800` (30 minutes in seconds)

6. Click **"Submit"**

### Step 3: Note Your OAuth Credentials

After creating the OAuth application, you'll have:

- **Client ID**: A unique identifier like `f0c0a403d7be461eba635ce4d2bbcd2e`
- **Client Secret**: A secret like `Hxd6N-ppEN`
- **Authorization URL**: `https://YOUR_INSTANCE.service-now.com/oauth_auth.do`
- **Token URL**: `https://YOUR_INSTANCE.service-now.com/oauth_token.do`
- **Instance URL**: `https://YOUR_INSTANCE.service-now.com`

**Important**: Save these credentials securely.

### Step 4: Configure OAuth Scopes

ServiceNow OAuth requires scopes for access:

1. In the OAuth application, click on the **"OAuth Entity Scopes"** related list
2. Click **"New"**
3. Add required scopes:
   - `useraccount`: Access user account information
   - `app`: Full access to APIs (most common)

For more granular control, create custom scopes.

### Step 5: Configure Agentic Coworker for OAuth

This was already covered in the OAuth setup guides. The ServiceNow OAuth provider is configured in:

```json
{
  "provider_id": "servicenow",
  "provider_name": "ServiceNow",
  "provider_type": "servicenow",
  "clientId": "YOUR_CLIENT_ID",
  "clientSecret": "YOUR_CLIENT_SECRET"
}
```

Refer to the main OAuth documentation for complete setup instructions.

---

## Method 2: Basic Authentication with API Keys (Simpler for Development)

Basic Authentication uses username and password (or API key) for authentication. This is simpler but less secure than OAuth.

### Step 1: Create ServiceNow User Account

If you don't have a user account:

1. Log in to your ServiceNow instance as an admin
2. Navigate to **User Administration > Users**
3. Click **"New"** to create a new user
4. Fill in user details:
   - **User ID**: `api_user` (or your preferred username)
   - **First name**: `API`
   - **Last name**: `User`
   - **Email**: Your email
   - **Password**: Set a strong password
   - **Active**: Checked
   - **Web service access only**: Checked (recommended for API-only users)

5. Assign appropriate roles:
   - **rest_api_explorer**: For API access
   - **itil**: For ITSM operations
   - Additional roles based on needed access

6. Click **"Submit"**

### Step 2: Generate API Credentials

ServiceNow doesn't have a separate "API key" - you use the username and password:

**Option A: Use Username and Password**
- Username: Your ServiceNow username (e.g., `api_user`)
- Password: Your ServiceNow password

**Option B: Use Basic Auth Token**
- Encode credentials as Base64: `base64(username:password)`
- Example: `echo -n "api_user:password123" | base64`
- Result: `YXBpX3VzZXI6cGFzc3dvcmQxMjM=`

### Step 3: Test Basic Authentication

Test your credentials before configuring Agentic Coworker:

#### Using cURL with Username/Password:

```bash
curl -X GET "https://YOUR_INSTANCE.service-now.com/api/now/table/incident?sysparm_limit=1" \
  -H "Accept: application/json" \
  -u "username:password"
```

#### Using cURL with Authorization Header:

```bash
curl -X GET "https://YOUR_INSTANCE.service-now.com/api/now/table/incident?sysparm_limit=1" \
  -H "Accept: application/json" \
  -H "Authorization: Basic BASE64_ENCODED_CREDENTIALS"
```

#### Expected Response:

```json
{
  "result": [
    {
      "sys_id": "...",
      "number": "INC0000001",
      "short_description": "Sample incident",
      "state": "1",
      "priority": "3",
      ...
    }
  ]
}
```

### Step 4: Configure Agentic Coworker for Basic Auth

#### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_app_keys.json` file:
   ```bash
   cp update_app_keys.json.template update_app_keys.json
   ```

3. Add ServiceNow configuration:
   ```json
   {
     "default": [
       {
         "app_url": "https://YOUR_INSTANCE.service-now.com",
         "agent_id": "agent-admin",
         "secrets": {
           "headers": {
             "Authorization": "Basic BASE64_ENCODED_CREDENTIALS"
           }
         }
       }
     ]
   }
   ```

4. Apply the configuration:
   ```bash
   docker exec agent-ops python -m agent_ops update
   ```

#### Option B: Using the Agent Studio UI

1. Navigate to **Agent Studio**: http://localhost:3000
2. Log in with your credentials
3. Go to **"Service Secrets"** in the sidebar
4. Add a new entry for ServiceNow
5. Configure:
   - **App URL**: `https://YOUR_INSTANCE.service-now.com`
   - **Agent ID**: Select your agent
   - **Secret Type**: Headers
   - **Header Name**: `Authorization`
   - **Header Value**: `Basic BASE64_ENCODED_CREDENTIALS`
6. Click **"Save"**

---

## ServiceNow API Endpoints

### Common Table API Endpoints

ServiceNow uses the Table API for CRUD operations:

#### Get Records
```
GET /api/now/table/{table_name}
```

#### Create Record
```
POST /api/now/table/{table_name}
Content-Type: application/json

{
  "field1": "value1",
  "field2": "value2"
}
```

#### Update Record
```
PUT /api/now/table/{table_name}/{sys_id}
Content-Type: application/json

{
  "field1": "updated_value"
}
```

#### Delete Record
```
DELETE /api/now/table/{table_name}/{sys_id}
```

### Common Tables

| Table Name | Description |
|------------|-------------|
| `incident` | Incident records |
| `problem` | Problem records |
| `change_request` | Change requests |
| `sc_request` | Service catalog requests |
| `sc_req_item` | Requested items |
| `kb_knowledge` | Knowledge base articles |
| `cmdb_ci` | Configuration items |
| `sys_user` | User records |
| `sys_user_group` | User groups |
| `task` | Generic task records |

### Query Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `sysparm_query` | Encoded query | `state=1^priority=1` |
| `sysparm_limit` | Limit results | `10` |
| `sysparm_offset` | Offset for pagination | `20` |
| `sysparm_fields` | Fields to return | `number,short_description,state` |
| `sysparm_display_value` | Display values vs sys_ids | `true` or `false` |

### Example API Calls

#### Get All Open Incidents

```bash
curl -X GET "https://YOUR_INSTANCE.service-now.com/api/now/table/incident?sysparm_query=state=1&sysparm_limit=10" \
  -H "Accept: application/json" \
  -H "Authorization: Basic YOUR_BASE64_CREDENTIALS"
```

#### Create a New Incident

```bash
curl -X POST "https://YOUR_INSTANCE.service-now.com/api/now/table/incident" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YOUR_BASE64_CREDENTIALS" \
  -d '{
    "short_description": "Unable to access email",
    "urgency": "2",
    "impact": "2",
    "caller_id": "681ccaf9c0a8016400b98a06818d57c7"
  }'
```

#### Update an Incident

```bash
curl -X PUT "https://YOUR_INSTANCE.service-now.com/api/now/table/incident/SYS_ID" \
  -H "Accept: application/json" \
  -H "Content-Type: application/json" \
  -H "Authorization: Basic YOUR_BASE64_CREDENTIALS" \
  -d '{
    "state": "2",
    "comments": "Working on resolution"
  }'
```

#### Query Knowledge Base

```bash
curl -X GET "https://YOUR_INSTANCE.service-now.com/api/now/table/kb_knowledge?sysparm_query=short_descriptionLIKEpassword&sysparm_limit=5" \
  -H "Accept: application/json" \
  -H "Authorization: Basic YOUR_BASE64_CREDENTIALS"
```

---

## Troubleshooting

### Error: "User Not Authenticated"

**Cause**: Invalid credentials or authentication header.

**Solution**:
1. Verify username and password are correct
2. Check Base64 encoding is correct
3. Ensure "Authorization" header is present
4. Verify user account is active in ServiceNow

### Error: "Insufficient Rights"

**Cause**: User doesn't have required permissions.

**Solution**:
1. In ServiceNow, navigate to **User Administration > Users**
2. Find your API user
3. Check assigned roles
4. Add required roles (e.g., `rest_api_explorer`, `itil`)
5. Save and test again

### Error: "Invalid table name"

**Cause**: Table doesn't exist or is misspelled.

**Solution**:
1. Verify table name is correct
2. Check table exists: **System Definition > Tables**
3. Ensure you have read access to the table
4. Use correct table name (e.g., `incident` not `incidents`)

### Error: "Request URI Too Large"

**Cause**: Query string is too long.

**Solution**:
1. Simplify your query
2. Use shorter field lists
3. Reduce the number of filter conditions
4. Consider using POST with query in body

### Rate Limiting

ServiceNow has API rate limits:
- Varies by instance and license
- Typically 1000+ requests per hour
- Monitor response headers for rate limit info

**Solution**:
1. Implement request throttling
2. Cache frequently accessed data
3. Use bulk operations when possible
4. Contact ServiceNow for rate limit increases

### Connection Timeout

**Cause**: Network issues or instance is slow.

**Solution**:
1. Check instance status
2. Increase timeout settings
3. Verify network connectivity
4. Try during off-peak hours

---

## Security Best Practices

1. **Use OAuth 2.0 for production**:
   - More secure than Basic Auth
   - Token-based authentication
   - Automatic token refresh
   - User delegation support

2. **Never commit credentials to version control**:
   ```bash
   # Add to .gitignore
   update_app_keys.json
   update_oauth_providers.json
   .env*
   ```

3. **Use dedicated service accounts**:
   - Create separate API users
   - Assign minimum required permissions
   - Enable "Web service access only"
   - Disable interactive login

4. **Rotate credentials regularly**:
   - Change passwords periodically
   - Regenerate OAuth secrets
   - Update configuration accordingly

5. **Monitor API usage**:
   - Review access logs in ServiceNow
   - Track API call patterns
   - Set up alerts for unusual activity

6. **Use HTTPS only**:
   - Always use `https://` URLs
   - Never use unencrypted HTTP
   - Verify SSL certificates

7. **Implement role-based access control**:
   - Grant least privilege
   - Use custom roles for specific use cases
   - Regularly audit permissions

8. **Enable multi-factor authentication**:
   - For admin accounts
   - For users with elevated privileges
   - Consider for all accounts in production

---

## ServiceNow Instance Types

### Personal Developer Instance (PDI)
- **Free** for developers
- Hibernates after inactivity
- Must be woken up before use
- Data persists between hibernations
- Reclaimed after 10 days of inactivity

### Developer Instance
- Similar to PDI
- Available through ServiceNow Developer Program
- Good for testing and learning

### Production Instance
- Licensed ServiceNow environment
- Full features and support
- High availability
- SLA guarantees
- Higher API rate limits

---

## Advanced Features

### Using Query Operators

ServiceNow supports advanced query syntax:

```
# Equals
state=1

# Not equals
state!=6

# Greater than
priority>3

# Contains
short_descriptionLIKEpassword

# Starts with
numberSTARTSWITHINC

# Multiple conditions (AND)
state=1^priority=1

# Multiple conditions (OR)
state=1^ORstate=2

# Complex queries
state=1^priority=1^ORpriority=2
```

### Pagination

```bash
# First page (0-10)
sysparm_limit=10&sysparm_offset=0

# Second page (10-20)
sysparm_limit=10&sysparm_offset=10

# Third page (20-30)
sysparm_limit=10&sysparm_offset=20
```

### Display Values vs System Values

```bash
# System values (sys_ids)
sysparm_display_value=false

# Display values (human-readable)
sysparm_display_value=true

# Both
sysparm_display_value=all
```

### Field Selection

```bash
# Only specific fields
sysparm_fields=number,short_description,state,priority

# All fields (default)
# Don't specify sysparm_fields
```

---

## Next Steps

- Configure [Google OAuth](./google-oauth-setup.md) for Google services
- Configure [LinkedIn OAuth](./linkedin-oauth-setup.md) for LinkedIn integration
- Configure [GitHub OAuth](./github-oauth-setup.md) for GitHub integration
- Import ServiceNow APIs into your agent's tool library
- Build ITSM automation workflows
- Set up incident management automation

## Additional Resources

- [ServiceNow REST API Documentation](https://docs.servicenow.com/bundle/tokyo-application-development/page/integrate/inbound-rest/concept/c_RESTAPI.html)
- [ServiceNow Developer Portal](https://developer.servicenow.com/)
- [ServiceNow API Explorer](https://docs.servicenow.com/bundle/tokyo-api-reference/page/integrate/inbound-rest/concept/api-rest-explorer.html)
- [ServiceNow OAuth Setup](https://docs.servicenow.com/bundle/tokyo-platform-administration/page/administer/security/task/t_SettingUpOAuth.html)
- [ServiceNow Table API](https://docs.servicenow.com/bundle/tokyo-application-development/page/integrate/inbound-rest/concept/c_TableAPI.html)
- [ServiceNow Community](https://community.servicenow.com/)
