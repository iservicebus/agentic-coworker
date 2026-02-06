import logging
logger = logging.getLogger(__name__)
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
import httpx
from fastapi import Request, HTTPException
import os


def validate_token(request: Request):
    """
    Validates the OAuth token from the request headers.
    
    Args:
        request: FastAPI Request object
        
    Returns:
        dict: Decoded token payload with user information
        
    Raises:
        HTTPException: If token is invalid or missing
    """
    headers = dict(request.headers)
    auth_header = headers.get("authorization")
    client_id_header = headers.get("x-agent-id")
    return validate_auth(auth_header, client_id_header)


def decode_token(auth):
    """
    Decodes and validates a JWT token using Keycloak's public keys.
    
    Args:
        auth: Authorization header value (Bearer token)
        
    Returns:
        dict: Decoded token payload
        
    Raises:
        HTTPException: If token is invalid, expired, or cannot be verified
    """
    iam_url = os.getenv("IAM_URL")
    realm = os.getenv("REALM")

    KEYCLOAK_ISSUER = f"{iam_url}/realms/{realm}"
    jwks_url = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    token = auth.split(" ")[1]

    try:
        response = httpx.get(jwks_url)
        response.raise_for_status()
        keys = response.json()["keys"]
        jwks = {key["kid"]: key for key in keys}
        
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = jwks.get(kid)

        if not key:
            raise JWTError("Unknown key ID in token")
        
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="account",
            issuer=KEYCLOAK_ISSUER
        )
        
        return payload
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to fetch JWKS: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch authentication keys")
    except ExpiredSignatureError:
        logger.warning("Token validation failed: Expired signature")
        raise HTTPException(status_code=401, detail="Token has expired")
    except JWTError as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during token validation: {e}")
        raise HTTPException(status_code=500, detail="Internal server error during token validation")


def validate_auth(auth, client_id):
    """
    Validates authentication and adds client ID to payload.
    
    Args:
        auth: Authorization header value
        client_id: X-Agent-ID header value
        
    Returns:
        dict: Decoded token payload with x_agent_id added
    """
    payload = decode_token(auth)
    payload["x_agent_id"] = client_id
    return payload
