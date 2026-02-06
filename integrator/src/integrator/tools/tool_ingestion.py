import json
import os
from integrator.domains.domain_llm import get_domain_by_tool, get_capbility_by_tool_domain


from integrator.tools.tool_db_crud import upsert_tool,  get_staging_service_by_id, upsert_staging_service,upsert_application, insert_capability_tools, check_tool_has_capability
from integrator.tools.tool_etcd_crud import register_single_service
from integrator.tools.schemas import  ToolRequest
from integrator.tools.tool_graph_crud import correlate_tools
from integrator.utils.db import get_db_cm
from integrator.utils.llm import Embedder, LLM
from integrator.utils.host import generate_host_id
from integrator.utils.graph import get_graph_driver, close_graph_driver
from integrator.utils.exceptions import DuplicateToolError
import asyncio
from concurrent.futures import ThreadPoolExecutor
from integrator.utils.queue.queue_factory import queue_manager, QueueMessage
from integrator.tools.schemas import ToolRequest

from integrator.utils.logger import get_logger
from integrator.utils.etcd import get_etcd_client
from integrator.utils.queue.config import nats_queue_config, ConsumerMode

# Create a custom thread pool with 1 thread for processing queue messages
# This prevents concurrency issues with NATS PUSH consumer deliver_subject binding
TOOL_PROCESSING_THREAD_POOL = ThreadPoolExecutor(
    max_workers=1,
    thread_name_prefix="tool-ingestion"
)

logger = get_logger(__name__)


# Global variables for pull mode
_pull_task = None
_pull_running = False


async def enqueue_tool( queue_manager,sess, tool_data, tenant_name, username) -> bool:
    try:
        tool_id = tool_data.get("id")

        staging_id=None
        if tool_id:
            existing_staging = get_staging_service_by_id(sess, tool_id)
        else:
            existing_staging=None    

        if existing_staging:
                staging_id=existing_staging.id


        logger.info(f"Enqueuing tool for tool name: {tool_id}")
                # Create tool schema
                
        # Create ingestion request
        request = ToolRequest(
            tool_dict=tool_data,
            tenant_name=tenant_name,
            username=username,
            staging_id=staging_id
        )
                
        # Serialize the request and enqueue it
        payload = request.model_dump_json()
        task_id = await queue_manager.publish(payload)
                
        logger.info(f"✓ Tool enqueued successfully: {tool_id}, Task ID: {task_id}")
        return True       
    except Exception as e:
        error_count += 1
        logger.error(
            f"✗ Failed to enqueue tool: {tool_data.get('name', 'unknown')}",
            error=str(e)
        )
        return False

def ingest_tool(etcd_client, sess, gsess, emb, llm, tenant_name, tool_data, username: str, routing_overwrite=True, metadata_overwrite=True):
    try:
        tool_name = tool_data.get("name")
        logger.info(f"\n Ingesting tool: {tool_name}")

        update, tool=upsert_tool(etcd_client, sess, emb, llm,  tool_data, tenant_name)

        # insert_tool_skills(sess, tool, selected)
        register_single_service(etcd_client,sess,tenant_name,tool.id, tool_data,routing_overwrite, metadata_overwrite)
        sess.flush()
        # url_dict = tool_data.get("staticInput", {}).get("url")
        # if url_dict:
        #     host_id, base_url, _ = generate_host_id(url_dict)
        #     logger.info(f"update or insert application : {host_id} for tenant: {tenant_name}")
        #     # Pass etcd_client, db, tenant_name, service_data_item, and username
        #     app_data = {
        #         "app_name": host_id,
        #         "app_note": base_url
        #     }
        #     upsert_application(sess, app_data, tenant_name)
        #     logger.info(f"inserted or updated application for tool name: {tool_name}. app_name: {host_id}")

        sess.flush()
        sess.commit()


        #if not update:
        if check_tool_has_capability(sess, tool):
            return tool
        target = tool.canonical_data


        domain=get_domain_by_tool(sess, llm, tenant_name, target)
        domain_name=domain.get("domain_name", "")

        cap=get_capbility_by_tool_domain(sess, llm, tenant_name, domain_name, target)
        capability_name=cap.get("capability_name")

        if not capability_name:
            raise Exception("capability is not found")
        insert_capability_tools(sess, capability_name, [tool])


        # domains = get_domains_by_description(
        #     sess,
        #     emb,
        #     q=target.get("domain") or target.get("Domain") or target.get("category") or target.get("Category"),
        #     k=3,
        # )
        # domain_names=[domain["name"] for domain in domains]
        # #print(domain_names, "\n")
        # caps = get_capabilities_by_query(
        #     sess,
        #     emb,
        #     q=target.get("capability") or target.get("Capability"),
        #     domain_names=domain_names,
        #     k=5,
        # )
        # cap_names=[cap["name"] for cap in caps]
        # #print(cap_names, "\n") 

        # candidates=nearest_ops(sess, emb, q=target.get("description") or target.get("Description"), inputs=target.get("inputs") or target.get("Inputs"), outputs=target.get("outputs") or target.get("Outputs"), capability_names=cap_names, k=10)
        # #print(candidates)
        # selected= rerank_operations(candidates, target, llm)
        # print(selected)


        # insert_tool_skills(sess, tool, selected)
        sess.flush()
        sess.commit()

        #build skills
        correlate_tools(gsess, sess,llm, emb, tenant_name, domain_name, capability_name, tool)

        return tool
        # Example usage of insert_tool_operations:
        # insert_tool_operations(sess, tool, selected)
    except DuplicateToolError as e:
        logger.warning(f"Duplicate tool detected: {tool_data.get('name', 'unknown')}, error: {str(e)}")
        return None
    except Exception as e:
        logger.error(f"Failed to ingest tool: {tool_data.get('name', 'unknown')}, error: {str(e)}")
        



