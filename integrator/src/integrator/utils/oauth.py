
import logging
logger = logging.getLogger(__name__)
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
import httpx
from fastapi import Request, HTTPException
import os



def validate_token(request: Request):
    headers = dict(request.headers)
    auth_header = headers.get("Authorization".lower())
    client_id_header = headers.get("X-Agent-ID".lower())
    tenant_name=headers.get("X-Tenant".lower())

    rs=validate_auth(auth_header, client_id_header, tenant_name)
    return rs


def decode_token(auth, tenant_name):
    iam_url = os.getenv("IAM_URL")
    #realm = os.getenv("REALM")

    KEYCLOAK_ISSUER = f"{iam_url}/realms/{tenant_name}"

    jwks_url = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    token = auth.split(" ")[1]

    try:
        response = httpx.get(jwks_url)
        response.raise_for_status() # Raise an exception for HTTP errors (4xx or 5xx)
        keys = response.json()["keys"]
        jwks = {key["kid"]: key for key in keys}
        
        unverified = jwt.get_unverified_header(token)
        kid = unverified.get("kid")
        key = jwks.get(kid)

        if not key:
            # This specific error could also be a 500 if server config is wrong,
            # but 401 is safer for client-facing errors.
            raise JWTError("Unknown key ID in token")
        
        # Check if issuer validation should be performed
        issuer_validation = os.getenv("ISSUER_VALIDATION", "false").lower()
        
        decode_options = {
            "algorithms": ["RS256"],
            "audience": "account"  # Make sure this audience is correct for your Keycloak setup
        }
        
        # Only add issuer parameter if validation is enabled
        if issuer_validation != "false":
            decode_options["issuer"] = KEYCLOAK_ISSUER
        
        payload = jwt.decode(
            token,
            key,
            **decode_options
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

def validate_auth(auth, client_id, tenant_name):
    payload=decode_token(auth, tenant_name)
    payload["x_agent_id"]=client_id
    return payload
