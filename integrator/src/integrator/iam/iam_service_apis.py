from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import os
from integrator.utils.db import get_db

# === backend/main.py ===
from fastapi import APIRouter, Depends,  HTTPException, Request, Path as PathParam
from sqlalchemy.orm import Session
import os
from pydantic import BaseModel, Field, ValidationError
from typing import Dict, Any, Optional, List # Added List
from uuid import UUID
from datetime import datetime, timezone # Added timezone
import json
import jsonschema
from pathlib import Path as FilePath

from integrator.iam.iam_db_model import User, Agent, Tenant, AuthProvider, Role, AgentProfile, UserAgent, RoleDomain
from integrator.tools.tool_db_model import AppKey, Application
from integrator.utils.oauth import validate_token
from integrator.utils.crypto_utils import decrypt

from integrator.iam.iam_db_crud import get_agents_by_username
from integrator.iam.iam_auth import validate_agent_id, validate_tenant

from integrator.iam.iam_db_model import RoleAgent
from integrator.domains.domain_db_model import Domain, Capability, DomainCapability
from integrator.utils.logger import get_logger

logger = get_logger(__name__)
    
# === Tenant Helper Functions ===

def validate_tenant_access(sess, payload: dict, tenant_name: str):
    if not validate_tenant(sess,payload, tenant_name):
        raise HTTPException(
            status_code=403, 
            detail=f"Access denied to tenant '{tenant_name}'"
        )

# Pydantic models for new API responses and requests
class WorkingAgentInfo(BaseModel):
    agent_id: str
    name: Optional[str] = None

# ServiceSecretEntry is no longer directly used in Tenant/ActiveTenantInfo responses
# class ServiceSecretEntry(BaseModel):
#     service_name: str
#     secrets: Dict[str, Any]
#
#     class Config:
#         from_attributes = True

class ActiveTenantInfo(BaseModel):
    id: UUID
    name: str

    class Config:
        from_attributes = True

class UserLoginResponse(BaseModel):
    username: str
    user_type: str
    active_tenant: Optional[ActiveTenantInfo] = None
    roles: Optional[List[str]] = None

    class Config:
        from_attributes = True

# Removed SvcInputUpdate
# class SvcInputUpdate(BaseModel):
#     svc_inputs: Dict[str, Any]

class ServiceSecretUpdatePayload(BaseModel):
    app_name: str = Field(..., description="The name of the application for which secrets are being updated.")
    secrets: Dict[str, Any] = Field(..., description="The secrets data for the service.")

class ServiceSecretInfo(BaseModel):
    app_name: str
    secrets: Dict[str, Any]

    class Config:
        from_attributes = True

class TenantResponse(BaseModel):
    id: UUID
    name: str
    description: Optional[str] = None
    app_keys: Optional[Dict[str, Dict[str, Any]]] = Field(default_factory=dict) # Changed to Dict
    created_at: datetime

    class Config:
        from_attributes = True

# Removed SvcInputsResponse
# class SvcInputsResponse(BaseModel):
#     svc_inputs: Dict[str, Any]

# This model is no longer needed as ActiveTenantInfo will be used.
# class SvcInputsResponse(BaseModel):
#     svc_inputs: Dict[str, Any]

class AuthProviderInfo(BaseModel):
    provider_id: str
    provider_name: str
    provider_type: str
    type: str
    client_id: str
    options: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class AuthProviderDetails(BaseModel):
    provider_id: str
    provider_name: str
    provider_type: str
    type: str
    client_id: str
    client_secret: str
    is_built_in: bool
    options: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

user_router = APIRouter(prefix="/users", tags=["users"])

# === New API Models ===
class AgentInfo(BaseModel):
    agent_id: str
    name: Optional[str] = None
    tenant_name: Optional[str] = None
    roles: Optional[List[str]] = None
    role: Optional[str] = None  # Role from user_agent relationship
    context: Optional[Dict[str, Any]] = None  # Context from user_agent relationship

    class Config:
        from_attributes = True

class UserInfo(BaseModel):
    username: str
    email: Optional[str] = None
    roles: Optional[List[str]] = None

    class Config:
        from_attributes = True

class RoleInfo(BaseModel):
    name: str
    label: str
    description: Optional[str] = None

    class Config:
        from_attributes = True

class UpdateRoleAgentPayload(BaseModel):
    agent_id: str
    role_names: List[str]

class UpdateWorkingAgentPayload(BaseModel):
    working_agent_id: str

# === Agent Profile API Models ===
class AgentProfileInfo(BaseModel):
    agent_id: str
    context: Optional[dict] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True

class UpdateAgentProfilePayload(BaseModel):
    context: Optional[dict] = None

# === Role with Domains and Tool Counts API Models ===
class DomainToolCountInfo(BaseModel):
    name: str
    label: str
    description: str
    tool_count: int

    class Config:
        from_attributes = True

class RoleWithDomainsAndToolsInfo(BaseModel):
    role_name: str
    role_label: str
    role_description: str
    role_type: Optional[str] = None
    tool_count: int
    domains: List[DomainToolCountInfo]

    class Config:
        from_attributes = True

# === Auth Provider Management API Models ===
class AuthProviderCreatePayload(BaseModel):
    provider_id: str
    provider_name: str
    provider_type: str
    type: str
    client_id: str
    client_secret: str
    is_built_in: bool = True
    options: Optional[Dict[str, Any]] = None

class AuthProviderUpdatePayload(BaseModel):
    provider_name: str
    provider_type: str
    type: str
    client_id: str
    client_secret: str
    is_built_in: bool = True
    options: Optional[Dict[str, Any]] = None


