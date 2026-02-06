"""Test script for the workflows tool-counts REST API endpoint."""

import requests
import json

# Base URL for the API
BASE_URL = "http://localhost:5000"

def test_workflows_tool_counts_api():
    """Test the GET /domains/workflows/tool-counts endpoint."""
    
    endpoint = f"{BASE_URL}/domains/workflows/tool-counts"
    
    print("Testing GET /domains/workflows/tool-counts")
    print("=" * 80)
    print(f"Endpoint: {endpoint}\n")
    
    try:
        response = requests.get(endpoint)
        
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            workflows = response.json()
            print(f"\nFound {len(workflows)} workflows\n")
            
            for workflow in workflows:
                print(f"Workflow: {workflow['name']}")
                print(f"  Label: {workflow['label']}")
                print(f"  Description: {workflow['description']}")
                print(f"  Total Tool Count: {workflow['tool_count']}")
                print(f"  Workflow Steps ({len(workflow['workflow_steps'])}):")
                
                for step in workflow['workflow_steps']:
                    print(f"    - Step {step['step_order']}: {step['name']}")
                    print(f"      Label: {step['label']}")
                    print(f"      Intent: {step['intent']}")
                    print(f"      Tool Count: {step['tool_count']}")
                
                print()
            
            # Print as JSON for easier inspection
            print("\n" + "=" * 80)
            print("JSON Response:")
            print("=" * 80)
            print(json.dumps(workflows, indent=2))
            
        else:
            print(f"Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the API server.")
        print(f"Please ensure the server is running at {BASE_URL}")
    except Exception as e:
        print(f"ERROR: {str(e)}")


if __name__ == "__main__":
    test_workflows_tool_counts_api()
