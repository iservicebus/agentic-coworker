import requests
import asyncio
import json

# Keycloak configuration
AUTH_URL = "http://localhost:8888"
TENANT = "default"
AGENT_ID = "agent-client"
AGENT_SECRET = "agent-secret"

TOKEN_URL = f"{AUTH_URL}/realms/{TENANT}/protocol/openid-connect/token"

def get_access_token():
    data = {
        "grant_type": "client_credentials",
        "client_id": AGENT_ID,
        "client_secret": AGENT_SECRET
    }

    try:
        response = requests.post(TOKEN_URL, data=data)
        response.raise_for_status()  # Raise an exception for bad status codes
        token_data = response.json()
        access_token = token_data.get("access_token")
        print("Access token acquired.")
        return access_token
    except requests.exceptions.RequestException as e:
        print(f"Failed to get token: {e}")
        print("Response:", e.response.text if e.response else "No response")
        return None

def get_auth_headers():
    access_token = get_access_token()
    if not access_token:
        return None

    headers = {
        "Authorization": f"Bearer {access_token}",
        "X-Agent-ID": AGENT_ID,
        "Content-Type": "application/json"
    }
    return headers

async def test_mcp_validation():
    headers = get_auth_headers()
    if not headers:
        print("Could not get auth headers, exiting.")
        return

    api_url = "http://localhost:6060/clients/mcp_validation"

    test_cases = [
        {
            "service_name": "add-service",
            "data": {"body": {"a": 3, "b": 4}}
        },
        {
            "service_name": "greet_user",
            "data": {"body": {"name": "Bob"}}
        },
        {
            "service_name": "get_raw_email_body",
            "data": {"body": {"sender": "jingnan.zhou@gmail.com", "recipient": "jingnan.zhou@gmail.com", "subject": "test", "body": "test only"}}
        }
    ]

    for payload in test_cases:
        print(f"Calling {api_url} with payload: {json.dumps(payload)}")

        try:
            # Using a synchronous request for simplicity in this test case
            response = await asyncio.to_thread(requests.post, api_url, headers=headers, json=payload)
            
            print("Status code:", response.status_code)
            print("Response:", response.text)

        except requests.exceptions.RequestException as e:
            print(f"An error occurred: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(test_mcp_validation())
    except KeyboardInterrupt:
        print("Program interrupted by user (Ctrl+C)")
    except Exception as e:
        print(f"Unhandled exception during execution: {e}")
