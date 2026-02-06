import httpx, json
from urllib.parse import urlencode


import requests

# Replace with your actual values
KEYCLOAK_URL = "http://localhost:8888"
REALM = "default"
CLIENT_ID = "agent-client"
USERNAME = "agent-admin"
PASSWORD = "securepass" # Make sure this is a secure password for your test user
SECRET = "agent-secret" # Client secret for 'agent-client'

# API Endpoints
LOGIN_API_URL = "http://localhost:6060/users/login"
# URLs for the new endpoints will be constructed dynamically in the test functions


def get_token():
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    payload = {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD,
        "client_secret": SECRET

    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code != 200:
        print(response.text)
        raise Exception("Failed to get token")
    return response.json()["access_token"]


params={}

def test_service_deletion():
    tenant = "default"
    service_name ="add-service"
    client = httpx.Client()
    url=f"http://localhost:6060/mcp/services/{tenant}/{service_name}"

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID} # X-Agent-ID might be used by gateway/middleware

    response = client.request(
                method="delete",
                url=url,
                headers=headers
            )

    print(f"Response Status Code: {response.status_code}")

    if response.status_code == 200:
        try:
            # Parse the JSON response
            res_data = response.json()
            print("Received data:")
            print(res_data) # Pretty print the full response

        except json.JSONDecodeError:
            print("Error: Failed to decode JSON response.")
            print("Raw response text:")
            print(response.text)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print("Error: Request failed.")
        print("Response Text:")
        print(response.text)



def test_tool_list():
    client = httpx.Client()
    url="http://localhost:6060/mcp/list_tools"
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID} # X-Agent-ID might be used by gateway/middleware

    response = client.request(
                method="get",
                url=url,
                headers=headers,
                params=params
            )

    print(f"Response Status Code: {response.status_code}")

    if response.status_code == 200:
        try:
            # Parse the JSON response
            mcp_tools_data = response.json()
            print("Received data:")
            print(json.dumps(mcp_tools_data, indent=2)) # Pretty print the full response

            # Extract the list of tool names (keys of the dictionary)
            tool_names = list(mcp_tools_data.keys())

            print("\nExtracted MCP Tool Names:")
            if tool_names:
                for name in tool_names:
                    meta = mcp_tools_data[name]
                    print(meta["description"])
                    print(meta["input_schema"])
            else:
                print("No MCP tools found.")

        except json.JSONDecodeError:
            print("Error: Failed to decode JSON response.")
            print("Raw response text:")
            print(response.text)
        except Exception as e:
            print(f"An unexpected error occurred: {e}")
    else:
        print("Error: Request failed.")
        print("Response Text:")
        print(response.text)



def test_service_registration():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID} # X-Agent-ID might be used by gateway/middleware


    client = httpx.Client()
    url="http://localhost:6060/mcp/services"

    # Define the payload for the add-service API
    data = {
        "name": "add-service",
        "description": "Add two integers together.",
        "transport": "http",
        "staticInput": {
            "method": "POST",
            "url": {
            "protocol": "http",
            "host": [
                "host",
                "docker",
                "internal"
            ],
            "port": "9000",
            "path": [
                "add"
            ],
            "query": {}
            },
            "headers": {
            "accept": "application/json",
            "Content-Type": "application/json"
            },
            "body": "<body>"
        },
        "inputSchema": {
            "type": "object",
            "properties": {
            "body": {
                "type": "object",
                "properties": {
                "a": {
                    "type": "integer",
                    "description": "First number"
                },
                "b": {
                    "type": "integer",
                    "description": "Second number"
                }
                },
                "required": [
                "a",
                "b"
                ]
            }
            }
        }
        }


    try:
        response = client.request(
            method="post",
            url=url,
            headers=headers,
            params=params,
            data=json.dumps(data) # httpx handles urlencoding dict data
        )
        # Ensure client is closed
        client.close()

        print("Status Code (httpx urlencoded):", response.status_code)
        print("Response JSON (httpx urlencoded):", response.json())
    except httpx.ResponseNotRead:
         print("Response Text (httpx urlencoded):", response.text)
    except Exception as e:
        print(f"httpx urlencoded: Could not decode JSON response: {e}")
        print("Response Text (httpx urlencoded):", response.text)





# You might want to add assertions here for automated testing, e.g.:
# assert response.status_code == 200
# assert "expected_tool_name" in tool_names


def test_get_mcp_services_by_tenant():
    tenant_id = "default"  # Example tenant ID
    client = httpx.Client()
    url = f"http://localhost:6060/mcp/tenants/{tenant_id}/services"
    
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}

    print(f"\nTesting GET {url}")

    try:
        response = client.request(
            method="get",
            url=url,
            headers=headers
        )

        print(f"Response Status Code: {response.status_code}")

        if response.status_code == 200:
            try:
                services_data = response.json()
                print("Received data:")
                print(json.dumps(services_data, indent=2)) # Pretty print the full response
                
                if isinstance(services_data, list):
                    print(f"\nFound {len(services_data)} services for tenant '{tenant_id}'.")
                    # You could add more specific assertions here, e.g., checking for expected service names or properties
                else:
                    print("Warning: Response is not a list as expected.")

            except json.JSONDecodeError:
                print("Error: Failed to decode JSON response.")
                print("Raw response text:")
                print(response.text)
            except Exception as e:
                print(f"An unexpected error occurred while processing the response: {e}")
        else:
            print("Error: Request failed.")
            print("Response Text:")
            print(response.text)
            
    except httpx.RequestError as e:
        print(f"Error during request to {url}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
    finally:
        client.close()


if __name__ == "__main__":
#    test_tool_list()
#    test_service_registration()
#    test_service_deletion()
    test_get_mcp_services_by_tenant()
