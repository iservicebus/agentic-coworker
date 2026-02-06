from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware # Added for CORS
import uvicorn
from dotenv import load_dotenv

# --- Centralized Logging Setup ---
from integrator.utils.logger import  get_logger
logger = get_logger(__name__) # Get a logger for this module

# --- FastAPI App ---
app = FastAPI(
    title="AI Integration Services", # Renamed title
    description="Provides AI Integration Services supporting access to mcp service metadata stored in etcd and allowing registration/deletion.",
    version="1.1.0"
)

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

from integrator.tools.publish.mcp_service_apis import mcp_router
from integrator.tools.staging.staging_service_apis import staging_router

from integrator.iam.iam_service_apis import user_router
from integrator.iam.access_token_apis import oauth_router, provider_token_router # Added provider_token_router
from integrator.logs.log_service_apis import log_router
from integrator.clients.consume_apis import client_router
from integrator.domains.domain_service_apis import domain_router # Added domain_router
from integrator.tools.tool_service_apis import tools_router # Added tools_router
from integrator.agents.apis.chat_apis import chat_router # Added chat_router
# No prefix needed here, since routers already have them
app.include_router(mcp_router)
app.include_router(log_router)
app.include_router(user_router)
app.include_router(staging_router)
app.include_router(oauth_router)
app.include_router(provider_token_router) # Added provider_token_router
app.include_router(client_router) # Added client_router
app.include_router(domain_router) # Added domain_router
app.include_router(tools_router) # Added tools_router
app.include_router(chat_router, prefix="/agents") # Added chat_router with /agents prefix
