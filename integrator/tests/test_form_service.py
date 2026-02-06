import httpx # Add httpx import
from urllib.parse import urlencode
#url = "http://localhost:9000/form-data"
url = "http://localhost/hostdockerinternal9000/form-data"  # Change to your Traefik endpoint URL

headers = {
    "accept": "application/json", # Keep original headers
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Custom-Header": "my-custom-header-value",
    "Authorization": "Bearer your_token_here"
}
params = {
    "q": "testquery"
}
data = {
    "name": "JohnDoe",
    "age": 30
}

# Use httpx client for the first request (urlencoded)
client_urlencoded = httpx.Client()
try:
    response = client_urlencoded.request(
        method="post",
        url=url,
        headers=headers,
        params=params,
        data=urlencode(data) # httpx handles urlencoding dict data
    )
    # Ensure client is closed
    client_urlencoded.close()

    print("Status Code (httpx urlencoded):", response.status_code)
    try:
        print("Response JSON (httpx urlencoded):", response.json())
    except httpx.ResponseNotRead:
         print("Response Text (httpx urlencoded):", response.text)
    except Exception as e:
        print(f"httpx urlencoded: Could not decode JSON response: {e}")
        print("Response Text (httpx urlencoded):", response.text)

except httpx.RequestError as exc:
    print(f"httpx urlencoded request failed: {exc}")
    # Ensure client is closed even on error
    client_urlencoded.close()


# --- httpx section: Sending urlencoded data via Dapr binding ---
import httpx
import json
 # Correct import

print("\n--- Testing with httpx (urlencoded via Dapr binding) ---")

# Dapr binding URL
dapr_url = "http://localhost:3500/v1.0/bindings/http.localhost.9000"

# Data dictionary (ensure it's defined if not global, but it is)
# data = {
#     "name": "JohnDoe",
#     "age": 30
# }

# URL-encode the data
encoded_data_str = urlencode(data)

# Define metadata for Dapr request
# Content-Type here tells Dapr what to set when calling the target service
metadata_dict = {
    "path": "/form-data?q=testquery", # Correct path for form data
    "method": "POST",
    "Content-Type": "application/x-www-form-urlencoded", # Target Content-
    'Accept-Encoding': 'gzip, deflate, zstd',    
    "X-Custom-Header": "my-custom-header-value-dapr", # Optional: Add other headers
    "Authorization": "Bearer your_token_here_dapr"
}

# Construct the Dapr payload
# The 'data' field contains the pre-encoded string
dapr_payload = {
    "operation": "post",
    "metadata": metadata_dict,
    "data": "name=JohnDoe&age=30" # Use the URL-encoded string
}

# Use a new httpx client for the Dapr request
client_dapr = httpx.Client()

try:
    response_dapr = client_dapr.request(
        method="post",
        url=dapr_url,
        json=dapr_payload # Send the payload as JSON to Dapr
    )
    # Ensure client is closed
    client_dapr.close()

    print("Dapr Binding Status Code:", response_dapr.status_code)
    try:
        # Dapr binding response might be empty or not JSON
        print("Dapr Binding Response Text:", response_dapr.text)
    except Exception as e:
        print(f"Dapr Binding: Error reading response: {e}")

except httpx.RequestError as exc:
    print(f"Dapr binding request failed: {exc}")
    # Ensure client is closed even on error
    client_dapr.close()

# --- End of Dapr binding section ---
