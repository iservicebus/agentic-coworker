import httpx
import json
import time


import requests

# Replace with your actual values
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
        print(response.text)
        raise Exception("Failed to get token")
    return response.json()["access_token"]




# Configuration
BASE_URL = "http://localhost:6060/staging"  # Assuming the service runs on port 6060
DEFAULT_TENANT = "default"

# To store the ID of a created service for subsequent tests
created_service_id = None
created_service_name = f"test-service-{int(time.time())}"

def print_response(response: httpx.Response, test_name: str):
    """Helper function to print response details."""
    print(f"\n--- {test_name} ---")
    print(f"URL: {response.request.method} {response.url}")
    print(f"Response Status Code: {response.status_code}")
    try:
        res_data = response.json()
        print("Response JSON:")
        print(json.dumps(res_data, indent=2))
        return res_data
    except json.JSONDecodeError:
        print("Error: Failed to decode JSON response.")
        print("Raw response text:")
        print(response.text)
        return None
    except Exception as e:
        print(f"An unexpected error occurred while processing response: {e}")
        print("Raw response text:")
        print(response.text)
        return None

def test_add_staging_service(headers):

    global created_service_id, created_service_name
    
    
    
    print(f"Attempting to add service: {created_service_name} for tenant: {DEFAULT_TENANT}")
    
    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/"
    payload = {
        "tenant": DEFAULT_TENANT,
        "service_data": {
            "name": created_service_name,
            "description": "A test service for staging API.",
            "version": "1.0",
            "details": {"key": "value"}
        }
    }
    
    try:
        with httpx.Client() as client:
            response = client.post(url, headers=headers, json=payload)
        
        res_data = print_response(response, "Add Staging Service")
        if response.status_code == 201 and res_data and "id" in res_data:
            created_service_id = res_data["id"]
            print(f"Service '{created_service_name}' added successfully with ID: {created_service_id}")
        else:
            print(f"Failed to add service. Status: {response.status_code}")
            if res_data:
                print(f"Error details: {res_data.get('detail')}")

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def test_list_staging_services(headers):
    if not DEFAULT_TENANT:
        print("Tenant not set, skipping list staging services test.")
        return

    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/"
    params = {"skip": 0, "limit": 10}

    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers, params=params)
        print_response(response, "List Staging Services")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def test_get_staging_service_by_id(headers):
    if not created_service_id:
        print("Service ID not available, skipping get staging service by ID test.")
        return

    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/{created_service_id}"
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
        print_response(response, f"Get Staging Service by ID ({created_service_id})")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

def test_get_staging_service_by_name(headers):
    if not created_service_name:
        print("Service name not available, skipping get staging service by name test.")
        return

    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/{created_service_name}"
    try:
        with httpx.Client() as client:
            response = client.get(url, headers=headers)
        print_response(response, f"Get Staging Service by Name ({created_service_name})")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def test_update_staging_service(headers):
    global created_service_name # Update global name if successful
    if not created_service_id:
        print("Service ID not available, skipping update staging service test.")
        return

    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/{created_service_id}"
    updated_service_name = f"{created_service_name}-updated"
    payload = {
        "service_data": {
            "name": updated_service_name, # Name can be updated via service_data
            "description": "An updated test service for staging API.",
            "version": "1.1",
            "details": {"key": "new_value", "status": "updated"}
        }
    }
    
    try:
        with httpx.Client() as client:
            response = client.put(url, headers=headers, json=payload)
        
        res_data = print_response(response, f"Update Staging Service ({created_service_id})")
        if response.status_code == 200 and res_data:
            created_service_name = updated_service_name
            print(f"Service ID {created_service_id} updated successfully. New name: {created_service_name}")
        elif res_data:
             print(f"Failed to update service. Status: {response.status_code}, Detail: {res_data.get('detail')}")
        else:
            print(f"Failed to update service. Status: {response.status_code}")


    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def test_populate_from_config(headers):
    # This endpoint might require specific setup or a known config file structure.
    # Assuming 'default' tenant for population as per API example.
    tenant_to_populate = "default" # Or use DEFAULT_TENANT if appropriate
    url = f"{BASE_URL}/tenants/{tenant_to_populate}/staging-services/populate-from-config"
    
    print(f"\nAttempting to populate services for tenant: {tenant_to_populate} from config...")
    try:
        with httpx.Client() as client:
            # This is a POST request as per the API definition
            response = client.post(url, headers=headers) 
        print_response(response, f"Populate Staging Services from Config for Tenant '{tenant_to_populate}'")
    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


def test_delete_staging_service(headers):
    if not created_service_id:
        print("Service ID not available, skipping delete staging service test.")
        return

    url = f"{BASE_URL}/tenants/{DEFAULT_TENANT}/staging-services/{created_service_id}"
    try:
        with httpx.Client() as client:
            response = client.delete(url, headers=headers)
        
        print(f"\n--- Delete Staging Service ({created_service_id}) ---")
        print(f"URL: {response.request.method} {response.url}")
        print(f"Response Status Code: {response.status_code}")
        if response.status_code == 204:
            print(f"Service ID {created_service_id} deleted successfully.")
        else:
            print("Failed to delete service.")
            try:
                res_data = response.json()
                print("Response JSON:")
                print(json.dumps(res_data, indent=2))
            except json.JSONDecodeError:
                print("Raw response text:")
                print(response.text)

    except httpx.RequestError as e:
        print(f"Request failed: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")


if __name__ == "__main__":
    print("Starting Staging Services API tests...")
    print(f"Using Tenant: {DEFAULT_TENANT}")
    print(f"Initial Service Name: {created_service_name}")
    print("IMPORTANT: Ensure the server is running and replace 'Bearer your_token_here' with a valid token in HEADERS.")

    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID,
            "accept": "application/json",
            "Content-Type": "application/json",
            }

    # Run tests in a sequence that makes sense (e.g., create before get/update/delete)
    test_add_staging_service(headers)
    
    if created_service_id:
        test_list_staging_services(headers) # List after adding one
        test_get_staging_service_by_id(headers)
        test_get_staging_service_by_name(headers) # Should match created_service_name
        test_update_staging_service(headers)
        test_get_staging_service_by_name(headers) # Check if name update reflected
        test_delete_staging_service(headers)
        test_list_staging_services(headers) # List after deleting one
    else:
        print("\nSkipping GET, UPDATE, DELETE tests as service creation failed or was skipped.")

    # This test can be run independently but might affect DB state.
    # test_populate_from_config() 
    
    print("\nStaging Services API tests finished.")
