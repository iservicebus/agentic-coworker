from dotenv import load_dotenv
import uvicorn
import os
import asyncio
import signal
from integrator.utils.env import load_env

# Load environment variables from .env file at the very beginning.
# This ensures that all subsequent modules have access to the environment variables.

load_env()

# Now that env vars are loaded, we can safely import other modules.
from integrator.apis.api_server import app
from integrator.utils.logger import get_logger
from integrator.tools.tool_ingestion import start_tool_listener, stop_tool_listener

async def main():
    """
    Main entry point for the application.
    Starts the enhanced NATS JetStream Queue Manager with long-running operation support
    and Uvicorn server concurrently.
    
    Features:
    - Enhanced callback functionality with additional arguments support
    - Long-running operation handling (up to 10 minutes per operation)
    - Configurable concurrency control (5 concurrent tool ingestions)
    - Shared resource optimization (embedder and LLM instances)
    - Comprehensive error handling and monitoring
    """
    logger = get_logger(__name__)
    
    # Flag to track if we should shutdown
    shutdown_event = asyncio.Event()
    
    def signal_handler():
        """Handle shutdown signals gracefully"""
        logger.info("Received shutdown signal, stopping services...")
        shutdown_event.set()
    
    # Set up signal handlers for graceful shutdown
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda s, f: signal_handler())

    try:    
        port = os.getenv("INTEGRATOR_PORT", 6060) # Default to 6060 if not set
        
        logger.info("🚀 Starting Enhanced NATS JetStream Queue Manager")
        logger.info("📋 Features enabled:")
        logger.info("   • Enhanced callback functionality with additional arguments")
        logger.info("   • Long-running operation support (up to 10 minutes)")
        logger.info("   • Configurable concurrency control (5 concurrent operations)")
        logger.info("   • Shared resource optimization (embedder & LLM)")
        logger.info("   • Comprehensive error handling and monitoring")
        
        # Start the enhanced background subscriber with long-running operation support
        await start_tool_listener()
        logger.info("✅ Enhanced NATS background subscriber started successfully")
        logger.info("🔧 Configuration:")
        logger.info("   • Acknowledgment timeout: 10 minutes")
        logger.info("   • Max concurrent callbacks: 5")
        logger.info("   • Thread pool workers: 5")
        logger.info("   • Retry attempts: 3 with exponential backoff")
        
        logger.info(f"🌐 Starting integrator API server on port {port}")
        
        # Create uvicorn config optimized for long-running operations
        config = uvicorn.Config(
            "integrator.apis.api_server:app", 
            host="0.0.0.0", 
            port=int(port), 
            reload=False,  # Set to False to avoid conflicts with async event loop
            log_level="info",
            # Optimize for concurrent processing and long-running operations
            workers=1,  # Single worker to share the same event loop with NATS
            loop="asyncio",  # Use asyncio event loop
            access_log=False,  # Disable access logs for better performance
            # Increase limits for better concurrency and long operations
            limit_concurrency=1000,
            limit_max_requests=10000,
            timeout_keep_alive=30,  # Increased for long-running operations
            timeout_graceful_shutdown=60,  # Allow time for operations to complete
        )
        
        # Create and start uvicorn server
        server = uvicorn.Server(config)
        
        # Run server in a separate task so it doesn't block the event loop
        server_task = asyncio.create_task(server.serve())
        
        logger.info("✅ Both enhanced NATS subscriber and API server are running")
        logger.info("📊 System optimized for:")
        logger.info("   • Concurrent message processing with callback arguments")
        logger.info("   • Long-running tool ingestion operations")
        logger.info("   • High-throughput API requests")
        logger.info("   • Resource-efficient shared instances")
        logger.info("🎯 Ready to handle operations that can take several minutes!")
        logger.info("Press Ctrl+C to shutdown gracefully")
        
        # Wait for shutdown signal or server completion
     
        done, pending = await asyncio.wait(
            [server_task, asyncio.create_task(shutdown_event.wait())],
            return_when=asyncio.FIRST_COMPLETED
        )
        
        # Cancel any pending tasks
        for task in pending:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        
        logger.info("🛑 Shutting down services gracefully...")
        logger.info("⏳ Allowing time for long-running operations to complete...")
        
    except Exception as e:
        logger.error(f"❌ Failed to start integrator: {e}")
        import traceback
        logger.error(f"Full error: {traceback.format_exc()}")
    
    finally:
        # Always cleanup NATS connection with proper shutdown handling
        try:
            logger.info("🔌 Stopping enhanced NATS tool listener...")
            logger.info("⏳ Waiting for active operations to complete...")
            await stop_tool_listener()
            logger.info("✅ Enhanced NATS tool listener stopped successfully")
            logger.info("🧹 All resources cleaned up properly")
        except Exception as e:
            logger.error(f"❌ Error stopping tool listener: {e}")





 

if __name__ == "__main__":
    asyncio.run(main())
