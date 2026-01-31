import hashlib
import json
import logging
from typing import Any, Optional, Dict

from sqlalchemy import select, func
from sqlalchemy.orm import Session, noload

from mcp_services.mcp_sessions.session_db_model import McpSession, SessionContextHistory

logger = logging.getLogger(__name__)


def _hash_context(context: dict[str, Any]) -> str:
    """
    Generate a SHA256 hash of the context dictionary for change detection.
    
    Args:
        context: The context dictionary to hash
        
    Returns:
        str: Hexadecimal hash string
    """
    payload = json.dumps(context, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def upsert_mcp_session(
    sess: Session,
    *,
    session_id: Optional[str] = None,
    tenant_name: str,
    agent_id: str,
) -> McpSession:
    """
    Create or update an MCP session.
    
    If session_id is None, creates a new session.
    If session_id is provided, retrieves existing session or creates new one with that ID.
    
    The unique constraint (agent_id, tenant_name) ensures only one session per agent per tenant.
    When a session_id is provided but a session already exists for that agent+tenant combination,
    we retrieve and return the existing session instead of creating a duplicate.
    
    Args:
        sess: SQLAlchemy session
        session_id: Optional session ID (UUID string)
        tenant_name: Tenant name (required)
        agent_id: Agent ID (required)
        
    Returns:
        McpSession: The created or updated session (not committed)
    """
    try:
        if session_id is None:
            # Try to find existing session by agent_id and tenant_name
            stmt = select(McpSession).where(
                McpSession.agent_id == agent_id,
                McpSession.tenant_name == tenant_name
            )
            session = sess.execute(stmt).scalar_one_or_none()
            
            if session:
                logger.info(f"Found existing MCP session with ID: {session.id} for agent: {agent_id}, tenant: {tenant_name}")
                return session
            
            # Create new session
            session = McpSession(
                tenant_name=tenant_name,
                agent_id=agent_id
            )
            sess.add(session)
            sess.flush()  # Assigns session ID
            logger.info(f"Created new MCP session with ID: {session.id} for tenant: {tenant_name}")
            return session

        # Try to get existing session by ID
        session = sess.get(McpSession, session_id)
        if session is None:
            # Check if a session already exists for this agent+tenant combination
            stmt = select(McpSession).where(
                McpSession.agent_id == agent_id,
                McpSession.tenant_name == tenant_name
            )
            existing_session = sess.execute(stmt).scalar_one_or_none()
            
            if existing_session:
                # Return the existing session instead of creating a duplicate
                logger.info(f"Session already exists for agent {agent_id} and tenant {tenant_name} with ID: {existing_session.id}, returning existing session instead of creating new one with ID: {session_id}")
                return existing_session
            
            # Create new session with provided ID
            session = McpSession(
                id=session_id,
                tenant_name=tenant_name,
                agent_id=agent_id
            )
            sess.add(session)
            sess.flush()
            logger.info(f"Created new MCP session with provided ID: {session_id} for tenant: {tenant_name}")
            return session

        # Validate tenant ownership
        if session.tenant_name != tenant_name:
            raise ValueError(f"Session {session_id} belongs to tenant {session.tenant_name}, not {tenant_name}")

        # Update existing session
        session.agent_id = agent_id
        sess.flush()
        logger.info(f"Updated existing MCP session: {session_id} for tenant: {tenant_name}")
        return session
        
    except Exception as e:
        logger.error(f"Error upserting MCP session: {str(e)}")
        raise


def ensure_latest_context(
    sess: Session,
    *,
    session_id: str,
    tenant_name: str,
    context: dict[str, Any],
) -> Dict[str, Any]:
    """
    Ensure the latest context is stored for a session (concurrency-safe).
    
    This function:
    - Locks the session row FOR UPDATE
    - Validates tenant ownership
    - Checks if the context has changed (via hash comparison)
    - Inserts a new history snapshot only if changed
    - Updates session.current_context_id to point to the latest snapshot
    
    Args:
        sess: SQLAlchemy session
        session_id: The session ID (UUID string)
        tenant_name: Tenant name (required for validation)
        context: The context dictionary to store
        
    Returns:
        Dict containing:
            - changed: bool - whether context was updated
            - context_id: str - ID of the context snapshot
            - seq: int - sequence number
            - context_hash: str - hash of the context
            
    Raises:
        ValueError: If session_id is not found or tenant mismatch
    """
    try:
        new_hash = _hash_context(context)

        # Lock the session row FOR UPDATE (explicitly disable relationship loading to avoid outer join)
        stmt = (
            select(McpSession)
            .where(McpSession.id == session_id)
            .options(noload(McpSession.current_context), noload(McpSession.history))
            .with_for_update()
        )
        session_row = sess.execute(stmt).scalar_one_or_none()
        
        if session_row is None:
            raise ValueError(f"Unknown session_id: {session_id}")

        # Validate tenant ownership
        if session_row.tenant_name != tenant_name:
            raise ValueError(f"Session {session_id} belongs to tenant {session_row.tenant_name}, not {tenant_name}")

        # Check if current context hash matches (fetch separately to avoid join lock issues)
        current_context_id = session_row.current_context_id
        if current_context_id is not None:
            current_context = sess.get(SessionContextHistory, current_context_id)
            if current_context and current_context.context_hash == new_hash:
                logger.info(f"Context unchanged for session {session_id} (tenant: {tenant_name})")
                return {
                    "changed": False,
                    "context_id": current_context.id,
                    "seq": current_context.seq,
                    "context_hash": new_hash,
                }

        # Calculate next sequence number for this session
        next_seq = sess.execute(
            select(func.coalesce(func.max(SessionContextHistory.seq), 0) + 1)
            .where(SessionContextHistory.session_id == session_id)
        ).scalar_one()

        # Insert new history row with tenant_name
        hist = SessionContextHistory(
            session_id=session_id,
            tenant_name=tenant_name,
            seq=int(next_seq),
            context=context,
            context_hash=new_hash,
        )
        sess.add(hist)
        sess.flush()  # Assigns context ID

        # Update pointer to latest context
        session_row.current_context_id = hist.id
        sess.flush()

        logger.info(f"Updated context for session {session_id} (tenant: {tenant_name}), seq={hist.seq}")
        return {
            "changed": True,
            "context_id": hist.id,
            "seq": hist.seq,
            "context_hash": new_hash
        }
        
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(f"Error ensuring latest context for session {session_id}: {str(e)}")
        raise


def get_latest_context(sess: Session, *, session_id: str, tenant_name: str) -> Dict[str, Any]:
    """
    Retrieve the latest context snapshot for a session.
    
    Args:
        sess: SQLAlchemy session
        session_id: The session ID (UUID string)
        tenant_name: Tenant name (required for validation)
        
    Returns:
        Dict containing:
            - session_id: str
            - context_id: str
            - seq: int
            - context_hash: str
            - created_at: str (ISO format)
            - context: dict
            
    Raises:
        ValueError: If session not found, tenant mismatch, or no context set
    """
    try:
        session = sess.get(McpSession, session_id)
        if session is None:
            raise ValueError(f"Session not found: {session_id}")

        # Validate tenant ownership
        if session.tenant_name != tenant_name:
            raise ValueError(f"Session {session_id} belongs to tenant {session.tenant_name}, not {tenant_name}")
            
        if session.current_context is None:
            return None

        hist = session.current_context
        
        result = {
            "session_id": session.id,
            "context_id": hist.id,
            "seq": hist.seq,
            "context_hash": hist.context_hash,
            "created_at": hist.created_at.isoformat(),
            "context": hist.context,
        }
        
        logger.info(f"Retrieved latest context for session {session_id} (tenant: {tenant_name}), seq={hist.seq}")
        return result
        
    except ValueError:
        # Re-raise ValueError as-is
        raise
    except Exception as e:
        logger.error(f"Error getting latest context for session {session_id}: {str(e)}")
        raise
