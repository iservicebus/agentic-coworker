import json
import difflib

def preprocess_keys(data: any) -> any:
    """
    Recursively traverses a Python object (from JSON) and standardizes the keys
    in all dictionaries by replacing '.' and '-' with '_'.

    Args:
        data: The input data (dict, list, or primitive).

    Returns:
        The data with its dictionary keys standardized.
    """
    if isinstance(data, dict):
        # Create a new dictionary to avoid issues while iterating
        new_dict = {}
        for key, value in data.items():
            # Standardize the current key
            new_key = key.replace('.', '_').replace('-', '_')
            # Recursively process the value
            new_dict[new_key] = preprocess_keys(value)
        return new_dict
    
    if isinstance(data, list):
        # Recursively process each item in the list
        return [preprocess_keys(item) for item in data]
    
    # Return primitives as-is
    return data


def transform_json_with_schema(input_data: any, schema: dict, similarity_cutoff: float = 0.8) -> any:
    """
    Recursively transforms input JSON to conform to a JSON schema, using difflib
    for fuzzy matching of field names. (This function is the same as before).
    """
    if not schema or input_data is None:
        return None

    schema_type = schema.get('type')

    # --- Handle Objects ---
    if schema_type == 'object':
        if not isinstance(input_data, dict):
            return None

        output_object = {}
        schema_properties = schema.get('properties', {})
        input_keys = list(input_data.keys())

        for schema_key, sub_schema in schema_properties.items():
            matches = difflib.get_close_matches(schema_key, input_keys, n=1, cutoff=similarity_cutoff)
            
            if matches:
                original_input_key = matches[0]
                input_value = input_data[original_input_key]
                transformed_value = transform_json_with_schema(input_value, sub_schema, similarity_cutoff)
                
                if transformed_value is not None:
                    output_object[schema_key] = transformed_value
                    
        return output_object if output_object else None

    # --- Handle Arrays ---
    elif schema_type == 'array':
        if not isinstance(input_data, list):
            return None

        output_array = []
        item_schema = schema.get('items', {})
        for item in input_data:
            transformed_item = transform_json_with_schema(item, item_schema, similarity_cutoff)
            if transformed_item is not None:
                output_array.append(transformed_item)
                
        return output_array

    # --- Handle Primitive Types ---
    else:
        try:
            if schema_type == 'integer': return int(input_data)
            elif schema_type == 'number': return float(input_data)
            elif schema_type == 'boolean':
                if isinstance(input_data, str):
                    return input_data.lower() in ('true', '1', 't', 'y', 'yes')
                return bool(input_data)
            elif schema_type == 'string': return str(input_data)
        except (ValueError, TypeError):
            return None
        return input_data


# --- Example Usage ---

if __name__ == "__main__":
    # 1. DEFINE THE TARGET JSON SCHEMA (using snake_case)
    target_schema = {
        "type": "object",
        "properties": {
            "user_id": {"type": "integer"},
            "user_name": {"type": "string"},
            "contact_info": {
                "type": "object",
                "properties": {
                    "email_address": {"type": "string"}
                }
            },
            "order_history": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "item_id": {"type": "string"},
                        "price_per_unit": {"type": "number"}
                    }
                }
            }
        }
    }

    # 2. PROVIDE INPUT DATA THAT USES DOTS, HYPHENS, AND HAS TYPOS
    input_json_data_with_dots = {
        "user.id": 9876,
        "userName": "JaneDoe", # A typo difflib will catch (userName vs user_name)
        "contact-info": {      # Uses a hyphen
            "email.addr": "jane.doe@example.com" # Uses a dot and an abbreviation
        },
        "order.hist": [      # Uses a dot and an abbreviation
            {
                "item-ID": "PROD-A", # Uses hyphen and PascalCase
                "price.per.unit": 19.99
            }
        ],
        "extra-field": "This should be ignored"
    }
    
    # 3. RUN THE TWO-STEP TRANSFORMATION
    
    # Step 3.1: Pre-process the keys to handle '.' and '-'
    print("--- Step 1: Pre-processing Input Data ---")
    preprocessed_input = preprocess_keys(input_json_data_with_dots)
    print(json.dumps(preprocessed_input, indent=2))
    
    # Step 3.2: Run the fuzzy transformation on the pre-processed data
    # We can use a higher cutoff now because the most obvious differences are gone.
    print("\n--- Step 2: Running Fuzzy Transformation ---")
    regenerated_data = transform_json_with_schema(preprocessed_input, target_schema, similarity_cutoff=0.8)

    # 4. PRINT THE FINAL RESULTS
    print("\n\n--- Original Input Data ---")
    print(json.dumps(input_json_data_with_dots, indent=2))
    
    print("\n\n--- Final Regenerated JSON Conforming to Schema ---")
    if regenerated_data:
        print(json.dumps(regenerated_data, indent=2))
    else:
        print("Transformation failed or resulted in empty data.")