"""
Main FastAPI server for agent chat REST API.
Provides OAuth-protected endpoints for agent chat functionality.
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from agents.utils.env import load_env
from agents.utils.logger import get_logger
from agents.apis.chat_apis import chat_router
from agents.apis.session_manager import get_session_manager

# Load environment variables
load_env()

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI application.
    Handles startup and shutdown events.
    """
    # Startup
    logger.info("Starting Agent Chat API server...")
    
    # Start session cleanup task
    session_manager = get_session_manager()
    await session_manager.start_cleanup_task(interval_minutes=10)
    logger.info("Session cleanup task started")
    
    yield
    
    # Shutdown
    logger.info("Shutting down Agent Chat API server...")
    await session_manager.stop_cleanup_task()
    logger.info("Session cleanup task stopped")


# Create FastAPI application
app = FastAPI(
    title="Agent Chat API",
    description="OAuth-protected REST API for agent chat functionality with session management",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router)


@app.get("/")
async def root():
    """Root endpoint providing API information."""
    return {
        "name": "Agent Chat API",
        "version": "1.0.0",
        "description": "OAuth-protected REST API for agent chat functionality",
        "endpoints": {
            "create_session": "POST /chat/sessions",
            "send_message": "POST /chat/message",
            "get_session": "GET /chat/sessions/{session_id}",
            "list_sessions": "GET /chat/sessions",
            "delete_session": "DELETE /chat/sessions/{session_id}"
        }
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    session_manager = get_session_manager()
    return {
        "status": "healthy",
        "active_sessions": session_manager.get_session_count()
    }


if __name__ == "__main__":
    import uvicorn
    
    host = os.getenv("HOST", "0.0.0.0")
    port = int(os.getenv("PORT", "8080"))
    
    logger.info(f"Starting server on {host}:{port}")
    
    uvicorn.run(
        "agents.apis.api_server:app",
        host=host,
        port=port,
        reload=True,
        log_level="info"
    )
