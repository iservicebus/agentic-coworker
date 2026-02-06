import json
from sqlalchemy.orm import Session
from collections import defaultdict

# Import utility functions
from integrator.utils.host import generate_host_id
from integrator.utils.logger import get_logger # Import the logger
from integrator.tools.tool_db_crud import  upsert_staging_service, delete_staging_service_by_id, get_staging_service_by_id

# Initialize logger for this module
logger = get_logger(__name__)

# Add etcd_client as the first argument
def register_routing(etcd_client, url, tenant="default", overwrite=True):
    """Registers the routing rules for a service in Traefik via etcd."""
    # Use service_name derived from url for routing keys
    routing_name, service_url, _ = generate_host_id(url)

    routing_name = f"{tenant}-{routing_name}"

    router_key = f"traefik/http/routers/{routing_name}-router/rule"
    value, _ = etcd_client.get(router_key)
    exists = value is not None

    if exists and not overwrite:
        logger.info(f"ℹ️ Routing for service '{routing_name}' (derived from URL {url}) already exists. Skipping registration.")
        return
    elif exists and overwrite:
        logger.warning(f"⚠️ Overwriting existing routing for service '{routing_name}' (derived from URL {url}).")
    else:
        logger.info(f"🚀 Registering routing for new service '{routing_name}' (derived from URL {url}).")

    # 1. Router config

    etcd_client.put(router_key, f"PathPrefix(`/{routing_name}`)")
    etcd_client.put(f"traefik/http/routers/{routing_name}-router/service", f"{routing_name}-service")
    etcd_client.put(f"traefik/http/routers/{routing_name}-router/entryPoints/0", "web")
    #etcd_client.put(f"traefik/http/routers/{routing_name}-router/entryPoints/1", "websecure")                                                                                                                                     

    # Only register on 'web' (HTTP) entrypoint to avoid HTTPS redirects
    etcd_client.put(f"traefik/http/routers/{routing_name}-router/middlewares", f"strip-{routing_name}@etcd")
    

    # 2. Middleware: use stripPrefix instead of regex
    middleware_key_base = f"traefik/http/middlewares/strip-{routing_name}/stripPrefix"
    etcd_client.put(f"{middleware_key_base}/prefixes/0", f"/{routing_name}")
    etcd_client.put(f"{middleware_key_base}/forceSlash", "false")

    #middleware_key_base = f"traefik/http/middlewares/strip-{service_name}"
    #etcd_client.put(f"{middleware_key_base}/replacepathregex/regex", f"^/{service_name}(/.*)?$")
    #etcd_client.put(f"{middleware_key_base}/replacepathregex/replacement", "$1")

    # 3. Service config
    service_key_base = f"traefik/http/services/{routing_name}-service"
    etcd_client.put(f"{service_key_base}/loadBalancer/servers/0/url", service_url)
    #etcd_client.put(f"{service_key_base}/loadBalancer/passHostHeader", "false")
    logger.info(f"✅ Routing for service '{routing_name}' registered.")