async def process_tool_request(message: QueueMessage, emb, llm, etcd_client) -> bool:
    """
    Async callback function that processes tool requests without blocking the event loop.
    Uses asyncio.to_thread to run blocking operations in a thread pool.
    Designed to handle long-running operations that can take minutes to complete.
    
    Args:
        message: QueueMessage containing the tool request
        emb: Embedder instance for text embeddings
        llm: LLM instance for language model operations
    """
    start_time = asyncio.get_event_loop().time()
    tool_name = "unknown"
    
    try:
        # The message.data is already a dict, not a JSON string
        # Parse the message data from the QueueMessage object
        if isinstance(message.data, str):
            # If it's a string, parse it as JSON
            message_data = json.loads(message.data)
        else:
            # If it's already a dict, use it directly
            message_data = message.data
            
        request = ToolRequest.model_validate(message_data)
        tool_dict = request.tool_dict
        tenant_name = request.tenant_name        
        tool_name = tool_dict.get('name', 'unknown')
        username=request.username
        staging_id=request.staging_id

        logger.info(f"Starting tool ingestion, tool_name: {tool_name}, tenant_name: {tenant_name}")
        logger.info(f"Message ID: {message.id}, this operation may take several minutes...")


        # Run the blocking operations in a thread pool to avoid blocking the event loop
        def blocking_ingest_tool():
            try:

                driver = get_graph_driver()

                # Use database context manager properly for each request
                with get_db_cm() as sess, driver.session() as gsess:
                    logger.info(f"Database session acquired for tool: {tool_name}")

                    staging_service=upsert_staging_service(sess,tool_dict,tenant_name, username)
                    tool_dict["id"]=str(staging_service.id)
                    sess.commit()
                    tool = ingest_tool(etcd_client, sess, gsess,  emb, llm, tenant_name, tool_dict, username)
                    logger.info(f"Tool ingestion database operations completed for: {tool_name}")
                    sess.commit()
                    close_graph_driver()
                    return tool
            except Exception as e:
                logger.error(f"Error in blocking_ingest_tool for {tool_name}: {str(e)}")
                raise

        # Execute blocking operations in custom thread pool (limited to 5 threads)
        # This can take several minutes for complex tools
        loop = asyncio.get_event_loop()
        logger.info(f"Submitting tool ingestion to thread pool for: {tool_name}")
        
        tool = await loop.run_in_executor(TOOL_PROCESSING_THREAD_POOL, blocking_ingest_tool)
        
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        if tool:
            # Use tool_name instead of tool.name to avoid DetachedInstanceError
            logger.info(f"Tool ingestion completed successfully, tool_name: {tool_name}, processing_time: {processing_time:.2f}s")
            return True
        else:
            logger.error(f"Tool ingestion returned None for tool_name: {tool_name}, processing_time: {processing_time:.2f}s")
            return False
               
    except asyncio.CancelledError:
        logger.warning(f"Tool ingestion was cancelled for tool_name: {tool_name}")
        raise  # Re-raise to properly handle cancellation
    except Exception as e:
        end_time = asyncio.get_event_loop().time()
        processing_time = end_time - start_time
        
        try:
            if isinstance(message.data, str):
                message_data = json.loads(message.data)
            else:
                message_data = message.data
            request = ToolRequest.model_validate(message_data)
            tool_name = request.tool.name
        except:
            pass
            
        logger.error(f"Tool ingestion failed, tool_name: {tool_name}, processing_time: {processing_time:.2f}s, error: {str(e)}")
        import traceback
        logger.error(f"Full error trace: {traceback.format_exc()}")
        return False


