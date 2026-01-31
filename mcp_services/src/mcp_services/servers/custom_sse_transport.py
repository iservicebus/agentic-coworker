from uuid import UUID, uuid4
from typing import Any
import anyio
from contextlib import asynccontextmanager
from mcp.server.sse import SseServerTransport  # Adjust import path as needed

class CustomSseServerTransport(SseServerTransport):
    @asynccontextmanager
    async def connect_sse(self, scope, receive, send):
        # Record existing session IDs
        existing_ids = set(self._read_stream_writers.keys())
        # Call the original SDK implementation
        async with super().connect_sse(scope, receive, send) as streams:
            # Find the new session ID added by SDK
            new_ids = set(self._read_stream_writers.keys()) - existing_ids
            session_id = next(iter(new_ids)) if new_ids else None
            # Yield the original streams plus the session_id
            yield (*streams, session_id)
