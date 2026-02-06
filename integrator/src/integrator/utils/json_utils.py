import json
from jsonschema import Draft202012Validator,Draft7Validator, validate, exceptions, validators, FormatChecker

def collect_schema_errors(schema_obj):
    """Return a list of jsonschema.ValidationError objects, sorted for stability."""
    validator = Draft202012Validator(Draft202012Validator.META_SCHEMA)
    return sorted(validator.iter_errors(schema_obj), key=lambda e: list(e.path))

def error_to_dict(err):
    """Convert a jsonschema.ValidationError to a serializable dict."""
    return {
        "message": err.message,
        "path": "/".join(map(str, err.path)) or "(root)",
        "validator": err.validator,                     # e.g., 'additionalProperties'
        "validator_value": err.validator_value,         # e.g., False or enum list
        "schema_path": "/".join(map(str, err.schema_path)),
        "instance": err.instance if not isinstance(err.instance, (dict, list)) else None,
    }

def format_errors_readable(errors):
    """Make a compact, LLM-friendly text block out of the errors with actionable guidance."""
    if not errors:
        return "No errors."
    
    lines = ["JSON Schema Validation Errors - Fix Required:"]
    lines.append("=" * 50)
    
    for i, e in enumerate(errors, 1):
        path = '/'.join(map(str, e.path)) or '(root)'
        lines.append(f"\nError #{i}:")
        lines.append(f"Location: {path}")
        lines.append(f"Issue: {e.message}")
        
        # Add specific guidance based on error type
        if e.validator == 'additionalProperties':
            if e.validator_value is False:
                lines.append("Fix: Remove the unexpected properties or ensure they are allowed by the schema.")
                if hasattr(e, 'instance') and isinstance(e.instance, dict):
                    unexpected = set(e.instance.keys()) - set(e.schema.get('properties', {}).keys())
                    if unexpected:
                        lines.append(f"Unexpected properties found: {', '.join(sorted(unexpected))}")
                        lines.append(f"Allowed properties: {', '.join(sorted(e.schema.get('properties', {}).keys()))}")
                        
                        # Special guidance for nested properties issue
                        if path == 'properties' and 'properties' in unexpected:
                            lines.append("STRUCTURAL ISSUE DETECTED:")
                            lines.append("- You have nested 'properties' within 'properties'")
                            lines.append("- This suggests the JSON structure doesn't match the expected MCP input format")
                            lines.append("- MCP expects 'properties' to contain HTTP request components (path, query, headers, body)")
                            lines.append("- NOT nested schema definitions with their own 'properties' field")
        
        elif e.validator == 'required':
            lines.append(f"Fix: Add the required property '{e.validator_value}' to the object at {path}")
            
        elif e.validator == 'type':
            lines.append(f"Fix: Change the value at {path} to be of type '{e.validator_value}' instead of '{type(e.instance).__name__}'")
            
        elif e.validator == 'enum':
            lines.append(f"Fix: Change the value at {path} to one of the allowed values: {e.validator_value}")
            
        elif e.validator == 'const':
            lines.append(f"Fix: Change the value at {path} to exactly: {e.validator_value}")
            
        elif e.validator in ['minimum', 'maximum']:
            lines.append(f"Fix: Ensure the value at {path} meets the {e.validator} constraint of {e.validator_value}")
            
        else:
            lines.append(f"Fix: Ensure the value at {path} conforms to the {e.validator} constraint")
        
        # Add schema context for better understanding
        lines.append(f"Schema path: {'/'.join(map(str, e.schema_path))}")
        
        # Show current value if it's simple
        if hasattr(e, 'instance') and not isinstance(e.instance, (dict, list)):
            lines.append(f"Current value: {repr(e.instance)}")
    
    lines.append("\n" + "=" * 50)
    lines.append("Summary: Fix the above issues to make the JSON instance conform to the schema.")
    
    return "\n".join(lines)

def validate_json_schema_and_collect(instance):
    """
    Validate a JSON Schema against the Draft 2020-12 meta-schema.
    Returns: (is_valid: bool, errors_json: list[dict], errors_text: str)
    """

    errors = collect_schema_errors(instance)
    if errors:
        errors_dict = [error_to_dict(e) for e in errors]
        errors_text = format_errors_readable(errors)
        return False, errors_dict, errors_text
    else:
        return True, [], "Schema is structurally valid JSON Schema."


