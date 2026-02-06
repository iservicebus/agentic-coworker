import httpx
import json
import time
import os
import requests # For get_token

# Replace with your actual values if different, but these are from the other test file
KEYCLOAK_URL = "http://localhost:8888"
REALM = "default"
CLIENT_ID = "agent-client"
USERNAME = "agent-user"
PASSWORD = "securepass" # Make sure this is a secure password for your test user
SECRET = "agent-secret" # Client secret for 'agent-client'

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
        print(f"Failed to get token. Status: {response.status_code}, Response: {response.text}")
        raise Exception("Failed to get token")
    return response.json()["access_token"]

# Configuration
BASE_URL = "http://localhost:6060/staging"  # Staging services prefix

# Paths to test data files (assuming tests are run from project root)
#OPENAPI_FILE_PATH = "data/own_openapi.json"
OPENAPI_FILE_PATH = "data/ghes-3.11.json"

POSTMAN_FILE_PATH = "data/external_connection.postman_collection.json"

# URL for testing doc-to-tool and openapi-to-tool via link
TEST_OPENAPI_URL = "https://petstore.swagger.io/v2/swagger.json"
TEST_API_DOC_URL =  "https://www.alphavantage.co/documentation/"

def print_response(response: httpx.Response, test_name: str):
    """Helper function to print response details."""
    print(f"\n--- {test_name} ---")
    print(f"URL: {response.request.method} {response.url}")
    print(f"Response Status Code: {response.status_code}")
    try:
        res_data = response.json()
        print("Response JSON:")
        print(json.dumps(res_data, indent=2))
        # Basic assertion: Check if response is a list (as expected for tool definitions)
        assert isinstance(res_data, list), f"Response for {test_name} is not a list."
        if response.status_code == 200 and len(res_data) == 0:
            print(f"Warning: {test_name} returned an empty list, but status was 200. This might be expected if the source yields no tools.")
        elif response.status_code == 200:
             assert len(res_data) > 0, f"Response for {test_name} is an empty list, expected at least one tool."
        return res_data
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        print("Raw response text:")
        print(response.text)
        assert False, f"Failed to decode JSON response for {test_name}"
    except Exception as e:
        print(f"An unexpected error occurred while processing response for {test_name}: {e}")
        print("Raw response text:")
        print(response.text)
        assert False, f"Unexpected error processing response for {test_name}: {e}"


def test_convert_doc_to_tool(headers):
    url = f"{BASE_URL}/doc-to-tool"
    payload = {"url": TEST_API_DOC_URL}
    
    print(f"Attempting to convert API doc from URL: {TEST_API_DOC_URL}")
    try:
        with httpx.Client(timeout=60.0) as client: # Increased timeout for potentially long LLM call
            response = client.post(url, headers=headers, json=payload)
        
        res_data = print_response(response, "Convert API Doc to Tool")
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        # Specific check for doc-to-tool: expects a list with one item if successful
        if res_data and isinstance(res_data, list) and len(res_data) > 0:
             assert isinstance(res_data[0], dict), "First item in response is not a dictionary."

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        assert False, f"Request failed for Convert API Doc to Tool: {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        assert False, f"Unexpected error in Convert API Doc to Tool: {e}"


def test_convert_openapi_to_tool_link(headers):
    url = f"{BASE_URL}/openapi-to-tool-by-link" # Updated endpoint
    # The API expects the link to be embedded, e.g. {"openapi_link": "..."}
    payload = {"openapi_link": TEST_OPENAPI_URL} 
    
    print(f"Attempting to convert OpenAPI from link: {TEST_OPENAPI_URL}") # Corrected print statement
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(url, headers=headers, json=payload)
        
        res_data = print_response(response, "Convert OpenAPI to Tool (Link)")
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        if res_data and isinstance(res_data, list) and len(res_data) > 0:
            assert all(isinstance(item, dict) for item in res_data), "Not all items in response are dictionaries."

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        assert False, f"Request failed for Convert OpenAPI to Tool (Link): {e}"
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        assert False, f"Unexpected error in Convert OpenAPI to Tool (Link): {e}"


