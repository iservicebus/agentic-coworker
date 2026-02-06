# GitHub OAuth 2.0 Setup Guide

This guide walks you through setting up GitHub OAuth 2.0 credentials for the Agentic Coworker platform. Your AI agents will use these credentials to authenticate users via GitHub and access GitHub APIs on their behalf.

## Overview

GitHub OAuth 2.0 allows your agents to:
- Authenticate users with their GitHub accounts
- Access repositories, issues, pull requests, and other GitHub resources
- Perform actions on behalf of users (create issues, manage repos, etc.)
- Access GitHub API with user permissions
- Integrate with GitHub Actions and other GitHub features

## Prerequisites

- A GitHub account
- Admin access to your organization (for organization OAuth apps) or personal account
- Admin access to your Agentic Coworker deployment

## Step 1: Choose OAuth App Type

GitHub offers two types of OAuth applications:

### OAuth Apps (Recommended for User Authentication)
- Simpler setup
- User-to-server authentication
- Access to user's resources
- Best for authentication and user-level actions

### GitHub Apps (Advanced)
- More complex but more powerful
- Fine-grained permissions
- Can act as the app or on behalf of users
- Better for integrations requiring repo access
- Requires webhook setup

**For Agentic Coworker authentication, use OAuth Apps.**

## Step 2: Create a GitHub OAuth App

You can create an OAuth app at the **personal** or **organization** level.

### Option A: Personal OAuth App

