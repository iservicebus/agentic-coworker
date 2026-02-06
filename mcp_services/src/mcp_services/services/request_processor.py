"""Request processing pipeline for MCP provider."""

import json
import pathlib
import io
import os
from typing import Dict, Any, Optional, Union, Tuple
from string import Template
import httpx

from mcp_services.services.http_client import HttpClientService
from mcp_services.utils.host import generate_host_id
from mcp_services.utils.logger import get_logger
from mcp_services.utils.env import load_env

# Load environment variables
load_env()

logger = get_logger(__name__)

FileLike = Union[io.IOBase, io.BytesIO]
FileTuple = Tuple[str, Union[bytes, FileLike], str]  # (filename, content, mime)


class RequestProcessor:
    """Handles HTTP request processing and generation."""
    
    def __init__(self, http_client: HttpClientService):
        self.proxy_url = os.getenv("PROXY_URL", "http://localhost")
        self.http_client = http_client
    
    def _looks_like_file_tuple(self, v: Any) -> bool:
        """Check if value looks like a file tuple."""
        return (
            isinstance(v, tuple)
            and len(v) in (2, 3)  # allow (filename, content) or (filename, content, mime)
            and isinstance(v[0], str)
            and isinstance(v[1], (bytes, bytearray, memoryview, io.IOBase, io.BytesIO))
        )
    
    def _split_form_body_for_multipart(self, form: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Split a mixed dict into data (non-file fields) and files (file fields)."""
        data_part = {}
        files_part = {}

        for k, v in form.items():
            if self._looks_like_file_tuple(v):
                # Normalize to (filename, fileobj/bytes, mime?) for httpx/requests
                if len(v) == 2:
                    files_part[k] = (v[0], v[1])  # client figures out mime if omitted
                else:
                    files_part[k] = (v[0], v[1], v[2])
            elif isinstance(v, (bytes, bytearray, memoryview)):
                # Treat raw bytes in a dict as a file only if caller wrapped as a tuple.
                data_part[k] = v.decode("utf-8", errors="ignore")
            elif isinstance(v, pathlib.Path):
                files_part[k] = (v.name, v.open("rb"))
            else:
                data_part[k] = v

        return data_part, files_part
    
    def generate_http_request(
        self,
        tenant: str,
        app_keys: Dict[str, Any],
        headers: Dict[str, str],
        arguments: Dict[str, Any],
        predefined_data: Dict[str, Any],
        token: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate HTTP request configuration."""
        req = {}
        pre_headers = predefined_data.get("headers", {})
        content_type = pre_headers.get("Content-Type")
        
        # Handle request body
        if content_type == "application/json":
            req["body"] = json.dumps(arguments.get("aint_body", {}))
        elif arguments.get("aint_body") is not None:
            req["body"] = arguments.get("aint_body")
        
        # Set method
        req["method"] = predefined_data.get("method")
        
        # Generate URL
        url = predefined_data.get("url")
        host_id, base_url, path = generate_host_id(url)
        host_id = f"{tenant}-{host_id}"

        if path and arguments.get("aint_path"):
            path = Template(path).substitute(arguments.get("aint_path"))

        if path:
            req["url"] = f"{self.proxy_url}/{host_id}/{path}"
        else:
            req["url"] = f"{self.proxy_url}/{host_id}"

        # Handle query parameters
        query = predefined_data.get("url", {}).get("query", {})
        if app_keys.get("query"):
            query = {**query, **app_keys.get("query")}

        if arguments.get("aint_query"):
            req["params"] = {**query, **arguments.get("aint_query")}
        else:
            req["params"] = query

        # Handle headers
        request_headers = predefined_data.get("headers", {})
        if app_keys.get("headers"):
            request_headers = {**request_headers, **app_keys.get("headers")}

        if token.get("accessToken"):
            request_headers["Authorization"] = f"Bearer {token.get('accessToken')}"

        if arguments.get("aint_headers"):
            req["headers"] = {**request_headers, **arguments.get("aint_headers")}
        else:
            req["headers"] = request_headers
        
        req["headers"]["Host"] = ".".join(url.get("host", []))

        return req
    
    async def execute_request(self, req: Dict[str, Any]) -> httpx.Response:
        """Execute HTTP request with proper content type handling."""
        body = req.get("body")
        headers = req.get("headers", {})
        content_type = headers.get("Content-Type", "").lower().strip()

        # No body at all
        if body is None:
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
            )
        
        # JSON: explicit or inferred
        elif isinstance(body, dict) and ("application/json" in content_type or content_type == ""):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                json=body
            )

        # application/x-www-form-urlencoded (typical HTML forms)
        elif isinstance(body, dict) and ("application/x-www-form-urlencoded" in content_type):
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                data=body,
            )
        
        # Multipart form with files (multipart/form-data)
        elif isinstance(body, dict) and (
            ("multipart/form-data" in content_type) or 
            any(self._looks_like_file_tuple(v) or isinstance(v, pathlib.Path) for v in body.values())
        ):
            data_part, files_part = self._split_form_body_for_multipart(body)

            # Let the client set the multipart boundary & header automatically.
            if "Content-Type" in headers and "multipart/form-data" in headers["Content-Type"].lower():
                headers.pop("Content-Type", None)
            
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                data=data_part if data_part else None,
                files=files_part if files_part else None
            )

        # Raw body via content= (bytes/str/stream or any custom Content-Type)
        elif isinstance(body, (bytes, bytearray, memoryview, io.IOBase, io.BytesIO)):
            headers.setdefault("Content-Type", "application/octet-stream")
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )

        # String body: send raw text
        elif isinstance(body, str):
            headers.setdefault("Content-Type", "text/plain; charset=utf-8")
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )

        # Fallback: try content= for unknown types
        else:
            return await self.http_client.request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )
    
    def sync_execute_request(self, req: Dict[str, Any]) -> httpx.Response:
        """Execute HTTP request synchronously with proper content type handling."""
        body = req.get("body")
        headers = req.get("headers", {})
        content_type = headers.get("Content-Type", "").lower().strip()

        # No body at all
        if body is None:
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
            )
        
        # JSON: explicit or inferred
        elif isinstance(body, dict) and ("application/json" in content_type or content_type == ""):
            if "Content-Type" not in headers:
                headers["Content-Type"] = "application/json"
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                json=body
            )

        # application/x-www-form-urlencoded (typical HTML forms)
        elif isinstance(body, dict) and ("application/x-www-form-urlencoded" in content_type):
            headers.setdefault("Content-Type", "application/x-www-form-urlencoded")
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                data=body,
            )
        
        # Multipart form with files (multipart/form-data)
        elif isinstance(body, dict) and (
            ("multipart/form-data" in content_type) or 
            any(self._looks_like_file_tuple(v) or isinstance(v, pathlib.Path) for v in body.values())
        ):
            data_part, files_part = self._split_form_body_for_multipart(body)

            # Let the client set the multipart boundary & header automatically.
            if "Content-Type" in headers and "multipart/form-data" in headers["Content-Type"].lower():
                headers.pop("Content-Type", None)
            
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                data=data_part if data_part else None,
                files=files_part if files_part else None
            )

        # Raw body via content= (bytes/str/stream or any custom Content-Type)
        elif isinstance(body, (bytes, bytearray, memoryview, io.IOBase, io.BytesIO)):
            headers.setdefault("Content-Type", "application/octet-stream")
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )

        # String body: send raw text
        elif isinstance(body, str):
            headers.setdefault("Content-Type", "text/plain; charset=utf-8")
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )

        # Fallback: try content= for unknown types
        else:
            return self.http_client.sync_request(
                method=req["method"],
                url=req["url"],
                headers=headers,
                params=req.get("params"),
                content=body,
            )