# Add etcd_client as the first argument
def delete_routing_by_url(etcd_client, url, tenant="default"):
    """
    Deletes the Traefik routing configuration associated with a specific URL,
    but only if that URL is not found in any existing service metadata.
    """
    logger.info(f"🔍 Checking if URL '{url}' is used in any service metadata...")

    metadata_prefix = "services_metadata/{tenant}"
    url_in_use = False
    service_using_url = None

    try:
        for value_bytes, meta in etcd_client.get_prefix(metadata_prefix):
            key = meta.key.decode('utf-8')
            if key.endswith("/staticInput"):
                try:
                    protocol_data = json.loads(value_bytes.decode('utf-8'))
                    if protocol_data.get("url") == url:
                        url_in_use = True
                        # Extract service name from the key path
                        service_using_url = key.split('/')[2] # e.g., services_metadata/service-name/protocol -> service-name
                        break # Found the URL, no need to check further
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Warning: Could not parse protocol JSON for key {key}")
                except Exception as e:
                     logger.warning(f"⚠️ Warning: Error processing metadata key {key}: {e}", exc_info=True)


    except Exception as e:
        logger.error(f"❌ Error checking service metadata: {e}", exc_info=True)
        return # Cannot safely proceed if metadata check failed

    if url_in_use:
        logger.warning(f"🚫 Cannot delete routing for URL '{url}'. It is currently used by service metadata: '{service_using_url}'.")
        logger.warning("   Delete the service metadata first using 'delete_service_metadata' if you want to remove this routing.")
        return

    logger.info(f"✅ URL '{url}' not found in any service metadata. Proceeding with routing deletion.")

    try:
        # Derive the service name used for routing keys from the URL
        routing_service_name, _, _ = generate_host_id(url)
        routing_service_name = f"{tenant}-{routing_service_name}"
        logger.info(f"   Derived routing service name: '{routing_service_name}'")
    except Exception as e:
        logger.error(f"❌ Error generating service name from URL '{url}': {e}", exc_info=True)
        return

    # Define prefixes for Traefik configuration keys
    router_prefix = f"traefik/http/routers/{routing_service_name}-router/"
    middleware_prefix = f"traefik/http/middlewares/strip-{routing_service_name}/"
    service_prefix = f"traefik/http/services/{routing_service_name}-service/"

    deleted_count = 0
    prefixes_to_delete = [router_prefix, middleware_prefix, service_prefix]

    logger.info(f"🗑️ Attempting to delete Traefik configuration for '{routing_service_name}'...")

    for prefix in prefixes_to_delete:
        try:
            response = etcd_client.delete_prefix(prefix)
            if response.deleted > 0:
                logger.info(f"   Deleted {response.deleted} key(s) with prefix '{prefix}'")
                deleted_count += response.deleted
            # else:
            #     logger.info(f"   No keys found with prefix '{prefix}'")
        except Exception as e:
            logger.error(f"❌ Error deleting keys with prefix '{prefix}': {e}", exc_info=True)

    if deleted_count > 0:
        logger.info(f"✅ Successfully deleted Traefik routing configuration for URL '{url}' (service name '{routing_service_name}').")
    else:
        logger.info(f"ℹ️ No Traefik routing configuration found or deleted for URL '{url}' (service name '{routing_service_name}'). It might have already been removed.")

# Add etcd_client as the first argument
def register_service_metadata(etcd_client, service_id, metadata, tenant="default", overwrite=True):
    """Registers the metadata for a service in etcd. Uses the explicit service_name provided and tenant."""
    metadata_base_key = f"services_metadata/{tenant}/{service_id}"
    name_key = f"{metadata_base_key}/name"

    value, _ = etcd_client.get(name_key)
    exists = value is not None

    if exists and not overwrite:
        logger.info(f"ℹ️ Metadata for service '{service_id}' exists and overwrite is False. Skipping registration.")
        return
    elif exists and overwrite:
        logger.info(f"🔄 Overwriting metadata for service '{service_id}'.")
    else:
        logger.info(f"📝 Registering metadata for new service '{service_id}'.")

    # Register or overwrite metadata fields using the provided service_name

    etcd_client.put(name_key, metadata.get("name", "")) # Use .get for safety
    etcd_client.put(f"{metadata_base_key}/description", metadata.get("description", "")) # Use .get for safety
    etcd_client.put(f"{metadata_base_key}/auth", json.dumps(metadata.get("auth", {})))
    etcd_client.put(f"{metadata_base_key}/appName", metadata.get("appName", ""))

    etcd_client.put(f"{metadata_base_key}/transport", metadata.get("transport", ""))
    etcd_client.put(f"{metadata_base_key}/inputSchema", json.dumps(metadata.get("inputSchema", {})))
    #etcd_client.put(f"{metadata_base_key}/output_schema", json.dumps(metadata.get("output_schema", {})))
    # Ensure transport is registered as part of metadata
    etcd_client.put(f"{metadata_base_key}/staticInput", json.dumps(metadata.get("staticInput", {})))
    # Add any other metadata fields here if necessary
    logger.info(f"✅ Metadata for service '{service_id}' registered.")