1. Navigate to [GitHub Settings](https://github.com/settings/profile)
2. In the left sidebar, click **"Developer settings"** (at the bottom)
3. In the left sidebar, click **"OAuth Apps"**
4. Click **"New OAuth App"** button
5. Fill in the application details:

   **Application name**: `Agentic Coworker` (or your preferred name)
   - This name will be shown to users during authorization

   **Homepage URL**: `http://localhost:3000`
   - For production: `https://yourdomain.com`
   - This is where users can learn about your application

   **Application description**: (Optional)
   ```
   AI agent platform with governed access to GitHub resources
   ```

   **Authorization callback URL**: `http://localhost:3000/api/auth/callback/github`
   - This must match exactly what NextAuth.js uses
   - For production: `https://yourdomain.com/api/auth/callback/github`
   - **IMPORTANT**: Must include the protocol (`http://` or `https://`)

   **Enable Device Flow**: (Optional)
   - Leave unchecked for web-based authentication

6. Click **"Register application"**

### Option B: Organization OAuth App

1. Navigate to your organization's page: `https://github.com/organizations/YOUR_ORG/settings/applications`
2. In the left sidebar, click **"Developer settings"**
3. Click **"OAuth Apps"**
4. Click **"New OAuth App"**
5. Fill in the same details as above
6. Click **"Register application"**

**Note**: Organization OAuth apps are visible to all organization members and can be managed by org owners.

## Step 3: Generate Client Secret

After registering your OAuth app:

1. You'll be taken to your app's settings page
2. You'll see your **Client ID** displayed:
   - Format: `Ov23liBGQAFJvifC2F7q` (20 characters, starts with `Ov` or `Iv`)
   - This is public and can be shared

3. Click **"Generate a new client secret"**
4. Your **Client Secret** will be displayed:
   - Format: A 40-character hexadecimal string like `311f5313a27c73f3e7487e0ba103be888c3d6cae`
   - **CRITICAL**: Copy it immediately - you won't be able to see it again
   - Store it securely

5. **Save both credentials** - you'll need them for configuration

## Step 4: Configure OAuth Scopes

GitHub OAuth uses scopes to define what your application can access. Configure scopes based on what your agents need:

### Basic Authentication Scopes

| Scope | Access |
|-------|--------|
| `user` | Read/write access to profile info (default) |
| `user:email` | Access to user's email addresses |
| `read:user` | Read-only access to user's profile |

### Repository Scopes

| Scope | Access |
|-------|--------|
| `repo` | Full control of private repos |
| `repo:status` | Access commit status |
| `repo_deployment` | Access deployment statuses |
| `public_repo` | Access public repositories only |
| `repo:invite` | Accept repo invitations |

### Organization Scopes

| Scope | Access |
|-------|--------|
| `read:org` | Read org and team membership |
| `write:org` | Manage org and team membership |
| `admin:org` | Full organization administration |

### Additional Scopes

| Scope | Access |
|-------|--------|
| `gist` | Create gists |
| `notifications` | Access notifications |
| `workflow` | Update GitHub Actions workflows |

**Recommended minimum scopes for authentication**:
```
user:email read:user
```

**For agents needing repository access**:
```
user:email read:user repo
```

**Note**: Scopes are requested at runtime by NextAuth.js, not configured in the GitHub OAuth app itself.

## Step 5: Configure Agentic Coworker

Now add your GitHub OAuth credentials to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_oauth_providers.json` file (create from template if it doesn't exist):
   ```bash
   cp update_oauth_providers.json.template update_oauth_providers.json
   ```

3. Update the GitHub provider section:
   ```json
   {
     "default": [
       {
         "provider_id": "github",
         "provider_name": "Github",
         "provider_type": "github",
         "clientId": "YOUR_GITHUB_CLIENT_ID",
         "clientSecret": "YOUR_GITHUB_CLIENT_SECRET"
       }
     ]
   }
   ```

4. Apply the configuration:
   ```bash
   docker exec agent-ops python -m agent_ops update
   ```

### Option B: Using the Agent Studio UI

1. Navigate to **Agent Studio**: http://localhost:3000
2. Log in with your credentials
3. Go to **"Auth Providers"** in the sidebar
4. Find the GitHub provider and click **"Edit"**
5. Enter your:
   - **Client ID**: Your GitHub OAuth Client ID
   - **Client Secret**: Your GitHub OAuth Client Secret
6. Click **"Save"**

## Step 6: Update NextAuth.js Configuration (If Needed)

The Agentic Coworker platform uses NextAuth.js with GitHub provider. The configuration is already set up in the codebase:

```typescript
// agent-studio/src/app/api/auth/[...nextauth]/route.ts
import GitHubProvider from 'next-auth/providers/github';
```

To customize GitHub scopes, you would modify the provider configuration:

```typescript
GitHubProvider({
  clientId: process.env.GITHUB_CLIENT_ID,
  clientSecret: process.env.GITHUB_CLIENT_SECRET,
  authorization: {
    params: {
      scope: 'user:email read:user repo' // Customize scopes here
    }
  }
})
```

However, this is **already handled by the dynamic provider system** in the current implementation.

## Step 7: Test the Integration

1. Restart the agent-studio service:
   ```bash
   docker-compose restart agent-studio
   ```

2. Navigate to Agent Studio: http://localhost:3000
3. You should see **"Sign in with GitHub"** as an authentication option
4. Click it to start the OAuth flow
5. GitHub will show the authorization page:
   - App name
   - Organization (if applicable)
   - Requested permissions
6. Click **"Authorize [app-name]"**
7. Verify you're redirected back and authenticated successfully

## Troubleshooting

### Error: "The redirect_uri MUST match the registered callback URL for this application."

**Cause**: The callback URL doesn't match what's configured in your GitHub OAuth app.

**Solution**:
1. Go to your OAuth app settings in GitHub
2. Check the **"Authorization callback URL"** field
3. Ensure it matches exactly:
   ```
   http://localhost:3000/api/auth/callback/github
   ```
4. Protocol (`http://` vs `https://`), port, path, and trailing slashes must match
5. No wildcards or multiple URLs are allowed - must be exact match

### Error: "Bad verification code" or "Incorrect client credentials"

**Cause**: Client ID or Client Secret is incorrect.

**Solution**:
1. Verify your Client ID in GitHub OAuth app settings
2. Generate a new Client Secret if needed
3. Ensure you copied the entire secret without extra spaces
4. Update your configuration with the correct credentials

### Error: "Application suspended"

**Cause**: Your OAuth app has been suspended by GitHub.

**Solution**:
1. Check your email for notifications from GitHub
2. Review GitHub's terms of service
3. Contact GitHub support if needed
4. Common reasons: violation of terms, suspicious activity, or spam reports

### Users See "Authorize application" Every Time

**Cause**: Tokens are not being properly stored or refreshed.

**Solution**:
1. Verify your database connection
2. Check NextAuth.js session configuration
3. Ensure cookies are being set correctly
4. For development, check that `NEXTAUTH_SECRET` is set

### Error: "Resource not accessible by integration"

**Cause**: The requested scope hasn't been granted or the token lacks permissions.

**Solution**:
1. Verify the scopes requested match what users authorized
2. Users may need to re-authorize with new scopes
3. Check that your OAuth app hasn't had permissions revoked

### Rate Limiting Issues

**Cause**: GitHub has rate limits for authenticated API requests.

**Solution**:
1. Authenticated requests: 5,000 requests/hour per user
2. Check rate limit headers in API responses
3. Implement caching and request throttling
4. Consider GitHub Apps for higher limits

## GitHub OAuth vs GitHub App

Understanding the differences:

| Feature | OAuth App | GitHub App |
|---------|-----------|------------|
| **Use Case** | User authentication | App integrations |
| **Permissions** | User-level | Granular, repository-level |
| **API Rate Limits** | 5,000/hour per user | Higher limits |
| **Installation** | User authorizes | Installed per repository/org |
| **Token Type** | User access token | Installation access token |
| **Webhooks** | Not supported | Built-in support |
| **Acting as** | User | App or user |
| **Best for** | Sign in, user actions | Repo automation, CI/CD |

**For Agentic Coworker authentication**: Use **OAuth Apps**

**For advanced repository automation**: Consider **GitHub Apps**

## Security Best Practices

1. **Never commit credentials to version control**:
   ```bash
   # Add to .gitignore
   .env*
   *oauth_providers.json
   ```

2. **Use HTTPS in production**:
   - GitHub requires HTTPS for production callback URLs
   - Configure SSL/TLS certificates

3. **Rotate Client Secrets regularly**:
   - Generate new secrets periodically
   - GitHub allows you to have multiple active secrets
   - Useful for zero-downtime rotation

4. **Request minimum necessary scopes**:
   - Only request permissions your agents need
   - Users can see and review permissions during authorization
   - More permissions = lower user trust

5. **Monitor OAuth app usage**:
   - Check authorized applications in GitHub settings
   - Review access logs
   - Revoke suspicious authorizations

6. **Handle token expiration**:
   - GitHub OAuth tokens don't expire by default
   - But users can revoke access anytime
   - Implement proper error handling for revoked tokens

7. **Implement PKCE (if applicable)**:
   - For enhanced security in public clients
   - NextAuth.js handles this automatically

8. **Review GitHub's policies**:
   - [GitHub Terms of Service](https://docs.github.com/en/site-policy/github-terms/github-terms-of-service)
   - [GitHub API Terms](https://docs.github.com/en/site-policy/github-terms/github-terms-for-additional-products-and-features#a-api-terms)
   - Comply with data retention and privacy requirements

## Managing Your OAuth App

### Update OAuth App Settings

1. Go to GitHub **Settings > Developer settings > OAuth Apps**
2. Click on your app name
3. You can update:
   - Application name
   - Homepage URL
   - Description
   - Authorization callback URL
   - Upload a logo (recommended)

### Revoke User Tokens

If you need to revoke access for all users:

1. In OAuth app settings, click **"Revoke all user tokens"**
2. This immediately invalidates all access tokens
3. Users will need to re-authorize

### Delete OAuth App

1. In OAuth app settings, scroll to the bottom
2. Click **"Delete application"**
3. Confirm deletion
4. **Warning**: This cannot be undone

### View OAuth App Statistics

GitHub doesn't provide detailed analytics for OAuth apps. For monitoring:

1. Implement your own logging
2. Track authorization events
3. Monitor API usage via GitHub API headers
4. Set up alerts for errors

## Going to Production

Before deploying to production:

1. **Update callback URL**:
   - Add HTTPS production URL to your OAuth app
   - Update Agentic Coworker configuration

2. **Add application logo**:
   - Upload a logo (200x200px recommended)
   - Improves user trust during authorization

3. **Complete app details**:
   - Add comprehensive description
   - Set correct homepage URL
   - Link to terms of service and privacy policy

4. **Test in staging**:
   - Test complete OAuth flow with HTTPS
   - Verify scope permissions work correctly
   - Test token refresh and error scenarios

5. **Monitor production usage**:
   - Set up error tracking
   - Monitor rate limit headers
   - Track authorization failures
   - Alert on unusual patterns

6. **Have a backup plan**:
   - Keep old Client Secrets active during rotation
   - Test rollback procedures
   - Document emergency access revocation process

## Advanced: Using GitHub API with OAuth Tokens

Once authenticated, your agents can use the GitHub API:

```typescript
// Example: Fetching user repositories
const response = await fetch('https://api.github.com/user/repos', {
  headers: {
    'Authorization': `Bearer ${accessToken}`,
    'Accept': 'application/vnd.github.v3+json'
  }
});
```

**API Endpoints Agents Might Use**:
- `/user` - Get authenticated user
- `/user/repos` - List user's repositories
- `/repos/{owner}/{repo}/issues` - Manage issues
- `/repos/{owner}/{repo}/pulls` - Manage pull requests
- `/orgs/{org}/repos` - List organization repos

**API Documentation**: https://docs.github.com/en/rest

## Next Steps

- Configure [Google OAuth](./google-oauth-setup.md)
- Configure [LinkedIn OAuth](./linkedin-oauth-setup.md)
- Set up GitHub webhooks for event-driven agent actions
- Configure repository-specific agent permissions
- Test agent workflows with GitHub integration
- Consider GitHub Apps for advanced automation needs

## Additional Resources

- [GitHub OAuth Apps Documentation](https://docs.github.com/en/developers/apps/building-oauth-apps)
- [GitHub API Documentation](https://docs.github.com/en/rest)
- [GitHub OAuth Scopes](https://docs.github.com/en/developers/apps/building-oauth-apps/scopes-for-oauth-apps)
- [Creating an OAuth App](https://docs.github.com/en/developers/apps/building-oauth-apps/creating-an-oauth-app)
- [NextAuth.js GitHub Provider](https://next-auth.js.org/providers/github)
- [GitHub Apps vs OAuth Apps](https://docs.github.com/en/developers/apps/getting-started-with-apps/about-apps)
