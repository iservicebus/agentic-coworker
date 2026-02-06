
import logging
logger = logging.getLogger(__name__)
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError
import httpx
from fastapi import  HTTPException
import os
from typing import Callable


async def validate_token(request, callback: Callable=None, *args, **kwargs):
    headers = dict(request.headers)
    auth_header = headers.get("Authorization".lower())
    client_id_header = headers.get("X-Agent-ID".lower())
    x_tenant_name=headers.get("X-Tenant".lower())
    return await validate_auth(auth_header, client_id_header, x_tenant_name, callback, *args, **kwargs)

async def get_auth_agent(headers, callback: Callable=None, *args, **kwargs):
  
    auth = headers.get("Authorization".lower())
    x_agent_id = headers.get("X-Agent-ID".lower())
    x_tenant_name =headers.get("X-Tenant".lower())

    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    token = auth.split(" ")[1]

    payload=await decode_token(token, x_tenant_name)

    user_type=payload.get("user_type")
    client_type=payload.get("client_type")
    scope=payload.get("scope")
    username = payload.get("preferred_username")

    if user_type=="agent":
        return username, x_tenant_name, scope
    elif user_type=="human" and x_agent_id and callback:
        if callback(x_agent_id, auth, x_tenant_name):
            return x_agent_id, x_tenant_name, scope
        else:
            return None, None, None
    elif client_type=="agent":
        return payload.get("azp"), x_tenant_name, scope    
    else:
        return None, None, None





async def decode_token(token, tenant_name):
    iam_url = os.getenv("IAM_URL")
    #realm = os.getenv("REALM")

    KEYCLOAK_ISSUER = f"{iam_url}/realms/{tenant_name}"

    jwks_url = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

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






async def validate_auth(auth, client_id, tenant_name, callback: Callable=None, *args, **kwargs):
    iam_url = os.getenv("IAM_URL")
#    realm = os.getenv("REALM")

    KEYCLOAK_ISSUER = f"{iam_url}/realms/{tenant_name}"

    jwks_url = f"{KEYCLOAK_ISSUER}/protocol/openid-connect/certs"

    print(f"IAM URL {iam_url}")
    
    if not auth or not auth.startswith("Bearer "):
        raise HTTPException(status_code=401, detail='Missing or invalid Authorization header')
    token = auth.split(" ")[1]

    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(jwks_url)
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
        
        payload = jwt.decode(
            token,
            key,
            algorithms=["RS256"],
            audience="account", # Make sure this audience is correct for your Keycloak setup
            issuer=KEYCLOAK_ISSUER
        )
        if payload.get("azp") != client_id:
            if callback: 
                working_agent_id=callback(payload.get("azp"), auth )
                if working_agent_id != client_id:
                    raise JWTError(f"Client ID mismatch: working agent_id {working_agent_id} and client id {client_id}")
            else:
                    raise JWTError(f"No call back for client id {client_id}")

        return True
            
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
