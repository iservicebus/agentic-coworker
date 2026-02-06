import requests
import json
import os
from integrator.utils.logger import get_logger


logger = get_logger(__name__)
KC_CONFIG={
    "KEYCLOAK_BASE": os.getenv("IAM_URL", "http://localhost:8888"),
    "ADMIN_REALM": "master",
    "ADMIN_USERNAME": os.getenv("KEYCLOAK_ADMIN_USERNAME", "admin"),
    "ADMIN_PASSWORD": os.getenv("KEYCLOAK_ADMIN_PASSWORD", "admin"),
    "ADMIN_CLIENT_ID":  "admin-cli",

    "REALM_ATTRIBUTES":{
        "realm": "", 
        "enabled": True,
        "sslRequired": "none",  # <--- This disables the HTTPS requirement
        "accessTokenLifespan": 1800,
        "ssoSessionIdleTimeout": 3600,
        "ssoSessionMaxLifespan": 28800                  
    },

    "CLIENT_ATTRIBUTES":{
        "clientId": "",
        "secret": "",
        "enabled": True,
        "protocol": "openid-connect",
        "publicClient": False,
        "serviceAccountsEnabled": True,
        "standardFlowEnabled": True,
        "redirectUris": [],
        "webOrigins": [],
        "directAccessGrantsEnabled": True,
        "clientAuthenticatorType": "client-secret"
    },
    "USER_ATTRIBUTES":{

        "username":"",
        "firstName":"",
        "lastName":"",
        "email": "",
        "enabled": True,
        "credentials":[],
        "attributes":"",
        "emailVerified":False,
        "realmRoles":"",
        "clientRoles":"",
        "groups":""
      }

}
def get_admin_token(kc_config=KC_CONFIG):

    """Get admin access token."""
    token_url = f'{kc_config["KEYCLOAK_BASE"]}/realms/{kc_config["ADMIN_REALM"]}/protocol/openid-connect/token'
    logger.info(" get admin token from token url: {token_url}")

    token_data = {
        "grant_type": "password",
        "client_id": kc_config["ADMIN_CLIENT_ID"],
        "username": kc_config["ADMIN_USERNAME"],
        "password": kc_config["ADMIN_PASSWORD"],
    }
    token_resp = requests.post(token_url, data=token_data)
    token_resp.raise_for_status()

    access_token=token_resp.json()["access_token"]
    logger.info(f" received admin access token. access_token: {access_token} ")
    return access_token


def disable_keycloak_ssl(realm, headers,  kc_config=KC_CONFIG):

    try:
        
        # 2. Update Realm Settings
        admin_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{realm}'
        payload = {
            "sslRequired": "none"
        }

        print(f"Updating realm '{kc_config['ADMIN_REALM']}' settings...")
        update_res = requests.put(admin_url, json=payload, headers=headers)
        update_res.raise_for_status()

        print("Success! HTTPS requirement has been disabled for the master realm.")

    except requests.exceptions.RequestException as e:
        print(f"Error: {e}")
        if e.response is not None:
            print(f"Response Body: {e.response.text}")



def create_realm(headers, tenant_name, kc_config=KC_CONFIG):
    """Create a new realm."""
    realm_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms'
    
    # Use configurable attributes from KC_CONFIG
    realm_data = kc_config["REALM_ATTRIBUTES"].copy()
    realm_data["realm"] = tenant_name  # Override with the specific tenant name
    
    realm_resp = requests.post(realm_url, json=realm_data, headers=headers)
    if realm_resp.status_code == 201:
        logger.info(f"Realm '{tenant_name}' created.")
        return True
    elif realm_resp.status_code == 409:
        logger.info(f"Realm '{tenant_name}' already exists.")
        return False
    else:
        logger.info(f"Error creating realm '{tenant_name}': {realm_resp.text}")
        return False

def create_client_scope( headers, tenant_name, scope, kc_config=KC_CONFIG):
    
    """Create scope in a realm."""
    scopes_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/client-scopes'
    scope_resp = requests.post(scopes_url, json=scope, headers=headers)
    if scope_resp.status_code == 201:
        logger.info(f"Scope '{scope['name']}' created in realm '{tenant_name}'.")
    elif scope_resp.status_code == 409:
        logger.info(f"Scope '{scope['name']}' already exists in realm '{tenant_name}'.")
    else:
        logger.error(f"Error creating scope '{scope['name']}': {scope_resp.text}")


