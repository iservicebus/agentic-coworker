# FRED API Key Setup Guide

This guide walks you through obtaining an API key for the Federal Reserve Economic Data (FRED) API to enable your AI agents to access economic data and statistics.

## Overview

FRED (Federal Reserve Economic Data) provides access to:
- 800,000+ economic time series data
- Data from 100+ sources including Federal Reserve, World Bank, OECD
- Historical economic indicators
- Real-time economic data updates
- Macroeconomic research data

Your agents can use FRED API to:
- Retrieve economic indicators (GDP, unemployment, inflation, etc.)
- Analyze historical economic trends
- Monitor real-time economic changes
- Build economic models and forecasts
- Generate economic reports and insights

## Prerequisites

- Internet access
- Email address for registration
- Admin access to your Agentic Coworker deployment

## Step 1: Create FRED Account

1. Navigate to [FRED Economic Data](https://fred.stlouisfed.org/)
2. Click **"My Account"** in the top right corner
3. Click **"Create Account"** or **"Sign Up"**
4. Fill in the registration form:
   - **Email address**: Your valid email
   - **Password**: Create a strong password
   - **Confirm password**: Re-enter password
   - **First name**: Your first name
   - **Last name**: Your last name
5. Accept the terms of service
6. Click **"Create Account"** or **"Sign Up"**
7. Check your email for a verification link
8. Click the verification link to activate your account

## Step 2: Request API Key

Once your account is verified:

1. Log in to [FRED](https://fred.stlouisfed.org/)
2. Click on your username in the top right corner
3. Select **"My Account"** from the dropdown menu
4. In the left sidebar, click **"API Keys"** or navigate directly to:
   [https://fred.stlouisfed.org/docs/api/api_key.html](https://fred.stlouisfed.org/docs/api/api_key.html)

5. Click **"Request API Key"** button
6. Fill in the API key request form:
   - **Application name**: `Agentic Coworker` (or your preferred name)
   - **Application description**:
     ```
     AI agent platform for automated economic data analysis and reporting
     ```
   - **Website URL** (optional): Your organization's website or `http://localhost:3000`
   - **Redirect URL** (optional): Leave blank for API key access

7. Agree to the API Terms of Use
8. Click **"Request API Key"**

## Step 3: Get Your API Key

After requesting:

1. Your API key will be displayed immediately
2. It will also be shown on your **"API Keys"** page
3. **Copy the API key**:
   - Format: 32-character hexadecimal string
   - Example: `f878542889b0e64a6873cb8c81ae1403`

4. **Store it securely** - you'll need it for configuration

**Note**: You can have multiple API keys for different applications. Each key can be managed independently.

## Step 4: Understand API Key Usage

FRED API key is passed as a query parameter:

### API Endpoint Format:
```
https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_API_KEY
```

### Query Parameters:
- `api_key`: Your FRED API key (required)
- `series_id`: Economic data series ID (e.g., `GDP`, `UNRATE`, `CPIAUCSL`)
- `file_type`: Response format (`json`, `xml`) - default is XML
- `observation_start`: Start date (YYYY-MM-DD)
- `observation_end`: End date (YYYY-MM-DD)

## Step 5: Test Your API Key

Before configuring Agentic Coworker, test your API key:

### Using cURL (JSON format):

```bash
curl "https://api.stlouisfed.org/fred/series/observations?series_id=GNPCA&api_key=YOUR_API_KEY&file_type=json"
```

### Using cURL (GDP data with date range):

```bash
curl "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_API_KEY&file_type=json&observation_start=2020-01-01&observation_end=2024-01-01"
```

### Using a Browser:

Simply paste this URL in your browser (replace YOUR_API_KEY):
```
https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=YOUR_API_KEY&file_type=json
```

### Expected Response (JSON):

```json
{
  "realtime_start": "2024-01-01",
  "realtime_end": "2024-01-01",
  "observation_start": "1776-07-04",
  "observation_end": "9999-12-31",
  "units": "lin",
  "output_type": 1,
  "file_type": "json",
  "order_by": "observation_date",
  "sort_order": "asc",
  "count": 850,
  "offset": 0,
  "limit": 100000,
  "observations": [
    {
      "realtime_start": "2024-01-01",
      "realtime_end": "2024-01-01",
      "date": "1948-01-01",
      "value": "3.4"
    },
    ...
  ]
}
```

## Step 6: Configure Agentic Coworker

Now add your FRED API key to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_app_keys.json` file (create from template if it doesn't exist):
   ```bash
   cp update_app_keys.json.template update_app_keys.json
   ```

3. Update the FRED API section:
   ```json
   {
     "default": [
       {
         "app_url": "https://api.stlouisfed.org",
         "agent_id": "agent-admin",
         "secrets": {
           "query": {
             "api_key": "YOUR_FRED_API_KEY_HERE"
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
4. Find or add the FRED API entry
5. Configure:
   - **App URL**: `https://api.stlouisfed.org`
   - **Agent ID**: Select your agent
   - **Secret Type**: Query Parameters
   - **Parameter Name**: `api_key`
   - **Parameter Value**: Your FRED API key
6. Click **"Save"**

## Step 7: Verify Integration

Test that your agents can access FRED API:

1. Restart the integrator service:
   ```bash
   docker-compose restart integrator
   ```

2. In Agent Studio, navigate to **"Tool Importer"**
3. Import a FRED API endpoint
4. Test with a series ID like `GDP` or `UNRATE`
5. Verify the API responds with economic data

## Popular FRED Series IDs

Here are commonly used economic indicators:

### GDP and Output

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `GDP` | Gross Domestic Product | Quarterly |
| `GDPC1` | Real Gross Domestic Product | Quarterly |
| `GNPCA` | Real Gross National Product | Annual |
| `INDPRO` | Industrial Production Index | Monthly |

### Employment and Unemployment

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `UNRATE` | Unemployment Rate | Monthly |
| `PAYEMS` | Total Nonfarm Payrolls | Monthly |
| `CIVPART` | Labor Force Participation Rate | Monthly |
| `EMRATIO` | Employment-Population Ratio | Monthly |

### Prices and Inflation

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `CPIAUCSL` | Consumer Price Index (CPI) | Monthly |
| `CPILFESL` | Core CPI (excluding food & energy) | Monthly |
| `PCEPI` | Personal Consumption Expenditures Price Index | Monthly |
| `PPIFIS` | Producer Price Index | Monthly |

### Interest Rates

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `DFF` | Federal Funds Effective Rate | Daily |
| `DTB3` | 3-Month Treasury Bill Rate | Daily |
| `DGS10` | 10-Year Treasury Constant Maturity Rate | Daily |
| `MORTGAGE30US` | 30-Year Fixed Rate Mortgage Average | Weekly |

### Money Supply

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `M1SL` | M1 Money Stock | Monthly |
| `M2SL` | M2 Money Stock | Monthly |
| `BOGMBASE` | Monetary Base | Weekly |

### Housing

| Series ID | Description | Frequency |
|-----------|-------------|-----------|
| `HOUST` | Housing Starts | Monthly |
| `PERMIT` | New Private Housing Permits | Monthly |
| `CSUSHPISA` | S&P/Case-Shiller Home Price Index | Monthly |

## Common API Endpoints

### Get Series Observations (Data Points)
```
GET /fred/series/observations
Parameters:
  - series_id (required)
  - api_key (required)
  - file_type=json
  - observation_start=YYYY-MM-DD
  - observation_end=YYYY-MM-DD
```

### Get Series Information
```
GET /fred/series
Parameters:
  - series_id (required)
  - api_key (required)
  - file_type=json
```

### Search for Series
```
GET /fred/series/search
Parameters:
  - search_text (required)
  - api_key (required)
  - file_type=json
```

### Get Category Information
```
GET /fred/category
Parameters:
  - category_id (required)
  - api_key (required)
  - file_type=json
```

### Get Related Tags
```
GET /fred/series/tags
Parameters:
  - series_id (required)
  - api_key (required)
  - file_type=json
```

## Troubleshooting

### Error: "Bad Request - api_key is required"

**Cause**: API key is missing from the request.

**Solution**:
1. Verify the API key is included in query parameters
2. Check the parameter name is exactly `api_key` (lowercase, underscore)
3. Ensure the key is properly URL-encoded if needed

### Error: "Bad Request - Invalid api_key"

**Cause**: The API key is incorrect or has been revoked.

**Solution**:
1. Verify you copied the entire API key
2. Check for extra spaces or characters
3. Log in to FRED and verify your API key is active
4. Generate a new API key if necessary

### Error: "Bad Request - series_id is required"

**Cause**: Missing series ID parameter.

**Solution**:
1. Add the `series_id` parameter to your request
2. Example: `series_id=GDP`
3. Verify the series ID exists in FRED database

### Error: "Bad Request - Unknown series_id"

**Cause**: The series ID doesn't exist.

**Solution**:
1. Search for the correct series ID on [FRED website](https://fred.stlouisfed.org/)
2. Use the search endpoint to find valid series IDs
3. Check for typos in the series ID

### Error: "429 Too Many Requests"

**Cause**: Rate limit exceeded.

**Solution**:
1. FRED has generous rate limits but they exist
2. Implement request throttling in your agents
3. Cache responses to reduce API calls
4. Wait before retrying

### Empty Results

**Cause**: Data doesn't exist for the requested date range.

**Solution**:
1. Check the series frequency (daily, weekly, monthly, etc.)
2. Adjust `observation_start` and `observation_end` dates
3. Verify the series has data for your date range

## API Rate Limits and Best Practices

### Rate Limits:
- **Requests per day**: Generous limits (typically thousands)
- **No specific published limit**, but reasonable use is expected
- Excessive usage may trigger temporary restrictions

### Best Practices:

1. **Cache responses**:
   - Economic data doesn't change retroactively
   - Cache historical data locally
   - Only fetch updates for recent periods

2. **Use appropriate date ranges**:
   - Don't request all data if you only need recent values
   - Use `observation_start` and `observation_end` parameters

3. **Batch requests efficiently**:
   - Plan your queries to minimize API calls
   - Fetch multiple data points in a single series request

4. **Request JSON format**:
   - Specify `file_type=json` for easier parsing
   - Default XML format is more verbose

5. **Monitor API usage**:
   - Track your API calls
   - Implement logging for troubleshooting
   - Set up alerts for errors

6. **Handle errors gracefully**:
   - Implement retry logic with exponential backoff
   - Validate responses before processing
   - Log errors for debugging

## Security Best Practices

1. **Never commit API keys to version control**:
   ```bash
   # Add to .gitignore
   update_app_keys.json
   .env*
   ```

2. **Use environment variables**:
   - Store API keys in environment variables
   - Never hard-code keys in source code

3. **Rotate API keys periodically**:
   - Generate new keys regularly
   - Delete old unused keys
   - Update configuration accordingly

4. **Monitor for unauthorized usage**:
   - Track API usage patterns
   - Set up alerts for unusual activity
   - Review access logs regularly

5. **Use HTTPS only**:
   - Always use `https://api.stlouisfed.org`
   - Never use unencrypted HTTP

## Data Usage Terms

FRED data is **free to use** with the following conditions:

1. **Attribution**: Credit the Federal Reserve Bank of St. Louis when using FRED data
2. **Non-commercial and commercial use**: Both allowed
3. **Redistribution**: Allowed with proper attribution
4. **No warranty**: Data provided "as is"
5. **Terms compliance**: Follow [FRED Terms of Use](https://fred.stlouisfed.org/legal/)

**Recommended attribution**:
```
Data source: Federal Reserve Economic Data (FRED), Federal Reserve Bank of St. Louis
```

## Advanced Usage

### Filtering and Sorting

```
GET /fred/series/observations?series_id=GDP&api_key=YOUR_KEY&file_type=json&sort_order=desc&limit=10
```

### Multiple Series Comparison

To compare multiple series, make separate requests:
```bash
# GDP
curl "https://api.stlouisfed.org/fred/series/observations?series_id=GDP&api_key=YOUR_KEY&file_type=json"

# Unemployment
curl "https://api.stlouisfed.org/fred/series/observations?series_id=UNRATE&api_key=YOUR_KEY&file_type=json"
```

### Real-time vs Vintage Data

FRED tracks revisions to data:
```
GET /fred/series/observations?series_id=GDP&api_key=YOUR_KEY&realtime_start=2023-01-01&realtime_end=2023-12-31&file_type=json
```

## Next Steps

- Explore the [FRED website](https://fred.stlouisfed.org/) for available data series
- Configure [SAP API](./sap-api-key-setup.md) for business data
- Configure [SEC API](./sec-api-key-setup.md) for financial filings
- Configure [Alpha Vantage API](./alphavantage-api-key-setup.md) for market data
- Import FRED APIs into your agent's tool library
- Build economic analysis workflows for your agents

## Additional Resources

- [FRED API Documentation](https://fred.stlouisfed.org/docs/api/fred/)
- [FRED Website](https://fred.stlouisfed.org/)
- [FRED Blog](https://fredblog.stlouisfed.org/)
- [Economic Research at St. Louis Fed](https://research.stlouisfed.org/)
- [FRED Add-Ins for Excel](https://fred.stlouisfed.org/fred-addin/)
- [FRED Mobile App](https://fred.stlouisfed.org/mobile/)
