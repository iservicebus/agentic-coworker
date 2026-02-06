"""
Session management for agent chat conversations.
Handles session creation, retrieval, and cleanup with thread-safe operations.
"""
import uuid
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
import asyncio
from threading import Lock
from agents.utils.logger import get_logger

logger = get_logger(__name__)


class ChatSession:
    """Represents a single chat session with an agent."""
    
    def __init__(self, session_id: str, user_id: str, agent_id: Optional[str] = None):
        self.session_id = session_id
        self.user_id = user_id
        self.agent_id = agent_id
        self.created_at = datetime.utcnow()
        self.last_accessed = datetime.utcnow()
        self.thread_id = str(uuid.uuid4())  # LangGraph thread ID for checkpointing
        self.metadata: Dict[str, Any] = {}
        
    def update_access_time(self):
        """Update the last accessed timestamp."""
        self.last_accessed = datetime.utcnow()
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert session to dictionary representation."""
        return {
            "session_id": self.session_id,
            "user_id": self.user_id,
            "agent_id": self.agent_id,
            "thread_id": self.thread_id,
            "created_at": self.created_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat(),
            "metadata": self.metadata
        }


class SessionManager:
    """
    Manages chat sessions for multiple users.
    Provides thread-safe session creation, retrieval, and cleanup.
    """
    
    def __init__(self, session_timeout_minutes: int = 60):
        """
        Initialize the session manager.
        
        Args:
            session_timeout_minutes: Minutes of inactivity before session expires
        """
        self._sessions: Dict[str, ChatSession] = {}
        self._lock = Lock()
        self.session_timeout = timedelta(minutes=session_timeout_minutes)
        self._cleanup_task: Optional[asyncio.Task] = None
        logger.info(f"SessionManager initialized with {session_timeout_minutes} minute timeout")
        
    def create_session(self, user_id: str, agent_id: Optional[str] = None) -> ChatSession:
        """
        Create a new chat session for a user.
        
        Args:
            user_id: Unique identifier for the user
            agent_id: Optional agent identifier
            
        Returns:
            ChatSession: Newly created session
        """
        session_id = str(uuid.uuid4())
        session = ChatSession(session_id, user_id, agent_id)
        
        with self._lock:
            self._sessions[session_id] = session
            
        logger.info(f"Created session {session_id} for user {user_id}")
        return session
        
    def get_session(self, session_id: str) -> Optional[ChatSession]:
        """
        Retrieve a session by ID and update its access time.
        
        Args:
            session_id: Session identifier
            
        Returns:
            ChatSession if found and not expired, None otherwise
        """
        with self._lock:
            session = self._sessions.get(session_id)
            
            if session is None:
                logger.warning(f"Session {session_id} not found")
                return None
                
            # Check if session has expired
            if datetime.utcnow() - session.last_accessed > self.session_timeout:
                logger.info(f"Session {session_id} has expired")
                del self._sessions[session_id]
                return None
                
            session.update_access_time()
            return session
            
    def delete_session(self, session_id: str) -> bool:
        """
        Delete a session.
        
        Args:
            session_id: Session identifier
            
        Returns:
            bool: True if session was deleted, False if not found
        """
        with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Deleted session {session_id}")
                return True
            return False
            
    def get_user_sessions(self, user_id: str) -> list[ChatSession]:
        """
        Get all active sessions for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of active ChatSession objects for the user
        """
        with self._lock:
            return [
                session for session in self._sessions.values()
                if session.user_id == user_id
            ]
            
    def cleanup_expired_sessions(self) -> int:
        """
        Remove all expired sessions.
        
        Returns:
            int: Number of sessions cleaned up
        """
        now = datetime.utcnow()
        expired_sessions = []
        
        with self._lock:
            for session_id, session in list(self._sessions.items()):
                if now - session.last_accessed > self.session_timeout:
                    expired_sessions.append(session_id)
                    
            for session_id in expired_sessions:
                del self._sessions[session_id]
                
        if expired_sessions:
            logger.info(f"Cleaned up {len(expired_sessions)} expired sessions")
            
        return len(expired_sessions)
        
    async def start_cleanup_task(self, interval_minutes: int = 10):
        """
        Start a background task to periodically clean up expired sessions.
        
        Args:
            interval_minutes: Minutes between cleanup runs
        """
        async def cleanup_loop():
            while True:
                await asyncio.sleep(interval_minutes * 60)
                self.cleanup_expired_sessions()
                
        self._cleanup_task = asyncio.create_task(cleanup_loop())
        logger.info(f"Started session cleanup task (interval: {interval_minutes} minutes)")
        
    async def stop_cleanup_task(self):
        """Stop the background cleanup task."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
            logger.info("Stopped session cleanup task")
            
    def get_session_count(self) -> int:
        """Get the total number of active sessions."""
        with self._lock:
            return len(self._sessions)


# Global session manager instance
_session_manager: Optional[SessionManager] = None


def get_session_manager() -> SessionManager:
    """
    Get the global session manager instance.
    Creates one if it doesn't exist.
    
    Returns:
        SessionManager: Global session manager instance
    """
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager()
    return _session_manager
