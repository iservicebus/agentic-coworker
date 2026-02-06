"""Test script for get_capabilities_with_tool_and_skill_count function."""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integrator.domains.domain_db_crud import get_capabilities_with_tool_and_skill_count, get_domains_with_tool_count
from integrator.utils.db import get_db_cm


def test_capabilities_for_domain():
    """Test getting capabilities with tool and skill counts for a specific domain."""
    print("\n=== Testing get_capabilities_with_tool_and_skill_count() ===")
    
    with get_db_cm() as sess:
        # First, get a domain with tools
        domains = get_domains_with_tool_count(sess)
        
        if not domains:
            print("No domains found in the database.")
            return
        
        # Test with the domain that has the most tools
        test_domain = domains[0]['domain_name']
        print(f"\nTesting with domain: {test_domain}")
        print(f"Domain has {domains[0]['tool_count']} tools total")
        
        results = get_capabilities_with_tool_and_skill_count(sess, test_domain)
        
        print(f"\nFound {len(results)} capabilities in domain '{test_domain}':")
        print("-" * 80)
        print(f"{'Capability Name':<50} | {'Tools':>6} | {'Skills':>6}")
        print("-" * 80)
        for item in results:
            print(f"{item['capability_name']:<50} | {item['tool_count']:>6} | {item['skill_count']:>6}")
        print("-" * 80)
        
        # Test with another domain
        if len(domains) > 1:
            test_domain2 = domains[1]['domain_name']
            print(f"\n\nTesting with another domain: {test_domain2}")
            print(f"Domain has {domains[1]['tool_count']} tools total")
            
            results2 = get_capabilities_with_tool_and_skill_count(sess, test_domain2)
            
            print(f"\nFound {len(results2)} capabilities in domain '{test_domain2}':")
            print("-" * 80)
            print(f"{'Capability Name':<50} | {'Tools':>6} | {'Skills':>6}")
            print("-" * 80)
            for item in results2:
                print(f"{item['capability_name']:<50} | {item['tool_count']:>6} | {item['skill_count']:>6}")
            print("-" * 80)
        
        return results


def main():
    """Run all tests."""
    try:
        results = test_capabilities_for_domain()
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
