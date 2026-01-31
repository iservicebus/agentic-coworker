
import asyncio
import json
from integrator.utils.queue.queue_factory import get_queue_manager, QueueMessage
from integrator.tools.tool_ingestion import start_tool_listener, stop_tool_listener
from integrator.utils.logger import get_logger

# Configure logging
logger = get_logger(__file__)


async def example_message_processor_with_args(message: QueueMessage, prefix: str, multiplier: int, config: dict) -> bool:
    """Example message processor that demonstrates additional arguments functionality."""
    task_id = message.data.get('task_id', 0)
    result = task_id * multiplier
    
    logger.info(f"{prefix}: Processing message {message.id}")
    logger.info(f"  Task ID: {task_id}, Multiplier: {multiplier}, Result: {result}")
    logger.info(f"  Config: {config}")
    logger.info(f"  Message data: {message.data}")
    
    print(f"{prefix}: Processing message {message.id} with data: {message.data}")
    print(f"  Calculated result: {task_id} * {multiplier} = {result}")
    print(f"  Config: {config}")
    
    # Simulate processing time
    await asyncio.sleep(0.1)
    
    # Simulate occasional failures (10% failure rate for demo)
    import random
    if random.random() < 0.1:
        print(f"Simulated failure for message: {message.id}")
        return False
    
    print(f"Successfully processed message: {message.id}")
    return True