async def pull_message_loop(emb, llm, etcd_client):
    """
    Main pull message loop that continuously polls for messages.
    This runs in the background when pull mode is enabled.
    """
    global _pull_running
    
    logger.info(f"[PULL] Starting pull message loop with batch_size={nats_queue_config.pull_batch_size}, timeout={nats_queue_config.pull_timeout}s")
    
    while _pull_running:
        try:
            # Pull messages from the consumer
            await queue_manager.pull_messages(
                nats_queue_config.pull_batch_size,
                nats_queue_config.pull_timeout,
                process_tool_request,
                emb,
                llm,
                etcd_client,
            )
                # No messages available, wait before next poll
            await asyncio.sleep(nats_queue_config.pull_polling_interval)
                
        except asyncio.CancelledError:
            logger.info("[PULL] Pull message loop cancelled")
            break
        except Exception as e:
            logger.error(f"[PULL] Error in pull message loop: {str(e)}")
            # Wait before retrying to avoid tight error loops
            await asyncio.sleep(nats_queue_config.pull_polling_intervalL)
    
    logger.info("[PULL] Pull message loop stopped")


async def start_tool_listener ():
    """Tool listener function - supports both callback and pull modes"""
    global _pull_task, _pull_running
    
    logger.info(f"🚀 Start NATS JetStream Queue Manager to listen tool subscription (mode: {nats_queue_config.consumer_mode})")
    
    try:
        # Create shared instances for embedder and LLM
        emb = Embedder()
        llm = LLM()
        etcd_client=get_etcd_client()
        
        logger.info("✅ Created shared instances: embedder, LLM, and queue manager")
        
        if nats_queue_config.consumer_mode == ConsumerMode.PULL:
            # Pull mode: Create pull consumer and start polling loop
            logger.info(f"📋 Starting PULL mode ")
            
            # Start pull message loop
            _pull_running = True
            _pull_task = asyncio.create_task(pull_message_loop(emb, llm, etcd_client))
            logger.info("✅ Started pull message loop")
            
        else:
            # Callback mode: Use existing callback subscription
            logger.info("📋 Starting CALLBACK mode with background subscriber")
            
            subscription_id = await queue_manager.start_background_subscriber(
                process_tool_request, 
                emb,                  # embedder instance
                llm,
                etcd_client                                      # LLM instance  
            )
            logger.info(f"✅ Started background subscription: {subscription_id}")
            
    except Exception as e:
        logger.error(f"❌ Tool listener failed: {e}")
        import traceback
        logger.error(f"Full error for tool listener: {traceback.format_exc()}")
        
    #finally:
        # Clean up
    #    await _queue_manager.disconnect()
    #    logger.info("🔌 Queue manager for tool listener disconnected")

async def stop_tool_listener ():
    """Tool listener function - supports both callback and pull modes"""
    global _pull_task, _pull_running
    
    logger.info(f"🚀 Stop NATS JetStream Queue Manager to listen tool subscription (mode: {nats_queue_config.consumer_mode})")
    
    try:
        if nats_queue_config.consumer_mode == ConsumerMode.PULL:
            # Stop pull mode
            logger.info("🛑 Stopping PULL mode...")
            
            # Stop the pull loop
            _pull_running = False
            
            # Cancel the pull task if it exists
            if _pull_task and not _pull_task.done():
                _pull_task.cancel()
                try:
                    await _pull_task
                except asyncio.CancelledError:
                    pass
                logger.info("✅ Pull message loop stopped")
        
        # Disconnect NATS queue manager
        if queue_manager is not None:
            await queue_manager.disconnect()
            logger.info("🔌 Queue manager for tool listener disconnected")
        
        # Shutdown the custom thread pool
        TOOL_PROCESSING_THREAD_POOL.shutdown(wait=True)
        logger.info("🔌 Tool processing thread pool shutdown completed")

    except Exception as e:
        logger.error(f"❌ Tool listener failed to stop: {e}")
        import traceback
        logger.error(f"Full error for stopping tool listener: {traceback.format_exc()}")

    
async def main():
    print("🚀 NATS JetStream Queue Manager For Tool Listner ")
    
    try:
        await start_tool_listener()
        await asyncio.Event().wait()
            
    except Exception as e:
        await stop_tool_listener()
        print(f"❌ failed: {e}")


if __name__=="__main__":
    asyncio.run(main())
