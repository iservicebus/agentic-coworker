# Agentic Coworker - Setup Documentation

This directory contains comprehensive setup guides for configuring OAuth providers and API keys to enable your AI agents to access external services and data sources.

## OAuth 2.0 Setup Guides

These guides walk you through obtaining OAuth 2.0 credentials for user authentication and API access:

### [Google OAuth Setup](./setup-guides/google-oauth-setup.md)
Configure Google authentication to enable your agents to:
- Authenticate users with Google accounts
- Access Gmail, Calendar, Drive, and other Google services
- Manage user data with proper OAuth scopes

**Key topics**: Google Cloud Console, OAuth consent screen, API enablement, client credentials

---

### [GitHub OAuth Setup](./setup-guides/github-oauth-setup.md)
Configure GitHub authentication to enable your agents to:
- Authenticate users with GitHub accounts
- Access repositories, issues, and pull requests
- Manage GitHub resources on behalf of users

**Key topics**: OAuth Apps vs GitHub Apps, authorization scopes, repository access

---

### [LinkedIn OAuth Setup](./setup-guides/linkedin-oauth-setup.md)
Configure LinkedIn authentication to enable your agents to:
- Authenticate users with LinkedIn accounts
- Access LinkedIn profile data
- Post content and manage connections

**Key topics**: LinkedIn Developer Portal, OpenID Connect, product approval, API scopes

---

## API Key Setup Guides

These guides walk you through obtaining API keys for accessing external data services:

### [SAP API Key Setup](./setup-guides/sap-api-key-setup.md)
Configure SAP API Business Hub access to enable your agents to:
- Access SAP Business APIs (S/4HANA, SuccessFactors, Ariba)
- Work with enterprise data and workflows
- Test with sandbox environments

**Key topics**: SAP API Hub registration, sandbox vs production, OData endpoints

---

### [FRED API Key Setup](./setup-guides/fred-api-key-setup.md)
Configure Federal Reserve Economic Data (FRED) API to enable your agents to:
- Access 800,000+ economic time series
- Retrieve GDP, unemployment, inflation, and other indicators
- Analyze historical economic trends

**Key topics**: FRED account creation, API key request, economic indicators, query syntax

---

### [SEC API Key Setup](./setup-guides/sec-api-key-setup.md)
Configure SEC-API.io access to enable your agents to:
- Access SEC EDGAR filings (10-K, 10-Q, 8-K)
- Search company financial disclosures
- Extract structured financial data

**Key topics**: SEC-API.io registration, filing types, full-text search, rate limits

---

### [Alpha Vantage API Key Setup](./setup-guides/alphavantage-api-key-setup.md)
Configure Alpha Vantage API to enable your agents to:
- Access real-time and historical stock data
- Retrieve technical indicators (50+ indicators)
- Monitor forex and cryptocurrency prices

**Key topics**: Free API key, stock quotes, technical analysis, rate limits

---

## Dual Authentication Support

### [ServiceNow API Setup](./setup-guides/servicenow-api-setup.md)
Configure ServiceNow access using **either OAuth 2.0 or Basic Authentication** to enable your agents to:
- Manage incidents, problems, and change requests
- Access ITSM workflows
- Query and update ServiceNow tables

**Key topics**: OAuth vs Basic Auth, Personal Developer Instance, Table API, query syntax

---

## Quick Configuration Steps

After following the setup guides to obtain your credentials:

### 1. Prepare Configuration Files

```bash
cd data/update_data

# Copy templates
cp update_app_keys.json.template update_app_keys.json
cp update_oauth_providers.json.template update_oauth_providers.json
```

### 2. Add Your Credentials

Edit the JSON files with the credentials you obtained from the setup guides:

**For OAuth providers** (`update_oauth_providers.json`):
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

**For API keys** (`update_app_keys.json`):
```json
{
  "default": [
    {
      "app_url": "https://api.stlouisfed.org",
      "agent_id": "agent-admin",
      "secrets": {
        "query": {
          "api_key": "YOUR_FRED_API_KEY"
        }
      }
    }
  ]
}
```