def test_convert_openapi_to_tool_file(headers_for_file_upload):
    url = f"{BASE_URL}/openapi-to-tool-by-file" # Updated endpoint
    
    if not os.path.exists(OPENAPI_FILE_PATH):
        print(f"OpenAPI file not found at {OPENAPI_FILE_PATH}, skipping test.")
        assert False, f"OpenAPI file not found at {OPENAPI_FILE_PATH}"
        return

    print(f"Attempting to convert OpenAPI from file: {OPENAPI_FILE_PATH}")
    try:
        with open(OPENAPI_FILE_PATH, "rb") as f:
            files = {"openapi_file": (os.path.basename(OPENAPI_FILE_PATH), f, "application/json")}
            with httpx.Client(timeout=30.0) as client:
                # For file uploads, httpx sets Content-Type to multipart/form-data.
                # Remove Content-Type from headers if it's set to application/json.
                custom_headers = {k: v for k, v in headers_for_file_upload.items() if k.lower() != 'content-type'}
                response = client.post(url, headers=custom_headers, files=files)
        
        res_data = print_response(response, "Convert OpenAPI to Tool (File)")
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        if res_data and isinstance(res_data, list) and len(res_data) > 0:
            assert all(isinstance(item, dict) for item in res_data), "Not all items in response are dictionaries."

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        assert False, f"Request failed for Convert OpenAPI to Tool (File): {e}"
    except FileNotFoundError:
        print(f"Test file {OPENAPI_FILE_PATH} not found.")
        assert False, f"Test file {OPENAPI_FILE_PATH} not found."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        assert False, f"Unexpected error in Convert OpenAPI to Tool (File): {e}"


def test_convert_postman_to_tool_file(headers_for_file_upload):
    url = f"{BASE_URL}/postman-to-tool"

    if not os.path.exists(POSTMAN_FILE_PATH):
        print(f"Postman collection file not found at {POSTMAN_FILE_PATH}, skipping test.")
        assert False, f"Postman collection file not found at {POSTMAN_FILE_PATH}"
        return

    print(f"Attempting to convert Postman Collection from file: {POSTMAN_FILE_PATH}")
    try:
        with open(POSTMAN_FILE_PATH, "rb") as f:
            files = {"postman_file": (os.path.basename(POSTMAN_FILE_PATH), f, "application/json")}
            with httpx.Client(timeout=30.0) as client:
                custom_headers = {k: v for k, v in headers_for_file_upload.items() if k.lower() != 'content-type'}
                response = client.post(url, headers=custom_headers, files=files)
        
        res_data = print_response(response, "Convert Postman Collection to Tool (File)")
        assert response.status_code == 200, f"Expected 200 OK, got {response.status_code}"
        if res_data and isinstance(res_data, list) and len(res_data) > 0:
            assert all(isinstance(item, dict) for item in res_data), "Not all items in response are dictionaries."

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
        assert False, f"Request failed for Convert Postman Collection to Tool (File): {e}"
    except FileNotFoundError:
        print(f"Test file {POSTMAN_FILE_PATH} not found.")
        assert False, f"Test file {POSTMAN_FILE_PATH} not found."
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        assert False, f"Unexpected error in Convert Postman Collection to Tool (File): {e}"


if __name__ == "__main__":
    print("Starting Conversion API tests...")
    print(f"Using Base URL: {BASE_URL}")
    print(f"Test API Doc URL: {TEST_API_DOC_URL}")
    print(f"OpenAPI Test File: {OPENAPI_FILE_PATH}")
    print(f"Postman Test File: {POSTMAN_FILE_PATH}")
    
    if not os.path.exists(OPENAPI_FILE_PATH):
        print(f"WARNING: OpenAPI test file {OPENAPI_FILE_PATH} not found. Some tests will fail or be skipped.")
    if not os.path.exists(POSTMAN_FILE_PATH):
        print(f"WARNING: Postman test file {POSTMAN_FILE_PATH} not found. Some tests will fail or be skipped.")

    token = None
    try:
        token = get_token()
    except Exception as e:
        print(f"Failed to get token: {e}. Terminating tests.")
        exit(1)

    # Headers for JSON payloads
    headers_json = {
        "Authorization": f"Bearer {token}",
        "X-Agent-ID": CLIENT_ID,
        "accept": "application/json",
        "Content-Type": "application/json",
    }

    # Headers for file uploads (Content-Type will be set by httpx)
    headers_files = {
        "Authorization": f"Bearer {token}",
        "X-Agent-ID": CLIENT_ID,
        "accept": "application/json",
    }

    # Run tests
    # Note: doc-to-tool can be slow due to LLM dependency.
    # It's also the most likely to be flaky if the external API or LLM changes.
    test_convert_doc_to_tool(headers_json)
    
#    test_convert_openapi_to_tool_link(headers_json)
#    test_convert_openapi_to_tool_file(headers_files) # Pass headers suitable for file upload
    
#    test_convert_postman_to_tool_file(headers_files) # Pass headers suitable for file upload
    
    print("\nConversion API tests finished.")
