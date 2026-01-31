#!/usr/bin/env python3
"""
Producer script - Enqueues tools from JSON file into NATS queue.
"""
import asyncio
import json, os
import sys
from pathlib import Path

# Import infrastructure
from integrator.utils.queue.config import nats_queue_config
from integrator.utils.logger import get_logger
from integrator.utils.queue.queue_factory import queue_manager
from integrator.tools.schemas import  ToolRequest 

TOOLS_JSON_PATH = os.path.join(os.path.dirname(__file__), "../../../../init/services_backup.json")

logger = get_logger(__name__)

async def enqueue_tools_from_file(tenant_name, username:str, file_path: str = None) -> bool:
    """
    Enqueue tools from a JSON file for processing via the queue system.
    
    Args:
        file_path: Path to the JSON file containing tools
        
    Returns:
        True if enqueuing was successful, False otherwise
    """
    
    try:
        logger.info(f"Starting tool enqueuing from file: {file_path}")
        
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        services = data.get("default", [])
        if not services:
            logger.warning("No services found in the file")
            return False
        
        success_count = 0
        error_count = 0
        
        logger.info(f"Found {len(services)} tools to enqueue")
        
        for idx, service in enumerate(services):
            try:
                tool_name = service.get("name", f"tool_{idx}")
                logger.info(f"Enqueuing tool {idx+1}/{len(services)}: {tool_name}")
                
                
                # Create ingestion request
                request = ToolRequest(
                    tool_dict=service,
                    tenant_name=tenant_name,
                    username=username
                )
                
                # Serialize the request and enqueue it
                payload = request.model_dump_json()
                task_id = await queue_manager.publish(payload, nats_queue_config.default_subject)
                success_count += 1
                
                logger.info(f"✓ Tool enqueued successfully: {tool_name}, Task ID: {task_id}")
                
            except Exception as e:
                error_count += 1
                logger.error(
                    f"✗ Failed to enqueue tool: {service.get('name', 'unknown')}",
                    error=str(e)
                )
        
        # Final summary
        logger.info("=" * 50)
        logger.info("ENQUEUING SUMMARY:")
        logger.info(f"Total tools: {len(services)}")
        logger.info(f"Successfully enqueued: {success_count}")
        logger.info(f"Failed: {error_count}")
        logger.info("=" * 50)
        
        # Show queue stats
        try:
            stats = queue_manager.get_queue_stats()
            logger.info(f"Current queue stats: {stats}")
        except Exception as e:
            logger.warning(f"Could not get queue stats: {e}")
        
        return error_count == 0
        
    except Exception as e:
        logger.error(f"Failed to enqueue tools from file: {str(e)}")
        return False

async def main():
    """Main producer function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Tool Producer - Enqueue tools into NATS")
    parser.add_argument("--file", "-f", help="Path to JSON file containing tools")
    parser.add_argument("--stats", "-s", action="store_true", help="Show queue statistics only")
    parser.add_argument("--replay", "-r",  help="Replay the failed or max delivered messages")
    parser.add_argument("--purge", "-p",  help="purge all the messages")
    parser.add_argument("--clean", "-c",  help="clean all the streams")


    args = parser.parse_args()
    #args.stats=True
    try:
        
        logger.info("Tool Producer starting up")
        logger.info(f"NATS URL: {nats_queue_config.url}")
        
        if args.stats:
            # Just show queue statistics
            try:
                stats = await queue_manager.get_message_counts()
                logger.info("Current queue statistics:")
                for status, count in stats.items():
                    logger.info(f"  {status}: {count}")
            except Exception as e:
                logger.error(f"Failed to get queue statistics: {str(e)}")
            return

        if args.replay:

            try:

                # Feature 4: Retry failed messages
                logger.info(f"\n📋 4. Retrying failed messages...")
                retried_count = await queue_manager.retry_failed_messages()
                logger.info(f"✅ Retried {retried_count} failed messages")

            except Exception as e:
                logger.error(f"Failed to retry the messages: {str(e)}")

        if args.purge:

            try:

                logger.info("\n📋 5. Purging messages...")
                await queue_manager.purge_all_messages()
                logger.info("✅ All messages purged")

            except Exception as e:
                logger.error(f"Failed to purge all the messages: {str(e)}")

        if args.clean:

            try:

                logger.info("\n📋 5. reset all the streams")
                await queue_manager.reset_streams()
                logger.info("✅ All streams are reset")

            except Exception as e:
                logger.error(f"Failed to reset all the streams: {str(e)}")



        # Enqueue tools
        success = await enqueue_tools_from_file("default", "agent-admin", TOOLS_JSON_PATH)
        
        if success:
            logger.info("✅ All tools enqueued successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Some tools failed to enqueue")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("Producer interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Producer failed with unexpected error: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