# Add etcd_client, db, username as arguments
def delete_service_metadata(etcd_client, db: Session, service_id: str, tenant: str, agent_id: str = None, username: str = None):
    """
    Deletes the metadata for a specific service from etcd (for a given tenant)
    and then attempts to delete the corresponding Traefik routing if the URL
    is not used elsewhere.
    """
    metadata_base_key = f"services_metadata/{tenant}/{service_id}"
    protocol_key = f"{metadata_base_key}/staticInput" # Used for URL retrieval for routing
    retrieved_url = None # For routing deletion logic

    logger.info(f"🗑️ Attempting to delete metadata for service '{service_id}' (tenant: {tenant}) and manage staging...")

    # --- Staging Logic: Add to staging if not present ---
    retrieved_service_data_for_staging = {}
    try:
        logger.info(f"   Retrieving metadata for '{service_id}' (tenant: {tenant}) for staging purposes...")
        # Retrieve all parts of the service definition needed for staging

        name_bytes, _ = etcd_client.get(f"{metadata_base_key}/name")
        desc_bytes, _ = etcd_client.get(f"{metadata_base_key}/description")
        transport_bytes, _ = etcd_client.get(f"{metadata_base_key}/transport")
        auth_bytes, _ = etcd_client.get(f"{metadata_base_key}/auth")
        app_name_bytes, _ = etcd_client.get(f"{metadata_base_key}/appName")
        input_schema_bytes, _ = etcd_client.get(f"{metadata_base_key}/inputSchema")
        static_input_bytes, _ = etcd_client.get(protocol_key) # Use protocol_key for staticInput

        if static_input_bytes:
            retrieved_service_data_for_staging = {
                "id": service_id,
                "name": name_bytes.decode('utf-8') if desc_bytes else "",
                "description": desc_bytes.decode('utf-8') if desc_bytes else "",
                "appName": app_name_bytes.decode('utf-8') if app_name_bytes else "",
                "transport": transport_bytes.decode('utf-8') if transport_bytes else "",
                "auth": json.loads(auth_bytes.decode('utf-8')) if auth_bytes else {},
                "inputSchema": json.loads(input_schema_bytes.decode('utf-8')) if input_schema_bytes else {},
                "staticInput": json.loads(static_input_bytes.decode('utf-8')) # This is critical
            }
            # Also extract URL for routing deletion from staticInput
            protocol_data = retrieved_service_data_for_staging["staticInput"]
            retrieved_url = protocol_data.get("url") # This is the dict form of URL
            if retrieved_url:
                 logger.info(f"   Found URL in metadata for potential routing deletion: {retrieved_url}")
            else:
                logger.info(f"   Protocol metadata found, but no 'url' field present for routing deletion.")


            logger.info(f"   Checking staging: Does service '{service_id}' (tenant: {tenant}) already exist?")
            existing_staging_service = get_staging_service_by_id(db, service_id)
            if not existing_staging_service:
                logger.info(f"   Service '{service_id}' not in staging. Adding it...")
                upsert_staging_service(db,retrieved_service_data_for_staging, tenant, username or "system")
                logger.info(f"   Successfully added service '{service_id}' to staging.")
            else:
                upsert_staging_service(db,retrieved_service_data_for_staging, tenant, username=existing_staging_service.updated_by, service_id=existing_staging_service.id)
                logger.info(f"   Service '{service_id}' already exists in staging (ID: {existing_staging_service.id}). No action needed.")
        else:
            logger.warning(f"   Could not retrieve sufficient metadata (staticInput missing) for '{service_id}' to add to staging or determine routing URL.")
            # If staticInput is missing, we might not have the URL for routing deletion either.
            # The original logic for URL retrieval for routing deletion is now integrated here.

    except json.JSONDecodeError as e:
        logger.warning(f"⚠️ Warning: Could not parse JSON for service '{service_id}' metadata: {e}. Staging/routing may be affected.", exc_info=True)
    except Exception as e:
        logger.error(f"⚠️ Error during staging logic or metadata retrieval for '{service_id}': {e}", exc_info=True)
    # --- End Staging Logic ---

    # --- Original Metadata Deletion and Routing Deletion Logic ---
    # 1. Try to retrieve the URL from metadata before deleting (already done above if staticInput was found)
    # If retrieved_url is still None here, it means staticInput wasn't found or didn't contain a URL.
    if not retrieved_url and static_input_bytes: # Re-check if static_input_bytes was fetched but URL was not extracted
        try:
            protocol_data_for_url = json.loads(static_input_bytes.decode('utf-8'))
            retrieved_url_obj = protocol_data_for_url.get("url")
            if retrieved_url_obj: # This is the dict form of URL
                 # Convert dict URL to string if generate_host_id expects string or handle dict in delete_routing_by_url
                 # For now, assuming delete_routing_by_url can handle the dict form or it's handled there.
                 # The current delete_routing_by_url expects a string URL.
                 # This part needs careful handling of URL format.
                 # For simplicity, let's assume retrieved_url is the string form if needed by delete_routing_by_url
                 # However, generate_host_id takes the dict form.
                 # Let's ensure retrieved_url is the dict form for generate_host_id if used by delete_routing_by_url
                 retrieved_url = retrieved_url_obj # Keep as dict for generate_host_id
                 logger.info(f"   Re-checked and found URL for routing deletion: {retrieved_url}")
            else:
                 logger.info(f"   Re-checked staticInput, but no 'url' field present for routing deletion.")
        except Exception as e:
            logger.warning(f"⚠️ Warning: Error re-checking staticInput for URL: {e}", exc_info=True)


    # 2. Attempt to delete the metadata from etcd
    metadata_deleted_successfully = False
    try:
        # Check if any keys with the prefix exist before attempting deletion
        found_keys = False
        for _, meta in etcd_client.get_prefix(metadata_base_key, keys_only=True):
            found_keys = True
            break # Found at least one key

        if not found_keys:
            logger.info(f"ℹ️ No metadata found for service '{service_id}'. Nothing to delete.")
            # Even if no metadata found, maybe routing exists orphanedly? Or maybe not.
            # Decide if we should still try deleting routing based on a potentially *stale* retrieved_url.
            # For now, let's only delete routing if metadata *was* found and deleted.
            return

        # Delete all keys starting with the metadata_base_key prefix
        logger.info(f"   Deleting metadata keys with prefix '{metadata_base_key}'...")
        response = etcd_client.delete_prefix(metadata_base_key)
        if response.deleted > 0:
            logger.info(f"✅ Successfully deleted {response.deleted} metadata key(s) for service '{service_id}'.")
            metadata_deleted_successfully = True
        else:
             logger.warning(f"🤔 Metadata for service '{service_id}' was found, but no keys were reported deleted by the delete operation.")
             # Consider if we should still proceed with routing deletion in this ambiguous case. Let's assume not for safety.
    except Exception as e:
        logger.error(f"❌ Error deleting metadata for service '{service_id}': {e}", exc_info=True)
        # If metadata deletion failed, do not proceed to delete routing
        return

    # 3. If metadata deletion was successful and we have a URL (dict form), attempt routing deletion
    # delete_routing_by_url expects the URL dict
    if metadata_deleted_successfully and retrieved_url: # retrieved_url is the dict form
        logger.info(f"\n   Proceeding to check and potentially delete routing for URL object: {retrieved_url}...")


        appName, _, _ = generate_host_id(retrieved_url)
        if get_service_metadata_count_by_app(etcd_client, appName,tenant)<1:
            delete_routing_by_url(etcd_client, retrieved_url, tenant) # Pass the dict URL
    elif metadata_deleted_successfully and not retrieved_url:
        logger.info(f"\n   Metadata deleted, but no URL was found in the metadata, so routing cannot be automatically deleted.")
    elif not metadata_deleted_successfully:
         logger.warning(f"\n   Metadata deletion did not complete successfully. Skipping routing deletion attempt.")




