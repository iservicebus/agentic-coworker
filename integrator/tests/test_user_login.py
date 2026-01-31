import requests


import base64
import json
from typing import Any, Dict

import requests


def b64url_decode(data: str) -> bytes:
    # Add padding if needed
    padding = "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(data + padding)


def decode_jwt_no_verify(token: str) -> Dict[str, Any]:
    """
    Decode a JWT without verifying the signature.
    Good for debugging what's inside the token.
    """
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("Not a JWT (expected 3 dot-separated parts).")
        header = json.loads(b64url_decode(parts[0]).decode("utf-8"))
        payload = json.loads(b64url_decode(parts[1]).decode("utf-8"))
        return {"header": header, "payload": payload}
    except Exception as e:
        raise RuntimeError(f"Failed to decode JWT: {e}") from e







# Replace with your actual values
KEYCLOAK_URL = "http://localhost:8888"
REALM = "default"
CLIENT_ID = "agent-client"
USERNAME = "testuser"
PASSWORD = "testpass" # Make sure this is a secure password for your test user
SECRET = "host-secret" # Client secret for 'agent-client'

# API Endpoints
LOGIN_API_URL = "http://localhost:6060/users/login"
PROVIDER_TOKENS_API_URL = "http://localhost:6060/provider_tokens"
TEST_PROVIDER_ID = "github"
# URLs for the new endpoints will be constructed dynamically in the test functions


def get_token():
    token_url = f"{KEYCLOAK_URL}/realms/{REALM}/protocol/openid-connect/token"
    payload = {
        "client_id": CLIENT_ID,
        "grant_type": "password",
        "username": USERNAME,
        "password": PASSWORD
#        "client_secret": SECRET

    }
    payload = {
           "grant_type": "client_credentials",
           "client_id": "agent-dev",
           "client_secret": "securepass",
           "scope":"mcp:tools"
       }


    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    response = requests.post(token_url, data=payload, headers=headers)
    if response.status_code != 200:
        print(response.text)
        raise Exception("Failed to get token")
    return response.json()["access_token"]

def test_user_login():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID} 
    
    response = requests.get(LOGIN_API_URL, headers=headers)

    if response.status_code == 200:
        login_data = response.json()
        print("✅ Success (Login Endpoint):", login_data)
        assert "username" in login_data
        assert "working_agent" in login_data
        assert "active_tenant" in login_data
    else:
        print("❌ Failed (Login Endpoint):", response.status_code, response.text)
        assert False, f"Login failed: {response.status_code}"

def test_update_app_keys():
    token = get_token()
    login_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    
    login_response = requests.get(LOGIN_API_URL, headers=login_headers)
    assert login_response.status_code == 200, f"Login failed for update test: {login_response.text}"
    
    login_data = login_response.json()
    assert login_data.get("active_tenant") and login_data["active_tenant"].get("name"), \
        "active_tenant or active_tenant.name missing."
    assert login_data.get("working_agent") and login_data["working_agent"].get("agent_id"), \
        "working_agent or agent_id missing."

    tenant_name = login_data["active_tenant"]["name"]
    agent_id = login_data["working_agent"]["agent_id"]
    
    test_app_name = "test_app_from_pytest"
    test_secrets_payload = {"api_key": "new_pytest_api_key_12345"}
    
    new_app_key_payload = {
        "appName": test_app_name,
        "secrets": test_secrets_payload
    }
    
    UPDATE_app_keys_URL = f"http://localhost:6060/users/agents/{agent_id}/tenants/{tenant_name}/app_keys"

    update_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Agent-ID": CLIENT_ID 
    }

    update_response = requests.put(UPDATE_app_keys_URL, headers=update_headers, json=new_app_key_payload)

    assert update_response.status_code == 200, f"Update service secrets failed: {update_response.status_code}, {update_response.text}"
    response_data = update_response.json()
    print("✅ Success (Update Service Secrets):", response_data)
    assert response_data["name"] == tenant_name