### 3. Apply Configuration

```bash
# Update the database with your credentials
docker exec agent-ops python -m agent_ops update

# Restart services to pick up changes
docker-compose restart agent-studio integrator
```

### 4. Verify Integration

1. Navigate to Agent Studio: http://localhost:3000
2. Check **"Auth Providers"** to verify OAuth providers
3. Check **"Service Secrets"** to verify API keys
4. Test authentication flows and API access

---

## Alternative: Configure via UI

Instead of editing JSON files, you can configure credentials through the Agent Studio web interface:

1. Navigate to http://localhost:3000
2. Log in with your credentials
3. Go to **"Auth Providers"** for OAuth configuration
4. Go to **"Service Secrets"** for API key configuration
5. Add or edit credentials directly in the UI

---

## Security Best Practices

When configuring credentials, always follow these security practices:

1. **Never commit credentials to version control**:
   ```bash
   # These files should be in .gitignore
   data/update_data/update_app_keys.json
   data/update_data/update_oauth_providers.json
   .env*
   ```

2. **Use environment-specific credentials**:
   - Development: Test/sandbox credentials
   - Staging: Separate credentials
   - Production: Production credentials with proper access controls

3. **Rotate credentials regularly**:
   - Change OAuth secrets periodically
   - Generate new API keys on a schedule
   - Update configuration promptly

4. **Monitor usage**:
   - Track API usage in provider dashboards
   - Set up alerts for unusual activity
   - Review access logs regularly

5. **Use least privilege**:
   - Only request necessary OAuth scopes
   - Grant minimum required API permissions
   - Create service-specific accounts when possible

---

## Troubleshooting

### Configuration Not Applied

**Problem**: Changes to JSON files don't seem to take effect.

**Solution**:
```bash
# Ensure you ran the update command
docker exec agent-ops python -m agent_ops update

# Restart services
docker-compose restart agent-studio integrator
```

### Invalid Credentials Error

**Problem**: Authentication fails with "Invalid credentials" error.

**Solution**:
1. Double-check you copied the complete credential strings
2. Verify there are no extra spaces or line breaks
3. Ensure credentials are for the correct environment (dev/prod)
4. Check the credential hasn't expired or been revoked
5. Review the specific setup guide for troubleshooting steps

### OAuth Redirect Mismatch

**Problem**: OAuth flow fails with "Redirect URI mismatch" error.

**Solution**:
1. Verify redirect URIs in provider console match exactly:
   - Development: `http://localhost:3000/api/auth/callback/[provider]`
   - Production: `https://yourdomain.com/api/auth/callback/[provider]`
2. Protocol (`http://` vs `https://`) must match exactly
3. No trailing slashes unless configured
4. Port numbers must match if specified

### Rate Limit Errors

**Problem**: API calls fail with rate limit or quota exceeded errors.

**Solution**:
1. Check your plan limits in the provider dashboard
2. Implement request throttling in your agent workflows
3. Cache responses to reduce API calls
4. Consider upgrading to higher-tier plans for production

---

## Getting Help

If you encounter issues not covered in these guides:

1. **Check the specific setup guide** for troubleshooting sections
2. **Review provider documentation** linked in each guide
3. **Check Agent Studio logs**:
   ```bash
   docker-compose logs -f agent-studio
   ```
4. **Open an issue** on GitHub with:
   - Setup guide you're following
   - Error messages (redact sensitive info)
   - Steps to reproduce
   - Environment details

---

## Additional Resources

- [Main README](../README.md) - Platform overview and quick start
- [Quick Reference Guide](../agent_ops/QUICK_REFERENCE.md) - Common operations
- [Operations Manual](../agent_ops/OPERATIONS.md) - Detailed procedures
- [Docker Environment Guide](../agent_ops/DOCKER-ENV.md) - Docker configuration

---

**Need to add support for a new OAuth provider or API?** Check the existing guides as templates and submit a PR with your new setup guide!
