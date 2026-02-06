# Alpha Vantage API Key Setup Guide

This guide walks you through obtaining an API key for Alpha Vantage to enable your AI agents to access real-time and historical stock market data, forex rates, cryptocurrency prices, and technical indicators.

## Overview

Alpha Vantage provides access to:
- Real-time and historical stock prices
- Intraday, daily, weekly, and monthly time series data
- Technical indicators (50+ indicators)
- Fundamental data (earnings, income statements, balance sheets)
- Foreign exchange (forex) rates
- Cryptocurrency prices
- Economic indicators
- Sector performances

Your agents can use Alpha Vantage API to:
- Track stock prices and market movements
- Perform technical analysis
- Monitor portfolio performance
- Analyze market trends
- Generate trading insights
- Build financial dashboards
- Automate investment research

## Prerequisites

- Email address for registration
- Admin access to your Agentic Coworker deployment

## Step 1: Get Your Free API Key

Alpha Vantage offers a **completely free API key** with generous limits:

1. Navigate to [Alpha Vantage Get API Key](https://www.alphavantage.co/support/#api-key)
2. Scroll to the **"Claim Your Free API Key Today"** section
3. Fill in the registration form:
   - **First Name**: Your first name
   - **Last Name**: Your last name
   - **Email Address**: Your valid email address
   - **Organization** (optional): Your company or project name
   - **I agree to the Terms of Service**: Check the box

4. Complete the CAPTCHA if presented
5. Click **"GET FREE API KEY"**

## Step 2: Receive Your API Key

After submitting:

1. Your API key will be displayed immediately on the screen
2. You'll also receive an email with your API key
3. **Copy and save the API key**:
   - Format: 16-character alphanumeric string
   - Example: `AI7DB1K16B0K47LD`

4. Store it securely - you'll need it for configuration

**Note**: Your API key is sent to your email, so you can always retrieve it later.

## Step 3: Understand API Key Usage

Alpha Vantage API key is passed as a query parameter:

### API Endpoint Format:
```
https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&apikey=YOUR_API_KEY
```

### Common Query Parameters:
- `function`: API function (e.g., `TIME_SERIES_DAILY`, `GLOBAL_QUOTE`)
- `symbol`: Stock ticker (e.g., `AAPL`, `MSFT`)
- `apikey`: Your Alpha Vantage API key (required)
- `interval`: For intraday data (`1min`, `5min`, `15min`, `30min`, `60min`)
- `outputsize`: `compact` (latest 100 data points) or `full` (full history)
- `datatype`: `json` (default) or `csv`

## Step 4: Test Your API Key

Before configuring Agentic Coworker, test your API key:

### Test 1: Get Real-Time Stock Quote

Using cURL:
```bash
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_API_KEY"
```

Using a browser:
```
https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=AAPL&apikey=YOUR_API_KEY
```

### Test 2: Get Daily Time Series

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=MSFT&apikey=YOUR_API_KEY"
```

### Test 3: Get Technical Indicator (SMA)

```bash
curl "https://www.alphavantage.co/query?function=SMA&symbol=AAPL&interval=daily&time_period=20&series_type=close&apikey=YOUR_API_KEY"
```

### Expected Response (Global Quote):

```json
{
  "Global Quote": {
    "01. symbol": "AAPL",
    "02. open": "180.0500",
    "03. high": "182.1000",
    "04. low": "179.8500",
    "05. price": "181.7200",
    "06. volume": "45678900",
    "07. latest trading day": "2024-02-05",
    "08. previous close": "179.9800",
    "09. change": "1.7400",
    "10. change percent": "0.9671%"
  }
}
```

## Step 5: Configure Agentic Coworker

Now add your Alpha Vantage API key to the Agentic Coworker platform:

### Option A: Using the Configuration File

1. Navigate to your project directory:
   ```bash
   cd /path/to/agentic-coworker/data/update_data
   ```

2. Edit the `update_app_keys.json` file (create from template if it doesn't exist):
   ```bash
   cp update_app_keys.json.template update_app_keys.json
   ```

3. Update the Alpha Vantage section:
   ```json
   {
     "default": [
       {
         "app_url": "https://www.alphavantage.co/documentation/",
         "agent_id": "agent-admin",
         "secrets": {
           "query": {
             "apikey": "YOUR_ALPHAVANTAGE_API_KEY_HERE"
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
4. Find or add the Alpha Vantage entry
5. Configure:
   - **App URL**: `https://www.alphavantage.co/documentation/`
   - **Agent ID**: Select your agent
   - **Secret Type**: Query Parameters
   - **Parameter Name**: `apikey`
   - **Parameter Value**: Your Alpha Vantage API key
6. Click **"Save"**

## Step 6: Verify Integration

Test that your agents can access Alpha Vantage API:

1. Restart the integrator service:
   ```bash
   docker-compose restart integrator
   ```

2. In Agent Studio, navigate to **"Tool Importer"**
3. Import Alpha Vantage API endpoints
4. Test with a stock symbol like `AAPL` or `MSFT`
5. Verify the API responds with market data

## Available API Functions

### Stock Time Series Data

| Function | Description | Update Frequency |
|----------|-------------|------------------|
| `TIME_SERIES_INTRADAY` | Intraday time series (1min to 60min) | Real-time |
| `TIME_SERIES_DAILY` | Daily time series | End of day |
| `TIME_SERIES_DAILY_ADJUSTED` | Daily adjusted for splits/dividends | End of day |
| `TIME_SERIES_WEEKLY` | Weekly time series | Weekly |
| `TIME_SERIES_WEEKLY_ADJUSTED` | Weekly adjusted | Weekly |
| `TIME_SERIES_MONTHLY` | Monthly time series | Monthly |
| `TIME_SERIES_MONTHLY_ADJUSTED` | Monthly adjusted | Monthly |
| `GLOBAL_QUOTE` | Latest price and volume | Real-time |

### Fundamental Data

| Function | Description |
|----------|-------------|
| `OVERVIEW` | Company information, financials, ratios |
| `INCOME_STATEMENT` | Income statements (annual/quarterly) |
| `BALANCE_SHEET` | Balance sheets (annual/quarterly) |
| `CASH_FLOW` | Cash flow statements (annual/quarterly) |
| `EARNINGS` | Earnings data and estimates |
| `EARNINGS_CALENDAR` | Upcoming earnings |
| `IPO_CALENDAR` | IPO calendar |
| `LISTING_STATUS` | Active/delisted stocks |

### Technical Indicators

Over 50 indicators available including:

| Function | Description |
|----------|-------------|
| `SMA` | Simple Moving Average |
| `EMA` | Exponential Moving Average |
| `RSI` | Relative Strength Index |
| `MACD` | Moving Average Convergence/Divergence |
| `STOCH` | Stochastic Oscillator |
| `BBANDS` | Bollinger Bands |
| `ADX` | Average Directional Index |
| `ATR` | Average True Range |

### Forex & Crypto

| Function | Description |
|----------|-------------|
| `CURRENCY_EXCHANGE_RATE` | Real-time forex rates |
| `FX_INTRADAY` | Intraday forex time series |
| `FX_DAILY` | Daily forex time series |
| `CRYPTO_RATING` | Cryptocurrency ratings |
| `DIGITAL_CURRENCY_DAILY` | Daily cryptocurrency prices |
| `DIGITAL_CURRENCY_WEEKLY` | Weekly cryptocurrency prices |
| `DIGITAL_CURRENCY_MONTHLY` | Monthly cryptocurrency prices |

### Economic Indicators

| Function | Description |
|----------|-------------|
| `REAL_GDP` | Real GDP |
| `REAL_GDP_PER_CAPITA` | Real GDP per capita |
| `TREASURY_YIELD` | Treasury yields |
| `FEDERAL_FUNDS_RATE` | Federal funds rate |
| `CPI` | Consumer Price Index |
| `INFLATION` | Inflation rates |
| `RETAIL_SALES` | Retail sales |
| `UNEMPLOYMENT` | Unemployment rate |

## API Usage Examples

### Get Stock Quote

```bash
curl "https://www.alphavantage.co/query?function=GLOBAL_QUOTE&symbol=TSLA&apikey=YOUR_API_KEY"
```

### Get Daily Stock Data (Last 100 Days)

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=GOOGL&outputsize=compact&apikey=YOUR_API_KEY"
```

### Get Full Historical Data

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&outputsize=full&apikey=YOUR_API_KEY"
```

### Get Intraday Data (5-minute intervals)

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol=MSFT&interval=5min&apikey=YOUR_API_KEY"
```

### Get Technical Indicator (RSI)

```bash
curl "https://www.alphavantage.co/query?function=RSI&symbol=AAPL&interval=daily&time_period=14&series_type=close&apikey=YOUR_API_KEY"
```

### Get Company Overview

```bash
curl "https://www.alphavantage.co/query?function=OVERVIEW&symbol=NVDA&apikey=YOUR_API_KEY"
```

### Get Forex Exchange Rate

```bash
curl "https://www.alphavantage.co/query?function=CURRENCY_EXCHANGE_RATE&from_currency=USD&to_currency=EUR&apikey=YOUR_API_KEY"
```

### Get Cryptocurrency Price

```bash
curl "https://www.alphavantage.co/query?function=DIGITAL_CURRENCY_DAILY&symbol=BTC&market=USD&apikey=YOUR_API_KEY"
```

### Get Economic Indicator (GDP)

```bash
curl "https://www.alphavantage.co/query?function=REAL_GDP&interval=annual&apikey=YOUR_API_KEY"
```

## Troubleshooting

### Error: "Invalid API call"

**Cause**: Missing required parameters or incorrect function name.

**Solution**:
1. Verify the `function` parameter is correct
2. Check all required parameters are included
3. Ensure `symbol` is valid for stock functions
4. Review [API documentation](https://www.alphavantage.co/documentation/) for correct syntax

### Error: "Invalid API key"

**Cause**: API key is incorrect or missing.

**Solution**:
1. Verify you copied the entire API key (16 characters)
2. Check for extra spaces or characters
3. Ensure parameter name is `apikey` (lowercase, no underscore)
4. Retrieve your key from the email you received

### Error: "Thank you for using Alpha Vantage! Our standard API call frequency is..."

**Cause**: Rate limit exceeded.

**Solution**:
1. Free tier: 5 API calls per minute, 500 calls per day
2. Wait 60 seconds before making another request
3. Implement request throttling (max 5 requests/minute)
4. Cache responses to reduce API calls
5. Consider upgrading to [Premium](https://www.alphavantage.co/premium/) for higher limits

### Empty or Null Data

**Cause**: Invalid symbol or data not available.

**Solution**:
1. Verify the stock ticker symbol is correct (e.g., `AAPL` not `Apple`)
2. Check if the symbol is listed on a supported exchange
3. Try a different symbol to verify your API key works
4. Some functions may not support all symbols

### Error: "Note" in Response

**Cause**: Informational message, not necessarily an error.

**Solution**:
1. Read the note message for details
2. Common notes include rate limit reminders
3. These are warnings, not errors - check if data is also present

### Stale or Delayed Data

**Cause**: Data update frequency varies by endpoint.

**Solution**:
1. Real-time quotes: Updates every few seconds
2. Daily data: Updates after market close (typically 4-5 PM ET)
3. Intraday data: Updates every minute
4. For truly real-time data, consider premium plans

## API Rate Limits

### Free Tier Limits:
- **5 API calls per minute**
- **500 API calls per day**
- No credit card required
- Lifetime free access

### Best Practices:

1. **Implement rate limiting**:
   ```javascript
   // Example: Max 5 requests per minute
   const delay = (ms) => new Promise(resolve => setTimeout(resolve, ms));

   async function callAPI() {
     const response = await fetch(apiUrl);
     await delay(12000); // 12 seconds between calls = 5 per minute
     return response;
   }
   ```

2. **Cache aggressively**:
   - Daily data changes once per day
   - Cache historical data permanently
   - Only fetch recent updates

3. **Use appropriate functions**:
   - Use `GLOBAL_QUOTE` for latest price (lighter)
   - Avoid `TIME_SERIES_INTRADAY` with `outputsize=full` (heavy)
   - Use `outputsize=compact` when possible

4. **Batch operations**:
   - Queue multiple symbol requests
   - Process with 12-second delays
   - Avoid parallel requests

5. **Monitor usage**:
   - Track API call counts
   - Log timestamps of requests
   - Set up alerts before hitting limits

## Premium Plans

For higher limits, consider upgrading:

| Plan | Requests/Min | Requests/Day | Price |
|------|--------------|--------------|-------|
| **Free** | 5 | 500 | $0 |
| **Premium** | 75 | 75,000 | $49.99/month |
| **Ultimate** | 150 | 150,000 | $99.99/month |
| **Enterprise** | Custom | Custom | Contact sales |

**Premium benefits**:
- Higher rate limits
- Priority support
- Additional data feeds
- Real-time websockets (some plans)

Visit [Alpha Vantage Premium](https://www.alphavantage.co/premium/) for details.

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

3. **Monitor usage**:
   - Track API call patterns
   - Set up alerts for unusual activity
   - Review logs regularly

4. **Use HTTPS only**:
   - Always use `https://www.alphavantage.co`
   - Verify SSL certificates

5. **Rotate keys if compromised**:
   - Request a new API key if exposed
   - Update configuration immediately
   - Monitor old key usage

## Data Attribution

When using Alpha Vantage data:

**Required attribution**:
```
Data provided by Alpha Vantage
```

**Links**:
- Alpha Vantage: https://www.alphavantage.co/

## Advanced Usage Tips

### Efficient Data Fetching

```bash
# Get only the latest 100 data points
function=TIME_SERIES_DAILY&outputsize=compact

# Get full historical data (20+ years)
function=TIME_SERIES_DAILY&outputsize=full
```

### CSV Format (Faster Processing)

```bash
curl "https://www.alphavantage.co/query?function=TIME_SERIES_DAILY&symbol=AAPL&datatype=csv&apikey=YOUR_API_KEY"
```

### Multiple Indicators Workflow

```bash
# 1. Get price data
# 2. Wait 12 seconds
# 3. Get RSI
# 4. Wait 12 seconds
# 5. Get MACD
```

### Forex Pairs

```bash
# USD to EUR
from_currency=USD&to_currency=EUR

# Bitcoin to USD
from_currency=BTC&to_currency=USD
```

## Common Use Cases for Agents

1. **Portfolio tracking**:
   - Fetch daily quotes for multiple stocks
   - Calculate portfolio value
   - Track performance over time

2. **Technical analysis**:
   - Get historical prices
   - Calculate indicators (RSI, MACD, etc.)
   - Identify trading signals

3. **Market monitoring**:
   - Track specific stocks
   - Alert on price movements
   - Generate daily reports

4. **Fundamental analysis**:
   - Fetch company financials
   - Compare metrics across companies
   - Analyze earnings trends

5. **Economic research**:
   - Monitor economic indicators
   - Correlate with market movements
   - Build economic models

## Next Steps

- Explore [Alpha Vantage Documentation](https://www.alphavantage.co/documentation/)
- Configure [FRED API](./fred-api-key-setup.md) for economic data
- Configure [SEC API](./sec-api-key-setup.md) for SEC filings
- Configure [SAP API](./sap-api-key-setup.md) for business data
- Import Alpha Vantage tools into your agent's library
- Build financial analysis workflows
- Set up automated market monitoring

## Additional Resources

- [Alpha Vantage Website](https://www.alphavantage.co/)
- [API Documentation](https://www.alphavantage.co/documentation/)
- [Support Forum](https://www.alphavantage.co/support/)
- [Premium Plans](https://www.alphavantage.co/premium/)
- [Python Library](https://github.com/RomelTorres/alpha_vantage)
- [Excel Add-In](https://www.alphavantage.co/excel/)