def test_get_app_keys():
    token = get_token()
    login_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    
    login_response = requests.get(LOGIN_API_URL, headers=login_headers)
    assert login_response.status_code == 200, f"Login failed for get secrets test: {login_response.text}"
    
    login_data = login_response.json()
    assert login_data.get("active_tenant") and login_data["active_tenant"].get("name"), \
        "active_tenant or active_tenant.name missing."
    assert login_data.get("working_agent") and login_data["working_agent"].get("agent_id"), \
        "working_agent or agent_id missing."

    tenant_name = login_data["active_tenant"]["name"]
    agent_id = login_data["working_agent"]["agent_id"]
    test_app_name = "test_app_from_pytest"
    GET_SECRETS_URL = f"http://localhost:6060/users/agents/{agent_id}/tenants/{tenant_name}/app_keys/{test_app_name}"
    
    get_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    get_response = requests.get(GET_SECRETS_URL, headers=get_headers)
    
    assert get_response.status_code == 200, f"Get service secrets failed: {get_response.status_code}, {get_response.text}"
    secrets_dict = get_response.json()
    print("✅ Success (Get Service Secrets):", secrets_dict)
    assert isinstance(secrets_dict, dict)
    # Further assertions can be made if we know what secrets to expect.
    if "test_app_from_pytest" in secrets_dict:
        assert secrets_dict["test_app_from_pytest"] == {"api_key": "new_pytest_api_key_12345"}

def test_delete_app_key():
    token = get_token()
    login_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    
    login_response = requests.get(LOGIN_API_URL, headers=login_headers)
    assert login_response.status_code == 200, f"Login failed for delete test: {login_response.text}"
    
    login_data = login_response.json()
    assert login_data.get("active_tenant") and login_data["active_tenant"].get("name"), \
        "active_tenant or active_tenant.name missing."
    assert login_data.get("working_agent") and login_data["working_agent"].get("agent_id"), \
        "working_agent or agent_id missing."

    tenant_name = login_data["active_tenant"]["name"]
    agent_id = login_data["working_agent"]["agent_id"]
    app_name_to_delete = "test_app_from_pytest" # Assuming this was created in the update test

    DELETE_URL = f"http://localhost:6060/users/agents/{agent_id}/tenants/{tenant_name}/app_keys/{app_name_to_delete}"
    
    delete_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    delete_response = requests.delete(DELETE_URL, headers=delete_headers)
    
    assert delete_response.status_code == 204, f"Delete service secret failed: {delete_response.status_code}, {delete_response.text}"
    print(f"✅ Success (Delete Service Secret): {app_name_to_delete}")


def test_get_active_tenant_by_agent_id():
    token = get_token()
    login_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    
    login_response = requests.get(LOGIN_API_URL, headers=login_headers)
    assert login_response.status_code == 200, f"Login failed for get active tenant test: {login_response.text}"

    login_data = login_response.json()
    assert login_data.get("working_agent") and login_data["working_agent"].get("agent_id"), \
        "working_agent or agent_id missing. Ensure test user has working agent."
    
    agent_id_text = login_data["working_agent"]["agent_id"]
    GET_ACTIVE_TENANT_URL = f"http://localhost:6060/users/agents/{agent_id_text}/active_tenant"
    
    print(f"Attempting to get active tenant for Agent ID: {agent_id_text} at {GET_ACTIVE_TENANT_URL}")
    get_headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID} 
    active_tenant_response = requests.get(GET_ACTIVE_TENANT_URL, headers=get_headers)

    if active_tenant_response.status_code == 200:
        response_data = active_tenant_response.json()
        print("✅ Success (Get Active Tenant by Agent ID):", response_data)
        assert "id" in response_data and "name" in response_data and "app_keys" in response_data
        assert isinstance(response_data["app_keys"], dict)
        if login_data.get("active_tenant"):
            assert response_data["id"] == login_data["active_tenant"].get("id")
            assert response_data["name"] == login_data["active_tenant"].get("name")
    else:
        print(f"❌ Failed (Get Active Tenant by Agent ID): {active_tenant_response.status_code}, {active_tenant_response.text}")
        assert False, f"Get active tenant failed: {active_tenant_response.status_code}"

