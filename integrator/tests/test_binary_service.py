import requests
import httpx
import base64 # Import base64

# Read your binary file
with open("/Users/jingnan.zhou/go/bin/gopls", "rb") as f:
    binary_data = f.read()

def test_binary():
    #url = "http://localhost:9000/binary-data"
    url = "http://localhost/hostdockerinternal9000/binary-data"  # Change to your Traefik endpoint URL

    headers = {
        "accept": "application/json",
        "Content-Type": "application/octet-stream",
        "X-Custom-Header": "my-custom-header-value",
        "Authorization": "Bearer your_token_here"
    }
    params = {
        "q": "testquery"
    }


    client_urlencoded = httpx.Client()
    try:
        response = client_urlencoded.request(
            method="post",
            url=url,
            headers=headers,
            params=params,
            #data=binary_data # httpx handles urlencoding dict data
            data=base64.b64encode(binary_data) # httpx handles urlencoding dict data
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






    response = requests.post(url, headers=headers, params=params, data=binary_data)

    print("Status Code:", response.status_code)
    print("Response JSON:", response.json())

test_binary()

import httpx
import json
import base64 # Import base64

print("\n--- Testing with httpx (binary via Dapr binding) ---")

# Dapr binding URL
dapr_url = "http://localhost:3500/v1.0/bindings/http.localhost.9000"

# Base64 encode the binary data
# binary_data is already read from the file above
binary_data_base64 = base64.b64encode(binary_data).decode('ascii')

# Define metadata for Dapr request
# Content-Type tells Dapr what header to set for the target service
metadata_dict = {
    "path": "binary-data?q=testquery", # Correct path for binary data
    "method": "POST",
    "Content-Type": "application/octet-stream", # Target Content-Type
    "X-Custom-Header": "my-custom-header-value-dapr", # Optional: Add other headers
    "Authorization": "Bearer your_token_here_dapr"
}

# Construct the Dapr payload
# The 'data' field contains the Base64 encoded string
dapr_payload = {
    "operation": "post",
    "metadata": metadata_dict,
    "data": binary_data_base64 # Use the Base64 encoded string
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
