"""Stream service for managing SSE connections."""

from typing import Dict, Any, Optional
from uuid import UUID

from mcp_services.utils.logger import get_logger
from mcp_services.services import AuthService

logger = get_logger(__name__)


class StreamService:
    """Manages SSE streams and session handling."""
    
    def __init__(self, auth_service:AuthService):
        self.sse_streams: Dict[UUID, Dict[str, Any]] = {}
        self.auth_service: AuthService= auth_service
    
    def register_stream(
        self, 
        agent_id: str,
        session_id: UUID, 
        read_stream: Any, 
        write_stream: Any,
        additional_context: Optional[Dict[str, Any]] = None
    ):
        """Register SSE streams for a session."""
        stream_info = {
            'read_stream': read_stream,
            'write_stream': write_stream,
            'session_id': session_id,
            agent_id: agent_id
        }
        
        if additional_context:
            stream_info.update(additional_context)
        if not self.sse_streams.get(agent_id):
            self.sse_streams[agent_id]={}        
        self.sse_streams[agent_id][session_id] = stream_info
        logger.debug(f"Registered SSE streams for session {session_id.hex}")
    
    def unregister_stream(self, agent_id, session_id: UUID) -> bool:
        """Unregister SSE streams for a session."""
        if agent_id in self.sse_streams:
            if session_id in self.sse_streams[agent_id]:
                del self.sse_streams[agent_id][session_id]
                if len(self.sse_streams[agent_id])==0:
                    del self.sse_streams[agent_id]
                logger.debug(f"Unregistered SSE streams for session {session_id.hex}")
                return True
        return False
    
    def get_stream_info(self, agent_id) -> Optional[Dict[str, Any]]:
        """Get stream information for a session."""
        return self.sse_streams.get(agent_id, {})
    
    async def get_current_sse_streams(self, request_context) -> Optional[Dict[str, Any]]:
        """
        Get the SSE streams for the current request context.
        Returns a dict with 'read_stream', 'write_stream', and 'session_id' if available.
        Returns None if not in an SSE context or streams not found.
        """
        try:
            # Try to get session_id from query params first
            session_id_str = request_context.request.query_params.get("session_id")


            ctx_headers = dict(request_context.request.headers)
            agent_id, _ = await self.auth_service.validate_auth(ctx_headers)
            if session_id_str:
                try:
                    session_uuid = UUID(session_id_str)
                    return self.sse_streams.get(agent_id,{}).get(session_uuid)
                except ValueError:
                    logger.warning(f"Invalid session_id format: {session_id_str}")
            
            # If no session_id in query params, try to find by matching request headers
            # This is a fallback approach
            
            if agent_id:
                # Find session by matching agent_id (this is less precise but can work as fallback)
                for session_id, stream_info in self.sse_streams.items():
                    # You could store additional context in stream_info to match
                    return stream_info
            
            return None
        except Exception as e:
            logger.warning(f"Could not retrieve SSE streams from context: {e}")
            return None
    
    def get_active_sessions(self) -> Dict[UUID, Dict[str, Any]]:
        """Get all active sessions."""
        return self.sse_streams.copy()
    
    def get_session_count(self) -> int:
        """Get the number of active sessions."""
        return len(self.sse_streams)
    
    def cleanup_sessions(self):
        """Clean up all sessions (useful for shutdown)."""
        session_count = len(self.sse_streams)
        self.sse_streams.clear()
        logger.info(f"Cleaned up {session_count} SSE sessions")
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Get session statistics."""
        return {
            "active_sessions": len(self.sse_streams),
            "session_ids": [sid.hex for sid in self.sse_streams.keys()]
        }


# Global stream service instance
_stream_service: Optional[StreamService] = None

def get_stream_service(auth_service:AuthService) -> StreamService:
    """Get the global stream service instance."""
    global _stream_service
    if _stream_service is None:
        _stream_service = StreamService(auth_service)
    return _stream_service