# --- Provider Token Tests ---

def test_add_or_update_provider_token():
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Agent-ID": CLIENT_ID
    }

    login_response = requests.get(LOGIN_API_URL, headers={"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID})
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    
    login_data = login_response.json()
    tenant_name = login_data.get("active_tenant", {}).get("name")
    agent_id_from_login = login_data.get("working_agent", {}).get("agent_id")

    assert tenant_name, "Active tenant name is required."
    assert agent_id_from_login, "Agent ID from login is required."

    # --- Test Case 1: Add new token with agent_id and username ---
    print(f"\n--- Add/Update Case 1: Add new token for AGENT_ID: {agent_id_from_login}, USERNAME: {USERNAME} ---")
    add_payload = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "agent_id": agent_id_from_login,
        "username": USERNAME, 
        "token": {"access_token": "initial_access_token", "refresh_token": "initial_refresh_token"}
    }
    response_add = requests.post(PROVIDER_TOKENS_API_URL, headers=headers, json=add_payload)
    print(f"Add Response: {response_add.status_code}, {response_add.text}")
    assert response_add.status_code == 201, f"Failed to add token: {response_add.text}"
    added_token_data = response_add.json()
    assert added_token_data["agent_id"] == agent_id_from_login and added_token_data["username"] == USERNAME
    assert added_token_data["token"]["access_token"] == "initial_access_token"
    original_token_id = added_token_data["id"]
    print(f"✅ Added token ID {original_token_id}")

    # --- Test Case 2: Update existing token (identified by agent_id), also update username ---
    print(f"\n--- Add/Update Case 2: Update token for AGENT_ID: {agent_id_from_login}, new USERNAME ---")
    updated_username = f"{USERNAME}_test_update"
    update_payload_new_user = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "agent_id": agent_id_from_login,
        "username": updated_username, "token": {"access_token": "updated_access_token_new_user"}
    }
    response_update_new_user = requests.post(PROVIDER_TOKENS_API_URL, headers=headers, json=update_payload_new_user)
    print(f"Update (New User) Response: {response_update_new_user.status_code}, {response_update_new_user.text}")
    assert response_update_new_user.status_code == 201
    updated_token_data_new_user = response_update_new_user.json()
    assert updated_token_data_new_user["id"] == original_token_id
    assert updated_token_data_new_user["username"] == updated_username
    assert updated_token_data_new_user["token"]["access_token"] == "updated_access_token_new_user"
    print(f"✅ Updated token ID {original_token_id}, username to {updated_username}")

    # --- Test Case 3: Update existing token, provide only agent_id (username should be preserved) ---
    print(f"\n--- Add/Update Case 3: Update token for AGENT_ID: {agent_id_from_login} (preserve username) ---")
    update_payload_preserve_user = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "agent_id": agent_id_from_login,
        "token": {"access_token": "final_access_token_preserve_user"}
        # No username in payload, API should preserve existing one
    }
    response_update_preserve_user = requests.post(PROVIDER_TOKENS_API_URL, headers=headers, json=update_payload_preserve_user)
    print(f"Update (Preserve User) Response: {response_update_preserve_user.status_code}, {response_update_preserve_user.text}")
    assert response_update_preserve_user.status_code == 201
    final_token_data = response_update_preserve_user.json()
    assert final_token_data["id"] == original_token_id
    assert final_token_data["username"] == updated_username # Should be username from Case 2
    assert final_token_data["token"]["access_token"] == "final_access_token_preserve_user"
    print(f"✅ Updated token ID {original_token_id}, username '{updated_username}' preserved.")

    # --- Test Case 4: Attempt to add token with missing agent_id (should fail with 422) ---
    print(f"\n--- Add/Update Case 4: Add token missing agent_id (expect 422) ---")
    invalid_payload_no_agent = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "username": USERNAME,
        "token": {"access_token": "invalid_token"}
    }
    response_invalid_no_agent = requests.post(PROVIDER_TOKENS_API_URL, headers=headers, json=invalid_payload_no_agent)
    print(f"Invalid (No AgentID) Response: {response_invalid_no_agent.status_code}, {response_invalid_no_agent.text}")
    assert response_invalid_no_agent.status_code == 422
    print(f"✅ Correctly failed with 422 for missing agent_id.")

