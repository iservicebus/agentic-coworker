from fastapi import APIRouter, Request, HTTPException, Depends, status, Path
from pydantic import BaseModel, model_validator
import uuid
from datetime import datetime

from integrator.utils.db import get_db
from sqlalchemy.orm import Session
from sqlalchemy.sql import func
from sqlalchemy import select, delete

from integrator.utils.oauth import validate_token
from integrator.iam.iam_db_model import ProviderToken


oauth_router = APIRouter(prefix="/oauth", tags=["oauth"])


from typing import Dict, Any, Optional, List

# Pydantic model for the request body of update_credential
class CredentialData(BaseModel):
    provider_id: str
    token: Dict[str, Any]
    tenant_name: str
    agent_id: str




# Pydantic models for ProviderToken
class ProviderTokenPayload(BaseModel):
    provider_id: str
    tenant_name: str
    token: Dict[str, Any]
    agent_id: str  # Now required for identifying the record
    username: Optional[str] = None # Username is optional, can be updated if provided

class ProviderTokenResponse(BaseModel):
    id: uuid.UUID
    provider_id: str
    tenant_name: str
    token: Dict[str, Any]
    username: Optional[str] = None
    agent_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class ProviderTokenDeletePayload(BaseModel):
    provider_id: str
    tenant_name: str
    agent_id: str # Now required for deletion

@oauth_router.put("/update_credential/providers/{provider}")
def upasyncdate_oauth_credential(
    provider: str,
    payload: ProviderTokenPayload,
    req: Request,
    _: dict = Depends(validate_token),
    db: Session = Depends(get_db)
    ):
        if not provider:
            raise HTTPException(status_code=404, detail=f"Unsupported service: {provider}")

        try:
            existing_token = db.query(ProviderToken).filter_by(
                provider_id=payload.provider_id,
                tenant_name=payload.tenant_name,
                agent_id=payload.agent_id
            ).first()

            if existing_token:
                # Token found, update it
                existing_token.token = payload.token
                if payload.username is not None:
                    existing_token.username = payload.username
                existing_token.updated_at = func.now()
                db.commit()
                db.refresh(existing_token)
                return existing_token
            else:
                # Token not found, insert a new one
                new_token_data = {
                    "provider_id": payload.provider_id,
                    "tenant_name": payload.tenant_name,
                    "agent_id": payload.agent_id,
                    "token": payload.token,
                    "username": payload.username,
                    "updated_at": func.now()
                }
                db_token = ProviderToken(**new_token_data)
                db.add(db_token)
                db.commit()
                db.refresh(db_token)
                return db_token
        except HTTPException:
            raise
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected database error occurred: {str(e)}")




#    return {"status": "success", "message": f"Credential for {provider} updated successfully."}

# Router for provider tokens
provider_token_router = APIRouter(prefix="/provider_tokens", tags=["Provider Tokens"])

@provider_token_router.post("", response_model=ProviderTokenResponse, status_code=status.HTTP_201_CREATED)
async def add_or_update_provider_token(
    payload: ProviderTokenPayload,
    db: Session = Depends(get_db),
     user: dict = Depends(validate_token) # Assuming authentication is needed
):
    """
    Adds a new provider token or updates an existing one.

    - The token is identified by the combination of `provider_id`, `tenant_name`, and `agent_id`.
    - `agent_id` is a required field in the payload.
    - If a token with the given `provider_id`, `tenant_name`, and `agent_id` exists:
        - Its `token` field is updated with the `token` from the payload.
        - If `username` is provided in the payload, the existing token's `username` is also updated.
          If `username` is not provided in the payload, the existing token's `username` remains unchanged.
        - The `updated_at` timestamp is updated.
    - If no such token exists:
        - A new token record is created with all details from the payload (`provider_id`, `tenant_name`,
          `agent_id`, `token`, and `username` if provided).
    """
    try:
        existing_token = db.query(ProviderToken).filter_by(
            provider_id=payload.provider_id,
            tenant_name=payload.tenant_name,
            agent_id=payload.agent_id
        ).first()

        if existing_token:
            # Token found, update it
            existing_token.token = payload.token
            if payload.username is not None:
                existing_token.username = payload.username
            existing_token.updated_at = func.now()
            db.commit()
            db.refresh(existing_token)
            return existing_token
        else:
            # Token not found, insert a new one
            new_token_data = {
                "provider_id": payload.provider_id,
                "tenant_name": payload.tenant_name,
                "agent_id": payload.agent_id,
                "token": payload.token,
                "username": payload.username,
                "updated_at": func.now()
            }
            db_token = ProviderToken(**new_token_data)
            db.add(db_token)
            db.commit()
            db.refresh(db_token)
            return db_token
    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected database error occurred: {str(e)}")