def assign_scope_to_client( headers, tenant_name, client_name, scope_json, kc_config=KC_CONFIG) -> None:




    # Get clients (agents) using new approach
    clients_url = f"{kc_config['KEYCLOAK_BASE']}/admin/realms/{tenant_name}/clients"
    params={"name": client_name}

    clients_response = requests.get(clients_url, headers=headers, params=params)
    clients_response.raise_for_status()

    clients = clients_response.json()
    if not clients:
        raise ValueError(f"Client not found by clientId: {client_name}")
    client_id=clients[0]["id"]


    scopes_url = f"{kc_config['KEYCLOAK_BASE']}/admin/realms/{tenant_name}/client-scopes"

    scopes_raw = requests.get( scopes_url,headers=headers)
    scopes_raw.raise_for_status()
    scopes = scopes_raw.json()
    scope_id=None
    for s in scopes:
        if s.get("name") == scope_json.get("name"):
            scope_id=s["id"]
            break 
    if not scope_id:
        logger.error(f"Error: scope name={scope_json.get('name')} is not found") 
        return

    """
    Assigns a client scope to a client.
    For default scope:
        PUT /admin/realms/{realm}/clients/{client-uuid}/default-client-scopes/{clientScopeId}
    """


    if scope_json.get("type")=="default":
        assign_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients/{client_id}/default-client-scopes/{scope_id}'
    else:
        assign_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients/{client_id}/optional-client-scopes/{scope_id}'

    res = requests.put(assign_url, headers=headers)
    # 204 No Content on success
    res.raise_for_status()



def create_realm_roles(headers, tenant_name, roles, kc_config=KC_CONFIG):
    """Create roles in a realm."""
    for role in roles:
        create_realm_role(headers, tenant_name, role, kc_config)

def create_realm_role( headers, tenant_name, role, kc_config=KC_CONFIG):
    """Create roles in a realm."""
    roles_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/roles'
    role_data = {"name": role["name"], "description": role.get("description", "")}
    role_resp = requests.post(roles_url, json=role_data, headers=headers)
    if role_resp.status_code == 201:
        logger.info(f"Role '{role['name']}' created in realm '{tenant_name}'.")
    elif role_resp.status_code == 409:
        logger.info(f"Role '{role['name']}' already exists in realm '{tenant_name}'.")
    else:
        logger.error(f"Error creating role '{role['name']}': {role_resp.text}")


def create_users(headers, tenant_name, users, kc_config=KC_CONFIG):
    """Create users in a realm."""
    for user in users:
        create_user(kc_config, headers, tenant_name, user)

def create_user(headers, tenant_name, user, kc_config=KC_CONFIG):
    """Create users in a realm."""
    users_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/users'
    
    # Start with default attributes from KC_CONFIG
    user_keys = kc_config["USER_ATTRIBUTES"].keys()
    

    filtered_user = {key: value for key, value in user.items() if key in user_keys}
 
    user_resp = requests.post(users_url, json=filtered_user, headers=headers)
    if user_resp.status_code == 201:
        logger.info(f"User '{filtered_user['username']}' created in realm '{tenant_name}'.")
    elif user_resp.status_code == 409:
        logger.info(f"User '{filtered_user['username']}' already exists in realm '{tenant_name}'.")
    else:
        logger.error(f"Error creating user '{filtered_user['username']}': {user_resp.text}")

def filter_realm(realm_data, kc_config=KC_CONFIG):
        # Filter to only return attributes defined in KC_CONFIG
        filtered_realm = {}
        for key in kc_config["REALM_ATTRIBUTES"].keys():
            filtered_realm[key] = realm_data.get(key, kc_config["REALM_ATTRIBUTES"][key])

        return filtered_realm    

def get_realm(headers, realm_name, kc_config=KC_CONFIG):
    """Get realm by name with all attributes defined in KC_CONFIG."""
    realm_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{realm_name}'
    
    try:
        realm_resp = requests.get(realm_url, headers=headers)
        if realm_resp.status_code == 200:
            realm_data = realm_resp.json()
            
            # Filter to only return attributes defined in KC_CONFIG
            filtered_realm = filter_realm(realm_data, kc_config)
           
            logger.info(f"Realm '{realm_name}' retrieved successfully.")
            return filtered_realm
        elif realm_resp.status_code == 404:
            logger.info(f"Realm '{realm_name}' not found.")
            return None
        else:
            logger.error(f"Error retrieving realm '{realm_name}': {realm_resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while retrieving realm '{realm_name}': {e}")
        return None

