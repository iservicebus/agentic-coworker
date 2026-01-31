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


from integrator.utils.oauth import validate_token
from integrator.utils.logger import get_logger


from integrator.agents.apis.session_manager import get_session_manager, ChatSession

from sqlalchemy.orm import Session
from integrator.utils.db import get_db
from integrator.iam.iam_auth import get_auth_agent

logger = get_logger(__name__)

# Create router
chat_router = APIRouter(
    prefix="/chat",
    tags=["chat"],
)




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


async def get_mcp_tools(auth_token: str, agent_id: str, tenant_name:str):
    """
    Connect to MCP server and retrieve available tools.
    
    Args:
        auth_token: Bearer token for authentication
        agent_id: Agent ID for X-Agent-ID header
        
    Returns:
        Tuple of (tools, streams_context, session_context) - contexts must be kept alive
        
    Raises:
        HTTPException: If connection fails
    """
    server_url = os.getenv("MCP_URL", "http://localhost:6666/sse")
    
    headers = {
        "Authorization": auth_token,
        "X-Agent-ID": agent_id,
        "X-Tenant": tenant_name
    }
    
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
        
        # CRITICAL: Return the contexts along with tools
        # The MCP session must stay alive for tools to work
        return tools, _streams_context, _session_context
        
    except Exception as e:
        logger.error(f"Failed to connect to MCP server: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to MCP server: {str(e)}"
        )



@chat_router.post("/sessions", response_model=CreateSessionResponse)
async def create_chat_session(
    http_request: Request,
    request: CreateSessionRequest,
    db: Session = Depends(get_db),
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


       # Get authorization token

        tenant_name=http_request.headers.get("x-tenant")
        auth_token = http_request.headers.get("authorization")
        if not auth_token or not tenant_name:
            raise HTTPException(status_code=401, detail="Missing authorization header or tenant name")


        username = user.get("preferred_username")
        agent_id, _ = get_auth_agent(db, user, tenant_name)
        if not username or not agent_id:
            raise HTTPException(status_code=404, detail=f"agent is not found for login user: {username}, or not provided. agent id must belongs to the user")
        
        # Get session manager
        session_manager = get_session_manager()
        tools, streams_context, session_context = await get_mcp_tools(auth_token, agent_id, tenant_name)     
        # Create new session
        session = await session_manager.create_session(
            user_id=username,
            agent_id=agent_id,
            tools=tools,
            mcp_streams_context=streams_context,
            mcp_session_context=session_context,
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
    db: Session = Depends(get_db),
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
        
        # Configure with thread ID from session
        config = {"configurable": {"thread_id": session.thread_id}}

        # Use the agent from the session (created during session creation)
        # This ensures the MCP connection stays alive and tools work properly
        result = await session.agent.ainvoke(
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
        
        # Delete session (now async to cleanup MCP connections)
        await session_manager.delete_session(session_id)
        
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
