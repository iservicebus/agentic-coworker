import requests
import httpx
#url = "http://localhost:9000/text-data"
url = "http://localhost/hostdockerinternal9000/text-data"  # Change to your Traefik endpoint URL

headers = {
    "accept": "application/json",
    "X-Custom-Header": "my-custom-header-value",
    "Authorization": "Bearer your_token_here",
    "Content-Type": "text/plain"
}
params = {
    "q": "testquery"
}
text_data = "This is a sample plain text body."





client_urlencoded = httpx.Client()
try:
    response = client_urlencoded.request(
        method="post",
        url=url,
        headers=headers,
        params=params,
        data=text_data # httpx handles urlencoding dict data
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






response = requests.post(url, headers=headers, params=params, data=text_data.encode('utf-8'))

print("Status Code:", response.status_code)
print("Response JSON:", response.json())


import httpx
import json
# Removed unused urlencode import

client = httpx.Client()
dapr_url="http://localhost:3500/v1.0/bindings/http.localhost.9000"
# Serialize metadata to a JSON string
# Create a copy of headers and remove Content-Type, as Dapr might handle it
metadata_headers = headers.copy()
metadata_headers.pop("Content-Type", None) # Remove Content-Type if it exists

metadata_dict = {
    "path": "/text-data?q=testquery", # Path without query params
    "method": "POST",
    "X-Custom-Header": "my-custom-header-value",
    "Authorization": "Bearer your_token_here",
    "Content-Type": "text/plain",
}
metadata_json_string = json.dumps(metadata_dict) # Serialize metadata back to string

# For text/plain, data should be the raw string
dapr_payload = {
    "operation": "post",
    "metadata": metadata_dict, # Use the JSON string
    "data": text_data
}

response = client.request(
            method="post",
            url=dapr_url,
            json=dapr_payload
        )

print(response)