def validator_for(schema: dict):
    """Pick the right validator class based on the schema's $schema field."""
    try:
        cls = validators.validator_for(schema)
        cls.check_schema(schema)  # fail early if the schema itself is invalid
        return cls
    except exceptions.SchemaError as e:
        # Fall back to Draft7 if $schema is missing or unrecognized, but re-raise for true errors
        try:
            # Try the newer exception type first
            from referencing.exceptions import Unresolvable
            if isinstance(e, Unresolvable):
                raise
        except ImportError:
            # Fall back to the deprecated exception type
            if isinstance(e, exceptions.RefResolutionError):
                raise
        return Draft7Validator

def validate_instance(instance_input: str|dict, schema_input:str|dict) -> tuple[bool, list[dict], str]:
    """
    Validate a JSON instance against a JSON schema.
    
    Args:
        instance_input: Either a JSON string or a Python dict/list representing the instance
        schema_input: Either a JSON string or a Python dict representing the schema
    
    Returns:
        tuple: (is_valid: bool, errors_json: list[dict], errors_text: str)
    """
    
    # Parse instance - handle both string and object inputs
    if isinstance(instance_input, str):
        try:
            instance = json.loads(instance_input)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON syntax in instance: {e}"
            return False, [{"message": msg, "path": "(root)", "validator": "json", "schema_path": "", "instance": None}], msg
    else:
        # Assume it's already a Python object (dict, list, etc.)
        instance = instance_input

    # Parse schema - handle both string and object inputs
    if isinstance(schema_input, str):
        try:
            schema = json.loads(schema_input)
        except json.JSONDecodeError as e:
            msg = f"Invalid JSON syntax in schema: {e}"
            return False, [{"message": msg, "path": "(root)", "validator": "json", "schema_path": "", "instance": None}], msg
    else:
        # Assume it's already a Python object (dict)
        schema = schema_input

    # First validate that the instance is a valid JSON Schema (if that's what we're checking)
    # Note: This seems to be checking if the instance itself is a valid schema, which might not be intended
    # Commenting this out as it seems like we want to validate instance against schema, not validate instance as schema
    # is_valid, errors_json, errors_text = validate_json_schema_and_collect(instance)
    # if not is_valid:
    #     return is_valid, errors_json, errors_text

    # Validate instance against schema
    try:
        Validator = validator_for(schema)
        v = Validator(schema, format_checker=FormatChecker())
        errors = sorted(v.iter_errors(instance), key=lambda e: e.path)
        
        if not errors:
            return True, [], "Instance is valid according to the schema."
        else:
            # Convert validation errors to our format
            errors_dict = [error_to_dict(e) for e in errors]
            errors_text = format_errors_readable(errors)
            return False, errors_dict, errors_text
            
    except exceptions.SchemaError as e:
        msg = f"Schema error: {e}"
        return False, [{"message": msg, "path": "(root)", "validator": "schema", "schema_path": "", "instance": None}], msg
    except Exception as e:
        msg = f"Validation error: {e}"
        return False, [{"message": msg, "path": "(root)", "validator": "unknown", "schema_path": "", "instance": None}], msg





if __name__ == "__main__":


    # Load the JSON schema (the validator)
    with open("/Users/jingnan.zhou/workspace/aintegrator/integrator/config/schema/mcp_input_schema.json", "r", encoding="utf-8") as f:
        schema_str = f.read()
    
    # Load the JSON instance (the data to validate)
    with open("/Users/jingnan.zhou/workspace/aintegrator/integrator/src/integrator/utils/schema.json", "r", encoding="utf-8") as f:
        instance_str = f.read()


    is_valid, errors_json, errors_text = validate_instance(instance_str, schema_str)



    # Console-friendly output
    print(errors_text)

    # If you want machine-readable errors for the LLM:
    if not is_valid:
        print("\n--- JSON (for programmatic use) ---")
        print(json.dumps({"errors": errors_json}, ensure_ascii=False, indent=2))