def get_user(headers, tenant_name, username, kc_config=KC_CONFIG):
    """Get user by username with all attributes defined in KC_CONFIG."""
    users_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/users'
    
    try:
        # Search for user by username
        search_params = {"username": username, "exact": "true"}
        users_resp = requests.get(users_url, headers=headers, params=search_params)
        
        if users_resp.status_code == 200:
            users_data = users_resp.json()
            if users_data:
                user_data = users_data[0]  # Get first match
                
                # Filter to only return attributes defined in KC_CONFIG
                filtered_user = {}
                for key in kc_config["USER_ATTRIBUTES"].keys():
                    filtered_user[key] = user_data.get(key, kc_config["USER_ATTRIBUTES"][key])
                
                logger.info(f"User '{username}' retrieved successfully from realm '{tenant_name}'.")
                return filtered_user
            else:
                logger.info(f"User '{username}' not found in realm '{tenant_name}'.")
                return None
        else:
            logger.error(f"Error retrieving user '{username}': {users_resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while retrieving user '{username}': {e}")
        return None

def delete_user(headers, tenant_name, username, kc_config=KC_CONFIG):
    """Delete user by username from a realm."""
    users_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/users'
    
    try:
        # First, search for user by username to get the user ID
        search_params = {"username": username, "exact": "true"}
        users_resp = requests.get(users_url, headers=headers, params=search_params)
        
        if users_resp.status_code == 200:
            users_data = users_resp.json()
            if users_data:
                user_id = users_data[0]["id"]  # Get the internal user ID
                
                # Delete the user using the user ID
                delete_url = f'{users_url}/{user_id}'
                delete_resp = requests.delete(delete_url, headers=headers)
                
                if delete_resp.status_code == 204:
                    logger.info(f"User '{username}' deleted successfully from realm '{tenant_name}'.")
                    return True
                else:
                    logger.error(f"Error deleting user '{username}': {delete_resp.text}")
                    return False
            else:
                logger.info(f"User '{username}' not found in realm '{tenant_name}'.")
                return False
        else:
            logger.error(f"Error retrieving user '{username}' for deletion: {users_resp.text}")
            return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while deleting user '{username}': {e}")
        return False

def get_client( headers, tenant_name, client_id, kc_config=KC_CONFIG):
    """Get client (agent) by clientId with all attributes defined in KC_CONFIG."""
    clients_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients'
    
    try:
        # Search for client by clientId
        search_params = {"clientId": client_id}
        clients_resp = requests.get(clients_url, headers=headers, params=search_params)
        
        if clients_resp.status_code == 200:
            clients_data = clients_resp.json()
            if clients_data:
                client_data = clients_data[0]  # Get first match
                
                # Filter to only return attributes defined in KC_CONFIG
                filtered_client = {}
                for key in kc_config["CLIENT_ATTRIBUTES"].keys():
                    filtered_client[key] = client_data.get(key, kc_config["CLIENT_ATTRIBUTES"][key])
                
                logger.info(f"Agent (client) '{client_id}' retrieved successfully from realm '{tenant_name}'.")
                return filtered_client
            else:
                logger.info(f"Agent (client) '{client_id}' not found in realm '{tenant_name}'.")
                return None
        else:
            logger.error(f"Error retrieving agent '{client_id}': {clients_resp.text}")
            return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while retrieving agent '{client_id}': {e}")
        return None

def create_clients( headers, tenant_name, clients, kc_config=KC_CONFIG):
    for client in clients:
        create_client(kc_config, headers, tenant_name, client)

