# Google OAuth 2.0 Setup Guide

This guide walks you through setting up Google OAuth 2.0 credentials for the Agentic Coworker platform. Your AI agents will use these credentials to authenticate users via Google and access Google services on their behalf.

## Overview

Google OAuth 2.0 allows your agents to:
- Authenticate users with their Google accounts
- Access Google APIs (Gmail, Calendar, Drive, etc.) with user permission
- Maintain secure, token-based access with automatic refresh

## Prerequisites

- A Google account
- Access to [Google Cloud Console](https://console.cloud.google.com/)
- Admin access to your Agentic Coworker deployment

## Step 1: Create a Google Cloud Project

1. Navigate to [Google Cloud Console](https://console.cloud.google.com/)
2. Click on the project dropdown at the top of the page
3. Click **"New Project"**
4. Enter a project name (e.g., "Agentic Coworker")
5. Select your organization (if applicable)
6. Click **"Create"**
7. Wait for the project to be created and select it from the project dropdown

## Step 2: Enable Required APIs

Your agents need access to Google APIs. Enable the APIs your agents will use:

1. In the Google Cloud Console, go to **"APIs & Services" > "Library"**
2. Search for and enable the following APIs (at minimum):
   - **Google+ API** (for basic profile information)
   - **People API** (for user profile data)
   - Optional: Enable additional APIs based on your needs:
     - **Gmail API** (for email access)
     - **Google Calendar API** (for calendar access)
     - **Google Drive API** (for file storage access)

3. Click **"Enable"** for each API

## Step 3: Configure OAuth Consent Screen

1. Go to **"APIs & Services" > "OAuth consent screen"**
2. Select **User Type**:
   - **Internal**: Only for Google Workspace users in your organization
   - **External**: For any Google account user
3. Click **"Create"**

4. Fill in the **App Information**:
   - **App name**: `Agentic Coworker` (or your preferred name)
   - **User support email**: Your support email address
   - **App logo**: (Optional) Upload your logo
   - **Application home page**: `http://localhost:3000` (or your deployment URL)
   - **Application privacy policy link**: Your privacy policy URL (if available)
   - **Application terms of service link**: Your terms of service URL (if available)
   - **Authorized domains**: Add your domain (e.g., `localhost` for development)
   - **Developer contact information**: Your email address

5. Click **"Save and Continue"**

6. **Scopes**: Click **"Add or Remove Scopes"**
   - Add the following scopes at minimum:
     - `openid`
     - `email`
     - `profile`
   - Add additional scopes based on the Google services your agents need:
     - Gmail: `https://www.googleapis.com/auth/gmail.readonly`
     - Calendar: `https://www.googleapis.com/auth/calendar.readonly`
     - Drive: `https://www.googleapis.com/auth/drive.readonly`
   - Click **"Update"** then **"Save and Continue"**

7. **Test users** (if using External user type in development):
   - Add email addresses of users who can test your OAuth integration
   - Click **"Save and Continue"**

8. Review your settings and click **"Back to Dashboard"**

## Step 4: Create OAuth 2.0 Credentials

1. Go to **"APIs & Services" > "Credentials"**
2. Click **"Create Credentials" > "OAuth client ID"**
3. Select **Application type**: **"Web application"**
4. Enter a **Name**: `Agentic Coworker Web Client` (or your preferred name)

5. Configure **Authorized JavaScript origins**:
   - For local development: `http://localhost:3000`
   - For production: `https://yourdomain.com`

6. Configure **Authorized redirect URIs**:
   Add the following redirect URIs (adjust based on your deployment):
   ```
   http://localhost:3000/api/auth/callback/google
   ```
   For production:
   ```
   https://yourdomain.com/api/auth/callback/google
   ```

7. Click **"Create"**

## Step 5: Save Your Credentials

After creating the OAuth client:

1. A dialog will appear showing your **Client ID** and **Client Secret**
2. **IMPORTANT**: Copy both values immediately:
   - **Client ID**: Looks like `988696783390-xxxxx.apps.googleusercontent.com`
   - **Client Secret**: Looks like `GOCSPX-xxxxx`

3. Store these securely - you'll need them for configuration

You can always view these credentials later by:
- Going to **"APIs & Services" > "Credentials"**
- Clicking on your OAuth 2.0 Client ID name

## Step 6: Configure Agentic Coworker

Now add your Google OAuth credentials to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_oauth_providers.json` file (create from template if it doesn't exist):
   ```bash
   cp update_oauth_providers.json.template update_oauth_providers.json
   ```

3. Update the Google provider section:
   ```json
   {
     "default": [
       {
         "provider_id": "google",
         "provider_name": "Google",
         "provider_type": "google",
         "clientId": "YOUR_GOOGLE_CLIENT_ID",
         "clientSecret": "YOUR_GOOGLE_CLIENT_SECRET"
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
4. Find the Google provider and click **"Edit"**
5. Enter your:
   - **Client ID**: Your Google OAuth Client ID
   - **Client Secret**: Your Google OAuth Client Secret
6. Click **"Save"**

## Step 7: Test the Integration

1. Restart the agent-studio service:
   ```bash
   docker-compose restart agent-studio
   ```

2. Navigate to Agent Studio: http://localhost:3000
3. You should see **"Sign in with Google"** as an authentication option
4. Click it and verify that the Google OAuth flow works correctly

## Required Scopes for Common Use Cases

Configure these scopes based on what your agents need to access:

| Scope | Purpose |
|-------|---------|
| `openid` | Required for OpenID Connect |
| `email` | Access user's email address |
| `profile` | Access user's basic profile info |
| `https://www.googleapis.com/auth/gmail.readonly` | Read Gmail messages |
| `https://www.googleapis.com/auth/gmail.send` | Send emails via Gmail |
| `https://www.googleapis.com/auth/calendar.readonly` | Read calendar events |
| `https://www.googleapis.com/auth/calendar.events` | Create/modify calendar events |
| `https://www.googleapis.com/auth/drive.readonly` | Read Google Drive files |
| `https://www.googleapis.com/auth/drive.file` | Access specific Drive files |

## Troubleshooting

### Error: "Redirect URI mismatch"

**Cause**: The redirect URI in your request doesn't match what's configured in Google Cloud Console.

**Solution**:
1. Go to **"APIs & Services" > "Credentials"**
2. Click on your OAuth 2.0 Client ID
3. Verify the redirect URI matches exactly:
   ```
   http://localhost:3000/api/auth/callback/google
   ```
4. Note: `http://` vs `https://` and trailing slashes matter

### Error: "Access blocked: This app's request is invalid"

**Cause**: OAuth consent screen is not properly configured.

**Solution**:
1. Complete the OAuth consent screen configuration
2. Ensure you've added required scopes
3. If using "External" user type in development, add test users

### Error: "Access Not Configured"

**Cause**: Required Google APIs are not enabled.

**Solution**:
1. Go to **"APIs & Services" > "Library"**
2. Enable the required APIs (Google+ API, People API, etc.)
3. Wait a few minutes for the changes to propagate

### Error: "Invalid client_id"

**Cause**: The Client ID is incorrect or the OAuth client was deleted.

**Solution**:
1. Verify your Client ID in Google Cloud Console
2. Ensure you copied the entire Client ID string
3. Check that there are no extra spaces or characters

### Token Refresh Issues

**Cause**: Refresh tokens may expire or be revoked.

**Solution**:
1. Ensure you've requested `offline` access in your OAuth scopes
2. Check that your application handles token refresh properly
3. Users may need to re-authenticate if their refresh token is revoked

## Security Best Practices

1. **Never commit credentials to version control**:
   - Add `.env*` and `*oauth_providers.json` to `.gitignore`
   - Use environment variables for sensitive data

2. **Use HTTPS in production**:
   - Configure SSL/TLS certificates for your domain
   - Update authorized origins and redirect URIs to use `https://`

3. **Restrict API scopes**:
   - Only request the minimum scopes your agents need
   - Users will see what permissions you're requesting

4. **Rotate credentials regularly**:
   - Periodically generate new Client Secrets
   - Update your configuration accordingly

5. **Monitor OAuth usage**:
   - Check Google Cloud Console for API usage and quotas
   - Set up billing alerts to avoid unexpected charges

6. **Publish your OAuth app** (for production):
   - Submit your app for Google's verification process
   - Remove the "unverified app" warning users see

## Next Steps

- Configure [LinkedIn OAuth](./linkedin-oauth-setup.md)
- Configure [GitHub OAuth](./github-oauth-setup.md)
- Set up additional Google API integrations for your agents
- Test agent workflows with Google service access

## Additional Resources

- [Google OAuth 2.0 Documentation](https://developers.google.com/identity/protocols/oauth2)
- [Google Cloud Console](https://console.cloud.google.com/)
- [Google API Scopes](https://developers.google.com/identity/protocols/oauth2/scopes)
- [NextAuth.js Google Provider](https://next-auth.js.org/providers/google)
