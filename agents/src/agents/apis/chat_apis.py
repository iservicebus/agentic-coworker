"""
REST API endpoints for agent chat functionality.
Provides OAuth-protected endpoints for creating sessions and chatting with agents.
"""
import os
from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.checkpoint.memory import InMemorySaver

from agents.utils.oauth import validate_token
from agents.utils.logger import get_logger
from agents.utils.llm import LLM
from agents.base.base_agent import BaseAgent
from agents.apis.session_manager import get_session_manager, ChatSession

logger = get_logger(__name__)

# Create router
chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)

# Global memory checkpointer for agent state persistence
memory = InMemorySaver()


class CreateSessionRequest(BaseModel):
    """Request model for creating a new chat session."""
    agent_id: Optional[str] = Field(None, description="Optional agent ID to associate with session")


class CreateSessionResponse(BaseModel):
    """Response model for session creation."""
    session_id: str
    thread_id: str
    user_id: str
    agent_id: Optional[str]
    created_at: str
    message: str = "Session created successfully"


class ChatMessageRequest(BaseModel):
    """Request model for sending a chat message."""
    session_id: str = Field(..., description="Session ID for the conversation")
    message: str = Field(..., description="User message to send to the agent")


class ChatMessageResponse(BaseModel):
    """Response model for chat message."""
    session_id: str
    user_message: str
    agent_response: str
    messages: List[Dict[str, Any]] = Field(default_factory=list, description="Full message history")


class SessionInfoResponse(BaseModel):
    """Response model for session information."""
    session_id: str
    user_id: str
    agent_id: Optional[str]
    thread_id: str
    created_at: str
    last_accessed: str
    metadata: Dict[str, Any]


class DeleteSessionResponse(BaseModel):
    """Response model for session deletion."""
    session_id: str
    message: str


async def get_mcp_tools(auth_token: str, agent_id: str):
    """
    Connect to MCP server and retrieve available tools.
    
    Args:
        auth_token: Bearer token for authentication
        agent_id: Agent ID for X-Agent-ID header
        
    Returns:
        List of MCP tools
        
    Raises:
        HTTPException: If connection fails
    """
    server_url = os.getenv("MCP_URL", "http://localhost:6666/sse")
    tenant = os.getenv("REALM", "default")
    
    headers = {
        "Authorization": auth_token,
        "X-Agent-ID": agent_id,
        "X-Tenant": tenant
    }
    
    _streams_context = None
    _session_context = None
    
    try:
        # Create SSE client connection
        _streams_context = sse_client(url=server_url, headers=headers)
        streams = await _streams_context.__aenter__()
        
        # Create MCP session using streams
        _session_context = ClientSession(*streams)
        session = await _session_context.__aenter__()
        
        await session.initialize()
        
        # Get tools
        tools = await load_mcp_tools(session)
        logger.info(f"Successfully loaded {len(tools)} MCP tools")
        
        return tools
        
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to MCP server: {str(e)}"
        )
    finally:
        # Cleanup
        if _session_context:
            await _session_context.__aexit__(None, None, None)
        if _streams_context:
            await _streams_context.__aexit__(None, None, None)