async def test_basic_callback_with_args():
    """Test basic callback functionality with additional arguments."""
    print("🔍 Testing basic callback with additional arguments")
    
    # Create queue manager with 3 concurrent callbacks for testing
    queue_manager = get_queue_manager(
        stream_name="TEST_CALLBACK_QUEUE",
        max_concurrent_callbacks=3
    )
    
    try:
        # Purge any existing messages
        print("🧹 Purging existing messages...")
        await queue_manager.purge_all_messages()
        
        # Subscribe with callback and additional arguments
        print("📋 Setting up subscription with additional arguments...")
        config = {"timeout": 30, "retry_count": 3, "mode": "test"}
        subscription_id = await queue_manager.start_background_subscriber(
            example_message_processor_with_args,
            "TEST_PREFIX",  # prefix (positional arg)
            5,              # multiplier (positional arg)
            config=config   # config (keyword arg)
        )
        print(f"✅ Created subscription: {subscription_id}")
        
        # Wait a moment for subscription to be ready
        await asyncio.sleep(1)
        
        # Publish test messages
        print("📤 Publishing test messages...")
        message_ids = []
        for i in range(5):
            msg_id = await queue_manager.publish(
                subject="test.callback",
                data={"task_id": i + 1, "description": f"Test message {i + 1}"}
            )
            message_ids.append(msg_id)
            print(f"✅ Published message: {msg_id}")
        
        # Wait for processing
        print("⏳ Waiting for message processing...")
        await asyncio.sleep(5)
        
        # Check message counts
        counts = await queue_manager.get_message_counts()
        print(f"📊 Message counts: {counts}")
        
        # Clean up
        await queue_manager.unsubscribe(subscription_id)
        await queue_manager.disconnect()
        
        return counts.get("success", 0) >= 4  # Allow for 1 simulated failure
        
    except Exception as e:
        print(f"❌ Basic callback test failed: {e}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return False


async def test_tool_ingestion_callback():
    """Test the tool ingestion callback functionality."""
    print("🔍 Testing tool ingestion callback functionality")
    
    try:
        # Start the tool listener
        print("📋 Starting tool listener...")
        await start_tool_listener()
        print("✅ Tool listener started")
        
        # Wait a moment for the listener to be ready
        await asyncio.sleep(2)
        
        # Create a separate queue manager to publish test messages
        publisher = get_queue_manager(
            stream_name="TOOL_INGESTION_QUEUE",
            max_concurrent_callbacks=5
        )
        
        # Purge any existing messages
        print("🧹 Purging existing messages...")
        await publisher.purge_all_messages()
        
        # Create test tool data that matches the ToolRequest schema
        test_tool_data = {
            "tool": {
                "name": "test_calculator",
                "description": "A simple calculator tool for basic arithmetic operations",
                "meta_data": {
                    "category": "Mathematics",
                    "capability": "Calculation",
                    "description": "Performs basic arithmetic calculations like addition, subtraction, multiplication, and division",
                    "inputs": "Two numbers and an operation type",
                    "outputs": "The result of the arithmetic operation"
                }
            },
            "tenant_name": "default",     # Use default tenant
            "username": "test-user"       # Add username field
        }
        
        # Publish test tool requests
        print("📤 Publishing test tool requests...")
        message_ids = []
        for i in range(3):
            # Modify the tool name for each request
            tool_data = test_tool_data.copy()
            tool_data["tool"]["name"] = f"test_calculator_{i}"
            tool_data["tool"]["description"] = f"Calculator tool #{i} for testing"
            
            msg_id = await publisher.publish(
                subject="tool.ingest",
                data=tool_data
            )
            message_ids.append(msg_id)
            print(f"✅ Published tool request: {msg_id}")
        
        # Wait for processing - tool ingestion can take several minutes
        print("⏳ Waiting for tool ingestion processing (this may take several minutes)...")
        await asyncio.sleep(30)  # Give more time for tool ingestion - up to 30 seconds for test
        
        # Check final message counts
        counts = await publisher.get_message_counts()
        print(f"📊 Final message counts: {counts}")
        
        # Check individual message statuses
        print("📋 Individual message statuses:")
        for msg_id in message_ids:
            status = publisher.get_message_status(msg_id)
            print(f"  Message {msg_id}: {status}")
        
        await publisher.disconnect()
        
        # Determine if test passed
        success_count = counts.get("success", 0)
        failure_count = counts.get("failure", 0)
        expected_count = len(message_ids)
        
        print(f"\n📊 Tool Ingestion Test Results:")
        print(f"  Expected: {expected_count} messages")
        print(f"  Successful: {success_count}")
        print(f"  Failed: {failure_count}")
        
        return success_count > 0  # At least some should succeed
        
    except Exception as e:
        print(f"❌ Tool ingestion test failed: {e}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")
        return False
        
    finally:
        # Clean up
        try:
            await stop_tool_listener()
            print("🔌 Tool listener stopped")
        except Exception as e:
            print(f"Error stopping tool listener: {e}")


async def main():
    """Main test function"""
    print("🚀 NATS JetStream Queue Manager - Enhanced Callback Testing")
    
    try:
        # Test 1: Basic callback with additional arguments
        print("\n" + "="*60)
        print("TEST 1: Basic Callback with Additional Arguments")
        print("="*60)
        
        basic_test_passed = await test_basic_callback_with_args()
        print(f"✅ Basic callback test: {'PASSED' if basic_test_passed else 'FAILED'}")
        
        # Test 2: Tool ingestion callback
        print("\n" + "="*60)
        print("TEST 2: Tool Ingestion Callback")
        print("="*60)
        
        tool_test_passed = await test_tool_ingestion_callback()
        print(f"✅ Tool ingestion test: {'PASSED' if tool_test_passed else 'FAILED'}")
        
        # Overall results
        print("\n" + "="*60)
        print("OVERALL TEST RESULTS")
        print("="*60)
        
        if basic_test_passed and tool_test_passed:
            print("🎉 ALL TESTS PASSED! Enhanced callback functionality is working correctly.")
        elif basic_test_passed:
            print("⚠️  PARTIAL SUCCESS: Basic callbacks work, but tool ingestion has issues.")
        elif tool_test_passed:
            print("⚠️  PARTIAL SUCCESS: Tool ingestion works, but basic callbacks have issues.")
        else:
            print("❌ ALL TESTS FAILED! There are issues with the callback functionality.")
            
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        import traceback
        print(f"Full error: {traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
