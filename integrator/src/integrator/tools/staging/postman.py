
import json
import re
from typing import Dict, Any, List
from integrator.utils import host

# Helper function to check if a string contains a Postman variable syntax (e.g., {{variable_name}})
def is_postman_variable(value: str) -> bool:
    return isinstance(value, str) and re.match(r"^{{[a-zA-Z0-9_]+}}$", value)

# Heuristic list for identifying security-related parameter names (case-insensitive)
# This list can be expanded based on common API key/token naming conventions.
SECURITY_KEYWORDS = ["api_key", "apikey", "token", "auth", "authorization", "x-api-key", "x-auth-token"]

def convert_postman_item_to_tool_definition(postman_item: Dict[str, Any]) -> Dict[str, Any]:
    """
    Converts a Postman collection item into a JSON tool definition
    that strictly conforms to the provided generic JSON schema.

    Args:
        postman_item (Dict[str, Any]): A dictionary representing a single Postman
                                       collection item (e.g., as exported from Postman JSON).

    Returns:
        Dict[str, Any]: A dictionary representing the API tool definition in the
                        specified generic JSON schema format.
    """

    # Initialize the base structure of the tool definition
    tool_definition: Dict[str, Any] = {
        "transport": "http",
        "staticInput": {
            "url": {}
            # Headers will be added if present
        },
        "inputSchema": {
            "type": "object",
            "description": "Dynamic input parameters for the API call.",
            "properties": {}
            # 'required' is handled implicitly by parameter presence or within body schema
        }
    }

    # Extract basic info: name and description
    tool_definition["name"] = postman_item.get("name", "UnnamedTool")
    # Sanitize tool name to match pattern '^[a-zA-Z0-9_\.-]+$'
    tool_definition["name"] = re.sub(r'[^a-zA-Z0-9_\.\-]', '', tool_definition["name"])
    description = postman_item["request"].get("description")
    if isinstance(description, dict):
        tool_definition["description"] = description.get("content", "No description provided.")
    elif isinstance(description, str):
        tool_definition["description"] = description
    else:
        tool_definition["description"] = "No description provided."

    request = postman_item["request"]

    # 1. Map Static API Elements (`staticInput`)
    tool_definition["staticInput"]["method"] = request["method"].upper() # Ensure uppercase method

    # --- URL components ---
    url_data = request.get("url", {})
    
    # Convert query list to dictionary format for host.generate_host_id()
    url_data_for_host = url_data.copy()
    if "query" in url_data_for_host and isinstance(url_data_for_host["query"], list):
        query_dict = {}
        for param in url_data_for_host["query"]:
            if not param.get("disabled", False):
                query_dict[param["key"]] = param.get("value", "")
        url_data_for_host["query"] = query_dict
    
    host_id, _, _ = host.generate_host_id(url_data_for_host)
    if host_id:
         tool_definition["appName"] = host_id

    tool_definition["staticInput"]["url"]["protocol"] = url_data.get("protocol")
    tool_definition["staticInput"]["url"]["host"] = url_data.get("host", [])
    if url_data.get("port"):
        tool_definition["staticInput"]["url"]["port"] = url_data["port"]

    # Path segments: Identify dynamic parameters and format them for staticInput
    static_path_segments: List[str] = []
    dynamic_path_properties: Dict[str, Any] = {}
    if url_data.get("path"):
        for segment in url_data["path"]:
            if isinstance(segment, str) and segment.startswith(":"):
                param_name = segment[1:]
                static_path_segments.append(f"${param_name}")
                dynamic_path_properties[param_name] = {
                    "type": "string", # Default type for path parameters
                    "description": f"Dynamic path parameter '{param_name}'."
                }
            elif is_postman_variable(segment):
                param_name = segment.strip('{}')
                static_path_segments.append(f"${param_name}")
                dynamic_path_properties[param_name] = {
                    "type": "string",
                    "description": f"Dynamic path parameter '{param_name}'."
                }
            else:
                static_path_segments.append(str(segment)) # Ensure all segments are strings
    tool_definition["staticInput"]["url"]["path"] = static_path_segments
    if dynamic_path_properties:
        tool_definition["inputSchema"]["properties"]["aint_path"] = {
            "type": "object",
            "properties": dynamic_path_properties
        }

    # Query parameters: Distinguish static, dynamic, and security tokens
    static_query_params: Dict[str, str] = {}
    dynamic_query_properties: Dict[str, Any] = {}
    if url_data.get("query"):
        for param in url_data["query"]:
            if param.get("disabled", False):
                continue

            param_key = param["key"]
            param_value = param.get("value", "")

            is_security_param = any(keyword in param_key.lower() for keyword in SECURITY_KEYWORDS)
            is_dynamic_variable = is_postman_variable(param_value)

            if is_dynamic_variable:
                param_name = param_value.strip('{}')
                static_query_params[param_key] = f"${param_name}"
                dynamic_query_properties[param_name] = {
                    "type": "string",
                    "description": param.get("description", f"Query parameter '{param_name}'.")
                }
            elif is_security_param:
                static_query_params[param_key] = f"${param_key}"
                dynamic_query_properties[param_key] = {
                    "type": "string",
                    "description": param.get("description", f"Query parameter '{param_key}'.")
                }
            else:
                static_query_params[param_key] = param_value
    
    if static_query_params:
        tool_definition["staticInput"]["url"]["query"] = static_query_params
    
    if dynamic_query_properties:
        tool_definition["inputSchema"]["properties"]["aint_query"] = {
            "type": "object",
            "properties": dynamic_query_properties
        }


    # --- Headers ---
    static_headers: Dict[str, str] = {}
    dynamic_headers_properties: Dict[str, Any] = {}

    # CRITICAL: Handle Security Tokens / API Keys from Postman's 'auth' section first
    auth_data = request.get("auth")
    if auth_data:
        auth_type = auth_data.get("type")
        if auth_type == "bearer":
            # For bearer token, the standard header is "Authorization"
            # Value format: "Bearer $Authorization" as per instruction: "$<parameter_original_name>"
            static_headers["Authorization"] = "Bearer $Authorization"
        elif auth_type == "apikey":
            # Postman's API key details are in a list of {key, value} for key and value fields
            api_key_details = {item["key"]: item["value"] for item in auth_data.get("apikey", [])}
            
            key_name = api_key_details.get("key")
            add_to = api_key_details.get("in") # Specifies "header" or "query"

            if key_name and add_to:
                if add_to == "header":
                    static_headers[key_name] = f"${key_name}"
                elif add_to == "query":
                    # If an API key from auth section uses query, add it to staticInput.url.query
                    tool_definition["staticInput"]["url"].setdefault("query", {})[key_name] = f"${key_name}"
            
    # Process regular headers
    if request.get("header"):
        for header in request["header"]:
            if header.get("disabled", False):
                continue
            
            header_key = header["key"]
            header_value = header.get("value", "")

            # Avoid re-processing 'Authorization' if it was already handled by the 'auth' section
            if header_key.lower() == "authorization" and "Authorization" in static_headers:
                continue
            
            is_security_header = any(keyword in header_key.lower() for keyword in SECURITY_KEYWORDS)
            is_dynamic_variable = is_postman_variable(header_value)

            if is_dynamic_variable:
                param_name = header_value.strip('{}')
                static_headers[header_key] = f"${param_name}"
                dynamic_headers_properties[param_name] = {
                    "type": "string",
                    "description": header.get("description", f"Header '{param_name}'.")
                }
            elif is_security_header:
                static_headers[header_key] = f"${header_key}"
                dynamic_headers_properties[header_key] = {
                    "type": "string",
                    "description": header.get("description", f"Header '{header_key}'.")
                }
            else:
                static_headers[header_key] = header_value

    if static_headers:
        tool_definition["staticInput"]["headers"] = static_headers
    
    if dynamic_headers_properties:
        tool_definition["inputSchema"]["properties"]["aint_headers"] = {
            "type": "object",
            "properties": dynamic_headers_properties
        }


    # Request Body: Define its JSON Schema within inputSchema.body
    request_body = request.get("body")
    # For GET, DELETE, HEAD requests, the body is typically absent or ignored.
    # The generic schema implies `inputSchema.body` should be absent for these methods.
    if request["method"] not in ["GET", "HEAD", "DELETE"] and request_body and request_body.get("mode"):
        
        body_schema: Any = None
        body_required_fields: List[str] = []

        if request_body["mode"] == "raw":
            # Determine content type from raw body or headers
            raw_content = request_body.get("raw", "")
            content_type = None
            
            # Check if Content-Type is already set in headers
            for header in request.get("header", []):
                if header.get("key", "").lower() == "content-type" and not header.get("disabled", False):
                    content_type = header.get("value", "")
                    break
            
            # If no Content-Type header found, try to infer from content
            if not content_type:
                try:
                    json.loads(raw_content)
                    content_type = "application/json"
                except json.JSONDecodeError:
                    # Check if it looks like XML
                    if raw_content.strip().startswith('<') and raw_content.strip().endswith('>'):
                        content_type = "application/xml"
                    else:
                        content_type = "text/plain"
            
            # Set Content-Type header if not already present
            if content_type and "Content-Type" not in static_headers:
                static_headers["Content-Type"] = content_type
            
            try:
                # Attempt to parse raw body as JSON
                json_content = json.loads(raw_content)
                if isinstance(json_content, dict):
                    # Infer a basic JSON schema for an object body
                    body_props = {}
                    for key, value in json_content.items():
                        prop_type = "string" # Default type
                        if isinstance(value, int): prop_type = "integer"
                        elif isinstance(value, float): prop_type = "number"
                        elif isinstance(value, bool): prop_type = "boolean"
                        elif isinstance(value, list): prop_type = "array"
                        elif isinstance(value, dict): prop_type = "object"
                        
                        body_props[key] = {"type": prop_type, "description": f"Field '{key}'."}
                        # If a field's value contains a Postman variable, mark it as required
                        if is_postman_variable(str(value)):
                             body_required_fields.append(key)
                    
                    body_schema = {
                        "type": "object",
                        "properties": body_props,
                        "description": "JSON request body content."
                    }
                    if body_required_fields:
                        body_schema["required"] = body_required_fields
                elif isinstance(json_content, list):
                    # For a raw JSON array, provide a simplified schema
                    body_schema = {
                        "type": "array",
                        "items": {"type": "object"}, # Placeholder items type; can be refined
                        "description": "JSON array request body content."
                    }
                else:
                    # Raw content that is not a JSON object or array (e.g., number, boolean, plain string)
                    body_schema = "string" # Adhering to the 'oneOf' for body schema
            except json.JSONDecodeError:
                # Handle non-JSON content types
                if content_type and content_type.startswith('text/'):
                    body_schema = {
                        "type": "string",
                        "description": f"{content_type} body content"
                    }
                elif content_type and (content_type.startswith('application/xml') or content_type.startswith('text/xml')):
                    body_schema = {
                        "type": "string",
                        "description": "XML body content"
                    }
                elif content_type and (content_type.startswith('application/octet-stream') or 
                                    content_type.startswith('image/') or 
                                    content_type.startswith('video/') or 
                                    content_type.startswith('audio/')):
                    body_schema = {
                        "type": "string",
                        "format": "binary",
                        "description": f"{content_type} binary content"
                    }
                else:
                    # Generic fallback for unknown content types
                    body_schema = {
                        "type": "string",
                        "description": f"{content_type or 'Raw'} body content"
                    }

        elif request_body["mode"] == "urlencoded" and request_body.get("urlencoded"):
            # Set Content-Type header for URL-encoded form data
            static_headers["Content-Type"] = "application/x-www-form-urlencoded"
            
            # Infer schema for URL-encoded form data
            body_props = {}
            for item in request_body["urlencoded"]:
                if not item.get("disabled", False):
                    prop_type = "string" # Default type
                    body_props[item["key"]] = {"type": prop_type, "description": f"URL-encoded field '{item['key']}'."}
                    if is_postman_variable(item.get("value", "")):
                        body_required_fields.append(item["key"])
            body_schema = {
                "type": "object",
                "properties": body_props,
                "description": "URL-encoded request body."
            }
            if body_required_fields:
                body_schema["required"] = body_required_fields

        elif request_body["mode"] == "formdata" and request_body.get("formdata"):
            # Set Content-Type header for multipart form data
            static_headers["Content-Type"] = "multipart/form-data"
            
            # Infer schema for multipart form data
            body_props = {}
            for item in request_body["formdata"]:
                if not item.get("disabled", False):
                    prop_type = "string" # Default type
                    if item.get("type") == "file":
                        prop_type = "string" # Represent file upload as a string path/identifier
                        body_props[item["key"]] = {
                            "type": prop_type, 
                            "format": "binary",
                            "description": f"File upload field '{item['key']}'."
                        }
                    else:
                        body_props[item["key"]] = {"type": prop_type, "description": f"Form-data field '{item['key']}'."}
                    if is_postman_variable(item.get("value", "")):
                        body_required_fields.append(item["key"])
            body_schema = {
                "type": "object",
                "properties": body_props,
                "description": "Multipart form-data request body."
            }
            if body_required_fields:
                body_schema["required"] = body_required_fields
        
        if body_schema:
            tool_definition["inputSchema"]["properties"]["aint_body"] = body_schema
    
    # --- Final Cleanup ---
    # Remove staticInput.headers if empty
    if not tool_definition["staticInput"].get("headers"):
        tool_definition["staticInput"].pop("headers", None)
    
    # Remove staticInput.url.query and port if empty
    if not tool_definition["staticInput"]["url"].get("query"):
        tool_definition["staticInput"]["url"].pop("query", None)
    if not tool_definition["staticInput"]["url"].get("port"):
        tool_definition["staticInput"]["url"].pop("port", None)
    
    # Remove inputSchema if its 'properties' are empty after processing
    if not tool_definition["inputSchema"].get("properties"):
        tool_definition.pop("inputSchema", None)
    else:
        # Remove any empty categories from inputSchema.properties (e.g., if no dynamic query params)
        for key in list(tool_definition["inputSchema"]["properties"].keys()):
            if not tool_definition["inputSchema"]["properties"][key]:
                tool_definition["inputSchema"]["properties"].pop(key)
        # If properties becomes empty after this cleanup, then remove inputSchema entirely
        if not tool_definition["inputSchema"]["properties"]:
            tool_definition.pop("inputSchema", None)
        
    return tool_definition






