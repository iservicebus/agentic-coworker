# SAP API Key Setup Guide

This guide walks you through obtaining API credentials for SAP API Business Hub to enable your AI agents to access SAP services and APIs.

## Overview

SAP API Business Hub provides access to:
- SAP Business APIs (S/4HANA, SuccessFactors, Ariba, etc.)
- Sandbox environments for testing
- Pre-configured test data
- API documentation and discovery
- Integration with SAP systems

Your agents can use these APIs to:
- Access SAP business data
- Trigger SAP workflows
- Integrate with ERP systems
- Automate SAP-related tasks

## Prerequisites

- SAP account (free registration available)
- Access to [SAP API Business Hub](https://api.sap.com/)
- Admin access to your Agentic Coworker deployment

## Step 1: Create SAP Account

If you don't have an SAP account:

1. Navigate to [SAP API Business Hub](https://api.sap.com/)
2. Click **"Login"** in the top right corner
3. Click **"Register"**
4. Fill in your details:
   - Email address
   - Password
   - First and last name
   - Company information (optional)
5. Accept the terms and conditions
6. Click **"Submit"**
7. Check your email and verify your account
8. Complete your profile setup

## Step 2: Access SAP API Business Hub

1. Log in to [SAP API Business Hub](https://api.sap.com/)
2. You'll be taken to the main dashboard
3. Browse available APIs by:
   - Product (S/4HANA, SuccessFactors, etc.)
   - Industry
   - Use case
   - Recently added

## Step 3: Get Your API Key

SAP API Business Hub uses API keys for authentication:

### Method 1: Via "Show API Key" (Recommended)

1. Once logged in, click on your **profile icon** in the top right corner
2. Select **"Settings"** from the dropdown menu
3. Navigate to the **"API Keys"** section or look for **"Show API Key"**
4. Your API key will be displayed
5. Click **"Copy"** to copy the API key

### Method 2: Via Specific API Page

1. Navigate to any API you want to use (e.g., S/4HANA Cloud APIs)
2. Click on the API to view its details
3. Click **"Try Out"** or **"Show API Key"**
4. Your API key will be displayed in the header section
5. Look for a string like: `SPACAQ42m1FVOrDpWcIRiAoRMa1Xk4hb`

**API Key Format**:
- Length: ~32 characters
- Pattern: Alphanumeric string (e.g., `SPACAQ42m1FVOrDpWcIRiAoRMa1Xk4hb`)
- **Important**: Keep this key secret

## Step 4: Choose API Environment

SAP provides different environments:

### Sandbox Environment (Default)
```
https://sandbox.api.sap.com
```
- Free to use
- Pre-configured test data
- Limited functionality
- No impact on production systems
- **Recommended for development and testing**

### Production Environment
```
https://api.sap.com
```
- Requires SAP system credentials
- Access to real business data
- Requires proper licensing
- Use for production deployments

**For Agentic Coworker, use the sandbox environment initially.**

## Step 5: Test Your API Key

Before configuring Agentic Coworker, test your API key:

### Using cURL:

```bash
curl -X GET "https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner" \
  -H "APIKey: YOUR_API_KEY_HERE" \
  -H "Accept: application/json"
```

### Using Postman:

1. Open Postman
2. Create a new GET request
3. URL: `https://sandbox.api.sap.com/s4hanacloud/sap/opu/odata/sap/API_BUSINESS_PARTNER/A_BusinessPartner`
4. Add header:
   - Key: `APIKey`
   - Value: `YOUR_API_KEY_HERE`
5. Click **"Send"**
6. You should receive a JSON response with business partner data

### Expected Response:

```json
{
  "d": {
    "results": [
      {
        "BusinessPartner": "1000000",
        "BusinessPartnerFullName": "Test Partner",
        ...
      }
    ]
  }
}
```

## Step 6: Configure Agentic Coworker

Now add your SAP API key to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_app_keys.json` file (create from template if it doesn't exist):
   ```bash
   cp update_app_keys.json.template update_app_keys.json
   ```

3. Update the SAP API section:
   ```json
   {
     "default": [
       {
         "app_url": "https://sandbox.api.sap.com",
         "agent_id": "agent-admin",
         "secrets": {
           "headers": {
             "APIKey": "YOUR_SAP_API_KEY_HERE"
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

### Option B: Using the Agent Studio UI

1. Navigate to **Agent Studio**: http://localhost:3000
2. Log in with your credentials
3. Go to **"Service Secrets"** in the sidebar
4. Find or add the SAP API entry
5. Configure:
   - **App URL**: `https://sandbox.api.sap.com`
   - **Agent ID**: Select your agent
   - **Secret Type**: Headers
   - **Header Name**: `APIKey`
   - **Header Value**: Your SAP API key
6. Click **"Save"**

## Step 7: Verify Integration

Test that your agents can access SAP APIs:

1. Restart the integrator service:
   ```bash
   docker-compose restart integrator
   ```

2. In Agent Studio, navigate to **"Tool Importer"**
3. Try importing an SAP API (e.g., Business Partner API)
4. Test the tool execution with sample data
5. Verify the API responds correctly

## Available SAP APIs

### Popular SAP Cloud APIs

| API | Description | Base Path |
|-----|-------------|-----------|
| **Business Partner** | Customer and supplier master data | `/API_BUSINESS_PARTNER` |
| **Sales Order** | Sales order management | `/API_SALES_ORDER_SRV` |
| **Purchase Order** | Purchase order management | `/API_PURCHASEORDER_PROCESS_SRV` |
| **Product Master** | Product and material data | `/API_PRODUCT_SRV` |
| **Invoice** | Invoice processing | `/API_BILLING_DOCUMENT_SRV` |
| **Material Stock** | Inventory management | `/API_MATERIAL_STOCK_SRV` |

### SAP SuccessFactors APIs

| API | Description |
|-----|-------------|
| **Employee Central** | Employee master data |
| **Recruiting** | Recruitment management |
| **Learning** | Training and development |
| **Performance & Goals** | Performance management |

### SAP Ariba APIs

| API | Description |
|-----|-------------|
| **Procurement** | Purchase requisitions and orders |
| **Supplier Management** | Supplier information |
| **Contract Management** | Contract lifecycle |

## Troubleshooting

### Error: "401 Unauthorized"

**Cause**: Invalid or missing API key.

**Solution**:
1. Verify your API key is correct
2. Check that you copied the entire key without spaces
3. Ensure the header name is exactly `APIKey` (case-sensitive)
4. Try regenerating your API key in SAP API Business Hub

### Error: "403 Forbidden"

**Cause**: API key doesn't have access to the requested API.

**Solution**:
1. Log in to SAP API Business Hub
2. Navigate to the specific API you're trying to access
3. Click **"Try Out"** to activate access
4. Some APIs require additional permissions or subscriptions

### Error: "404 Not Found"

**Cause**: Incorrect API endpoint or base URL.

**Solution**:
1. Verify the base URL: `https://sandbox.api.sap.com`
2. Check the API path in SAP API Business Hub documentation
3. Ensure you're using the correct API version
4. For sandbox, not all APIs are available

### Error: "429 Too Many Requests"

**Cause**: Rate limit exceeded.

**Solution**:
1. Sandbox environment has request limits
2. Implement request throttling in your agents
3. Wait before retrying
4. Consider upgrading to production environment with higher limits

### Error: "Service Unavailable"

**Cause**: Sandbox environment is temporarily down or being maintained.

**Solution**:
1. Check [SAP API Business Hub Status](https://api.sap.com/)
2. Wait and retry later
3. Check SAP Community for known issues
4. Sandbox maintenance is usually announced in advance

## API Key Best Practices

1. **Never commit API keys to version control**:
   ```bash
   # Add to .gitignore
   update_app_keys.json
   .env*
   ```

2. **Use separate keys for different environments**:
   - Development: Sandbox API key
   - Staging: Separate sandbox key
   - Production: Production API key (requires SAP license)

3. **Rotate API keys regularly**:
   - Generate new keys periodically
   - Update configuration accordingly
   - SAP allows multiple active keys for rotation

4. **Monitor API usage**:
   - Track API calls in SAP API Business Hub
   - Set up alerts for unusual activity
   - Monitor rate limits

5. **Use least privilege principle**:
   - Only enable access to APIs your agents need
   - Don't share keys across teams unnecessarily

6. **Store keys securely**:
   - Use encrypted storage
   - Environment variables for configuration
   - Never log API keys

## Sandbox Limitations

Be aware of sandbox environment limitations:

1. **Data Limitations**:
   - Pre-configured test data only
   - Cannot create/modify/delete data in some APIs
   - Data resets periodically

2. **Functionality Limitations**:
   - Some APIs not available in sandbox
   - Reduced feature set compared to production
   - Limited to read operations for many APIs

3. **Rate Limits**:
   - Lower rate limits than production
   - Shared resources with other developers
   - May experience slowdowns during peak usage

4. **Availability**:
   - Not guaranteed 99.9% uptime
   - Maintenance windows
   - No SLA for sandbox

## Moving to Production

When ready for production SAP API access:

1. **Obtain SAP System Access**:
   - Requires SAP Cloud subscription
   - Work with your SAP account team
   - Proper licensing required

2. **Configure Production Credentials**:
   - Use production base URL
   - Configure OAuth 2.0 (more secure than API keys)
   - Set up service user accounts

3. **Update Agentic Coworker Configuration**:
   ```json
   {
     "app_url": "https://api.sap.com",
     "secrets": {
       "headers": {
         "APIKey": "PRODUCTION_API_KEY"
       }
     }
   }
   ```

4. **Test Thoroughly**:
   - Test in staging environment first
   - Verify all API endpoints work
   - Check data access permissions
   - Monitor performance and rate limits

## Additional Authentication Methods

### OAuth 2.0 (Recommended for Production)

For production environments, use OAuth 2.0:

```json
{
  "app_url": "https://api.sap.com",
  "secrets": {
    "oauth": {
      "client_id": "YOUR_CLIENT_ID",
      "client_secret": "YOUR_CLIENT_SECRET",
      "token_url": "https://YOUR_TENANT.authentication.sap.hana.ondemand.com/oauth/token"
    }
  }
}
```

### Basic Authentication

Some SAP systems support basic auth:

```json
{
  "app_url": "https://your-sap-system.com",
  "secrets": {
    "headers": {
      "Authorization": "Basic BASE64_ENCODED_CREDENTIALS"
    }
  }
}
```

## Next Steps

- Explore [SAP API Business Hub](https://api.sap.com/) for available APIs
- Configure [FRED API](./fred-api-key-setup.md) for economic data
- Configure [SEC API](./sec-api-key-setup.md) for financial filings
- Import SAP APIs into your agent's tool library
- Test agent workflows with SAP integration
- Build use cases for SAP business process automation

## Additional Resources

- [SAP API Business Hub](https://api.sap.com/)
- [SAP API Documentation](https://help.sap.com/docs/)
- [SAP Community](https://community.sap.com/)
- [SAP Developer Center](https://developers.sap.com/)
- [SAP OData Documentation](https://www.odata.org/)
- [SAP Cloud Platform](https://www.sap.com/products/technology-platform.html)
