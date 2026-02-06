"""
Custom exceptions for the tool index system.
Provides structured error handling with clear error types and messages.
"""

from typing import Optional, Dict, Any


class QueueError(Exception):
    """Base exception for all tool index related errors."""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)

class DequeueError(QueueError):
    """Raised when tool ingestion fails."""
    
    def __init__(self, reason: str, details: Optional[Dict[str, Any]] = None, item: Any =None):
        message = f"Failed to dequeue message: {reason}"
        super().__init__(message, details)
        self.item = item


def handle_queue_error(func):
    """Decorator to handle database errors consistently."""
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            # Convert SQLAlchemy errors to our custom DatabaseError
            raise QueueError(f"Database operation failed: {str(e)}", {"original_error": str(e)})
    return wrapper

