# SEC API Key Setup Guide

This guide walks you through obtaining an API key for SEC-API.io to enable your AI agents to access SEC EDGAR filings, financial data, and corporate disclosures.

## Overview

SEC-API.io provides access to:
- Real-time SEC EDGAR filings (10-K, 10-Q, 8-K, etc.)
- Historical SEC documents dating back to 1993
- Full-text search across all filings
- Structured financial data extraction
- Executive compensation data
- Insider trading information
- Beneficial ownership reports

Your agents can use SEC API to:
- Monitor company filings in real-time
- Extract financial statements and metrics
- Analyze corporate disclosures
- Track insider transactions
- Generate investment research reports
- Perform due diligence and compliance checks

## Prerequisites

- Credit card for paid plans (free tier available)
- Email address for registration
- Admin access to your Agentic Coworker deployment

## Step 1: Create SEC-API.io Account

1. Navigate to [SEC-API.io](https://sec-api.io/)
2. Click **"Sign Up"** or **"Get Started"** button
3. Choose your plan:
   - **Free Plan**: 100 API calls/month
   - **Starter**: 10,000 calls/month ($49/month)
   - **Professional**: 100,000 calls/month ($199/month)
   - **Enterprise**: Custom pricing

4. Click **"Sign Up"** for your chosen plan
5. Fill in the registration form:
   - **Email address**: Your business email
   - **Password**: Create a secure password
   - **Company name** (optional): Your organization name

6. For paid plans: Enter payment information
7. Accept the terms of service
8. Click **"Create Account"** or **"Complete Sign Up"**
9. Check your email for verification link
10. Click the verification link to activate your account

## Step 2: Get Your API Key

After account creation and login:

1. You'll be taken to your **Dashboard**
2. Your API key is displayed prominently at the top
3. Look for a section labeled **"API Key"** or **"Your API Key"**
4. Click **"Show"** or **"Copy"** to reveal the full key

**API Key Format**:
- Length: 64 characters
- Pattern: Hexadecimal string
- Example: `cc17e0ab45e6b81c403582a747755229dcae94a6720cb5c32cbf5eefae90647a`

5. **Copy and save this key securely** - you'll need it for configuration

### Alternative: Via API Settings

1. Navigate to **"Settings"** or **"API Keys"** in the dashboard
2. Your active API key(s) will be listed
3. You can generate additional keys if needed
4. Click **"Copy"** to copy the key to clipboard

## Step 3: Understand API Key Authentication

SEC-API.io uses API key in the Authorization header:

### Request Header Format:
```
Authorization: YOUR_API_KEY_HERE
```

**Important**:
- Do NOT include "Bearer" prefix
- Just the raw API key string
- Must be sent in the `Authorization` header

## Step 4: Test Your API Key

Before configuring Agentic Coworker, test your API key:

### Test 1: Query Latest Filings

Using cURL:
```bash
curl -X GET "https://api.sec-api.io/filings?query=formType:\"10-K\"&size=10" \
  -H "Authorization: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json"
```

### Test 2: Full-Text Search

```bash
curl -X POST "https://api.sec-api.io/full-text-search" \
  -H "Authorization: YOUR_API_KEY_HERE" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Microsoft AND revenue",
    "formTypes": ["10-K"],
    "startDate": "2023-01-01",
    "endDate": "2024-12-31"
  }'
```

### Test 3: Get Specific Filing

```bash
curl -X GET "https://api.sec-api.io/filing-reader?url=https://www.sec.gov/Archives/edgar/data/789019/000156459021039151/0001564590-21-039151-index.htm" \
  -H "Authorization: YOUR_API_KEY_HERE"
```

### Expected Response (Filings Query):

```json
{
  "total": {
    "value": 1234,
    "relation": "eq"
  },
  "filings": [
    {
      "id": "...",
      "accessionNo": "0001564590-21-039151",
      "cik": "0000789019",
      "ticker": "MSFT",
      "companyName": "MICROSOFT CORP",
      "companyNameLong": "MICROSOFT CORPORATION",
      "formType": "10-K",
      "description": "Annual Report",
      "filedAt": "2021-07-30T16:15:00-04:00",
      "linkToFilingDetails": "...",
      "linkToTxt": "...",
      "linkToHtml": "...",
      "entities": [...]
    },
    ...
  ]
}
```

## Step 5: Configure Agentic Coworker

Now add your SEC API key to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_app_keys.json` file (create from template if it doesn't exist):
   ```bash
   cp update_app_keys.json.template update_app_keys.json
   ```

3. Update the SEC API section:
   ```json
   {
     "default": [
       {
         "app_url": "https://api.sec-api.io",
         "agent_id": "agent-admin",
         "secrets": {
           "headers": {
             "Authorization": "YOUR_SEC_API_KEY_HERE"
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
4. Find or add the SEC API entry
5. Configure:
   - **App URL**: `https://api.sec-api.io`
   - **Agent ID**: Select your agent
   - **Secret Type**: Headers
   - **Header Name**: `Authorization`
   - **Header Value**: Your SEC API key (no "Bearer" prefix)
6. Click **"Save"**

## Step 6: Verify Integration

Test that your agents can access SEC API:

1. Restart the integrator service:
   ```bash
   docker-compose restart integrator
   ```

2. In Agent Studio, navigate to **"Tool Importer"**
3. Import SEC API endpoints
4. Test with a query for recent 10-K filings
5. Verify the API responds with filing data

## Common SEC Filing Types

| Form Type | Description | Frequency |
|-----------|-------------|-----------|
| **10-K** | Annual report | Annual |
| **10-Q** | Quarterly report | Quarterly |
| **8-K** | Current report (material events) | As needed |
| **DEF 14A** | Proxy statement | Annual |
| **S-1** | IPO registration | As needed |
| **4** | Insider trading statement | As needed |
| **13F** | Institutional holdings report | Quarterly |
| **SC 13D** | Beneficial ownership report (>5%) | As needed |
| **SC 13G** | Passive beneficial ownership | Annual |
| **20-F** | Annual report (foreign companies) | Annual |

## Available API Endpoints

### 1. Query API - Search Filings

```
GET /filings?query={query}&size={size}&from={from}
```

**Parameters**:
- `query`: Search query (e.g., `formType:"10-K" AND ticker:AAPL`)
- `size`: Number of results (default: 10, max: 100)
- `from`: Offset for pagination (default: 0)

**Example queries**:
```
formType:"10-K" AND ticker:MSFT
formType:"8-K" AND filedAt:[2024-01-01 TO 2024-12-31]
companyName:"Tesla" AND formType:"10-Q"
ticker:AAPL AND NOT formType:"4"
```

### 2. Full-Text Search API

```
POST /full-text-search
Content-Type: application/json

{
  "query": "revenue growth",
  "formTypes": ["10-K", "10-Q"],
  "startDate": "2023-01-01",
  "endDate": "2024-12-31",
  "ticker": "AAPL"
}
```

### 3. Filing Reader API - Parse Filing Content

```
GET /filing-reader?url={url}&type={type}
```

**Parameters**:
- `url`: SEC EDGAR URL of the filing
- `type`: Response format (`text`, `html`, or `pdf`)

### 4. Mapper API - Extract Structured Data

```
GET /mapper?url={url}
```

Extracts structured financial data from filings.

### 5. Real-Time Stream API

```
GET /streaming
```

WebSocket endpoint for real-time filing notifications.

### 6. Executive Compensation API

```
GET /executive-compensation?ticker={ticker}&year={year}
```

### 7. Insider Trading API

```
GET /insider-trading?ticker={ticker}&type={type}
```

## Query Syntax Examples

### By Company

```
ticker:AAPL
ticker:(AAPL MSFT GOOGL)
companyName:"Apple Inc"
cik:0000320193
```

### By Form Type

```
formType:"10-K"
formType:("10-K" OR "10-Q")
formType:"8-K" AND NOT formType:"8-K/A"
```

### By Date

```
filedAt:[2024-01-01 TO 2024-12-31]
filedAt:{2024-01-01 TO *}
periodOfReport:[2023-01-01 TO 2023-12-31]
```

### Full-Text Search

```
"risk factors" AND "climate change"
revenue AND (growth OR increase)
"artificial intelligence" AND formType:"10-K"
```

### Combining Criteria

```
ticker:TSLA AND formType:"10-K" AND filedAt:[2020-01-01 TO *]
(ticker:AAPL OR ticker:MSFT) AND formType:"10-Q"
companyName:Tesla AND NOT formType:"4"
```

## Troubleshooting

### Error: "401 Unauthorized"

**Cause**: Invalid or missing API key.

**Solution**:
1. Verify your API key is correct
2. Check that you copied the entire 64-character key
3. Ensure the header name is `Authorization` (case-sensitive)
4. Do NOT include "Bearer" prefix - just the raw key
5. Check your account is active and not suspended

### Error: "403 Forbidden"

**Cause**: API key doesn't have access or subscription expired.

**Solution**:
1. Log in to SEC-API.io dashboard
2. Check your subscription status
3. Verify payment information is up to date
4. Ensure you haven't exceeded your plan limits

### Error: "429 Too Many Requests"

**Cause**: Rate limit exceeded.

**Solution**:
1. Check your plan's rate limits:
   - Free: 100 calls/month
   - Starter: 10,000 calls/month
   - Professional: 100,000 calls/month
2. Implement request throttling
3. Cache responses to reduce API calls
4. Consider upgrading your plan
5. Wait until your monthly quota resets

### Error: "400 Bad Request - Invalid query"

**Cause**: Malformed query syntax.

**Solution**:
1. Check query syntax follows Elasticsearch query string format
2. Ensure date ranges use correct format: `[YYYY-MM-DD TO YYYY-MM-DD]`
3. Verify field names are correct (e.g., `ticker`, `formType`, `filedAt`)
4. Test queries in SEC-API.io dashboard first

### Empty Results

**Cause**: No filings match your query criteria.

**Solution**:
1. Broaden your search criteria
2. Check ticker symbols are correct
3. Verify date ranges include filing dates
4. Try searching by company name instead of ticker
5. Check if the company actually files that form type

### Slow Response Times

**Cause**: Large result sets or complex queries.

**Solution**:
1. Reduce the `size` parameter
2. Use more specific queries
3. Implement pagination with `from` parameter
4. Cache frequently accessed data
5. Use the Query API instead of Full-Text Search when possible

## API Rate Limits and Usage

### Plan Limits:

| Plan | Monthly Calls | Rate Limit | Cost |
|------|---------------|------------|------|
| **Free** | 100 | N/A | $0 |
| **Starter** | 10,000 | ~7 req/min | $49/month |
| **Professional** | 100,000 | ~70 req/min | $199/month |
| **Enterprise** | Custom | Custom | Custom |

### Best Practices:

1. **Monitor usage**:
   - Check dashboard for current usage
   - Set up alerts before hitting limits
   - Track usage patterns

2. **Cache aggressively**:
   - SEC filings don't change once filed
   - Cache filing content locally
   - Only fetch new filings

3. **Use efficient queries**:
   - Be specific with date ranges
   - Filter by ticker when possible
   - Use the Query API for simple searches
   - Reserve Full-Text Search for complex queries

4. **Implement pagination**:
   - Use `size` and `from` parameters
   - Fetch data in chunks
   - Don't request all results at once

5. **Handle errors gracefully**:
   - Implement exponential backoff
   - Retry failed requests
   - Log errors for debugging

## Security Best Practices

1. **Never commit API keys to version control**:
   ```bash
   # Add to .gitignore
   update_app_keys.json
   .env*
   ```

2. **Store keys securely**:
   - Use environment variables
   - Encrypt configuration files
   - Never log API keys

3. **Rotate keys periodically**:
   - Generate new keys regularly
   - Deactivate old keys
   - Update configuration promptly

4. **Monitor for unauthorized usage**:
   - Review usage dashboard regularly
   - Set up usage alerts
   - Investigate unusual patterns

5. **Use HTTPS only**:
   - Always use `https://api.sec-api.io`
   - Verify SSL certificates

## Data Usage and Attribution

### Terms of Use:
- SEC filings are public domain
- SEC-API.io provides aggregation and parsing services
- Follow SEC-API.io [Terms of Service](https://sec-api.io/terms)
- Respect rate limits and fair use policies

### Attribution:
While SEC data is public, consider crediting SEC-API.io when using their service:
```
Data provided by SEC-API.io
Source: SEC EDGAR Database
```

## Advanced Features

### Real-Time Filing Alerts

Connect to WebSocket for real-time updates:
```javascript
const ws = new WebSocket('wss://api.sec-api.io/streaming?token=YOUR_API_KEY');

ws.on('message', (data) => {
  const filing = JSON.parse(data);
  console.log('New filing:', filing);
});
```

### Extract Financial Tables

Use the Mapper API to extract structured data:
```bash
curl -X GET "https://api.sec-api.io/mapper?url=FILING_URL" \
  -H "Authorization: YOUR_API_KEY"
```

### Bulk Download Filings

For large-scale analysis:
```bash
# Get 1000 10-K filings
curl -X GET "https://api.sec-api.io/filings?query=formType:\"10-K\"&size=100&from=0" \
  -H "Authorization: YOUR_API_KEY" > filings_batch_1.json
```

## Next Steps

- Configure [FRED API](./fred-api-key-setup.md) for economic data
- Configure [Alpha Vantage API](./alphavantage-api-key-setup.md) for market data
- Configure [SAP API](./sap-api-key-setup.md) for enterprise data
- Import SEC API tools into your agent's library
- Build financial analysis workflows
- Set up real-time filing monitoring

## Additional Resources

- [SEC-API.io Website](https://sec-api.io/)
- [SEC-API.io Documentation](https://sec-api.io/docs)
- [API Playground](https://sec-api.io/playground)
- [SEC EDGAR Database](https://www.sec.gov/edgar)
- [SEC Filing Types Guide](https://www.sec.gov/forms)
- [Query Syntax Reference](https://sec-api.io/docs/query-api)
- [Code Examples](https://sec-api.io/docs/examples)
