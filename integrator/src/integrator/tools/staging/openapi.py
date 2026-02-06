


import json
import re
import requests
import yaml
from integrator.utils import host
# import copy # Using json.loads(json.dumps()) for deepcopy of JSON-like structures

class OpenAPIToToolConverter:
    def __init__(self, openapi_spec: dict = None, openapi_link: str = None):
        """
        Initializes the converter with the OpenAPI specification,
        either directly or by fetching from a link.
        # ... (rest of docstring)
        """
        if openapi_link:
            try:
                response = requests.get(openapi_link)
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                is_yaml = ('yaml' in content_type or 'yml' in content_type or
                           openapi_link.endswith(('.yaml', '.yml')))
                is_json = ('json' in content_type or
                           openapi_link.endswith('.json'))

                if is_yaml:
                    self.openapi_spec = yaml.safe_load(response.text)
                elif is_json:
                    self.openapi_spec = response.json()
                else:
                    try:
                        self.openapi_spec = response.json()
                    except json.JSONDecodeError:
                        try:
                            self.openapi_spec = yaml.safe_load(response.text)
                        except yaml.YAMLError:
                            raise ValueError(
                                "Failed to parse OpenAPI spec from link. "
                                "Content is not valid JSON or YAML."
                            )
            except requests.exceptions.RequestException as e:
                raise ValueError(f"Failed to fetch OpenAPI spec from link: {e}")
            except (json.JSONDecodeError, yaml.YAMLError) as e:
                raise ValueError(f"Failed to parse OpenAPI spec from link (tried JSON/YAML): {e}")
            except Exception as e:
                raise ValueError(f"An unexpected error occurred while processing the OpenAPI link: {e}")

        elif openapi_spec:
            self.openapi_spec = openapi_spec
        else:
            raise ValueError("Either openapi_spec (dict) or openapi_link (str) must be provided.")

        if not isinstance(self.openapi_spec, dict):
            raise ValueError(f"The final OpenAPI specification must be a dictionary, but got type {type(self.openapi_spec)}. "
                             "Ensure the link points to a single OpenAPI document object.")

    # --- Reference Resolver Methods ---
    def _resolve_pointer(self, pointer: str, document: dict) -> any:
        """
        Resolves a JSON pointer string (e.g., "#/components/schemas/MySchema")
        against a given document. Only supports local fragment identifiers.
        """
        if not pointer.startswith('#/'):
            raise ValueError(f"Unsupported reference format: {pointer}. Only '#/' fragment pointers are supported.")
        
        parts = pointer[2:].split('/')
        current = document
        for part_encoded in parts:
            part = part_encoded.replace('~1', '/').replace('~0', '~') # Decode JSON Pointer encoding
            if isinstance(current, dict):
                if part not in current:
                    raise ValueError(f"Reference not found: {pointer}. Missing key: {part}")
                current = current[part]
            elif isinstance(current, list):
                try:
                    idx = int(part)
                    if not (0 <= idx < len(current)):
                         raise ValueError(f"Reference not found: {pointer}. Index {idx} out of bounds for part: {part}")
                    current = current[idx]
                except ValueError:
                    raise ValueError(f"Reference not found: {pointer}. Invalid array index: {part}")
            else:
                raise ValueError(f"Reference not found: {pointer}. Cannot traverse part: {part} in non-dict/list item: {type(current)}")
        return current

    def _resolve_recursive(self, item: any, root_document: dict, visited_refs: set) -> any:
        """
        Recursively resolves $ref keywords within an item (dict or list).
        `root_document` is self.openapi_spec.
        `visited_refs` is used to break circular references for the current resolution path.
        Returns a new item with refs resolved, or the original item if no refs or not a dict/list.
        Makes copies of resolved content to avoid modifying the original spec and to handle
        shared components that might be resolved differently down different paths.
        """
        if isinstance(item, dict):
            if '$ref' in item:
                ref_path = item['$ref']
                if not isinstance(ref_path, str): # $ref value must be a string
                    return item # Malformed $ref, return item as is

                if ref_path in visited_refs:
                    # Circular reference detected for this specific resolution path.
                    # Return the original reference object to break the loop.
                    return item # Original item might be {'$ref': ref_path, 'description': 'original description'}

                new_visited_refs = visited_refs.copy()
                new_visited_refs.add(ref_path)

                try:
                    resolved_target = self._resolve_pointer(ref_path, root_document)
                    # Deepcopy the resolved target *before* recursively resolving its contents.
                    # This ensures that:
                    # 1. Modifications (like resolving nested $refs) don't alter the original spec tree.
                    # 2. If a shared component is referenced multiple times, each resolution path gets
                    #    its own copy to work on, preventing interference if resolution paths differ
                    #    (e.g. due to different `visited_refs` sets in deeper recursion).
                    copied_resolved_target = json.loads(json.dumps(resolved_target))
                    return self._resolve_recursive(copied_resolved_target, root_document, new_visited_refs)
                except ValueError: # Error from _resolve_pointer (e.g., ref not found, unsupported format)
                    # Could not resolve this $ref. Return the original $ref object itself.
                    return item 
            else:
                # Not a $ref dict itself, but might contain $refs in its values.
                new_dict = {}
                for key, value in item.items():
                    new_dict[key] = self._resolve_recursive(value, root_document, visited_refs)
                return new_dict
        elif isinstance(item, list):
            new_list = []
            for list_item in item:
                new_list.append(self._resolve_recursive(list_item, root_document, visited_refs))
            return new_list
        else:
            # Primitive type (or not dict/list), return as is.
            return item

    def _get_fully_resolved_schema(self, schema_object: any) -> any:
        """
        Takes a schema object and returns a new schema object with all internal $refs resolved.
        Handles non-dict/list schema_objects (e.g. boolean schemas, None) by returning them as is.
        """
        if schema_object is None or not isinstance(schema_object, (dict, list)):
            # Handles None, boolean schemas (true/false), numbers, strings.
            # These don't contain $refs themselves.
            return schema_object

        try:
            # Deepcopy the input to ensure resolution operates on a fresh copy.
            copied_schema_object = json.loads(json.dumps(schema_object))
        except (TypeError, json.JSONDecodeError):
            # Should not happen with valid JSON-like schema objects.
            # If it does, return original to avoid crashing.
            return schema_object
        
        return self._resolve_recursive(copied_schema_object, self.openapi_spec, set())

    def _get_security_params_map(self) -> dict:
        # ... (existing code) ...
        security_params_map = {}
        if 'components' in self.openapi_spec and 'securitySchemes' in self.openapi_spec['components']:
            for scheme_name, scheme_def in self.openapi_spec['components']['securitySchemes'].items():
                if scheme_def.get('type') == 'apiKey':
                    param_name = scheme_def.get('name')
                    param_in = scheme_def.get('in')
                    if param_name and param_in:
                        security_params_map[(param_name.lower(), param_in)] = True
                elif scheme_def.get('type') == 'http' and scheme_def.get('scheme') == 'bearer':
                    security_params_map[("authorization", "header")] = True
        return security_params_map


    def _get_base_url_info(self) -> dict:
        # ... (existing code) ...
        servers = self.openapi_spec.get('servers', [])
        if not servers:
            return {'protocol': 'http', 'host': ['localhost'], 'base_path': [], 'port': None}
        base_url = servers[0].get('url', '/')
        parsed_url = re.match(r'^(?P<protocol>https?):\/\/(?P<host>[^\/:]+)(?::(?P<port>\d+))?(?P<path>.*)?$', base_url)
        protocol = 'https'
        host_parts = ['api', 'example', 'com']
        base_path = []
        port = None
        if parsed_url:
            parts = parsed_url.groupdict()
            protocol = parts['protocol']
            host_parts = parts['host'].split('.')
            if parts['path']:
                base_path = [p for p in parts['path'].strip('/').split('/') if p]
            port = parts['port']
        else:
            if base_url and base_url != '/':
                base_path = [p for p in base_url.strip('/').split('/') if p]

        # Filter out placeholder segments like {protocol}:, {hostname}, {protocol}, and {port}
        # from base_path as these concepts are typically handled by dedicated fields
        # ('protocol', 'host', 'port') in the URL structure.
        segments_to_ignore = ["{protocol}:", "{hostname}", "{protocol}", "{port}"]
        filtered_base_path = [
            segment for segment in base_path if segment.lower() not in segments_to_ignore
        ]
        base_path = filtered_base_path

        return {
            'protocol': protocol, 'host': host_parts, 'base_path': base_path,
            'port': port if port else None
        }

    def _create_base_tool_def(self, operation: dict, method: str, path: str, base_url_info: dict) -> dict:
        # ... (existing code) ...
        tool_name = operation.get('operationId')
        if not tool_name:
            cleaned_path = path.strip('/').replace('/', '_').replace('{', '').replace('}', '')
            tool_name = f"{method.lower()}_{cleaned_path}" # Corrected name generation
            if not cleaned_path: # Handle case of root path '/' effectively
                tool_name = f"{method.lower()}_root"

        # Sanitize tool name to match pattern '^[a-zA-Z0-9_\.-]+$'
        tool_name = re.sub(r'[^a-zA-Z0-9_\.\-]', '', tool_name)

        description = operation.get('description') or operation.get('summary') or f"Calls the {method.upper()} {path} API endpoint."

        url={
                'protocol': base_url_info['protocol'], 'host': base_url_info['host'],
                'path': base_url_info['base_path'].copy(), 'query': {}
            }
        if base_url_info['port']:
            url["port"]=base_url_info['port']

        host_id, _, _=host.generate_host_id(url)

        tool_def = {
            'name': tool_name, 'description': description, 'transport': 'http', 'appName':host_id,
            'staticInput': {
                'method': method.upper(),
                'url': url, 'headers': {}
            }
        }
        if base_url_info['port']:
            tool_def['staticInput']['url']['port'] = base_url_info['port']
        return tool_def


    def _process_path_params(self, path: str, operation_parameters: list) -> tuple[list, list]:
        import re
        path_segments = path.strip('/').split('/')
        processed_path_segments = []
        dynamic_path_params = []

        # Helper to avoid duplicate dynamic params
        def add_dynamic_param(param_name, param_def):
            # Check if already added
            if any(p['name'] == param_name for p in dynamic_path_params):
                return
            # Resolve schema if it's a $ref
            param_openapi_schema = param_def.get('schema', {})
            resolved_schema = self._get_fully_resolved_schema(param_openapi_schema)
            # Extract info from resolved schema, with fallbacks
            schema_type = 'string'
            param_description = param_def.get('description', '') # Fallback to param's own description
            if isinstance(resolved_schema, dict):
                schema_type = resolved_schema.get('type', 'string')
                param_description = resolved_schema.get('description', param_description) # Prefer schema's description
            if schema_type == 'integer':
                schema_type = 'number'
            current_param_schema_for_tool = {
                'type': schema_type,
                'description': param_description
            }
            dynamic_path_params.append({
                'name': param_name,
                'schema': current_param_schema_for_tool,
                'required': param_def.get('required', False)
            })

        # Regex to match {param}, ${param}, or $param anywhere in the segment
        dynamic_param_pattern = re.compile(r"\{([A-Za-z0-9_]+)\}|\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)")

        all_path_vars = set()
        for segment in path_segments:
            # Find all dynamic variable patterns in the segment
            for m in dynamic_param_pattern.finditer(segment):
                param_name = m.group(1) or m.group(2) or m.group(3)
                all_path_vars.add(param_name)
                param_def = next((p for p in operation_parameters if p.get('name') == param_name and p.get('in') == 'path'), None)
                if param_def:
                    add_dynamic_param(param_name, param_def)
            # Always append the original segment (let _replace_dynamic_vars handle the replacement)
            processed_path_segments.append(segment)
        # Return all found path vars (for replacement) and only defined params (for inputSchema)
        return processed_path_segments, dynamic_path_params, all_path_vars

    def convert(self) -> list:
        tool_definitions = []
        base_url_info = self._get_base_url_info()
        security_params_map = self._get_security_params_map()

        for path, path_item in self.openapi_spec.get('paths', {}).items():
            for method, operation in path_item.items():
                if method.lower() not in ["get", "post", "put", "delete", "patch", "head", "options"]:
                    continue

                tool_def = self._create_base_tool_def(operation, method, path, base_url_info)
                static_input = tool_def['staticInput']
                
                input_schema_properties = {
                    'aint_path': {'type': 'object', 'properties': {}, 'required': []},
                    'aint_query': {'type': 'object', 'properties': {}, 'required': []},
                    'aint_headers': {'type': 'object', 'properties': {}, 'required': []},
                    'aint_body': None
                }

                operation_parameters = operation.get('parameters', [])
                path_level_parameters = path_item.get('parameters', [])
                
                # --- NEW: Resolve $ref for parameter objects ---
                def _resolve_param_object(param):
                    if isinstance(param, dict) and '$ref' in param:
                        # Resolve the parameter object itself, not just its schema
                        resolved_param = self._get_fully_resolved_schema(param)
                        # If resolution fails, fallback to original param
                        if isinstance(resolved_param, dict):
                            return resolved_param
                        else:
                            return param
                    return param

                merged_parameters_map = {}
                for p in path_level_parameters:
                    resolved_p = _resolve_param_object(p)
                    if isinstance(resolved_p, dict) and 'name' in resolved_p and 'in' in resolved_p:
                        merged_parameters_map[(resolved_p['name'], resolved_p['in'])] = resolved_p
                for p in operation_parameters:
                    resolved_p = _resolve_param_object(p)
                    if isinstance(resolved_p, dict) and 'name' in resolved_p and 'in' in resolved_p:
                        merged_parameters_map[(resolved_p['name'], resolved_p['in'])] = resolved_p
                final_operation_parameters = list(merged_parameters_map.values())

                # Unpack: processed_path_segments, dynamic_path_params, all_path_vars
                processed_path_segments, dynamic_path_params, all_path_vars = self._process_path_params(path, final_operation_parameters)


                # Apply dynamic variable replacement directly to processed_path_segments
                replaced_path_segments = [
                    self._replace_dynamic_vars(seg, all_path_vars) if isinstance(seg, str) else seg
                    for seg in processed_path_segments
                ]
                print("DEBUG: processed_path_segments =", processed_path_segments)
                print("DEBUG: replaced_path_segments =", replaced_path_segments)
                # Forced test: replace all {param}-style patterns with ${param} in all path segments
                forced_pattern = re.compile(r"\{([A-Za-z0-9_]+)\}")
                forced_replaced_segments = [
                    forced_pattern.sub(lambda m: f"${{{m.group(1)}}}", seg) if isinstance(seg, str) else seg
                    for seg in processed_path_segments
                ]
                print("DEBUG: forced_replaced_segments =", forced_replaced_segments)

                # Combine server base_path and replaced operation path segments
                combined_path_segments = base_url_info['base_path'] + replaced_path_segments
                # Remove any empty segments (e.g., from leading/trailing slashes)
                combined_path_segments = [seg for seg in combined_path_segments if seg]
                static_input['url']['path'] = combined_path_segments

                # Do NOT overwrite staticInput with another replacement pass; use the already replaced static_input
                tool_def['staticInput'] = static_input

                print("DEBUG: FINAL staticInput =", json.dumps(tool_def['staticInput'], indent=2))

                if dynamic_path_params:
                    for p in dynamic_path_params:
                        input_schema_properties['aint_path']['properties'][p['name']] = p['schema']
                        if p.get('required'):
                            input_schema_properties['aint_path']['required'].append(p['name'])
                    
                for param in final_operation_parameters:
                    param_name = param.get('name')
                    param_in = param.get('in')
                    if param_in == 'path':
                        continue

                    required = param.get('required', False)
                    is_security_param = (param_name.lower(), param_in) in security_params_map

                    if is_security_param:
                        if param_in == 'query':
                            static_input['url']['query'][param_name] = f"$"
                        elif param_in == 'header':
                            static_input['headers'][param_name] = f"$"
                    else:
                        target_prop_dict = None
                        target_required_list = None
                        if param_in == 'query':
                            target_prop_dict = input_schema_properties['aint_query']['properties']
                            target_required_list = input_schema_properties['aint_query']['required']
                        elif param_in == 'header':
                            target_prop_dict = input_schema_properties['aint_headers']['properties']
                            target_required_list = input_schema_properties['aint_headers']['required']

                        if target_prop_dict is not None:
                            param_openapi_schema = param.get('schema', {})
                            resolved_schema = self._get_fully_resolved_schema(param_openapi_schema)

                            def _convert_schema_to_json_schema(schema, fallback_description=None):
                                """
                                Recursively convert an OpenAPI schema object to a JSON schema fragment,
                                copying all relevant fields for all types.
                                """
                                if not isinstance(schema, dict):
                                    return schema
                                result = {}
                                # Copy type and description
                                if 'type' in schema:
                                    result['type'] = schema['type']
                                if 'description' in schema:
                                    result['description'] = schema['description']
                                elif fallback_description:
                                    result['description'] = fallback_description
                                # Copy common fields
                                for key in [
                                    'enum', 'format', 'pattern', 'default', 'nullable', 'readOnly', 'writeOnly',
                                    'minimum', 'maximum', 'exclusiveMinimum', 'exclusiveMaximum', 'minLength', 'maxLength',
                                    'minItems', 'maxItems', 'uniqueItems', 'multipleOf', 'example', 'title'
                                ]:
                                    if key in schema:
                                        result[key] = schema[key]
                                # Handle array
                                if schema.get('type') == 'array' and 'items' in schema:
                                    result['items'] = _convert_schema_to_json_schema(schema['items'])
                                # Handle object
                                if schema.get('type') == 'object':
                                    if 'properties' in schema:
                                        result['properties'] = {}
                                        for prop, prop_schema in schema['properties'].items():
                                            result['properties'][prop] = _convert_schema_to_json_schema(prop_schema)
                                    if 'required' in schema:
                                        result['required'] = schema['required']
                                    if 'additionalProperties' in schema:
                                        result['additionalProperties'] = schema['additionalProperties']
                                # Handle allOf, anyOf, oneOf, not
                                for comp in ['allOf', 'anyOf', 'oneOf']:
                                    if comp in schema:
                                        result[comp] = [
                                            _convert_schema_to_json_schema(subschema)
                                            for subschema in schema[comp]
                                        ]
                                if 'not' in schema:
                                    result['not'] = _convert_schema_to_json_schema(schema['not'])
                                return result

                            param_def_for_input_schema = _convert_schema_to_json_schema(
                                resolved_schema, fallback_description=param.get('description', '')
                            )
                            target_prop_dict[param_name] = param_def_for_input_schema
                            if required:
                                target_required_list.append(param_name)

                request_body_def = operation.get('requestBody', {})
                if '$ref' in request_body_def:
                    request_body_def = self._get_fully_resolved_schema(request_body_def)

                if isinstance(request_body_def, dict) and 'content' in request_body_def:
                    content_types = request_body_def.get('content', {})
                    
                    # Process all content types generically
                    for content_type, content_spec in content_types.items():
                        # Set Content-Type header for the first content type found
                        if 'Content-Type' not in static_input['headers']:
                            static_input['headers']['Content-Type'] = content_type
                        
                        # Handle schema-based content types
                        if content_spec and 'schema' in content_spec:
                            resolved_body_schema = self._get_fully_resolved_schema(content_spec['schema'])
                            input_schema_properties['aint_body'] = resolved_body_schema
                            break  # Use the first content type with a schema
                        
                        # Handle content types without explicit schemas
                        elif content_type.startswith('text/'):
                            input_schema_properties['aint_body'] = {
                                'type': 'string', 
                                'description': f'{content_type} body content'
                            }
                            break
                        elif content_type.startswith('application/octet-stream') or content_type.startswith('image/') or content_type.startswith('video/') or content_type.startswith('audio/'):
                            input_schema_properties['aint_body'] = {
                                'type': 'string', 
                                'format': 'binary',
                                'description': f'{content_type} binary content'
                            }
                            break
                        else:
                            # Generic fallback for unknown content types
                            input_schema_properties['aint_body'] = {
                                'type': 'string',
                                'description': f'{content_type} content'
                            }
                            break

                # Build the final inputSchema properties
                final_properties = {}
                
                # Process path, query, headers
                for key in ['aint_path', 'aint_query', 'aint_headers']:
                    schema_group = input_schema_properties[key]
                    # Only include the group if it has defined properties
                    if schema_group['properties']:
                        # If there are no required params in the group, remove the empty 'required' list
                        if not schema_group['required']:
                            del schema_group['required']
                        else:
                            # Sort for consistent output
                            schema_group['required'].sort()
                        final_properties[key] = schema_group
                
                # Process body
                if input_schema_properties['aint_body']:
                    final_properties['aint_body'] = input_schema_properties['aint_body']

                # Only create an inputSchema if there are any dynamic properties
                if final_properties:
                    tool_def['inputSchema'] = {
                        'type': 'object',
                        'description': operation.get('description') or operation.get('summary') or f"Dynamic inputs for {tool_def['name']}",
                        'properties': final_properties
                    }
                    
                    # The top-level 'required' array should only contain top-level properties, like 'aint_body'.
                    top_level_required = []
                    if 'aint_body' in final_properties and isinstance(request_body_def, dict) and request_body_def.get('required', False):
                        top_level_required.append('aint_body')
                    
                    if top_level_required:
                        tool_def['inputSchema']['required'] = top_level_required


                tool_definitions.append(tool_def)
        return tool_definitions

    def _replace_dynamic_vars(self, obj, path_vars):
        """
        Recursively replace dynamic variable patterns in all string values of obj
        with ${param} style. Handles {param}, ${param}, $param,
        and quoted variants like "'{param}'", '"${param}"', etc.
        Replaces even when dynamic variable is embedded within a string (e.g., DeliveryTemplates({ID})).
        Only replaces if param is in path_vars.
        Adds debug output for troubleshooting.
        """
        if isinstance(obj, dict):
            return {k: self._replace_dynamic_vars(v, path_vars) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [self._replace_dynamic_vars(i, path_vars) for i in obj]
        elif isinstance(obj, str):
            # Only replace dynamic variable patterns, do NOT remove quotes or alter other characters
            def repl(m):
                param = m.group(1) or m.group(2) or m.group(3)
                if param in path_vars:
                    print(f"DEBUG: Replacing dynamic variable '{m.group(0)}' with '${{{param}}}' in string '{obj}' (path_vars={path_vars})")
                    return f"${{{param}}}"
                else:
                    print(f"DEBUG: Found dynamic variable '{m.group(0)}' but '{param}' not in path_vars={path_vars} (string='{obj}')")
                return m.group(0)
            pattern = re.compile(
                r"\{([A-Za-z0-9_]+)\}|\$\{([A-Za-z0-9_]+)\}|\$([A-Za-z0-9_]+)"
            )
            replaced = pattern.sub(repl, obj)
            if obj != replaced:
                print(f"DEBUG: String before replacement: '{obj}', after replacement: '{replaced}' (path_vars={path_vars})")
            else:
                print(f"DEBUG: No replacement in string: '{obj}' (path_vars={path_vars})")
            return replaced
        else:
            return obj









if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        openapi_path = sys.argv[1]
    else:
#        openapi_path = 'data/support_services_openAPI.json'
#        openapi_path = 'data/google_drive_create.yaml'
        openapi_path = 'data/localhost5000.json'

    with open(openapi_path, 'r') as f:
        if openapi_path.endswith(('.yaml', '.yml')):
            try:
                openapi_spec_input = yaml.safe_load(f)
            except yaml.YAMLError as e:
                print(f"Error parsing YAML file: {e}")
                raise
        else:
            try:
                openapi_spec_input = json.load(f)
            except json.JSONDecodeError:
                # If JSON parsing fails, try YAML
                f.seek(0)  # Reset file pointer
                try:
                    openapi_spec_input = yaml.safe_load(f)
                except yaml.YAMLError as e:
                    print(f"Error parsing as both JSON and YAML: {e}")
                    raise

    # --- Execution ---
    converter = OpenAPIToToolConverter(openapi_spec_input)
    converted_tool_definitions = converter.convert()

    # Output the generated JSON tool definitions
    # The output is a JSON array, which is a single complete JSON object.
    print(json.dumps(converted_tool_definitions, indent=2))
