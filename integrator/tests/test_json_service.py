import requests, httpx
import json

# Define the URL for the Traefik proxy (assuming Traefik is correctly routing requests)
traefik_url = "http://localhost/hostdockerinternal9000/add"  # Change to your Traefik endpoint URL

# Define the payload for the add-service API
data = {
    "a": 10,
    "b": 20
}
headers = {
    "accept": "application/json",
    "X-Custom-Header": "my-custom-header-value",
        "Content-Type": "application/json",
    "Authorization": "Bearer your_token_here"
}
params = {
    "q": "testquery"
}


client_urlencoded = httpx.Client()
try:
    response = client_urlencoded.request(
        method="post",
        url=traefik_url,
        headers=headers,
        params=params,
        data=json.dumps(data) # httpx handles urlencoding dict data
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






# Send the POST request to Traefik (which should route to the add-service behind it)
response = requests.post(traefik_url, json=data)

# Check the response status and handle the response
if response.status_code == 200:
    print("Successfully routed to the add-service!")
    print(f"Response: {response.json()}")
else:
    print(f"Failed to route to add-service. Status code: {response.status_code}")
    print(f"Error: {response.text}")