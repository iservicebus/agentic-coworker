from fastapi import FastAPI, Response, Request
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
import uvicorn, os
# --- Centralized Logging Setup ---
# Use shared utilities with fallback to local utils
from support_services.utils.env import load_env
from support_services.utils.logger import get_logger

logger = get_logger(__name__) # Get a logger for this module
load_env()


from starlette.middleware.base import BaseHTTPMiddleware

# --- FastAPI App ---
app = FastAPI(
    title="Support Services API",
    description="""
    Internal API services to support MCP (Model Context Protocol) services in agents.
    
    This API provides various support services including:
    - Authentication provider management
    - Email services
    - Sample data processing endpoints for testing and demonstration
    
    ## Authentication
    Most endpoints require Bearer token authentication. Include your token in the Authorization header:
    ```
    Authorization: Bearer your_token_here
    ```
    
    ## Sample Endpoints
    The `/samples` endpoints demonstrate various data processing capabilities and serve as templates for integration testing.
    """,
    version="1.0.0",
    contact={
        "name": "Support Services Team",
        "email": "support@example.com",
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT",
    },
    servers=[
        {
            "url": "http://host.docker.internal:5000",
            "description": "Docker internal host server (for containerized environments)"
        },
        {
            "url": "http://localhost:5000",
            "description": "Local development server"
        }

    ],
    openapi_tags=[
        {
            "name": "Sample APIs",
            "description": "Sample endpoints for testing different data processing scenarios including text, binary, and form data handling."
        },
        {
            "name": "File Operations",
            "description": "File upload, download, and management endpoints with authentication."
        },
        {
            "name": "Authentication",
            "description": "Authentication provider management endpoints."
        },
        {
            "name": "Email",
            "description": "Email service endpoints for sending notifications and communications."
        }
    ]
)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        body = await request.body()

        logger.info("Incoming Request: %s %s", request.method, request.url)
        logger.info("Headers: %s", dict(request.headers))

        try:
            logger.info("Body: %s", body.decode("utf-8"))
        except UnicodeDecodeError:
            logger.info("Body: <binary data, size: %d bytes>", len(body))

        async def receive():
            return {"type": "http.request", "body": body, "more_body": False}

        # Rebuild the request with a fresh receive channel
        request = Request(request.scope, receive=receive)

        response = await call_next(request)
        return response

app.add_middleware(RequestLoggingMiddleware)

# --- CORS Middleware ---
# Define allowed origins. For development, this often includes your frontend's address.
# For production, be more restrictive.
# Temporarily allowing all origins for debugging
origins = ["*"] # Allows all origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, # Allows all origins
    allow_credentials=True, # Allows cookies to be included in requests
    allow_methods=["*"],    # Allows all standard HTTP methods
    allow_headers=["*"],    # Allows all headers
)


from support_services.auths.provider import auth_router
from support_services.common.email import email_router
from support_services.samples.templates import sample_router
from support_services.samples.file_api import file_router


# No prefix needed here, since routers already have them
app.include_router(auth_router)
app.include_router(email_router)
app.include_router(sample_router)
app.include_router(file_router)

# Add endpoint for favicon.ico to prevent 404 errors
@app.get('/favicon.ico', include_in_schema=False)
async def favicon():
    # Return an empty response with a 200 status code
    # A more robust solution would serve an actual favicon file
    return Response(content='', media_type='image/x-icon', status_code=200)

if __name__ == "__main__":
    # Load environment variables using shared utility
    # This will automatically find the .env file or use a custom path
    load_env()

    support_port= int(os.getenv("SUPPORT_PORT", "5000"))
    logger.info("start support service") # Replaced print with logger
    # Use reload=True for development
    # The host/port configuration allows both 127.0.0.1 and any IP assigned to local machine
    # Using 0.0.0.0 binds to all available network interfaces on the local machine
    uvicorn.run("support_services.api_server:app", host="0.0.0.0", port=support_port, reload=True, log_level="debug")
