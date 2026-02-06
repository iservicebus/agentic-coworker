"""Test script for get_workflows_with_tool_count function."""

import sys
import os
import json

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integrator.utils.db import get_db_cm
from integrator.domains.domain_db_crud import get_workflows_with_tool_count


def test_get_workflows_with_tool_count():
    """Test the get_workflows_with_tool_count function."""
    
    with get_db_cm() as sess:
        print("Testing get_workflows_with_tool_count()...")
        print("=" * 80)
        
        workflows = get_workflows_with_tool_count(sess)
        
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
        print("JSON Output:")
        print("=" * 80)
        print(json.dumps(workflows, indent=2))


if __name__ == "__main__":
    test_get_workflows_with_tool_count()
