"""
Test script for get_roles_with_domains_and_tool_counts function.

This script tests the new function that extracts roles with domains and tool counts.
It tests both scenarios:
1. Getting all roles (agent_id=None)
2. Getting roles for a specific agent
"""

import json
import logging
from integrator.utils.db import get_db_cm
from integrator.iam.iam_db_crud import get_roles_with_domains_and_tool_counts

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def test_all_roles():
    """Test getting all roles with domains and tool counts."""
    logger.info("=" * 80)
    logger.info("TEST 1: Getting all roles with domains and tool counts")
    logger.info("=" * 80)
    
    with get_db_cm() as sess:
        try:
            roles = get_roles_with_domains_and_tool_counts(sess, agent_id=None)
            
            logger.info(f"\nFound {len(roles)} roles in total")
            
            for role in roles:
                logger.info(f"\n--- Role: {role['role_name']} ---")
                logger.info(f"  Label: {role['role_label']}")
                logger.info(f"  Type: {role['role_type']}")
                logger.info(f"  Description: {role['role_description']}")
                logger.info(f"  Total Tool Count: {role['tool_count']}")
                logger.info(f"  Number of Domains: {len(role['domains'])}")
                
                for domain in role['domains']:
                    logger.info(f"    - Domain: {domain['domain_name']}")
                    logger.info(f"      Label: {domain['domain_label']}")
                    logger.info(f"      Tool Count: {domain['tool_count']}")
            
            # Pretty print JSON output
            logger.info("\n" + "=" * 80)
            logger.info("JSON Output (All Roles):")
            logger.info("=" * 80)
            print(json.dumps(roles, indent=2))
            
            return roles
            
        except Exception as e:
            logger.error(f"Error in test_all_roles: {str(e)}", exc_info=True)
            raise


def test_agent_specific_roles(agent_id: str):
    """Test getting roles for a specific agent."""
    logger.info("\n" + "=" * 80)
    logger.info(f"TEST 2: Getting roles for agent_id: {agent_id}")
    logger.info("=" * 80)
    
    with get_db_cm() as sess:
        try:
            roles = get_roles_with_domains_and_tool_counts(sess, agent_id=agent_id)
            
            logger.info(f"\nFound {len(roles)} roles for agent '{agent_id}'")
            
            for role in roles:
                logger.info(f"\n--- Role: {role['role_name']} ---")
                logger.info(f"  Label: {role['role_label']}")
                logger.info(f"  Type: {role['role_type']}")
                logger.info(f"  Description: {role['role_description']}")
                logger.info(f"  Total Tool Count: {role['tool_count']}")
                logger.info(f"  Number of Domains: {len(role['domains'])}")
                
                for domain in role['domains']:
                    logger.info(f"    - Domain: {domain['domain_name']}")
                    logger.info(f"      Label: {domain['domain_label']}")
                    logger.info(f"      Tool Count: {domain['tool_count']}")
            
            # Pretty print JSON output
            logger.info("\n" + "=" * 80)
            logger.info(f"JSON Output (Agent: {agent_id}):")
            logger.info("=" * 80)
            print(json.dumps(roles, indent=2))
            
            return roles
            
        except Exception as e:
            logger.error(f"Error in test_agent_specific_roles: {str(e)}", exc_info=True)
            raise


def get_sample_agent_id():
    """Get a sample agent_id from the database for testing."""
    from integrator.iam.iam_db_crud import get_all_agents
    
    with get_db_cm() as sess:
        agents = get_all_agents(sess, limit=1)
        if agents:
            return agents[0].agent_id
        else:
            logger.warning("No agents found in database")
            return None


def main():
    """Main test function."""
    logger.info("Starting role tool count tests...")
    
    try:
        # Test 1: Get all roles
        all_roles = test_all_roles()
        
        # Test 2: Get roles for a specific agent
        sample_agent_id = get_sample_agent_id()
        if sample_agent_id:
            agent_roles = test_agent_specific_roles(sample_agent_id)
        else:
            logger.warning("Skipping agent-specific test - no agents found")
        
        logger.info("\n" + "=" * 80)
        logger.info("✅ All tests completed successfully!")
        logger.info("=" * 80)
        
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