def test_get_specific_provider_token():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    login_response = requests.get(LOGIN_API_URL, headers=headers)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    tenant_name = login_data.get("active_tenant", {}).get("name")
    agent_id_from_login = login_data.get("working_agent", {}).get("agent_id")
    assert tenant_name and agent_id_from_login, "Tenant name and Agent ID are required."

    # Ensure a token exists
    setup_payload = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "agent_id": agent_id_from_login,
        "username": f"{USERNAME}_specific", "token": {"access_token": "token_for_specific_get_test"}
    }
    add_resp = requests.post(PROVIDER_TOKENS_API_URL, headers={**headers, "Content-Type": "application/json"}, json=setup_payload)
    assert add_resp.status_code == 201, f"Setup for specific get failed: {add_resp.text}"
    added_token_id = add_resp.json()["id"]

    # --- Test Case 1: Get the specific token ---
    print(f"\n--- Specific Get Case 1: Get token for AGENT: {agent_id_from_login}, TENANT: {tenant_name}, PROVIDER: {TEST_PROVIDER_ID} ---")
    specific_get_url = f"{PROVIDER_TOKENS_API_URL}/tenants/{tenant_name}/providers/{TEST_PROVIDER_ID}/agents/{agent_id_from_login}"
    response_get = requests.get(specific_get_url, headers=headers)
    print(f"Specific Get Response: {response_get.status_code}, {response_get.text}")
    assert response_get.status_code == 200
    token_data = response_get.json()
    assert token_data["id"] == added_token_id and token_data["agent_id"] == agent_id_from_login
    assert token_data["token"]["access_token"] == "token_for_specific_get_test"
    print(f"✅ Successfully fetched specific token ID {added_token_id}")

    # --- Test Case 2: Attempt to get a non-existent token ---
    print(f"\n--- Specific Get Case 2: Get non-existent token ---")
    non_existent_agent = "agent_does_not_exist_123"
    url_non_existent = f"{PROVIDER_TOKENS_API_URL}/tenants/{tenant_name}/providers/{TEST_PROVIDER_ID}/agents/{non_existent_agent}"
    response_non_existent = requests.get(url_non_existent, headers=headers)
    print(f"Non-Existent Get Response: {response_non_existent.status_code}, {response_non_existent.text}")
    assert response_non_existent.status_code == 404
    print(f"✅ Correctly received 404 for non-existent specific token.")