# Add etcd_client, db, username as arguments
def register_single_service(etcd_client, db: Session, tenant: str, service_id: str, service_data: dict,  routing_overwrite=True, metadata_overwrite=True):
    """Registers a single service described by a dictionary (from JSON)."""
    inputSchema=service_data.get("inputSchema")
    http_obj=service_data.get("staticInput")


    url = http_obj.get("url")

    if not service_id:
        logger.warning("⚠️ Skipping service registration: 'name' is missing in service data.")
        return
    if not url or not url.get("host"):
        logger.warning(f"⚠️ Skipping service registration for '{service_id}': 'protocol.url' is missing.")
        return


    logger.info(f"\n--- Registering single service: {service_id} ---")

    # Register routing - uses service name derived *from URL* by generate_host_id
    register_routing(etcd_client, url, tenant, overwrite=routing_overwrite)


    # Register metadata - uses the explicit *service_name* from the input data and tenant
    register_service_metadata(etcd_client, service_id, service_data, tenant=tenant, overwrite=metadata_overwrite)

    # --- New Staging Logic: Delete from staging if present ---
    try:
        logger.info(f"Checking staging for existing service '{service_id}' in tenant '{tenant}' to remove if registered...")
        staging_service = get_staging_service_by_id(db, service_id)
        if staging_service:
            logger.info(f"Found service '{service_id}' in staging (ID: {staging_service.id}). Deleting it as it's now registered.")
            
            delete_staging_service_by_id(db,service_id=staging_service.id)
            logger.info(f"Successfully deleted service '{service_id}' from staging.")
        else:
            logger.info(f"Service '{service_id}' not found in staging. No removal action needed from staging.")
    except Exception as e:
        logger.error(f"⚠️ Error interacting with staging services for '{service_id}' during registration: {e}", exc_info=True)
    # --- End New Staging Logic ---

    logger.info(f"--- Finished registering single service: {service_id} (tenant: {tenant}) ---")


