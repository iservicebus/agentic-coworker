# LinkedIn OAuth 2.0 Setup Guide

This guide walks you through setting up LinkedIn OAuth 2.0 credentials for the Agentic Coworker platform. Your AI agents will use these credentials to authenticate users via LinkedIn and access LinkedIn APIs on their behalf.

## Overview

LinkedIn OAuth 2.0 allows your agents to:
- Authenticate users with their LinkedIn accounts
- Access LinkedIn profile data with user permission
- Post content, manage connections, and interact with LinkedIn on behalf of users
- Access LinkedIn Learning and other LinkedIn services

## Prerequisites

- A LinkedIn account
- Access to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
- Admin access to your Agentic Coworker deployment

## Step 1: Create a LinkedIn App

1. Navigate to [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
2. Click **"Create app"** in the top right corner
3. Fill in the required information:

   **App name**: `Agentic Coworker` (or your preferred name)

   **LinkedIn Page**: Select or create a LinkedIn Company Page
   - Note: You must have a LinkedIn Company Page to create an app
   - If you don't have one, click **"Create a new LinkedIn Page"** and follow the prompts

   **Privacy policy URL**: Your privacy policy URL (required)
   - For development: You can use a placeholder like `http://localhost:3000/privacy`

   **App logo**: Upload your application logo (optional but recommended)
   - Recommended size: 300x300 pixels

   **Legal agreement**: Check the box to agree to LinkedIn's API Terms of Use

4. Click **"Create app"**

## Step 2: Verify Your LinkedIn App

After creating your app, LinkedIn requires verification:

1. On your app's page, you'll see a **"Verify"** button under your app name
2. Click **"Verify"** and follow the verification process:
   - You may need to verify your email address
   - You may need to verify your company page association
3. Complete the verification steps as prompted
4. Once verified, you'll see a checkmark next to your app name

## Step 3: Configure App Settings

1. In your app's settings, navigate to the **"Settings"** tab
2. Configure the following:

   **App name**: Confirm your app name

   **App logo**: Upload a logo if you haven't already

   **Privacy policy URL**: Confirm the URL (required for production)

   **Redirect URLs**: Click **"Add redirect URL"** and add:
   ```
   http://localhost:3000/api/auth/callback/linkedin
   ```
   For production, also add:
   ```
   https://yourdomain.com/api/auth/callback/linkedin
   ```

3. Click **"Update"** to save your settings

## Step 4: Request API Products

LinkedIn uses a products-based access model. You need to request access to products for specific permissions:

1. Navigate to the **"Products"** tab in your app
2. Request access to the products you need:

   **Sign In with LinkedIn using OpenID Connect** (Recommended - Default):
   - Provides: OpenID Connect authentication
   - Scopes: `openid`, `profile`, `email`
   - Status: Usually granted immediately
   - Click **"Request access"**

   **Additional Products** (Optional, based on your needs):

   - **Share on LinkedIn**:
     - Allows posting content to LinkedIn
     - Scope: `w_member_social`
     - Requires application review

   - **Marketing Developer Platform**:
     - For advertising and analytics
     - Requires partnership and approval

   - **Compliance Program**:
     - For specific compliance use cases
     - Requires application review

3. Wait for approval (OpenID Connect is usually instant; others may take days)

## Step 5: Get Your Client Credentials

1. Navigate to the **"Auth"** tab in your app
2. You'll see your credentials:

   **Client ID**:
   - A string like `78qucifkas4k3o`
   - This is public and can be shared

   **Client Secret**:
   - A string like `WPL_AP1.xxxxx`
   - **IMPORTANT**: Keep this secret and never commit to version control
   - Click the eye icon to reveal it

3. **Copy both values** - you'll need them for configuration

4. Verify your **OAuth 2.0 settings**:
   - **Redirect URLs**: Should list your callback URLs
   - **Allowed scopes**: Based on approved products

## Step 6: Configure OAuth 2.0 Scopes

Based on the products you've been approved for, configure the appropriate scopes:

| Product | Scopes | Description |
|---------|--------|-------------|
| Sign In with LinkedIn (OpenID) | `openid`, `profile`, `email` | Basic profile and email access |
| Share on LinkedIn | `w_member_social` | Post updates to LinkedIn |
| Sign In with LinkedIn (Legacy) | `r_liteprofile`, `r_emailaddress` | Legacy authentication (deprecated) |

**Recommended minimum scopes**:
```
openid profile email
```

## Step 7: Configure Agentic Coworker

Now add your LinkedIn OAuth credentials to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_oauth_providers.json` file (create from template if it doesn't exist):
   ```bash
   cp update_oauth_providers.json.template update_oauth_providers.json
   ```

3. Update the LinkedIn provider section:
   ```json
   {
     "default": [
       {
         "provider_id": "linkedin",
         "provider_name": "Linkedin",
         "provider_type": "linkedin",
         "clientId": "YOUR_LINKEDIN_CLIENT_ID",
         "clientSecret": "YOUR_LINKEDIN_CLIENT_SECRET"
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
4. Find the LinkedIn provider and click **"Edit"**
5. Enter your:
   - **Client ID**: Your LinkedIn Client ID
   - **Client Secret**: Your LinkedIn Client Secret
6. Click **"Save"**

## Step 8: Test the Integration

1. Restart the agent-studio service:
   ```bash
   docker-compose restart agent-studio
   ```

2. Navigate to Agent Studio: http://localhost:3000
3. You should see **"Sign in with LinkedIn"** as an authentication option
4. Click it and verify that the LinkedIn OAuth flow works correctly
5. Grant the requested permissions
6. Verify you're redirected back and authenticated successfully

## Understanding LinkedIn OAuth Scopes

### OpenID Connect Scopes (Recommended)

| Scope | Access |
|-------|--------|
| `openid` | Required for OpenID Connect authentication |
| `profile` | Access to basic profile information (name, photo, headline) |
| `email` | Access to primary email address |

### Additional Scopes (Requires Product Approval)

| Scope | Access | Product Required |
|-------|--------|------------------|
| `w_member_social` | Share content as the authenticated user | Share on LinkedIn |
| `r_organization_social` | Read organization's posts | Marketing Developer Platform |
| `w_organization_social` | Post on behalf of organization | Marketing Developer Platform |
| `rw_organization_admin` | Manage organization pages | Marketing Developer Platform |

## Troubleshooting

### Error: "Redirect URI mismatch"

**Cause**: The redirect URI in your request doesn't match what's configured in LinkedIn Developer Portal.

**Solution**:
1. Go to your app's **"Settings"** tab
2. Check the **Redirect URLs** section
3. Ensure the URL matches exactly (including protocol and path):
   ```
   http://localhost:3000/api/auth/callback/linkedin
   ```
4. Note: `http://` vs `https://`, trailing slashes, and subdomains must match exactly

### Error: "Application not found" or "Invalid client_id"

**Cause**: The Client ID is incorrect or the app was deleted.

**Solution**:
1. Go to the **"Auth"** tab in your LinkedIn app
2. Verify your Client ID
3. Ensure you copied the entire Client ID string
4. Check for extra spaces or characters

### Error: "Unauthorized scope"

**Cause**: You're requesting a scope that hasn't been approved for your app.

**Solution**:
1. Go to the **"Products"** tab
2. Verify which products are approved
3. Request access to the required product
4. Wait for approval before using those scopes
5. For development, stick to OpenID Connect scopes

### Error: "Company page not found"

**Cause**: Your LinkedIn app must be associated with a company page.

**Solution**:
1. Create a LinkedIn Company Page if you don't have one
2. Ensure you're an admin of the company page
3. Link the company page to your app in the app creation process

### "App not verified" Warning

**Cause**: LinkedIn apps may show warnings if not fully set up.

**Solution**:
1. Complete the app verification process
2. Add a privacy policy URL
3. Upload an app logo
4. Request and get approved for necessary products

### Token Expiration Issues

**Cause**: LinkedIn access tokens expire after 60 days (for OpenID Connect).

**Solution**:
1. Implement token refresh in your application
2. Handle token expiration gracefully
3. Prompt users to re-authenticate when tokens expire
4. The Agentic Coworker platform handles this automatically via NextAuth.js

## LinkedIn API Rate Limits

Be aware of LinkedIn's rate limits:

- **Application-level**: Varies by product and endpoint
- **User-level**: Typically more restrictive
- **Throttling**: LinkedIn may throttle requests if limits are exceeded

**Best practices**:
1. Cache responses when possible
2. Implement exponential backoff for retries
3. Monitor your API usage in the LinkedIn Developer Portal
4. Request rate limit increases if needed for production use

## Security Best Practices

1. **Never commit credentials to version control**:
   - Add configuration files to `.gitignore`
   - Use environment variables for sensitive data

2. **Use HTTPS in production**:
   - LinkedIn requires HTTPS for production redirect URLs
   - Configure SSL/TLS certificates for your domain

3. **Rotate Client Secrets regularly**:
   - Generate new Client Secrets periodically
   - Update your configuration accordingly
   - LinkedIn allows multiple active secrets for zero-downtime rotation

4. **Request minimum necessary scopes**:
   - Only request permissions your agents actually need
   - Users can see what you're requesting during OAuth flow

5. **Monitor for suspicious activity**:
   - Check the **"Analytics"** tab in your LinkedIn app
   - Review OAuth authorization logs
   - Set up alerts for unusual patterns

6. **Comply with LinkedIn's policies**:
   - Review and follow the [LinkedIn API Terms of Use](https://www.linkedin.com/legal/l/api-terms-of-use)
   - Don't scrape or store LinkedIn data without permission
   - Respect user privacy and data retention policies

## Differences Between LinkedIn OAuth Versions

LinkedIn has two authentication methods:

### OpenID Connect (Recommended - Current)
- Modern standard-based authentication
- Scopes: `openid`, `profile`, `email`
- Simpler integration
- Better security
- Automatically approved for most apps

### Sign In with LinkedIn v2 (Legacy - Being Deprecated)
- Older LinkedIn-specific authentication
- Scopes: `r_liteprofile`, `r_emailaddress`
- Being phased out
- Use OpenID Connect for new integrations

**Recommendation**: Use **Sign In with LinkedIn using OpenID Connect** for all new integrations.

## Going to Production

Before deploying to production:

1. **Update redirect URLs**:
   - Add production HTTPS URLs to your LinkedIn app settings
   - Update your Agentic Coworker configuration

2. **Add privacy policy**:
   - Host a privacy policy at a publicly accessible URL
   - Update your LinkedIn app settings with the URL

3. **Complete app review** (if using advanced products):
   - Submit your app for review if using Share on LinkedIn or other products
   - Provide detailed use case descriptions
   - May take several days to weeks for approval

4. **Test thoroughly**:
   - Test the complete OAuth flow in a staging environment
   - Verify all required scopes work correctly
   - Test token refresh and expiration handling

5. **Monitor usage**:
   - Set up monitoring for OAuth failures
   - Track API usage in LinkedIn Developer Portal
   - Set up alerts for rate limit issues

## Next Steps

- Configure [Google OAuth](./google-oauth-setup.md)
- Configure [GitHub OAuth](./github-oauth-setup.md)
- Request additional LinkedIn products as needed
- Test agent workflows with LinkedIn integration
- Set up LinkedIn posting capabilities for your agents

## Additional Resources

- [LinkedIn Developer Portal](https://www.linkedin.com/developers/)
- [LinkedIn OAuth 2.0 Documentation](https://docs.microsoft.com/en-us/linkedin/shared/authentication/authentication)
- [LinkedIn API Documentation](https://docs.microsoft.com/en-us/linkedin/)
- [LinkedIn OpenID Connect](https://docs.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2)
- [NextAuth.js LinkedIn Provider](https://next-auth.js.org/providers/linkedin)
