"""HTTP client service with proper resource management."""

import httpx
from typing import Dict, Any, Optional, Union
from contextlib import asynccontextmanager
import asyncio

from mcp_services.utils.logger import get_logger

logger = get_logger(__name__)


class HttpClientService:
    """Centralized HTTP client service with connection pooling and proper resource management."""
    
    def __init__(self, timeout: float = 30.0, max_connections: int = 100):
        self.timeout = timeout
        self.max_connections = max_connections
        self._client: Optional[httpx.AsyncClient] = None
        self._sync_client: Optional[httpx.Client] = None
        self._lock = asyncio.Lock()
    
    async def get_async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client with connection pooling."""
        if self._client is None:
            async with self._lock:
                if self._client is None:
                    limits = httpx.Limits(
                        max_keepalive_connections=self.max_connections,
                        max_connections=self.max_connections
                    )
                    timeout = httpx.Timeout(self.timeout)
                    self._client = httpx.AsyncClient(
                        limits=limits,
                        timeout=timeout,
                        follow_redirects=False
                    )
        return self._client
    
    def get_sync_client(self) -> httpx.Client:
        """Get or create sync HTTP client with connection pooling."""
        if self._sync_client is None:
            limits = httpx.Limits(
                max_keepalive_connections=self.max_connections,
                max_connections=self.max_connections
            )
            timeout = httpx.Timeout(self.timeout)
            self._sync_client = httpx.Client(
                limits=limits,
                timeout=timeout,
                follow_redirects=False
            )
        return self._sync_client
    
    async def request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        content: Optional[Union[str, bytes]] = None,
        files: Optional[Dict[str, Any]] = None,
        raise_for_status: bool = True
    ) -> httpx.Response:
        """Make an async HTTP request with proper error handling."""
        client = await self.get_async_client()
        
        try:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                content=content,
                files=files
            )

            # Only raise for 4xx and 5xx errors, not 3xx redirects
            if raise_for_status and response.status_code >= 400:
                response.raise_for_status()

            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error for {method} {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise
    
    def sync_request(
        self,
        method: str,
        url: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Union[Dict[str, Any], str, bytes]] = None,
        content: Optional[Union[str, bytes]] = None,
        files: Optional[Dict[str, Any]] = None,
        raise_for_status: bool = True
    ) -> httpx.Response:
        """Make a sync HTTP request with proper error handling."""
        client = self.get_sync_client()
        
        try:
            response = client.request(
                method=method,
                url=url,
                headers=headers,
                params=params,
                json=json,
                data=data,
                content=content,
                files=files
            )

            # Only raise for 4xx and 5xx errors, not 3xx redirects
            if raise_for_status and response.status_code >= 400:
                response.raise_for_status()

            return response

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP {e.response.status_code} error for {method} {url}: {e}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error for {method} {url}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error for {method} {url}: {e}")
            raise
    
    async def get(self, url: str, **kwargs) -> httpx.Response:
        """Make a GET request."""
        return await self.request("GET", url, **kwargs)
    
    async def post(self, url: str, **kwargs) -> httpx.Response:
        """Make a POST request."""
        return await self.request("POST", url, **kwargs)
    
    async def put(self, url: str, **kwargs) -> httpx.Response:
        """Make a PUT request."""
        return await self.request("PUT", url, **kwargs)
    
    async def delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a DELETE request."""
        return await self.request("DELETE", url, **kwargs)
    
    def sync_get(self, url: str, **kwargs) -> httpx.Response:
        """Make a sync GET request."""
        return self.sync_request("GET", url, **kwargs)
    
    def sync_post(self, url: str, **kwargs) -> httpx.Response:
        """Make a sync POST request."""
        return self.sync_request("POST", url, **kwargs)
    
    def sync_put(self, url: str, **kwargs) -> httpx.Response:
        """Make a sync PUT request."""
        return self.sync_request("PUT", url, **kwargs)
    
    def sync_delete(self, url: str, **kwargs) -> httpx.Response:
        """Make a sync DELETE request."""
        return self.sync_request("DELETE", url, **kwargs)
    
    async def close(self):
        """Close all HTTP clients and clean up resources."""
        if self._client:
            await self._client.aclose()
            self._client = None
        
        if self._sync_client:
            self._sync_client.close()
            self._sync_client = None
    
    @asynccontextmanager
    async def session(self):
        """Context manager for HTTP client session."""
        try:
            yield self
        finally:
            await self.close()
    
    def __del__(self):
        """Cleanup on garbage collection."""
        if self._sync_client:
            try:
                self._sync_client.close()
            except Exception:
                pass


# Global HTTP client instance
_http_client: Optional[HttpClientService] = None

def get_http_client() -> HttpClientService:
    """Get the global HTTP client instance."""
    global _http_client
    if _http_client is None:
        _http_client = HttpClientService()
    return _http_client

async def close_http_client():
    """Close the global HTTP client."""
    global _http_client
    if _http_client:
        await _http_client.close()
        _http_client = None