@chat_router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(
    request: CreateSessionRequest,
    user: dict = Depends(validate_token)
):
    """
    Create a new chat session for the authenticated user.
    
    Args:
        request: Session creation request
        user: Authenticated user information from token
        
    Returns:
        CreateSessionResponse with session details
    """
    try:
        username = user.get("preferred_username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
        
        # Get session manager
        session_manager = get_session_manager()
        
        # Create new session
        session = session_manager.create_session(
            user_id=username,
            agent_id=request.agent_id
        )
        
        logger.info(f"Created chat session {session.session_id} for user {username}")
        
        return CreateSessionResponse(
            session_id=session.session_id,
            thread_id=session.thread_id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            created_at=session.created_at.isoformat()
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to create session: {str(e)}")


@chat_router.post("/message", response_model=ChatMessageResponse)
async def send_chat_message(
    request_obj: Request,
    chat_request: ChatMessageRequest,
    user: dict = Depends(validate_token)
):
    """
    Send a message to the agent in an existing chat session.
    
    Args:
        request_obj: FastAPI request object
        chat_request: Chat message request
        user: Authenticated user information from token
        
    Returns:
        ChatMessageResponse with agent's response
    """
    try:
        username = user.get("preferred_username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
        
        # Get session manager and retrieve session
        session_manager = get_session_manager()
        session = session_manager.get_session(chat_request.session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {chat_request.session_id} not found or expired"
            )
        
        # Verify session belongs to user
        if session.user_id != username:
            raise HTTPException(
                status_code=403,
                detail="Session does not belong to authenticated user"
            )
        
        # Get agent ID (from session or user's x_agent_id)
        agent_id = session.agent_id or user.get("x_agent_id")
        if not agent_id:
            raise HTTPException(
                status_code=400,
                detail="No agent ID associated with session or user"
            )
        
        # Get authorization token
        auth_token = request_obj.headers.get("authorization")
        if not auth_token:
            raise HTTPException(status_code=401, detail="Missing authorization header")
        
        # Connect to MCP and get tools
        tools = await get_mcp_tools(auth_token, agent_id)
        
        # Initialize LLM model
        model = LLM().get_model()
        
        # Build agent with tools and memory
        agent = await BaseAgent(model, tools).build(checkpointer=memory)
        
        # Configure with thread ID from session
        config = {"configurable": {"thread_id": session.thread_id}}
        
        # Invoke agent with user message
        result = await agent.ainvoke(
            {"messages": [{"role": "user", "content": chat_request.message}]},
            config
        )
        
        # Extract agent response
        messages = result.get("messages", [])
        agent_response = ""
        
        if messages:
            last_message = messages[-1]
            if hasattr(last_message, "content"):
                agent_response = last_message.content
            elif isinstance(last_message, dict):
                agent_response = last_message.get("content", "")
        
        logger.info(f"Processed message in session {session.session_id}")
        
        # Convert messages to serializable format
        serializable_messages = []
        for msg in messages:
            if hasattr(msg, "dict"):
                serializable_messages.append(msg.dict())
            elif hasattr(msg, "model_dump"):
                serializable_messages.append(msg.model_dump())
            elif isinstance(msg, dict):
                serializable_messages.append(msg)
            else:
                serializable_messages.append({"content": str(msg)})
        
        return ChatMessageResponse(
            session_id=session.session_id,
            user_message=chat_request.message,
            agent_response=agent_response,
            messages=serializable_messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing chat message: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Failed to process message: {str(e)}")


@chat_router.get("/sessions/{session_id}", response_model=SessionInfoResponse)
async def get_session_info(
    session_id: str,
    user: dict = Depends(validate_token)
):
    """
    Get information about a specific chat session.
    
    Args:
        session_id: Session identifier
        user: Authenticated user information from token
        
    Returns:
        SessionInfoResponse with session details
    """
    try:
        username = user.get("preferred_username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
        
        # Get session manager and retrieve session
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Verify session belongs to user
        if session.user_id != username:
            raise HTTPException(
                status_code=403,
                detail="Session does not belong to authenticated user"
            )
        
        return SessionInfoResponse(
            session_id=session.session_id,
            user_id=session.user_id,
            agent_id=session.agent_id,
            thread_id=session.thread_id,
            created_at=session.created_at.isoformat(),
            last_accessed=session.last_accessed.isoformat(),
            metadata=session.metadata
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving session info: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session: {str(e)}")


@chat_router.get("/sessions", response_model=List[SessionInfoResponse])
async def list_user_sessions(
    user: dict = Depends(validate_token)
):
    """
    List all active sessions for the authenticated user.
    
    Args:
        user: Authenticated user information from token
        
    Returns:
        List of SessionInfoResponse objects
    """
    try:
        username = user.get("preferred_username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
        
        # Get session manager
        session_manager = get_session_manager()
        sessions = session_manager.get_user_sessions(username)
        
        return [
            SessionInfoResponse(
                session_id=session.session_id,
                user_id=session.user_id,
                agent_id=session.agent_id,
                thread_id=session.thread_id,
                created_at=session.created_at.isoformat(),
                last_accessed=session.last_accessed.isoformat(),
                metadata=session.metadata
            )
            for session in sessions
        ]
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to list sessions: {str(e)}")


@chat_router.delete("/sessions/{session_id}", response_model=DeleteSessionResponse)
async def delete_chat_session(
    session_id: str,
    user: dict = Depends(validate_token)
):
    """
    Delete a chat session.
    
    Args:
        session_id: Session identifier
        user: Authenticated user information from token
        
    Returns:
        DeleteSessionResponse confirming deletion
    """
    try:
        username = user.get("preferred_username")
        if not username:
            raise HTTPException(status_code=401, detail="Invalid token: username missing")
        
        # Get session manager
        session_manager = get_session_manager()
        session = session_manager.get_session(session_id)
        
        if not session:
            raise HTTPException(
                status_code=404,
                detail=f"Session {session_id} not found or expired"
            )
        
        # Verify session belongs to user
        if session.user_id != username:
            raise HTTPException(
                status_code=403,
                detail="Session does not belong to authenticated user"
            )
        
        # Delete session
        session_manager.delete_session(session_id)
        
        logger.info(f"Deleted session {session_id} for user {username}")
        
        return DeleteSessionResponse(
            session_id=session_id,
            message="Session deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to delete session: {str(e)}")