def create_client( headers, tenant_name, client, kc_config=KC_CONFIG):
    """Create clients (agents) in a realm."""
    clients_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients'
    
    # Start with default attributes from KC_CONFIG
    client_data = kc_config["CLIENT_ATTRIBUTES"].copy()
    
    # Override with provided agent values, only for keys that exist in CLIENT_ATTRIBUTES
    for key in client_data.keys():
        if key in client:
            client_data[key] = client[key]
    
    # Special handling for clientId - use name or agent_id as fallback
    if not client_data["clientId"]:
        client_data["clientId"] = client.get("name") or client.get("agent_id", "")
    
    client_resp = requests.post(clients_url, json=client_data, headers=headers)
    if client_resp.status_code == 201:
        logger.info(f"Agent (client) '{client_data['clientId']}' created in realm '{tenant_name}'.")
    elif client_resp.status_code == 409:
        logger.info(f"Agent (client) '{client_data['clientId']}' already exists in realm '{tenant_name}'.")
    else:
        logger.error(f"Error creating agent '{client_data['clientId']}': {client_resp.text}")
def create_client_mapper( headers, tenant_name, client_id, mapper_json, kc_config=KC_CONFIG):
    """Create client mapper"""
    
    # First, get the internal client UUID using the clientId
    clients_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients'
    search_params = {"clientId": client_id}
    
    try:
        clients_resp = requests.get(clients_url, headers=headers, params=search_params)
        clients_resp.raise_for_status()
        clients_data = clients_resp.json()
        
        if not clients_data:
            logger.error(f"Client '{client_id}' not found in realm '{tenant_name}'.")
            return
        
        # Get the internal UUID of the client
        client_uuid = clients_data[0]["id"]
        logger.info(f"Found client '{client_id}' with UUID '{client_uuid}' in realm '{tenant_name}'.")
        
        # Check if mapper already exists for this specific client
        mapper_name = mapper_json.get("name")
        get_mappers_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients/{client_uuid}/protocol-mappers/models'
        
        existing_mappers_resp = requests.get(get_mappers_url, headers=headers)
        if existing_mappers_resp.status_code == 200:
            existing_mappers = existing_mappers_resp.json()
            logger.info(f"Client '{client_id}' has {len(existing_mappers)} existing mappers.")
            
            # Check if a mapper with the same name already exists for this client
            for existing_mapper in existing_mappers:
                if existing_mapper.get("name") == mapper_name:
                    logger.info(f"Mapper '{mapper_name}' already exists for client '{client_id}' (UUID: {client_uuid}) in realm '{tenant_name}'.")
                    return
        
        # Now use the UUID in the mapper URL to create the mapper
        mapper_url = f'{kc_config["KEYCLOAK_BASE"]}/admin/realms/{tenant_name}/clients/{client_uuid}/protocol-mappers/models'
        
        logger.info(f"Creating mapper '{mapper_name}' for client '{client_id}' (UUID: {client_uuid})...")
        mapper_resp = requests.post(mapper_url, json=mapper_json, headers=headers)
        if mapper_resp.status_code == 201:
            logger.info(f"✓ Mapper '{mapper_name}' for client '{client_id}' created successfully in realm '{tenant_name}'.")
        elif mapper_resp.status_code == 409:
            logger.warning(f"Mapper '{mapper_name}' for client '{client_id}' already exists (409 from Keycloak).")
        else:
            logger.error(f"Error creating mapper '{mapper_name}' for client '{client_id}': Status {mapper_resp.status_code}, Response: {mapper_resp.text}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error while creating mapper for client '{client_id}': {e}")


def main():
    import os
    """Main function to initialize Keycloak from a JSON file."""
    try:

        config_path = os.path.join(os.path.dirname(__file__), '../../..', 'init', 'init_iam.json')

        with open(config_path, 'r') as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: 'init/init_iam.json' not found.")
        return
    except json.JSONDecodeError:
        print("Error: Could not decode JSON from 'init/init_iam.json'.")
        return

    try:
        access_token = get_admin_token()
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json"
        }

        for tenant in config.get("tenants", []):
            tenant_name = tenant.get("name")
            if not tenant_name:
                print("Skipping tenant with no name.")
                continue

            print(f"--- Processing tenant: {tenant_name} ---")
            if create_realm(headers, tenant_name):
                print("Realm created. Please run the script again to process roles, users, and agents.")
                continue
            
            if "roles" in tenant:
                create_realm_roles(headers, tenant_name, tenant["roles"])
            if "users" in tenant:
                create_users(headers, tenant_name, tenant["users"])
            if "agents" in tenant:
                create_clients(headers, tenant_name, tenant["agents"])
            print(f"--- Finished processing tenant: {tenant_name} ---\n")

    except requests.exceptions.RequestException as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