def test_get_provider_tokens_list():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    login_response = requests.get(LOGIN_API_URL, headers=headers)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    tenant_name = login_data.get("active_tenant", {}).get("name")
    agent_id_from_login = login_data.get("working_agent", {}).get("agent_id")
    assert tenant_name and agent_id_from_login, "Tenant name and Agent ID are required."

    # Ensure at least one token exists for agent_id_from_login
    username_for_list_test = f"{USERNAME}_list_filter"
    setup_payload = {
        "provider_id": TEST_PROVIDER_ID, "tenant_name": tenant_name, "agent_id": agent_id_from_login,
        "username": username_for_list_test, "token": {"access_token": "token_for_list_filtering"}
    }
    add_resp = requests.post(PROVIDER_TOKENS_API_URL, headers={**headers, "Content-Type": "application/json"}, json=setup_payload)
    assert add_resp.status_code == 201, f"Setup for list test failed: {add_resp.text}"

    # --- Test Case 1: Get tokens by AGENT_ID ---
    print(f"\n--- List Tokens Case 1: Get by AGENT_ID: {agent_id_from_login} ---")
    params_agent = {"agent_id": agent_id_from_login, "tenant_name": tenant_name, "provider_id": TEST_PROVIDER_ID}
    response_agent = requests.get(PROVIDER_TOKENS_API_URL, headers=headers, params=params_agent)
    print(f"List by Agent Response: {response_agent.status_code}, {response_agent.text}")
    assert response_agent.status_code == 200
    agent_tokens = response_agent.json()
    assert isinstance(agent_tokens, list)
    assert any(t["agent_id"] == agent_id_from_login and t["username"] == username_for_list_test for t in agent_tokens)
    print(f"✅ Found tokens for agent {agent_id_from_login}")

    # --- Test Case 2: Get tokens by USERNAME ---
    print(f"\n--- List Tokens Case 2: Get by USERNAME: {username_for_list_test} ---")
    params_user = {"username": username_for_list_test, "tenant_name": tenant_name, "provider_id": TEST_PROVIDER_ID}
    response_user = requests.get(PROVIDER_TOKENS_API_URL, headers=headers, params=params_user)
    print(f"List by User Response: {response_user.status_code}, {response_user.text}")
    assert response_user.status_code == 200
    user_tokens = response_user.json()
    assert isinstance(user_tokens, list)
    assert any(t["username"] == username_for_list_test for t in user_tokens)
    print(f"✅ Found tokens for user {username_for_list_test}")

    # --- Test Case 3: Get tokens with no specific user/agent identifier (general list for tenant/provider) ---
    print(f"\n--- List Tokens Case 3: General list for TENANT: {tenant_name}, PROVIDER: {TEST_PROVIDER_ID} ---")
    params_general = {"tenant_name": tenant_name, "provider_id": TEST_PROVIDER_ID}
    response_general = requests.get(PROVIDER_TOKENS_API_URL, headers=headers, params=params_general)
    print(f"General List Response: {response_general.status_code}, {response_general.text}")
    assert response_general.status_code == 200
    general_tokens = response_general.json()
    assert isinstance(general_tokens, list)
    # Check if our setup token is in the general list
    assert any(t["agent_id"] == agent_id_from_login and t["username"] == username_for_list_test for t in general_tokens)
    print(f"✅ Received {len(general_tokens)} tokens for tenant/provider.")

    # --- Test Case 4: Get tokens for a non-existent agent_id (should return empty list) ---
    print(f"\n--- List Tokens Case 4: Get for non-existent agent_id ---")
    params_non_existent = {"agent_id": "agent_does_not_exist_456", "tenant_name": tenant_name}
    response_non_existent = requests.get(PROVIDER_TOKENS_API_URL, headers=headers, params=params_non_existent)
    print(f"Non-Existent Agent List Response: {response_non_existent.status_code}, {response_non_existent.text}")
    assert response_non_existent.status_code == 200
    assert response_non_existent.json() == []
    print(f"✅ Correctly received empty list for non-existent agent_id.")