def get_routing_by_url(etcd_client, url, tenant="default"):
    """
    Retrieves the Traefik routing configuration associated with a specific URL.
    
    Args:
        etcd_client: An initialized etcd3 client instance.
        url: The URL dict to get routing for.
        tenant (str): The tenant name. Defaults to "default".
    
    Returns:
        dict: A dictionary containing the routing configuration,
              or None if no routing is found.
    """
    try:
        # Derive the service name used for routing keys from the URL
        routing_name, _, _ = generate_host_id(url)
        routing_name = f"{tenant}-{routing_name}"
        logger.info(f"🔍 Retrieving routing configuration for service '{routing_name}' (derived from URL: {url})")
    except Exception as e:
        logger.error(f"❌ Error generating service name from URL '{url}': {e}", exc_info=True)
        return None

    # Define prefixes for Traefik configuration keys
    router_prefix = f"traefik/http/routers/{routing_name}-router/"
    middleware_prefix = f"traefik/http/middlewares/strip-{routing_name}/"
    service_prefix = f"traefik/http/services/{routing_name}-service/"

    routing_config = {
        "service_name": routing_name,
        "tenant": tenant,
        "url": url,
        "router": {},
        "middleware": {},
        "service": {}
    }

    found_any = False
    prefixes_to_check = [
        ("router", router_prefix),
        ("middleware", middleware_prefix), 
        ("service", service_prefix)
    ]

    logger.info(f"   Checking Traefik configuration for '{routing_name}'...")

    for config_type, prefix in prefixes_to_check:
        try:
            for value_bytes, metadata_obj in etcd_client.get_prefix(prefix):
                found_any = True
                key = metadata_obj.key.decode('utf-8')
                val_str = value_bytes.decode('utf-8')
                
                # Extract the field name relative to the prefix
                field_name = key.replace(prefix, "")
                routing_config[config_type][field_name] = val_str
                
        except Exception as e:
            logger.error(f"❌ Error retrieving {config_type} configuration with prefix '{prefix}': {e}", exc_info=True)

    if not found_any:
        logger.info(f"ℹ️ No routing configuration found for service '{routing_name}'.")
        return None

    logger.info(f"✅ Retrieved routing configuration for service '{routing_name}'.")
    return routing_config


