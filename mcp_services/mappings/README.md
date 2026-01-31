# Mapping Instruction

## Target Specification

name

description

protocol:

    (1) type: http 
    (2) url
    (3) method
    (4) params
    (5)header
    (6)body_type: key_value; json; binary; text

inputschema

    body_type=json:
        "input_schema": {
            "type": "object",
            "description": "Schema defining the tool's input",
            "properties": {
            "section_a": {
                "type": "object",
                "description": "Group A input parameters",
                "properties": {
                "field_a1": {
                    "type": "string",
                    "description": "String input value"
                },
                "field_a2": {
                    "type": "integer",
                    "description": "Integer input value"
                }
                },
                "required": ["field_a1"]
            }
            }
        }
    body_type=key_value:
        "input_schema": {
            "type": "object",
            "description": "Schema defining the tool's input",
            "properties": {
            "key1": {
                "type": "string", or "integer"
                "description": "value1"
            },
            "required": ["key1"]
            
            }
        }    

    body_type=binary:
        "input_schema": {
            "type": "object",
            "description": "Schema defining the tool's input",
            "properties": {
            "binary": {
                "type": "string", 
                "description": "base64 encoded value"
            },
            "required": ["binary"]
            
            }
        }    
    body_type=text:
        "input_schema": {
            "type": "object",
            "description": "Schema defining the tool's input",
            "properties": {
            "text": {
                "type": "string", 
                "description": "description for text"
            },
            "required": ["text"]
            
            }
        } 

Output_schema
Annotations