def test_delete_provider_token():
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "X-Agent-ID": CLIENT_ID
    }

    login_response = requests.get(LOGIN_API_URL, headers={"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID})
    assert login_response.status_code == 200, "Login failed for delete_provider_token test"
    login_data = login_response.json()
    tenant_name = login_data.get("active_tenant", {}).get("name")
    agent_id_from_login = login_data.get("working_agent", {}).get("agent_id")

    assert tenant_name, "Tenant name not found in login data for delete_provider_token test."
    assert agent_id_from_login, "agent_id_from_login is required for delete tests."
    
    agent_id_for_delete_test = agent_id_from_login 

    # --- Test Case 1: Add a token for the AGENT_ID specifically for deletion test ---
    print(f"\n--- Delete Test Case 1: Add token for AGENT_ID: {agent_id_for_delete_test} (Provider: {TEST_PROVIDER_ID}) ---")
    token_to_delete_payload = {
        "provider_id": TEST_PROVIDER_ID,
        "tenant_name": tenant_name,
        "agent_id": agent_id_for_delete_test,
        "username": f"{USERNAME}_delete_test", 
        "token": {"access_token": "token_for_deletion", "purpose": "delete_test"}
    }
    add_response = requests.post(PROVIDER_TOKENS_API_URL, headers=headers, json=token_to_delete_payload)
    assert add_response.status_code == 201, f"Failed to add token for deletion test: {add_response.text}"
    added_token_id = add_response.json()["id"]
    print(f"✅ Added token for AGENT_ID {agent_id_for_delete_test} (Provider: {TEST_PROVIDER_ID}) with ID {added_token_id} to be deleted.")

    # --- Test Case 2: Delete the added token using (provider_id, tenant_name, agent_id) ---
    print(f"\n--- Delete Test Case 2: Delete token for AGENT_ID: {agent_id_for_delete_test} (Provider: {TEST_PROVIDER_ID}) ---")
    delete_payload = {
        "provider_id": TEST_PROVIDER_ID,
        "tenant_name": tenant_name,
        "agent_id": agent_id_for_delete_test
    }
    response_delete = requests.delete(PROVIDER_TOKENS_API_URL, headers=headers, json=delete_payload)
    print(f"Delete Token Request Payload: {delete_payload}")
    print(f"Delete Token Response: {response_delete.status_code}, {response_delete.text}")
    assert response_delete.status_code == 204, f"Failed to delete token: {response_delete.text}"
    print(f"✅ Successfully deleted token for AGENT_ID {agent_id_for_delete_test} (Provider: {TEST_PROVIDER_ID}). Status 204.")

    # --- Test Case 3: Verify token is deleted (try fetching it via specific GET endpoint) ---
    print(f"\n--- Delete Test Case 3: Verify deletion for AGENT_ID: {agent_id_for_delete_test} (Provider: {TEST_PROVIDER_ID}) ---")
    specific_get_url = f"{PROVIDER_TOKENS_API_URL}/tenants/{tenant_name}/providers/{TEST_PROVIDER_ID}/agents/{agent_id_for_delete_test}"
    response_get_deleted = requests.get(specific_get_url, headers=headers) 
    assert response_get_deleted.status_code == 404, f"Token for AGENT_ID {agent_id_for_delete_test} was found after deletion (expected 404), got {response_get_deleted.status_code}."
    print(f"✅ Verified token for AGENT_ID {agent_id_for_delete_test} is no longer present (got 404).")

    # --- Test Case 4: Attempt to delete a non-existent token (should 404) ---
    print(f"\n--- Delete Test Case 4: Attempt to delete non-existent token (AGID: {agent_id_for_delete_test}) ---")
    response_delete_non_existent = requests.delete(PROVIDER_TOKENS_API_URL, headers=headers, json=delete_payload) 
    print(f"Delete Non-Existent Token Response: {response_delete_non_existent.status_code}, {response_delete_non_existent.text}")
    assert response_delete_non_existent.status_code == 404, "Deleting a non-existent token should return 404."
    print(f"✅ Correctly received 404 for deleting non-existent token (AGID: {agent_id_for_delete_test}).")

    # --- Test Case 5: Attempt to delete with missing agent_id in payload (should 422 from Pydantic) ---
    print(f"\n--- Delete Test Case 5: Attempt delete with missing agent_id (expect 422) ---")
    invalid_delete_payload_missing_agent_id = {
        "provider_id": TEST_PROVIDER_ID,
        "tenant_name": tenant_name
    }
    response_invalid_delete_missing_agent = requests.delete(PROVIDER_TOKENS_API_URL, headers=headers, json=invalid_delete_payload_missing_agent_id)
    print(f"Invalid Delete (Missing AgentID) Response: {response_invalid_delete_missing_agent.status_code}, {response_invalid_delete_missing_agent.text}")
    assert response_invalid_delete_missing_agent.status_code == 422, "Deleting with missing agent_id should be Pydantic validation error (422)."
    print(f"✅ Correctly received 422 for deleting with missing agent_id.")


def test_get_auth_providers():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}",
                       "X-Agent-ID": CLIENT_ID

               }
    
    # First, get the active tenant name from the login endpoint
    login_response = requests.get(LOGIN_API_URL, headers=headers)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    
    assert "active_tenant" in login_data and login_data["active_tenant"], "Active tenant not found for user."
    tenant_name = login_data["active_tenant"]["name"]
    
    # Construct the URL for the auth providers endpoint
    auth_providers_url = f"http://localhost:6060/users/tenants/{tenant_name}/auth_providers"
    
    # Make the request to get auth providers
    response = requests.get(auth_providers_url, headers=headers)
    
    if response.status_code == 200:
        providers_data = response.json()
        print(f"✅ Success (Get Auth Providers for tenant '{tenant_name}'):", providers_data)
        assert isinstance(providers_data, list), "Response should be a list of providers."
        # You can add more specific assertions here if you have known providers for the test tenant
        # For example, if you know 'github' should be a provider:
        # assert any(p['provider_id'] == 'github' for p in providers_data), "Expected 'github' provider not found."
    else:
        print(f"❌ Failed (Get Auth Providers): {response.status_code}, {response.text}")
        assert False, f"Get auth providers failed: {response.status_code}"