def get_service_metadata(etcd_client, service_id, tenant="default"):
    """
    Retrieves all metadata for a single service specified by its name and tenant from etcd.

    Args:
        etcd_client: An initialized etcd3 client instance.
        service_name (str): The name of the service to retrieve.
        tenant (str): The tenant of the service. Defaults to "default".

    Returns:
        dict: A dictionary containing all metadata for the service,
              or None if the service is not found or an error occurs.
    """
    prefix = f"services_metadata/{tenant}/{service_id}/"
    service_data = {}
    json_fields = {"inputSchema", "staticInput", "auth"}  # Known JSON fields
    found = False
    
    logger.info(f"🔍 Retrieving metadata for service '{service_id}' in tenant '{tenant}' with prefix '{prefix}'...")

    try:
        for value_bytes, metadata_obj in etcd_client.get_prefix(prefix):
            found = True
            key = metadata_obj.key.decode('utf-8')
            val_str = value_bytes.decode('utf-8')

            # Extract the field name from the key relative to the prefix
            field_name_part = key.replace(prefix, "")
            
            # Ensure we don't have nested slashes in field_name_part
            if "/" in field_name_part:
                logger.warning(f"⚠️ Skipping unexpected key structure within service prefix: {key}")
                continue

            field_name = field_name_part

            try:
                if field_name in json_fields:
                    service_data[field_name] = json.loads(val_str)
                else:
                    service_data[field_name] = val_str
            except json.JSONDecodeError:
                logger.warning(f"⚠️ Could not parse JSON for {key}. Storing as raw string: '{val_str}'")
                service_data[field_name] = val_str
            except Exception as e:
                logger.warning(f"⚠️ Error processing field {field_name} for service {service_id} in tenant {tenant}: {e}", exc_info=True)

        if not found:
            logger.info(f"ℹ️ No metadata found for service '{service_id}' in tenant '{tenant}'.")
            return None

        # Add the service name and tenant to the dictionary
        service_data["id"] = service_id
        service_data["tenant"] = tenant

        logger.info(f"✅ Retrieved metadata for service '{service_id}' in tenant '{tenant}'.")
        return service_data

    except Exception as e:
        logger.error(f"❌ Error retrieving data from etcd for service '{service_id}' in tenant '{tenant}': {e}", exc_info=True)
        return None


def get_services_by_tenant(etcd_client, tenant="default"):
    """
    Retrieves all service metadata for a specific tenant from etcd.
    
    Args:
        etcd_client: An initialized etcd3 client instance.
        tenant (str): The tenant name. Defaults to "default".
    
    Returns:
        list: A list of service definition dictionaries for the given tenant.
    """
    tenant_prefix = f"services_metadata/{tenant}/"
    services_for_tenant_temp = defaultdict(dict)
    
    logger.info(f"🔍 Retrieving service metadata for tenant '{tenant}' from etcd under prefix '{tenant_prefix}'...")

    try:
        for value_bytes, metadata_obj in etcd_client.get_prefix(tenant_prefix):
            key = metadata_obj.key.decode('utf-8')
            val_str = value_bytes.decode('utf-8')

            # Key structure: services_metadata/{tenant}/{service_name}/{field_name}
            relative_key_part = key.replace(tenant_prefix, "")
            parts = relative_key_part.split('/')

            if len(parts) >= 2:  # service_name, field_name
                service_id_from_key = parts[0]
                field_name = parts[1]

                # Ensure service name and tenant are recorded in each service's dictionary
                if "name" not in services_for_tenant_temp[service_id_from_key]:
                    services_for_tenant_temp[service_id_from_key]["id"] = service_id_from_key
                    services_for_tenant_temp[service_id_from_key]["tenant"] = tenant

                try:
                    # If schema or protocol, parse JSON; otherwise, store as string
                    if field_name in ["inputSchema", "staticInput", "auth"]:
                        services_for_tenant_temp[service_id_from_key][field_name] = json.loads(val_str)
                    else:
                        # Store other fields like 'description' directly
                        services_for_tenant_temp[service_id_from_key][field_name] = val_str
                except json.JSONDecodeError:
                    logger.warning(f"⚠️ Could not parse JSON for {key}. Storing as raw string: '{val_str}'")
                    services_for_tenant_temp[service_id_from_key][field_name] = val_str
                except Exception as e:
                    logger.warning(f"⚠️ Error processing field {field_name} for service {service_id_from_key} in tenant {tenant}: {e}", exc_info=True)

    except Exception as e:
        logger.error(f"❌ Error retrieving data from etcd for tenant '{tenant}': {e}", exc_info=True)
        return []

    # Convert defaultdict of dicts to a list of service dictionaries
    services_list = list(services_for_tenant_temp.values())
    logger.info(f"✅ Retrieved metadata for {len(services_list)} services in tenant '{tenant}'.")
    return services_list


