"""
Enhanced schema parser for handling complex JSON schemas with pattern properties,
property names constraints, and other advanced features.
"""
import json
import re
from typing import Any, Dict, List, Optional, Union


def extract_property_info(schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts property information from a JSON schema, handling various scenarios:
    - Standard properties
    - Pattern properties with regex patterns
    - Property names constraints (enum, pattern)
    - Nested objects and arrays
    - Complex validation rules
    
    Args:
        schema: The JSON schema to parse
        
    Returns:
        Dictionary containing extracted property information
    """
    if not isinstance(schema, dict):
        return {}
    
    result = {
        "type": schema.get("type", "object"),
        "properties": {},
        "pattern_properties": {},
        "property_names": {},
        "additional_properties": schema.get("additionalProperties", True),
        "required": schema.get("required", []),
        "description": schema.get("description", ""),
        "constraints": {}
    }
    
    # Extract standard properties
    if "properties" in schema:
        for prop_name, prop_schema in schema["properties"].items():
            result["properties"][prop_name] = _parse_property_schema(prop_schema)
    
    # Extract pattern properties
    if "patternProperties" in schema:
        for pattern, prop_schema in schema["patternProperties"].items():
            result["pattern_properties"][pattern] = _parse_property_schema(prop_schema)
    
    # Extract property names constraints
    if "propertyNames" in schema:
        prop_names = schema["propertyNames"]
        if "enum" in prop_names:
            result["property_names"]["allowed_names"] = prop_names["enum"]
        if "pattern" in prop_names:
            result["property_names"]["pattern"] = prop_names["pattern"]
    
    # Extract constraints
    for constraint in ["minProperties", "maxProperties", "minLength", "maxLength"]:
        if constraint in schema:
            result["constraints"][constraint] = schema[constraint]
    
    return result


def _parse_property_schema(prop_schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Parse individual property schema, handling nested structures.
    """
    if not isinstance(prop_schema, dict):
        return {"type": "string", "description": ""}
    
    parsed = {
        "type": prop_schema.get("type", "string"),
        "description": prop_schema.get("description", ""),
        "required": prop_schema.get("required", False)
    }
    
    # Handle anyOf/oneOf/allOf
    if "anyOf" in prop_schema:
        parsed["anyOf"] = prop_schema["anyOf"]
    if "oneOf" in prop_schema:
        parsed["oneOf"] = prop_schema["oneOf"]
    if "allOf" in prop_schema:
        parsed["allOf"] = prop_schema["allOf"]
    
    # Handle nested objects
    if parsed["type"] == "object":
        if "properties" in prop_schema:
            parsed["properties"] = {}
            for nested_name, nested_schema in prop_schema["properties"].items():
                parsed["properties"][nested_name] = _parse_property_schema(nested_schema)
        
        if "patternProperties" in prop_schema:
            parsed["pattern_properties"] = {}
            for pattern, nested_schema in prop_schema["patternProperties"].items():
                parsed["pattern_properties"][pattern] = _parse_property_schema(nested_schema)
        
        # Handle property names constraints for nested objects
        if "propertyNames" in prop_schema:
            parsed["property_names"] = {}
            prop_names = prop_schema["propertyNames"]
            if "enum" in prop_names:
                parsed["property_names"]["allowed_names"] = prop_names["enum"]
            if "pattern" in prop_names:
                parsed["property_names"]["pattern"] = prop_names["pattern"]
        
        # Handle additionalProperties for nested objects
        if "additionalProperties" in prop_schema:
            parsed["additional_properties"] = prop_schema["additionalProperties"]
    
    # Handle arrays
    if parsed["type"] == "array" and "items" in prop_schema:
        parsed["items"] = _parse_property_schema(prop_schema["items"])
    
    # Handle constraints
    for constraint in ["minLength", "maxLength", "minimum", "maximum", "pattern", "enum"]:
        if constraint in prop_schema:
            parsed[constraint] = prop_schema[constraint]
    
    return parsed


def validate_and_transform_input(input_data: Any, schema_info: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validates and transforms input data according to the extracted schema information.
    Handles pattern properties, property name constraints, and type coercion.
    
    Args:
        input_data: The input data to validate and transform
        schema_info: Schema information extracted by extract_property_info
        
    Returns:
        Transformed and validated data
    """
    if not isinstance(input_data, dict) or schema_info.get("type") != "object":
        return input_data
    
    result = {}
    
    # Process each input key-value pair
    for key, value in input_data.items():
        processed = False
        
        # Check against standard properties first
        if key in schema_info["properties"]:
            prop_info = schema_info["properties"][key]
            result[key] = _transform_value(value, prop_info)
            processed = True
        
        # Check against pattern properties
        elif schema_info["pattern_properties"]:
            for pattern, prop_info in schema_info["pattern_properties"].items():
                if re.match(pattern, key):
                    result[key] = _transform_value(value, prop_info)
                    processed = True
                    break
        
        # Check property name constraints
        if not processed and schema_info["property_names"]:
            allowed_names = schema_info["property_names"].get("allowed_names", [])
            name_pattern = schema_info["property_names"].get("pattern")
            
            # Check if key is in allowed names
            if allowed_names and key in allowed_names:
                # Use the first pattern property schema if available
                if schema_info["pattern_properties"]:
                    first_pattern_schema = next(iter(schema_info["pattern_properties"].values()))
                    result[key] = _transform_value(value, first_pattern_schema)
                    processed = True
            
            # Check if key matches name pattern
            elif name_pattern and re.match(name_pattern, key):
                if schema_info["pattern_properties"]:
                    first_pattern_schema = next(iter(schema_info["pattern_properties"].values()))
                    result[key] = _transform_value(value, first_pattern_schema)
                    processed = True
        
        # Handle additional properties
        if not processed and schema_info["additional_properties"]:
            result[key] = value
    
    return result


def _transform_value(value: Any, prop_info: Dict[str, Any]) -> Any:
    """
    Transform a value according to property schema information.
    """
    prop_type = prop_info.get("type", "string")
    
    # Handle anyOf - try each type until one works
    if "anyOf" in prop_info:
        for any_schema in prop_info["anyOf"]:
            try:
                return _coerce_type(value, any_schema.get("type", "string"))
            except (ValueError, TypeError):
                continue
        # If none work, return original value
        return value
    
    # Handle oneOf - similar to anyOf but stricter
    if "oneOf" in prop_info:
        valid_transforms = []
        for one_schema in prop_info["oneOf"]:
            try:
                transformed = _coerce_type(value, one_schema.get("type", "string"))
                valid_transforms.append(transformed)
            except (ValueError, TypeError):
                continue
        
        # Return the first valid transformation
        if valid_transforms:
            return valid_transforms[0]
        return value
    
    # Handle nested objects
    if prop_type == "object":
        if isinstance(value, dict):
            nested_schema_info = extract_property_info(prop_info)
            return validate_and_transform_input(value, nested_schema_info)
        return value
    
    # Handle arrays
    if prop_type == "array" and isinstance(value, list):
        if "items" in prop_info:
            return [_transform_value(item, prop_info["items"]) for item in value]
        return value
    
    # Handle primitive types
    return _coerce_type(value, prop_type)


def _coerce_type(value: Any, target_type: str) -> Any:
    """
    Coerce a value to the target type.
    """
    if target_type == "string":
        return str(value)
    elif target_type == "integer":
        return int(float(value))  # Handle string numbers
    elif target_type == "number":
        return float(value)
    elif target_type == "boolean":
        if isinstance(value, str):
            return value.lower() in ("true", "1", "t", "yes", "y")
        return bool(value)
    else:
        return value


def generalized_schema_parser(input_data: Any, schema: Dict[str, Any]) -> Any:
    """
    Main function to parse and transform input data according to a JSON schema.
    This is the generalized version that handles complex schemas including:
    - Pattern properties
    - Property name constraints
    - Nested objects and arrays
    - Type coercion and validation
    
    Args:
        input_data: The input data to transform
        schema: The JSON schema to conform to
        
    Returns:
        Transformed data conforming to the schema
    """
    if not schema:
        return input_data
    
    # Extract schema information
    schema_info = extract_property_info(schema)
    
    # Transform the input data
    return validate_and_transform_input(input_data, schema_info)


# Example usage and testing
if __name__ == "__main__":
    # Test with the complex schema from the issue
    test_schema = {
        "type": "object",
        "properties": {
            "path": {
                "type": "object",
                "maxProperties": 1,
                "minProperties": 1,
                "propertyNames": {
                    "enum": ["userId"]
                },
                "patternProperties": {
                    "^userId$": {
                        "type": "string",
                        "minLength": 1,
                        "description": "The user's email address. Use the special value 'me' to indicate the authenticated user."
                    }
                },
                "additionalProperties": False
            },
            "query": {
                "type": "object",
                "patternProperties": {
                    ".*": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "boolean"}
                        ]
                    }
                },
                "additionalProperties": False
            },
            "headers": {
                "type": "object",
                "patternProperties": {
                    ".*": {
                        "anyOf": [
                            {"type": "string"},
                            {"type": "number"},
                            {"type": "boolean"}
                        ]
                    }
                },
                "additionalProperties": False
            }
        },
        "description": "Dynamic inputs for the users.getProfile endpoint.",
        "additionalProperties": False
    }
    
    # Test input data
    test_input = {
        "path": {
            "userId": "me"
        },
        "query": {
            "includeProfile": True,
            "maxResults": 10,
            "format": "json"
        },
        "headers": {
            "Accept": "application/json",
            "User-Agent": "TestClient/1.0",
            "Timeout": 30
        }
    }
    
    print("Original input:")
    print(json.dumps(test_input, indent=2))
    
    print("\nTransformed output:")
    result = generalized_schema_parser(test_input, test_schema)
    print(json.dumps(result, indent=2))
    
    print("\nSchema info extraction:")
    schema_info = extract_property_info(test_schema)
    print(json.dumps(schema_info, indent=2, default=str))