def process_postman_items(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recursively processes Postman items, handling both individual requests and folders.
    """
    tool_definitions = []
    for item in items:
        # Check if the item is a folder (contains 'item' key)
        if "item" in item and isinstance(item["item"], list):
            tool_definitions.extend(process_postman_items(item["item"]))
        # Check if the item is a request (contains 'request' key)
        elif "request" in item:
            try:
                tool_definition = convert_postman_item_to_tool_definition(item)
                tool_definitions.append(tool_definition)
            except Exception as e:
                # Provide more context in the error message
                item_name = item.get("name", "Unnamed")
                print(f"Skipping item '{item_name}' due to an error: {e}")
    return tool_definitions


if __name__ == "__main__":
    # Path to the Postman collection JSON file
    file_path = '/Users/jingnan.zhou/workspace/aintegrator/integrator/data/external_connection.postman_collection.json'
    #file_path = "/Users/jingnan.zhou/workspace/aintegrator/docs/openapi/servicenow/ServiceNow.postman_collection.json"
    try:
        with open(file_path, 'r') as f:
            collection = json.load(f)
        
        # Extract and process items from the collection
        items = collection.get("item", [])
        all_tool_definitions = process_postman_items(items)

        # Output the generated JSON object in a JSON code block
        print(json.dumps(all_tool_definitions, indent=4))

    except FileNotFoundError:
        print(f"Error: The file '{file_path}' was not found.")
    except json.JSONDecodeError:
        print(f"Error: The file '{file_path}' is not a valid JSON file.")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