@user_router.get("/tenants/{tenant_name}/agents", response_model=List[AgentInfo])
def get_all_agents_api(
    tenant_name: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all agents from the database for a specific tenant with pagination.
    Requires authentication via access token.
    """
    from integrator.iam.iam_db_crud import get_all_agents
    from integrator.iam.iam_db_model import RoleAgent
    from sqlalchemy import func
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Get agents using the CRUD function
    agents = get_all_agents(db, tenant_name, skip=skip, limit=limit)
    
    # Enrich with roles information
    agent_infos = []
    for agent in agents:
        # Get roles for this agent
        roles_query = db.query(RoleAgent.role_name).filter(
            (RoleAgent.agent_id == agent.agent_id) &
            (RoleAgent.tenant_name == tenant_name)
        ).all()
        roles = [role.role_name for role in roles_query]
        
        agent_info = AgentInfo(
            agent_id=agent.agent_id,
            name=agent.name,
            roles=roles
        )
        agent_infos.append(agent_info)
    
    return agent_infos

@user_router.get("/tenants/{tenant_name}/users", response_model=List[UserInfo])
def get_all_users_api(
    tenant_name: str,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all users from the database for a specific tenant with pagination.
    Requires authentication via access token.
    """
    from integrator.iam.iam_db_crud import get_all_users
    from integrator.iam.iam_db_model import RoleUser
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Get users using the CRUD function
    users = get_all_users(db, tenant_name, skip=skip, limit=limit)
    
    # Enrich with roles information
    user_infos = []
    for user_obj in users:
        # Get roles for this user
        roles_query = db.query(RoleUser.role_name).filter(
            (RoleUser.username == user_obj.username) &
            (RoleUser.tenant_name == tenant_name)
        ).all()
        roles = [role.role_name for role in roles_query]
        
        user_info = UserInfo(
            username=user_obj.username,
            email=user_obj.email,
            roles=roles
        )
        user_infos.append(user_info)
    
    return user_infos

@user_router.get("/tenants/{tenant_name}/users/{username}/agents", response_model=List[AgentInfo])
def get_agents_by_username_api(
    tenant_name: str,
    username: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all agents associated with a specific username in a tenant, including role and context
    from the user_agent relationship table.
    Requires authentication via access token.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Get agents for the user using the CRUD function
    agents = get_agents_by_username(db, username, tenant_name)
    
    if not agents:
        return []
    
    # Enrich with roles information from role_agent table
    agent_infos = []
    for agent_dict in agents:
        # Get roles for this agent from role_agent table
        roles_query = db.query(RoleAgent.role_name).filter(
            (RoleAgent.agent_id == agent_dict["agent_id"]) &
            (RoleAgent.tenant_name == tenant_name)
        ).all()
        roles = [role.role_name for role in roles_query]
        
        agent_info = AgentInfo(
            agent_id=agent_dict["agent_id"],
            name=agent_dict["name"],
            tenant_name=agent_dict["tenant_name"],
            roles=roles,
            role=agent_dict.get("role"),  # Role from user_agent relationship
            context=agent_dict.get("context")  # Context from user_agent relationship
        )
        agent_infos.append(agent_info)
    
    return agent_infos

@user_router.get("/tenants/{tenant_name}/roles", response_model=List[RoleInfo])
def get_all_roles(
    tenant_name: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all roles for a specific tenant.
    Requires authentication via access token.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    roles = db.query(Role).filter(Role.tenant_name == tenant_name).all()
    return [RoleInfo.from_orm(role) for role in roles]

@user_router.put("/tenants/{tenant_name}/agents/{agent_id}/roles", status_code=204)
def update_role_agent(
    tenant_name: str,
    agent_id: str,
    payload: UpdateRoleAgentPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Updates roles for a specific agent in a tenant.
    Requires authentication via access token.
    """
    from integrator.iam.iam_db_crud import insert_role_agent
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Verify agent exists in this tenant
    agent_obj = db.query(Agent).filter(
        (Agent.agent_id == agent_id) &
        (Agent.tenant_name == tenant_name)
    ).first()
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found in tenant '{tenant_name}'")
    
    # Remove all existing role_agent entries for this agent in this tenant
    db.query(RoleAgent).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.tenant_name == tenant_name)
    ).delete()
    db.flush()
    
    # Add new role_agent entries
    for role_name in payload.role_names:
        # Validate role exists in this tenant
        role = db.query(Role).filter(
            (Role.name == role_name) &
            (Role.tenant_name == tenant_name)
        ).first()
        if not role:
            continue
        insert_role_agent(db, role_name, agent_id, tenant_name)
    
    # Clear agent filter in agent profile table
    agent_profile = db.query(AgentProfile).filter(
        (AgentProfile.agent_id == agent_id) &
        (AgentProfile.tenant_name == tenant_name)
    ).first()
    if agent_profile:
        agent_profile.context = None
        db.add(agent_profile)
    
    db.commit()
    return

class UpdateRoleUserPayload(BaseModel):
    username: str
    role_names: List[str]

@user_router.put("/tenants/{tenant_name}/users/{username}/roles", status_code=204)
def update_role_user(
    tenant_name: str,
    username: str,
    payload: UpdateRoleUserPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Updates roles for a specific user in a tenant.
    Requires authentication via access token.
    """
    from integrator.iam.iam_db_crud import insert_role_user
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Verify user exists in this tenant
    user_obj = db.query(User).filter(
        (User.username == username) &
        (User.tenant_name == tenant_name)
    ).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found in tenant '{tenant_name}'")
    
    # Remove all existing role_user entries for this user in this tenant
    from integrator.iam.iam_db_model import RoleUser
    db.query(RoleUser).filter(
        (RoleUser.username == username) &
        (RoleUser.tenant_name == tenant_name)
    ).delete()
    db.flush()
    
    # Add new role_user entries
    for role_name in payload.role_names:
        # Validate role exists in this tenant
        role = db.query(Role).filter(
            (Role.name == role_name) &
            (Role.tenant_name == tenant_name)
        ).first()
        if not role:
            continue
        insert_role_user(db, role_name, username, tenant_name)
    
    db.commit()
    return

@user_router.put("/working-agent", response_model=UserLoginResponse)
def update_working_agent(
    payload: UpdateWorkingAgentPayload,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Updates the working agent for the current user.
    """
    username = user["preferred_username"]
    user_obj = db.query(User).filter_by(username=username).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Validate that the agent exists
    agent_obj = db.query(Agent).filter(Agent.agent_id == payload.working_agent_id).first()
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent with ID '{payload.working_agent_id}' not found")

    # Update the user's working agent
    user_obj.working_agent_id = payload.working_agent_id
    db.commit()

    # Return updated user login response
    from integrator.iam.iam_db_crud import get_roles_by_username
    
    working_agent_info = None
    active_tenant_info = None
    tenant_name = user_obj.tenant_name

    if user_obj.working_agent_id:
        working_agent_db = db.query(Agent).filter(Agent.agent_id == user_obj.working_agent_id).first()
        if working_agent_db:
            working_agent_info = WorkingAgentInfo(agent_id=working_agent_db.agent_id, name=working_agent_db.name)
            tenant_name = working_agent_db.tenant_name
            active_tenant_db = db.query(Tenant).filter(Tenant.name == tenant_name).first()
            if active_tenant_db:
                active_tenant_info = ActiveTenantInfo.from_orm(active_tenant_db)

    # Fetch user roles with tenant_name
    roles_objs = get_roles_by_username(db, username, tenant_name)
    roles = [role.name for role in roles_objs] if roles_objs else []

    return UserLoginResponse(
        username=user_obj.username,
        user_type="human",
        active_tenant=active_tenant_info,
        roles=roles
    )

@user_router.get("/login", response_model=UserLoginResponse)
def user_login(user=Depends(validate_token), db: Session = Depends(get_db)):
    from integrator.iam.iam_db_crud import get_roles_by_username
    username = user["preferred_username"]
    user_type = user.get("user_type")
    
    if user_type == "agent":
        user_obj = db.query(Agent).filter(Agent.agent_id == username).first()
    else:    
        user_obj = db.query(User).filter_by(username=username).first()
    
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Get tenant_name from user object
    tenant_name = user_obj.tenant_name
    
    # Get active tenant info
    active_tenant_info = None
    if tenant_name:
        active_tenant_db = db.query(Tenant).filter(Tenant.name == tenant_name).first()
        if active_tenant_db:
            active_tenant_info = ActiveTenantInfo.from_orm(active_tenant_db)
 
    # Fetch user roles with tenant_name
    roles_objs = get_roles_by_username(db, username, tenant_name)
    roles = [role.name for role in roles_objs] if roles_objs else []

    return UserLoginResponse(
        username=username,
        user_type=user_type,
        active_tenant=active_tenant_info,
        roles=roles
    )


@user_router.get("/login-user-agents", response_model=List[AgentInfo])
def get_login_user_agents(user=Depends(validate_token), db: Session = Depends(get_db)):
    """
    Gets all agents for the current authenticated user via access token.
    Returns the list of agents with their roles and context.
    """
    username = user["preferred_username"]
    
    # Get user object to extract tenant_name
    user_obj = db.query(User).filter(User.username == username).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")
    
    tenant_name = user_obj.tenant_name

    agents = get_agents_by_username(db, username, tenant_name)
    if not agents:
        raise HTTPException(status_code=404, detail="agents not found")

    # Enrich with roles information from role_agent table
    agent_infos = []
    for agent_dict in agents:
        # Get roles for this agent from role_agent table
        roles_query = db.query(RoleAgent.role_name).filter(
            (RoleAgent.agent_id == agent_dict["agent_id"]) &
            (RoleAgent.tenant_name == tenant_name)
        ).all()
        roles = [role.role_name for role in roles_query]
        
        agent_info = AgentInfo(
            agent_id=agent_dict["agent_id"],
            name=agent_dict["name"],
            tenant_name=agent_dict["tenant_name"],
            roles=roles,
            role=agent_dict.get("role"),  # Role from user_agent relationship
            context=agent_dict.get("context")  # Context from user_agent relationship
        )
        agent_infos.append(agent_info)
    
    return agent_infos


@user_router.put("/agents/{agent_id}/tenants/{tenant_name}/app_keys", response_model=TenantResponse)
async def update_app_key(
    agent_id: str,
    tenant_name: str,
    payload: ServiceSecretUpdatePayload,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    # Optional: Validate that the user has rights to this agent/tenant
    # For now, we proceed directly with the provided agent_id and tenant_name

    # Check if the application exists, if not, create it
    application = db.query(Application).filter(
        Application.app_name == payload.app_name
    ).first()

    if not application:
        application = Application(
            app_name=payload.app_name,
            agent_id=agent_id,
            active_tenant_name=tenant_name
        )
        db.add(application)
        db.flush() # Use flush to get the ID before commit

    # Upsert logic for ServiceSecret
    existing_secret = db.query(AppKey).filter(
        AppKey.tenant_name == tenant_name,
        AppKey.app_name == payload.app_name,
        AppKey.agent_id == agent_id
    ).first()

    if existing_secret:
        existing_secret.secrets = payload.secrets
        db.add(existing_secret)
    else:
        new_secret_entry = AppKey(
            tenant_name=tenant_name,
            app_name=payload.app_name,
            agent_id=agent_id,
            secrets=payload.secrets
        )
        db.add(new_secret_entry)
    
    db.commit()

    # Since we no longer have a direct relationship from Tenant to ServiceSecret,
    # we can just return the tenant information.
    tenant_to_return = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_to_return:
        raise HTTPException(status_code=404, detail="Tenant not found after update")

    return tenant_to_return


@user_router.delete("/agents/{agent_id}/tenants/{tenant_name}/app_keys/{app_name}", status_code=204)
async def delete_app_key(
    agent_id: str,
    tenant_name: str,
    app_name: str,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Deletes an app key for a specific agent and tenant.
    """
    rs = validate_agent_id(db, user, agent_id)
    if not rs:
        raise HTTPException(status_code=403, detail="User cannot delete secrets for an agent that is not their working agent.")
    
    # Verify agent exists
    working_agent_db = db.query(Agent).filter(
        (Agent.agent_id == agent_id) &
        (Agent.tenant_name == tenant_name)
    ).first()
    if not working_agent_db:
        raise HTTPException(status_code=404, detail="Agent not found in specified tenant")

    # Verify tenant exists
    user_active_tenant = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not user_active_tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    # Find and delete the secret
    secret_to_delete = db.query(AppKey).filter(
        (AppKey.tenant_name == tenant_name) &
        (AppKey.app_name == app_name) &
        (AppKey.agent_id == agent_id)
    ).first()

    if not secret_to_delete:
        raise HTTPException(status_code=404, detail=f"Service secret for app '{app_name}' not found in tenant '{tenant_name}' for the specified agent.")

    db.delete(secret_to_delete)
    db.commit()

    return


@user_router.get("/agents/{agent_id}/tenants/{tenant_name}/app_keys", response_model=Dict[str, Dict[str, Any]])
def get_app_keys(
    agent_id: str,
    tenant_name: str,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    secrets_query = db.query(AppKey).filter(
        AppKey.agent_id == agent_id,
        AppKey.tenant_name == tenant_name,
    ).all()

    secrets_dict = {secret.app_name: secret.secrets for secret in secrets_query}
    
    return secrets_dict
@user_router.get("/agents/{agent_id}/tenants/{tenant_name}/app_keys/{app_name}", response_model=Dict[str, Dict[str, Any]])
def get_app_key(
    agent_id: str,
    tenant_name: str,
    app_name: str,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    secrets_query = db.query(AppKey).filter(
        AppKey.agent_id == agent_id,
        AppKey.tenant_name == tenant_name,
        AppKey.app_name == app_name
    ).all()

    secrets_dict = {secret.app_name: secret.secrets for secret in secrets_query}
    
    return secrets_dict

class ApplicationInfo(BaseModel):
    app_name: str
    app_note: Optional[str] = None

    class Config:
        from_attributes = True

@user_router.get("/tenants/{tenant_name}/applications", response_model=List[ApplicationInfo])
def get_all_applications(
    tenant_name: str,
    user: dict = Depends(validate_token),
    db: Session = Depends(get_db)
):
    """
    Retrieves all applications with their names and notes from the applications table for a specific tenant.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Note: Application table doesn't have tenant_name field, so we return all applications
    # This may need to be updated if applications should be tenant-specific
    applications = db.query(Application).all()
    return [ApplicationInfo.from_orm(app) for app in applications]




@user_router.get("/tenants/{tenant_name}/auth_providers", response_model=List[AuthProviderInfo])
def get_auth_providers(
    tenant_name: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves a list of authentication providers for a given tenant.
    """
    # Basic validation to ensure the user is associated with the tenant could be added here
    # For simplicity, this example assumes any authenticated user can query providers for any tenant.
    
    providers_db = db.query(AuthProvider).filter(AuthProvider.tenant_name == tenant_name).all()
    
    if not providers_db:
        # It's not an error if a tenant has no providers, so return an empty list.
        return []

    providers_info = []
    for config in providers_db:
        # The sample Typescript code shows decrypting a secret.
        # However, the secret is not part of the response model, so we don't need to decrypt it here.
        # If the response model were to include sensitive info, decryption would be necessary.
        
        provider_info = AuthProviderInfo.from_orm(config)
        providers_info.append(provider_info)

    return providers_info


@user_router.get("/tenants/{tenant_name}/auth_providers_with_secrets", response_model=List[AuthProviderDetails])
def get_auth_providers_with_secrets(
    tenant_name: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves a list of authentication providers for a given tenant with all details, including decrypted secrets.
    """
    providers_db = db.query(AuthProvider).filter(AuthProvider.tenant_name == tenant_name).all()
    
    if not providers_db:
        return []

    providers_details = []
    for config in providers_db:
        decrypted_secret = decrypt(config.encrypted_secret, config.iv)
        
        provider_details = AuthProviderDetails(
            provider_id=config.provider_id,
            provider_name=config.provider_name,
            provider_type=config.provider_type,
            type=config.type,
            client_id=config.client_id,
            client_secret=decrypted_secret,
            is_built_in=config.is_built_in,
            options=config.options
        )
        providers_details.append(provider_details)

    return providers_details

# === Agent Profile API Endpoints ===

@user_router.get("/tenants/{tenant_name}/agent-profile/{agent_id}", response_model=AgentProfileInfo)
def get_agent_profile(
    tenant_name: str,
    agent_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Fetches the agent profile for a specific agent in a tenant.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    agent_profile = db.query(AgentProfile).filter(
        (AgentProfile.agent_id == agent_id) &
        (AgentProfile.tenant_name == tenant_name)
    ).first()
    if not agent_profile:
        # Create a new profile if it doesn't exist
        agent_profile = AgentProfile(
            agent_id=agent_id,
            tenant_name=tenant_name,
            context=None
        )
        db.add(agent_profile)
        db.commit()
        db.refresh(agent_profile)
    
    return AgentProfileInfo.from_orm(agent_profile)

def _load_context_schema():
    """Load the context JSON schema for validation."""
    schema_path = FilePath(__file__).parent.parent.parent.parent / "config" / "schema" / "tool_filter_schema.json"
    try:
        with open(schema_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Context schema file not found")
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid context schema file")

def _validate_context(context: dict):
    """Validate context against JSON schema."""
    if context is None:
        return  # Allow None values
    
    try:
        schema = _load_context_schema()
        jsonschema.validate(context, schema)
    except jsonschema.ValidationError as e:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid context format: {e.message}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Context validation error: {str(e)}"
        )

@user_router.put("/tenants/{tenant_name}/agent-profile/{agent_id}", response_model=AgentProfileInfo)
def update_agent_profile(
    tenant_name: str,
    agent_id: str,
    payload: UpdateAgentProfilePayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Updates the agent profile for a specific agent in a tenant.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Validate context against JSON schema if provided
    if payload.context is not None:
        _validate_context(payload.context)
    
    agent_profile = db.query(AgentProfile).filter(
        (AgentProfile.agent_id == agent_id) &
        (AgentProfile.tenant_name == tenant_name)
    ).first()
    if not agent_profile:
        # Create a new profile if it doesn't exist
        agent_profile = AgentProfile(
            agent_id=agent_id,
            tenant_name=tenant_name,
            context=payload.context
        )
        db.add(agent_profile)
    else:
        # Update existing profile
        if payload.context is not None:
            agent_profile.context = payload.context
    
    db.commit()
    db.refresh(agent_profile)
    
    return AgentProfileInfo.from_orm(agent_profile)

# === Auth Provider Management API Endpoints ===

@user_router.post("/tenants/{tenant_name}/auth_providers", response_model=AuthProviderDetails)
def create_auth_provider(
    tenant_name: str,
    payload: AuthProviderCreatePayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Creates a new authentication provider for a tenant.
    """
    from integrator.iam.iam_db_crud import upsert_auth_provider
    
    # Check if provider already exists
    existing_provider = db.query(AuthProvider).filter(
        AuthProvider.tenant_name == tenant_name,
        AuthProvider.provider_id == payload.provider_id
    ).first()
    
    if existing_provider:
        raise HTTPException(status_code=400, detail=f"Auth provider '{payload.provider_id}' already exists for tenant '{tenant_name}'")
    
    # Prepare data for upsert_auth_provider function
    provider_data = {
        "provider_id": payload.provider_id,
        "provider_name": payload.provider_name,
        "provider_type": payload.provider_type,
        "type": payload.type,
        "clientId": payload.client_id,
        "clientSecret": payload.client_secret,
        "is_built_in": payload.is_built_in,
        "options": payload.options
    }
    
    # Use the existing upsert function
    upsert_auth_provider(db, provider_data, tenant_name)
    db.commit()
    
    # Return the created provider
    created_provider = db.query(AuthProvider).filter(
        AuthProvider.tenant_name == tenant_name,
        AuthProvider.provider_id == payload.provider_id
    ).first()
    
    if not created_provider:
        raise HTTPException(status_code=500, detail="Failed to create auth provider")
    
    decrypted_secret = decrypt(created_provider.encrypted_secret, created_provider.iv)
    
    return AuthProviderDetails(
        provider_id=created_provider.provider_id,
        provider_name=created_provider.provider_name,
        provider_type=created_provider.provider_type,
        type=created_provider.type,
        client_id=created_provider.client_id,
        client_secret=decrypted_secret,
        is_built_in=created_provider.is_built_in,
        options=created_provider.options
    )

@user_router.put("/tenants/{tenant_name}/auth_providers/{provider_id}", response_model=AuthProviderDetails)
def update_auth_provider(
    tenant_name: str,
    provider_id: str,
    payload: AuthProviderUpdatePayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Updates an existing authentication provider for a tenant.
    """
    from integrator.iam.iam_db_crud import upsert_auth_provider
    
    # Check if provider exists
    existing_provider = db.query(AuthProvider).filter(
        AuthProvider.tenant_name == tenant_name,
        AuthProvider.provider_id == provider_id
    ).first()
    
    if not existing_provider:
        raise HTTPException(status_code=404, detail=f"Auth provider '{provider_id}' not found for tenant '{tenant_name}'")
    
    # Prepare data for upsert_auth_provider function
    provider_data = {
        "provider_id": provider_id,
        "provider_name": payload.provider_name,
        "provider_type": payload.provider_type,
        "type": payload.type,
        "clientId": payload.client_id,
        "clientSecret": payload.client_secret,
        "is_built_in": payload.is_built_in,
        "options": payload.options
    }
    
    # Use the existing upsert function
    upsert_auth_provider(db, provider_data, tenant_name)
    db.commit()
    
    # Return the updated provider
    updated_provider = db.query(AuthProvider).filter(
        AuthProvider.tenant_name == tenant_name,
        AuthProvider.provider_id == provider_id
    ).first()
    
    decrypted_secret = decrypt(updated_provider.encrypted_secret, updated_provider.iv)
    
    return AuthProviderDetails(
        provider_id=updated_provider.provider_id,
        provider_name=updated_provider.provider_name,
        provider_type=updated_provider.provider_type,
        type=updated_provider.type,
        client_id=updated_provider.client_id,
        client_secret=decrypted_secret,
        is_built_in=updated_provider.is_built_in,
        options=updated_provider.options
    )

@user_router.delete("/tenants/{tenant_name}/auth_providers/{provider_id}", status_code=204)
def delete_auth_provider(
    tenant_name: str,
    provider_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Deletes an authentication provider for a tenant.
    """
    from integrator.iam.iam_db_model import ProviderToken
    
    # Check if provider exists
    existing_provider = db.query(AuthProvider).filter(
        AuthProvider.tenant_name == tenant_name,
        AuthProvider.provider_id == provider_id
    ).first()
    
    if not existing_provider:
        raise HTTPException(status_code=404, detail=f"Auth provider '{provider_id}' not found for tenant '{tenant_name}'")
    
    # First, explicitly delete related provider tokens to avoid foreign key constraint issues
    db.query(ProviderToken).filter(
        ProviderToken.tenant_name == tenant_name,
        ProviderToken.provider_id == provider_id
    ).delete(synchronize_session=False)
    
    # Then delete the provider
    db.delete(existing_provider)
    db.commit()
    
    return

# === Role with Domains and Tool Counts API Endpoints ===

@user_router.get("/roles-with-tool-counts", response_model=List[RoleWithDomainsAndToolsInfo])
def get_roles_with_tool_counts(
    agent_id: Optional[str] = None,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all roles with their associated domains and tool counts.
    
    If agent_id is provided, returns only roles for that specific agent.
    If agent_id is None, returns all roles in the system.
    
    Each role includes:
    - Role information (name, label, description, type)
    - Total tool count across all domains
    - List of domains with individual tool counts
    
    Args:
        agent_id: Optional agent_id to filter roles for a specific agent
        db: Database session
        user: Authenticated user from token
        
    Returns:
        List of roles with domains and tool counts
    """
    from integrator.iam.iam_db_crud import get_roles_with_domains_and_tool_counts
    
    try:
        roles_data = get_roles_with_domains_and_tool_counts(db, agent_id=agent_id)
        
        # Convert to Pydantic models
        result = []
        for role_dict in roles_data:
            domains = [
                DomainToolCountInfo(**domain_dict)
                for domain_dict in role_dict["domains"]
            ]
            
            role_info = RoleWithDomainsAndToolsInfo(
                role_name=role_dict["role_name"],
                role_label=role_dict["role_label"],
                role_description=role_dict["role_description"],
                role_type=role_dict["role_type"],
                tool_count=role_dict["tool_count"],
                domains=domains
            )
            result.append(role_info)
        
        return result
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving roles with tool counts: {str(e)}"
        )

# === Create Agent by User API Endpoints ===

class CreateAgentByUserPayload(BaseModel):
    agent_id: str = Field(..., description="The agent ID (username) for the new agent")
    email: Optional[str] = Field(None, description="Email address for the agent")
    password: str = Field(..., description="Password for the agent")
    tenant_name: Optional[str] = Field(None, description="Tenant name (defaults to user's active tenant)")
    name: Optional[str] = Field(None, description="Display name for the agent (defaults to agent_id)")

class CreateAgentByUserResponse(BaseModel):
    agent_id: str
    name: str
    email: Optional[str] = None
    active_tenant_name: str
    created_at: datetime
    message: str

    class Config:
        from_attributes = True

@user_router.post("/tenants/{tenant_name}/users/{username}/agents", response_model=CreateAgentByUserResponse)
def create_agent_by_user(
    tenant_name: str,
    username: str,
    payload: CreateAgentByUserPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Creates a new agent for a specific user in a tenant.
    
    This endpoint performs the following steps:
    1. Creates the agent in the database
    2. Creates the agent user in Keycloak
    3. Creates the user-agent relationship with role as 'owner'
    
    Args:
        tenant_name: The tenant name
        username: The username of the user creating the agent
        payload: Agent creation data including agent_id, email, password, etc.
        db: Database session
        user: Authenticated user from token
        
    Returns:
        CreateAgentByUserResponse with agent details and success message
    """
    from integrator.iam.iam_db_crud import upsert_agent, insert_user_agent
    from integrator.iam.iam_keycloak_crud import get_admin_token, create_user, KC_CONFIG
    
    # Verify the authenticated user matches the username in the path
    authenticated_username = user.get("preferred_username")
    if authenticated_username != username:
        raise HTTPException(
            status_code=403, 
            detail="You can only create agents for your own account"
        )
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Get the user from database to verify existence
    user_obj = db.query(User).filter(
        (User.username == username) &
        (User.tenant_name == tenant_name)
    ).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found in tenant '{tenant_name}'")
    
    # Check if agent already exists in this tenant
    existing_agent = db.query(Agent).filter(
        (Agent.agent_id == payload.agent_id) &
        (Agent.tenant_name == tenant_name)
    ).first()
    if existing_agent:
        raise HTTPException(
            status_code=400, 
            detail=f"Agent with agent_id '{payload.agent_id}' already exists in tenant '{tenant_name}'"
        )
    
    try:
        # Step 1: Create agent in database
        agent_data = {
            "username": payload.agent_id,
            "name": payload.name or payload.agent_id,
            "email": payload.email or f"{payload.agent_id}@example.com",
            "enabled": True,  # Ensure the agent is enabled in Keycloak
            "credentials": [{
                "type": "password",
                "value": payload.password,
                "temporary": False
            }],
            "attributes": {
                "user_type": ["agent"]
            }
        }
        
        upsert_agent(db, agent_data, tenant_name)
        # Commit the agent to database first so it exists for foreign key constraint
        db.commit()
        
        # Step 2: Create user in Keycloak
        try:
            access_token = get_admin_token(KC_CONFIG)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            create_user(headers, tenant_name, agent_data, KC_CONFIG)
        except Exception as kc_error:
            # Rollback database changes if Keycloak creation fails
            # Delete the agent we just created
            db.query(Agent).filter(
                (Agent.agent_id == payload.agent_id) &
                (Agent.tenant_name == tenant_name)
            ).delete()
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create agent in Keycloak: {str(kc_error)}"
            )
        
        # Step 3: Create user-agent relationship with role as 'owner'
        insert_user_agent(db, username, payload.agent_id, tenant_name, role="owner", context={})
        
        # Commit the user-agent relationship
        db.commit()
        
        # Retrieve the created agent
        created_agent = db.query(Agent).filter(
            (Agent.agent_id == payload.agent_id) &
            (Agent.tenant_name == tenant_name)
        ).first()
        
        return CreateAgentByUserResponse(
            agent_id=created_agent.agent_id,
            name=created_agent.name,
            email=agent_data.get("email"),
            active_tenant_name=created_agent.tenant_name,
            created_at=created_agent.created_at,
            message=f"Agent '{payload.agent_id}' created successfully and associated with user '{username}' as owner"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating agent: {str(e)}"
        )

@user_router.delete("/tenants/{tenant_name}/users/{username}/agents/{agent_id}", status_code=204)
def delete_agent_by_user(
    tenant_name: str,
    username: str,
    agent_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Deletes an agent for a specific user in a tenant.
    
    This endpoint performs the following steps:
    1. Verifies the user owns the agent (has 'owner' role in user_agent relationship) OR user has 'administrator' role
    2. Deletes the agent from Keycloak
    3. Deletes all related data from database:
       - User-agent relationships
       - Role-agent relationships
       - Agent profile
       - App keys associated with the agent
       - Agent record itself
    
    Args:
        tenant_name: The tenant name
        username: The username of the user deleting the agent
        agent_id: The agent_id to delete
        db: Session database session
        user: Authenticated user from token
        
    Returns:
        204 No Content on success
    """
    from integrator.iam.iam_keycloak_crud import get_admin_token, delete_user, KC_CONFIG
    from integrator.iam.iam_db_crud import is_admin_user
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Check if the authenticated user is an administrator
    is_admin = is_admin_user(db, user)
    
    # Get authenticated username
    authenticated_username = user.get("preferred_username")
    
    # If not admin, verify the authenticated user matches the username in the path
    if not is_admin and authenticated_username != username:
        raise HTTPException(
            status_code=403, 
            detail="You can only delete agents for your own account"
        )
    
    # Get the user from database to verify existence (only if not admin)
    if not is_admin:
        user_obj = db.query(User).filter(
            (User.username == username) &
            (User.tenant_name == tenant_name)
        ).first()
        if not user_obj:
            raise HTTPException(status_code=404, detail=f"User '{username}' not found in tenant '{tenant_name}'")
    
    # Get the agent from database
    agent_obj = db.query(Agent).filter(
        (Agent.agent_id == agent_id) &
        (Agent.tenant_name == tenant_name)
    ).first()
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found in tenant '{tenant_name}'")
    
    # If not admin, verify the user owns this agent (has 'owner' role in user_agent relationship)
    if not is_admin:
        user_agent_rel = db.query(UserAgent).filter(
            (UserAgent.username == username) &
            (UserAgent.agent_id == agent_id) &
            (UserAgent.tenant_name == tenant_name)
        ).first()
        
        if not user_agent_rel:
            raise HTTPException(
                status_code=403, 
                detail=f"User '{username}' does not have a relationship with agent '{agent_id}'"
            )
        
        if user_agent_rel.role != "owner":
            raise HTTPException(
                status_code=403, 
                detail=f"User '{username}' is not the owner of agent '{agent_id}' and cannot delete it"
            )
    
    try:
        # Step 1: Delete agent from Keycloak
        try:
            access_token = get_admin_token(KC_CONFIG)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            delete_success = delete_user(headers, tenant_name, agent_id, KC_CONFIG)
            if not delete_success:
                # Log warning but continue with database cleanup
                logger.warning(f"Failed to delete agent '{agent_id}' from Keycloak, but continuing with database cleanup")
        except Exception as kc_error:
            # Log error but continue with database cleanup
            logger.error(f"Error deleting agent from Keycloak: {str(kc_error)}")
        
        # Step 2: Delete related data from database
        
        # Delete user-agent relationships
        db.query(UserAgent).filter(
            (UserAgent.agent_id == agent_id) &
            (UserAgent.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Delete role-agent relationships
        db.query(RoleAgent).filter(
            (RoleAgent.agent_id == agent_id) &
            (RoleAgent.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Delete agent profile
        db.query(AgentProfile).filter(
            (AgentProfile.agent_id == agent_id) &
            (AgentProfile.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Delete app keys associated with the agent
        db.query(AppKey).filter(
            (AppKey.agent_id == agent_id) &
            (AppKey.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Finally, delete the agent itself
        db.delete(agent_obj)
        
        # Commit all changes
        db.commit()
        
        logger.info(f"Agent '{agent_id}' and all related data deleted successfully by user '{username}'")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting agent: {str(e)}"
        )

# === Create and Delete User API Endpoints ===

class CreateUserPayload(BaseModel):
    username: str = Field(..., description="The username for the new user")
    email: Optional[str] = Field(None, description="Email address for the user")
    password: str = Field(..., description="Password for the user")
    tenant_name: Optional[str] = Field(None, description="Tenant name (defaults to 'default')")

class CreateUserResponse(BaseModel):
    username: str
    email: Optional[str] = None
    active_tenant_name: str
    message: str

    class Config:
        from_attributes = True

@user_router.post("/tenants/{tenant_name}/users", response_model=CreateUserResponse)
def create_user_endpoint(
    tenant_name: str,
    payload: CreateUserPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Creates a new user in a specific tenant.
    
    This endpoint performs the following steps:
    1. Creates the user in the database
    2. Creates the user in Keycloak
    
    Args:
        tenant_name: The tenant name
        payload: User creation data including username, email, password, etc.
        db: Database session
        user: Authenticated user from token
        
    Returns:
        CreateUserResponse with user details and success message
    """
    from integrator.iam.iam_db_crud import upsert_user
    from integrator.iam.iam_keycloak_crud import get_admin_token, create_user, KC_CONFIG
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Check if user already exists in this tenant
    existing_user = db.query(User).filter(
        (User.username == payload.username) &
        (User.tenant_name == tenant_name)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=400, 
            detail=f"User with username '{payload.username}' already exists in tenant '{tenant_name}'"
        )
    
    try:
        # Step 1: Create user in database
        user_data = {
            "username": payload.username,
            "email": payload.email or f"{payload.username}@example.com",
            "enabled": True,  # Ensure the user is enabled in Keycloak
            "credentials": [{
                "type": "password",
                "value": payload.password,
                "temporary": False
            }],
            "attributes": {
                "user_type": ["human"]
            }
        }
        
        upsert_user(db, user_data, tenant_name)
        # Commit the user to database first
        db.commit()
        
        # Step 2: Create user in Keycloak
        try:
            access_token = get_admin_token(KC_CONFIG)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            create_user(headers, tenant_name, user_data, KC_CONFIG)
        except Exception as kc_error:
            # Rollback database changes if Keycloak creation fails
            # Delete the user we just created
            db.query(User).filter(
                (User.username == payload.username) &
                (User.tenant_name == tenant_name)
            ).delete()
            db.commit()
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create user in Keycloak: {str(kc_error)}"
            )
        
        return CreateUserResponse(
            username=payload.username,
            email=user_data.get("email"),
            active_tenant_name=tenant_name,
            message=f"User '{payload.username}' created successfully"
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error creating user: {str(e)}"
        )

@user_router.delete("/tenants/{tenant_name}/users/{username}", status_code=204)
def delete_user_endpoint(
    tenant_name: str,
    username: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Deletes a user from a specific tenant.
    
    This endpoint performs the following steps:
    1. Deletes the user from Keycloak
    2. Deletes all related data from database:
       - User-agent relationships
       - Role-user relationships
       - User record itself
    
    Args:
        tenant_name: The tenant name
        username: The username to delete
        db: Database session
        user: Authenticated user from token
        
    Returns:
        204 No Content on success
    """
    from integrator.iam.iam_keycloak_crud import get_admin_token, delete_user, KC_CONFIG
    
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Prevent users from deleting themselves
    authenticated_username = user.get("preferred_username")
    if authenticated_username == username:
        raise HTTPException(
            status_code=403, 
            detail="You cannot delete your own account"
        )
    
    # Get the user from database
    user_obj = db.query(User).filter(
        (User.username == username) &
        (User.tenant_name == tenant_name)
    ).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User '{username}' not found in tenant '{tenant_name}'")
    
    try:
        # Step 1: Delete user from Keycloak
        try:
            access_token = get_admin_token(KC_CONFIG)
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            delete_success = delete_user(headers, tenant_name, username, KC_CONFIG)
            if not delete_success:
                # Log warning but continue with database cleanup
                logger.warning(f"Failed to delete user '{username}' from Keycloak, but continuing with database cleanup")
        except Exception as kc_error:
            # Log error but continue with database cleanup
            logger.error(f"Error deleting user from Keycloak: {str(kc_error)}")
        
        # Step 2: Delete related data from database
        
        # Delete user-agent relationships
        db.query(UserAgent).filter(
            (UserAgent.username == username) &
            (UserAgent.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Delete role-user relationships
        from integrator.iam.iam_db_model import RoleUser
        db.query(RoleUser).filter(
            (RoleUser.username == username) &
            (RoleUser.tenant_name == tenant_name)
        ).delete(synchronize_session=False)
        
        # Finally, delete the user itself
        db.delete(user_obj)
        
        # Commit all changes
        db.commit()
        
        logger.info(f"User '{username}' and all related data deleted successfully")
        
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=500,
            detail=f"Error deleting user: {str(e)}"
        )

# === Domain and Capability Info Models (for IAM endpoints) ===

class DomainInfo(BaseModel):
    id: UUID
    name: str
    label: str
    description: Optional[str] = None
    scope: Optional[str] = None
    domain_entities: Optional[List] = None
    domain_purposes: Optional[str] = None
    value_metrics: Optional[List] = None
    created_at: Optional[str] = None
    workflows: Optional[List] = None
    services: Optional[List] = None

    class Config:
        from_attributes = True

class CapabilityInfo(BaseModel):
    id: UUID
    name: str
    label: str
    description: Optional[str] = None
    business_context: Optional[List] = None
    business_processes: Optional[List] = None
    outcome: Optional[str] = None
    business_intent: Optional[List] = None
    created_at: Optional[str] = None

    class Config:
        from_attributes = True

# === User-Agent Relationship Management API Endpoints ===

class UserAgentInfo(BaseModel):
    username: str
    role: Optional[str] = None
    context: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True

class UpsertUserAgentPayload(BaseModel):
    username: str
    role: Optional[str] = "member"
    context: Optional[Dict[str, Any]] = None

@user_router.get("/agents/{agent_id}/users", response_model=List[UserAgentInfo])
def get_users_for_agent(
    agent_id: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Retrieves all users associated with a specific agent.
    
    Args:
        agent_id: The agent_id to query
        db: Database session
        user: Authenticated user from token
        
    Returns:
        List of users with their roles and context for this agent
    """
    from integrator.iam.iam_db_crud import get_users_by_agent_id
    
    # Verify agent exists
    agent_obj = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Get all user-agent relationships for this agent using CRUD function
    user_agents = get_users_by_agent_id(db, agent_id)
    
    return [UserAgentInfo.from_orm(ua) for ua in user_agents]

@user_router.put("/agents/{agent_id}/users", response_model=UserAgentInfo)
def upsert_user_to_agent(
    agent_id: str,
    payload: UpsertUserAgentPayload,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Creates or updates a user-agent relationship.
    
    Args:
        agent_id: The agent_id
        payload: User information including username, role, and context
        db: Database session
        user: Authenticated user from token
        
    Returns:
        Created or updated user-agent relationship
    """
    from integrator.iam.iam_db_crud import upsert_user_agent
    
    # Verify agent exists
    agent_obj = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent_obj:
        raise HTTPException(status_code=404, detail=f"Agent '{agent_id}' not found")
    
    # Verify user exists
    user_obj = db.query(User).filter(User.username == payload.username).first()
    if not user_obj:
        raise HTTPException(status_code=404, detail=f"User '{payload.username}' not found")
    
    # Use upsert_user_agent which handles both create and update
    upsert_user_agent(db, payload.username, agent_id, role=payload.role, context=payload.context)
    db.commit()
    
    # Return the created/updated relationship
    user_agent_rel = db.query(UserAgent).filter(
        UserAgent.username == payload.username,
        UserAgent.agent_id == agent_id
    ).first()
    
    return UserAgentInfo.from_orm(user_agent_rel)

@user_router.delete("/agents/{agent_id}/users/{username}", status_code=204)
def remove_user_from_agent(
    agent_id: str,
    username: str,
    db: Session = Depends(get_db),
    user: dict = Depends(validate_token)
):
    """
    Removes a user-agent relationship.
    
    Args:
        agent_id: The agent_id
        username: The username to remove
        db: Database session
        user: Authenticated user from token
        
    Returns:
        204 No Content on success
    """
    from integrator.iam.iam_db_crud import delete_user_agent
    
    # Verify the relationship exists
    user_agent_rel = db.query(UserAgent).filter(
        UserAgent.username == username,
        UserAgent.agent_id == agent_id
    ).first()
    
    if not user_agent_rel:
        raise HTTPException(
            status_code=404,
            detail=f"No relationship found between user '{username}' and agent '{agent_id}'"
        )
    
    # Prevent removing the owner relationship if it's the last owner
    if user_agent_rel.role == "owner":
        # Count how many owners this agent has
        owner_count = db.query(UserAgent).filter(
            UserAgent.agent_id == agent_id,
            UserAgent.role == "owner"
        ).count()
        
        if owner_count <= 1:
            raise HTTPException(
                status_code=400,
                detail="Cannot remove the last owner of an agent. Assign another owner first."
            )
    
    # Delete the relationship using CRUD function
    delete_user_agent(db, username, agent_id)
    db.commit()
    
    return

# === IAM/Role-Based Domain Endpoints ===

@user_router.get("/tenants/{tenant_name}/roles/{role_name}/domains", response_model=List[DomainInfo])
def get_domains_by_role(
    tenant_name: str,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Fetches all domains associated with a specific role in a tenant."""
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    domains = db.query(Domain).join(
        RoleDomain, Domain.name == RoleDomain.domain_name
    ).filter(
        (RoleDomain.role_name == role_name) &
        (RoleDomain.tenant_name == tenant_name)
    ).all()
    
    return [DomainInfo.from_orm(domain) for domain in domains]

@user_router.get("/tenants/{tenant_name}/domains/{domain_name}/roles", response_model=List[dict])
def get_roles_by_domain(
    tenant_name: str,
    domain_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """Fetches all roles that have access to a specific domain in a tenant."""
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    roles = db.query(Role).join(
        RoleDomain, Role.name == RoleDomain.role_name
    ).filter(
        (RoleDomain.domain_name == domain_name) &
        (RoleDomain.tenant_name == tenant_name)
    ).all()
    
    return [
        {
            "name": role.name,
            "label": role.label,
            "description": role.description
        }
        for role in roles
    ]

@user_router.get("/tenants/{tenant_name}/agent-roles/{agent_id}/domains", response_model=List[DomainInfo])
def get_domains_by_agent_roles(
    tenant_name: str,
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches all domains accessible to an agent through its assigned roles in a tenant.
    Chain: agent → roles → domains
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    domains = db.query(Domain).join(
        RoleDomain, Domain.name == RoleDomain.domain_name
    ).join(
        RoleAgent, (RoleDomain.role_name == RoleAgent.role_name) & (RoleDomain.tenant_name == RoleAgent.tenant_name)
    ).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.tenant_name == tenant_name)
    ).distinct().all()
    
    return [DomainInfo.from_orm(domain) for domain in domains]

@user_router.get("/tenants/{tenant_name}/agent-roles/{agent_id}/hierarchy")
def get_agent_role_hierarchy(
    tenant_name: str,
    agent_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches the complete role → domain → capability hierarchy for an agent in a tenant.
    Returns a nested structure showing what the agent can access.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # Get roles for the agent in this tenant
    agent_roles = db.query(Role).join(
        RoleAgent, (Role.name == RoleAgent.role_name) & (Role.tenant_name == RoleAgent.tenant_name)
    ).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.tenant_name == tenant_name)
    ).all()
    
    hierarchy = []
    
    for role in agent_roles:
        # Get domains for this role in this tenant
        role_domains = db.query(Domain).join(
            RoleDomain, Domain.name == RoleDomain.domain_name
        ).filter(
            (RoleDomain.role_name == role.name) &
            (RoleDomain.tenant_name == tenant_name)
        ).all()
        
        domains_data = []
        for domain in role_domains:
            # Get capabilities for this domain
            domain_capabilities = db.query(Capability).join(
                DomainCapability, Capability.name == DomainCapability.capability_name
            ).filter(
                DomainCapability.domain_name == domain.name
            ).all()
            
            domains_data.append({
                "id": domain.id,
                "name": domain.name,
                "label": domain.label,
                "description": domain.description,
                "capabilities": [CapabilityInfo.from_orm(cap) for cap in domain_capabilities]
            })
        
        hierarchy.append({
            "role": {
                "name": role.name,
                "label": role.label,
                "description": role.description
            },
            "domains": domains_data
        })
    
    return hierarchy

@user_router.get("/tenants/{tenant_name}/agent-roles/{agent_id}/roles/{role_name}/domains", response_model=List[DomainInfo])
def get_agent_role_domains(
    tenant_name: str,
    agent_id: str,
    role_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches domains for a specific role that an agent has access to in a tenant (for on-demand loading).
    Only returns domains if the agent actually has the specified role.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # First verify the agent has this role in this tenant
    role_exists = db.query(RoleAgent).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.role_name == role_name) &
        (RoleAgent.tenant_name == tenant_name)
    ).first()
    
    if not role_exists:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} does not have role {role_name} in tenant {tenant_name}")
    
    # Get domains for this role in this tenant
    domains = db.query(Domain).join(
        RoleDomain, Domain.name == RoleDomain.domain_name
    ).filter(
        (RoleDomain.role_name == role_name) &
        (RoleDomain.tenant_name == tenant_name)
    ).all()
    
    return [DomainInfo.from_orm(domain) for domain in domains]

@user_router.get("/tenants/{tenant_name}/agent-roles/{agent_id}/roles/{role_name}/domains/{domain_name}/capabilities", response_model=List[CapabilityInfo])
def get_agent_role_domain_capabilities(
    tenant_name: str,
    agent_id: str,
    role_name: str,
    domain_name: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Fetches capabilities for a specific domain within a role that an agent has access to in a tenant (for on-demand loading).
    Only returns capabilities if the agent has the role and the role has access to the domain.
    """
    # Verify tenant exists
    tenant_obj = db.query(Tenant).filter(Tenant.name == tenant_name).first()
    if not tenant_obj:
        raise HTTPException(status_code=404, detail=f"Tenant '{tenant_name}' not found")
    
    # First verify the agent has this role in this tenant
    role_exists = db.query(RoleAgent).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.role_name == role_name) &
        (RoleAgent.tenant_name == tenant_name)
    ).first()
    
    if not role_exists:
        raise HTTPException(status_code=404, detail=f"Agent {agent_id} does not have role {role_name} in tenant {tenant_name}")
    
    # Verify the role has access to this domain in this tenant
    role_domain_exists = db.query(RoleDomain).filter(
        (RoleDomain.role_name == role_name) &
        (RoleDomain.domain_name == domain_name) &
        (RoleDomain.tenant_name == tenant_name)
    ).first()
    
    if not role_domain_exists:
        raise HTTPException(status_code=404, detail=f"Role {role_name} does not have access to domain {domain_name} in tenant {tenant_name}")
    
    # Get capabilities for this domain
    capabilities = db.query(Capability).join(
        DomainCapability, Capability.name == DomainCapability.capability_name
    ).filter(
        DomainCapability.domain_name == domain_name
    ).all()
    
    return [CapabilityInfo.from_orm(capability) for capability in capabilities]

# IMPORTANT: Ensure the FastAPI application includes user_router.
# No new router was created, modifications were made to the existing user_router.

@user_router.get("/tenants/{tenant_name}/agents/{agent_id}", response_model=AgentInfo)
def get_agent_by_agent_id(
    tenant_name: str = PathParam(...),
    agent_id: str = PathParam(...),
    db: Session = Depends(get_db),
    current_user: dict = Depends(validate_token)
):
    """
    Get agent information by agent_id for a specific tenant.
    
    Args:
        tenant_name: Name of the tenant
        agent_id: Agent ID to look up
        db: Database session
        current_user: Validated user from token
        
    Returns:
        Agent information including agent_id, name, tenant_name, and roles
        
    Raises:
        HTTPException: 404 if agent not found, 403 if access denied
    """
    from integrator.iam.iam_db_crud import get_agent_by_agent_id as get_agent_crud
    
    validate_tenant_access(db, current_user, tenant_name)
    
    # Use CRUD function to get agent
    agent = get_agent_crud(db, agent_id, tenant_name)
    
    if not agent:
        raise HTTPException(
            status_code=404, 
            detail=f"Agent '{agent_id}' not found in tenant '{tenant_name}'"
        )
    
    # Get roles for this agent
    roles_query = db.query(RoleAgent.role_name).filter(
        (RoleAgent.agent_id == agent_id) &
        (RoleAgent.tenant_name == tenant_name)
    ).all()
    roles = [role.role_name for role in roles_query]
    
    return AgentInfo(
        agent_id=agent.agent_id,
        name=agent.name,
        tenant_name=agent.tenant_name,
        roles=roles
    )
