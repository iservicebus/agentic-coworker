"""Test script for get_domains_with_tool_count function."""
import sys
import os

# Add the src directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from integrator.domains.domain_db_crud import get_domains_with_tool_count
from integrator.utils.db import get_db_cm


def test_all_domains():
    """Test getting all domains with tool counts."""
    print("\n=== Testing get_domains_with_tool_count() - All Domains ===")
    
    with get_db_cm() as sess:
        results = get_domains_with_tool_count(sess)
        
        print(f"\nFound {len(results)} domains:")
        print("-" * 100)
        for item in results:
            desc = item['description'][:50] + "..." if len(item['description']) > 50 else item['description']
            print(f"Domain: {item['domain_name']:30} | Tools: {item['tool_count']:3} | Desc: {desc}")
        print("-" * 100)
        
        return results


def test_agent_domains():
    """Test getting domains filtered by agent_id."""
    print("\n=== Testing get_domains_with_tool_count(agent_id) - Agent-Specific Domains ===")
    
    # First, let's get a sample agent_id from the database
    from integrator.iam.iam_db_model import Agent
    from sqlalchemy import select
    
    with get_db_cm() as sess:
        # Get the first agent from the database
        agent = sess.execute(select(Agent).limit(1)).scalar_one_or_none()
        
        if not agent:
            print("No agents found in the database. Skipping agent-specific test.")
            return []
        
        agent_id = agent.agent_id
        print(f"\nTesting with agent_id: {agent_id}")
        
        results = get_domains_with_tool_count(sess, agent_id=agent_id)
        
        print(f"\nFound {len(results)} domains associated with agent '{agent_id}':")
        print("-" * 60)
        for item in results:
            print(f"Domain: {item['domain_name']:30} | Tool Count: {item['tool_count']}")
        print("-" * 60)
        
        return results


def main():
    """Run all tests."""
    try:
        # Test 1: Get all domains
        all_domains = test_all_domains()
        
        # Test 2: Get agent-specific domains
        agent_domains = test_agent_domains()
        
        print("\n=== Test Summary ===")
        print(f"Total domains with tools: {len(all_domains)}")
        print(f"Agent-specific domains: {len(agent_domains)}")
        
        if all_domains:
            print(f"\nTop domain by tool count: {all_domains[0]['domain_name']} ({all_domains[0]['tool_count']} tools)")
        
        print("\n✅ All tests completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
