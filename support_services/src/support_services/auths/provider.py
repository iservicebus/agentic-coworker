from fastapi import FastAPI, HTTPException, Body, Query, Path, Depends, Request
import os
from fastapi import APIRouter

from support_services.utils.oauth import validate_token, get_agent_id
from support_services.utils.logger import get_logger # Import the logger


# Initialize logger for this module
logger = get_logger(__name__)


auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.get(
    "/providers/{provider_name}",
    summary="get authentication provider url by provider name such as google, linkedin, github et al",
    description="get authentication provider url by provider name such as google, linkedin, github et al so that agent can use the provider to request access token",
)
def get_provider_url(
    provider_name: str = Path(..., description="The name of the authentication provider such as google, linkedin, github et al to retrieve access token"),
    agent: dict = Depends(validate_token)

):
    """
    Retrieves the complete metadata for a single service identified by its `tenant`
    and `service_name` using the `retrieve_service_by_name` function.
    """
    logger.info(f"Request received for /providers/{provider_name}")
    agent_id=get_agent_id(agent)
    if not agent_id:
        raise HTTPException(status_code=401, detail=f"agent id is not found")

    integrator_base_url = os.getenv("META_AUTHORIZATION_LINK")
    return f"{integrator_base_url}/token/start/oauth_providers/{provider_name}?agent_id={agent_id}"