def test_get_auth_providers_with_secrets():
    token = get_token()
    headers = {"Authorization": f"Bearer {token}", "X-Agent-ID": CLIENT_ID}
    
    login_response = requests.get(LOGIN_API_URL, headers=headers)
    assert login_response.status_code == 200, f"Login failed: {login_response.text}"
    login_data = login_response.json()
    
    assert "active_tenant" in login_data and login_data["active_tenant"], "Active tenant not found for user."
    tenant_name = login_data["active_tenant"]["name"]
    
    auth_providers_url = f"http://localhost:6060/users/tenants/{tenant_name}/auth_providers_with_secrets"
    
    response = requests.get(auth_providers_url, headers=headers)
    
    if response.status_code == 200:
        providers_data = response.json()
        print(f"✅ Success (Get Auth Providers with Secrets for tenant '{tenant_name}'):", providers_data)
        assert isinstance(providers_data, list), "Response should be a list of providers."
        for provider in providers_data:
            assert "provider_id" in provider
            assert "type" in provider
            assert "client_id" in provider
            assert "client_secret" in provider
            assert "issuer" in provider
            assert "is_built_in" in provider
            assert provider["client_secret"] is not None, "client_secret should not be null"
    else:
        print(f"❌ Failed (Get Auth Providers with Secrets): {response.status_code}, {response.text}")
        assert False, f"Get auth providers with secrets failed: {response.status_code}"


if __name__ == "__main__":
    at=get_token()
    decode_jwt_no_verify(at)

    print("--- Testing Login Endpoint ---")
#    test_user_login()
    print("\n--- Testing Update Service Secrets Endpoint ---")
#    test_update_app_keys()

    print("\n--- Testing Update Service Secrets Endpoint ---")
    test_get_app_keys()
    print("\n--- Testing Get Active Tenant by Agent ID Endpoint ---")
#    test_get_active_tenant_by_agent_id()
    print("\n--- Testing Provider Token Add/Update ---")
#    test_add_or_update_provider_token()
    print("\n--- Testing Provider Token Specific Get ---")
#    test_get_specific_provider_token()
    print("\n--- Testing Provider Token List ---")
#    test_get_provider_tokens_list()
    print("\n--- Testing Provider Token Delete ---")
#    test_delete_provider_token()
    print("\n--- Testing Get Auth Providers ---")
#    test_get_auth_providers()
    print("\n--- Testing Get Auth Providers With Secrets ---")
    #test_get_auth_providers_with_secrets()