def get_all_services(etcd_client):
    """
    Retrieves all service metadata from etcd, organized by tenant.
    
    Args:
        etcd_client: An initialized etcd3 client instance.
    
    Returns:
        dict: A dictionary where keys are tenant names and values are lists of service definitions.
    """
    all_tenants_services = {}
    processed_tenants = set()
    base_prefix_for_tenants = "services_metadata/"

    logger.info(f"🔍 Discovering all tenants from etcd under prefix '{base_prefix_for_tenants}'...")

    try:
        # Iterate over keys under "services_metadata/" to find unique tenant names
        for _, metadata_obj in etcd_client.get_prefix(base_prefix_for_tenants, keys_only=True):
            key = metadata_obj.key.decode('utf-8')
            
            # Key structure: services_metadata/{tenant}/{service_name}/{field_name}
            relative_key = key.replace(base_prefix_for_tenants, "")
            parts = relative_key.split('/')
            
            if len(parts) >= 1 and parts[0]:  # parts[0] should be the tenant name
                tenant = parts[0]
                if tenant not in processed_tenants:
                    logger.info(f"   Discovered tenant: {tenant}. Retrieving services...")
                    tenant_services = get_services_by_tenant(etcd_client, tenant)
                    if tenant_services:  # Only add if services were actually found for this tenant
                        all_tenants_services[tenant] = tenant_services
                    processed_tenants.add(tenant)
        
        if not processed_tenants:
            logger.info("ℹ️ No tenants found under 'services_metadata/'.")
            return {}

    except Exception as e:
        logger.error(f"❌ Error discovering tenants or retrieving data from etcd: {e}", exc_info=True)
        return {}

    total_services_count = sum(len(services) for services in all_tenants_services.values())
    logger.info(f"✅ Retrieved metadata for {total_services_count} services across {len(all_tenants_services)} tenants.")
    return all_tenants_services


def get_service_metadata_count_by_app(etcd_client, app_name, tenant="default"):
    """
    Retrieves the count of service metadata entries for a specific app name within a tenant.
    
    Args:
        etcd_client: An initialized etcd3 client instance.
        app_name (str): The app name to count services for.
        tenant (str): The tenant name. Defaults to "default".
    
    Returns:
        int: The count of services with the specified app name.
    """
    tenant_prefix = f"services_metadata/{tenant}/"
    count = 0
    
    logger.info(f"🔍 Counting service metadata for app '{app_name}' in tenant '{tenant}'...")

    try:
        for value_bytes, metadata_obj in etcd_client.get_prefix(tenant_prefix):
            key = metadata_obj.key.decode('utf-8')
            
            # Key structure: services_metadata/{tenant}/{service_name}/{field_name}
            relative_key_part = key.replace(tenant_prefix, "")
            parts = relative_key_part.split('/')

            if len(parts) >= 2 and parts[1] == "appName":  # Check if this is an appName field
                val_str = value_bytes.decode('utf-8')
                if val_str == app_name:
                    count += 1
                    service_name = parts[0]
                    logger.info(f"   Found service '{service_name}' with app name '{app_name}'")

    except Exception as e:
        logger.error(f"❌ Error counting services for app '{app_name}' in tenant '{tenant}': {e}", exc_info=True)
        return 0

    logger.info(f"✅ Found {count} services with app name '{app_name}' in tenant '{tenant}'.")
    return count