@provider_token_router.get("/tenants/{tenant_name}/providers/{provider_id}/agents/{agent_id}", response_model=ProviderTokenResponse)
async def get_specific_provider_token(
    tenant_name: str = Path(..., description="The name of the tenant"),
    provider_id: str = Path(..., description="The ID of the provider"),
    agent_id: str = Path(..., description="The ID of the agent"),
    db: Session = Depends(get_db),
    # user: dict = Depends(validate_token) # Assuming authentication is needed
):
    """
    Get a specific provider token by tenant_name, provider_id, and agent_id.
    """
    token = db.query(ProviderToken).filter_by(
        tenant_name=tenant_name,
        provider_id=provider_id,
        agent_id=agent_id
    ).first()

    if not token:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Provider token not found for the given tenant, provider, and agent.")
    return token

@provider_token_router.get("", response_model=List[ProviderTokenResponse])
async def get_provider_tokens_by_user_or_agent( # Renamed for clarity
    username: Optional[str] = None,
    agent_id: Optional[str] = None,
    tenant_name: Optional[str] = None,
    provider_id: Optional[str] = None,
    db: Session = Depends(get_db),
    # user: dict = Depends(validate_token) # Assuming authentication is needed
):
    """
    Get a list of provider tokens.
    Can filter by `username` or `agent_id`.
    Can optionally filter by `tenant_name` and `provider_id`.
    If neither username nor agent_id is provided, it might return all tokens (consider security implications).
    For more targeted queries, use the specific GET endpoint.
    """
    # Consider if requiring at least one of username or agent_id is still desired for this broader query
    # if not username and not agent_id:
    #     raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Either username or agent_id query parameter must be provided for this general query.")

    stmt = select(ProviderToken)
    if username:
        stmt = stmt.where(ProviderToken.username == username)
    if agent_id: # This allows querying all tokens for a specific agent across tenants/providers if other filters are omitted
        stmt = stmt.where(ProviderToken.agent_id == agent_id)
    if tenant_name:
        stmt = stmt.where(ProviderToken.tenant_name == tenant_name)
    if provider_id:
        stmt = stmt.where(ProviderToken.provider_id == provider_id)

    result = db.execute(stmt)
    tokens = result.scalars().all()
    return tokens

@provider_token_router.delete("", status_code=status.HTTP_204_NO_CONTENT) # Consider changing path for specificity
async def delete_provider_token(
    payload: ProviderTokenDeletePayload, # Payload now contains provider_id, tenant_name, agent_id
    db: Session = Depends(get_db),
    # user: dict = Depends(validate_token) # Assuming authentication is needed
):
    """
    Delete a provider token based on provider_id, tenant_name, and agent_id.
    """
    stmt = delete(ProviderToken).where(
        ProviderToken.provider_id == payload.provider_id,
        ProviderToken.tenant_name == payload.tenant_name,
        ProviderToken.agent_id == payload.agent_id # Deletion is now strictly by these three
    )

    try:
        result = db.execute(stmt)
        db.commit()
        if result.rowcount == 0:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token not found for the given provider_id, tenant_name, and agent_id.")
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Database error during deletion: {str(e)}")
