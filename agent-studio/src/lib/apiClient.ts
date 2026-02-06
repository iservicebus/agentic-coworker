import { getSession, signOut } from "next-auth/react";
import { logger } from "./logger";
import { getTenantFromCookie } from "./tenantUtils";

// Custom error type that includes HTTP status information
export interface ApiError extends Error {
  status?: number;
  statusText?: string;
}

const INTEGRATOR_URL = process.env.INTEGRATOR_URL || "http://localhost:6060"; // Ensure this env var is set

interface ApiClientOptions extends RequestInit {
  includeAuth?: boolean;
  xAgentId?: string | null; // Allow explicitly passing null to not send it, or a specific agent's ID
  skipLogoutOn401?: boolean; // Skip automatic logout on 401 errors
}

async function apiClient<T>(
  endpoint: string,
  options: ApiClientOptions = {},
  provider: string ="keycloak"

): Promise<T> {
  const { includeAuth = true, xAgentId, skipLogoutOn401 = false, ...fetchOptions } = options; // Destructure xAgentId and skipLogoutOn401
  const headers = new Headers(fetchOptions.headers || {});
  if (includeAuth) {
    const session = await getSession();
    const accessToken = session?.loginProvider?.accessToken ||session?.accessToken

    if (accessToken) {
      headers.append("Authorization", `Bearer ${accessToken}`);
    } else { // includeAuth is already true in this block
      // Only throw error if auth was explicitly required and no token found
      // Or handle by redirecting to login, depending on app flow
      // For example: signOut({ redirect: true, callbackUrl: '/auth/signin' });
      throw new Error("User not authenticated or access token unavailable.");
    }
  }

  // Add X-Agent-ID header
  // If xAgentId is explicitly provided in options, use that value.
  // If xAgentId is explicitly null, do not add the header.
  if (xAgentId !== undefined) {
    if (xAgentId !== null) {
      headers.append("X-Agent-ID", xAgentId);
    }
    // If xAgentId is null, do nothing (header is not added)
  }

  // Add X-Tenant header from cookie
  const tenantValue = getTenantFromCookie();
  if (tenantValue) {
    headers.append("X-Tenant", tenantValue);
  }

  if (!headers.has("Content-Type") && !(fetchOptions.body instanceof FormData)) {
    headers.append("Content-Type", "application/json");
  }
  
  const response = await fetch(`${INTEGRATOR_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401 && includeAuth && !skipLogoutOn401) {
      // Handles 401 Unauthorized errors for authenticated requests (includeAuth = true).
      // This typically occurs due to an expired or invalid session token.
      // The user will be signed out and redirected to the login page.
      // Skip this behavior if skipLogoutOn401 is true (e.g., for testing endpoints).
      console.warn(
        "API request resulted in 401 Unauthorized. This usually means the session token is expired or invalid. Signing out and redirecting to login."
      );
      await signOut({ redirect: true, callbackUrl: '/' });
      // Throw an error to stop further processing in this function,
      // as redirection will handle the user flow.
      throw new Error("Session expired or token invalid. Redirecting to login.");
    }
    
    // Handle all other HTTP errors
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`;
    
    try {
      // Try to get error details from response body
      const contentType = response.headers.get("content-type");
      if (contentType && contentType.includes("application/json")) {
        const errorData = await response.json();
        // Extract error message from common error response formats
        if (errorData.detail) {
          errorMessage = errorData.detail;
        } else if (errorData.message) {
          errorMessage = errorData.message;
        } else if (errorData.error) {
          errorMessage = errorData.error;
        } else if (typeof errorData === 'string') {
          errorMessage = errorData;
        } else {
          errorMessage = `HTTP ${response.status}: ${JSON.stringify(errorData)}`;
        }
      } else {
        // Try to get plain text error message
        const errorText = await response.text();
        if (errorText) {
          errorMessage = errorText;
        }
      }
    } catch (parseError) {
      // If we can't parse the error response, use the default message
      console.warn("Failed to parse error response:", parseError);
    }
    
    // Create a custom error with status code information
    const error = new Error(errorMessage) as Error & { status?: number; statusText?: string };
    error.status = response.status;
    error.statusText = response.statusText;
    throw error;
  }

  // Handle cases where response might be empty (e.g., 204 No Content)
  const contentType = response.headers.get("content-type");
  if (response.status === 204 || !contentType || !contentType.includes("application/json")) {
    return undefined as T; // Or an appropriate empty value
  }

  return response.json() as Promise<T>;
}

import { McpService, McpServiceResponse, McpRegistrationResponse } from '@/types/mcp'; // Added McpService and McpRegistrationResponse

export default apiClient;

// --- Tool Importer API Types ---
export type ToolDefinition = Record<string, any>; // Can be refined with actual schema

export interface StagingServiceCreatePayload {
  tenant: string;
  service_data: ToolDefinition;
}

export interface StagingServiceResponse {
  id: string; // UUID
  tenant: string;
  name: string;
  service_data: ToolDefinition;
  created_by: string;
  created_at: string; // ISO datetime string
  updated_by?: string | null;
  updated_at: string; // ISO datetime string
}

// --- Tool Importer API Functions ---

export async function convertDocToTool(url: string): Promise<ToolDefinition[]> {
  return apiClient<ToolDefinition[]>('/staging/doc-to-tool', {
    method: 'POST',
    body: JSON.stringify({ url }),
  });
}

export async function convertOpenApiByLink(openapiLink: string): Promise<ToolDefinition[]> {
  return apiClient<ToolDefinition[]>('/staging/openapi-to-tool-by-link', {
    method: 'POST',
    body: JSON.stringify({ openapi_link: openapiLink }),
  });
}

export async function convertOpenApiByFile(file: File): Promise<ToolDefinition[]> {
  const formData = new FormData();
  formData.append('openapi_file', file);
  return apiClient<ToolDefinition[]>('/staging/openapi-to-tool-by-file', {
    method: 'POST',
    body: formData,
    // Content-Type is handled by apiClient for FormData
  });
}

export async function convertPostmanToTool(file: File): Promise<ToolDefinition[]> {
  const formData = new FormData();
  formData.append('postman_file', file);
  return apiClient<ToolDefinition[]>('/staging/postman-to-tool', {
    method: 'POST',
    body: formData,
  });
}

export async function addStagingService(
  tenant: string = 'default',
  serviceData: ToolDefinition
): Promise<StagingServiceResponse> {
  const payload: StagingServiceCreatePayload = {
    tenant, // The tenant is also part of the URL path
    service_data: serviceData,
  };
  return apiClient<StagingServiceResponse>(`/staging/tenants/${tenant}/staging-services/`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function listStagingServices(
  tenantName: string,
  skip: number = 0,
  limit: number = 100
): Promise<StagingServiceResponse[]> {
  return apiClient<StagingServiceResponse[]>(
    `/staging/tenants/${tenantName}/staging-services/?skip=${skip}&limit=${limit}`,
    {
      method: 'GET',
    }
  );
}

export interface StagingServiceUpdatePayload {
  service_data: ToolDefinition;
}

export async function updateStagingService(
  tenantName: string,
  serviceId: string, // Service ID (UUID string)
  serviceData: ToolDefinition
): Promise<StagingServiceResponse> {
  const payload: StagingServiceUpdatePayload = {
    service_data: serviceData,
  };
  return apiClient<StagingServiceResponse>(
    `/staging/tenants/${tenantName}/staging-services/${serviceId}`,
    {
      method: 'PUT',
      body: JSON.stringify(payload),
    }
  );
}

export async function deleteStagingService(
  tenantName: string,
  serviceId: string
): Promise<void> {
  return apiClient<void>(
    `/staging/tenants/${tenantName}/staging-services/${serviceId}`,
    {
      method: 'DELETE',
    }
  );
}

// --- MCP Services API Functions ---

export async function registerMcpService(
  toolDefinition: McpService,
  tenant: string = 'default',
  metadataOverwrite: boolean = true
): Promise<McpRegistrationResponse> {
  const endpoint = `/mcp/services?tenant=${encodeURIComponent(tenant)}&metadata_overwrite=${metadataOverwrite}`;
  return apiClient<McpRegistrationResponse>(endpoint, {
    method: 'POST',
    body: JSON.stringify(toolDefinition),
  });
}

export async function listMcpServices(
  tenantId: string
): Promise<McpServiceResponse[]> {
  return apiClient<McpServiceResponse[]>(
    `/mcp/tenants/${tenantId}/services`,
    {
      method: 'GET',
    }
  );
}

export async function deleteMcpService(
  tenantId: string,
  serviceId: string
): Promise<void> {
  return apiClient<void>(
    `/mcp/tenants/${tenantId}/services/${serviceId}`,
    {
      method: 'DELETE',
    }
  );
}

export async function validateMcpService(service_name: string, data: any, agent_id?: string): Promise<any> {
  return apiClient<any>('/clients/mcp_validation', {
    method: 'POST',
    body: JSON.stringify({ service_name, data, agent_id }),
    skipLogoutOn401: true, // Don't logout on 401 errors for testing endpoints
  });
}

// Updated UserLogin response types based on oauth_services.py

// For updating/creating service secrets
export interface ServiceSecretPayload {
  app_name: string;
  secrets: Record<string, any>;
}

// The backend's TenantResponse includes more fields than ActiveTenantInfo
// We can use this for the PUT response if it's returned and useful.
// ActiveTenantInfo: id, name, app_keys
// TenantResponse from backend: id, name, created_by, created_at, updated_by, updated_at, app_keys
export interface TenantResponse {
  id: string;
  name: string;
  app_keys?: Record<string, Record<string, any>> | null;
  created_by: string;
  created_at: string;
  updated_by?: string | null;
  updated_at: string;
}

export interface ActiveTenantInfo {
  id: string; // UUID as string
  name: string;
  app_keys?: Record<string, Record<string, any>> | null; // e.g., { "ServiceName1": { "key1": "val1" } }
}

export interface UserLoginResponse { // This is now a single object
  username: string;
  user_type: string;
  active_tenant?: ActiveTenantInfo | null;
  roles?: string[] | null;
}

// Old types - can be removed or commented out if no longer used elsewhere
// export interface AgentInfo {
//   id: string; // Assuming UUID is string
//   agent_id: string;
// }
// export interface TenantInfo {
//   id: string; // Assuming UUID is string
//   tenant_name: string | null;
// }
// export interface UserLoginResponseItem {
//   username: string;
//   agent: AgentInfo;
//   active_tenant: TenantInfo;
//   profile_data: Record<string, any> | null;
// }

// Example AgentProfile response type (might still be used for PUT /profile updates, or can be adapted for app_keys updates)
// For service secret updates, the response is TenantResponse from backend, which is similar to ActiveTenantInfo but includes all tenant fields.
// Let's keep AgentProfile for now, but we might need a more specific TenantResponse type later if we use the PUT response directly.
export interface AgentProfile {
    id: string; // UUID
    agent_id: string; // UUID
    tenant_id: string; // UUID
    profile_data: Record<string, any>;
    created_at: string; // ISO datetime string
    updated_at: string; // ISO datetime string
}

export interface ReturnMessage {

  status: string,
  message: string,

}
// --- IAM / User Related API Functions ---

/**
 * Fetches user login data, including username, working agent, and active tenant info.
 * Uses the portal's default agent ID if no specific agentId is provided.
 * @param agentId Optional specific agent ID to use for the X-Agent-ID header.
 *                If undefined, uses default. If null, X-Agent-ID is omitted.
 */
export async function fetchUserLoginData(): Promise<UserLoginResponse> {
  // The apiClient handles the logic for xAgentId:
  // - undefined: uses PORTAL_AGENT_ID
  // - null: omits X-Agent-ID header
  // - string: uses the provided string
  return apiClient<UserLoginResponse>("/users/login", { });
}

export interface ApplicationInfo {
  app_name: string;
  app_note?: string | null;
}

/**
 * Fetches all available applications with their names and notes for a specific tenant.
 */
export async function getAllApplications(tenantName: string): Promise<ApplicationInfo[]> {
  return apiClient<ApplicationInfo[]>(`/users/tenants/${tenantName}/applications`);
}

export async function getServiceSecrets(
  agentId: string,
  tenantName: string
): Promise<Record<string, Record<string, any>>> {
  return apiClient<Record<string, Record<string, any>>>(
    `/users/agents/${agentId}/tenants/${tenantName}/app_keys`
  );
}

export async function getServiceSecret(
  agentId: string,
  tenantName: string,
  appName: string
): Promise<Record<string, Record<string, any>>> {
  return apiClient<Record<string, Record<string, any>>>(
    `/users/agents/${agentId}/tenants/${tenantName}/app_keys/${appName}`
  );
}

/**
 * Upserts (updates or creates) service secrets for a given tenant.
 * @param tenantId The ID of the tenant.
 * @param agentId The ID of the working agent performing the operation (for X-Agent-ID header).
 * @param payload The service name and secrets data.
 * @returns The updated tenant information.
 */
export async function upsertServiceSecrets(
  agentId: string,
  tenantName: string,
  payload: ServiceSecretPayload
): Promise<TenantResponse> { // Backend returns TenantResponse
  return apiClient<TenantResponse>(
    `/users/agents/${agentId}/tenants/${tenantName}/app_keys`,
    {
      method: "PUT",
      body: JSON.stringify(payload),
    }
  );
}

/**
 * Deletes a specific service's secrets for a given tenant.
 * @param agentId The ID of the working agent performing the operation (for X-Agent-ID header).
 * @param tenantName The name of the tenant.
 * @param appName The name of the app whose secrets are to be deleted.
 */
export async function deleteServiceSecret(
  agentId: string,
  tenantName: string,
  appName: string
): Promise<void> {
  return apiClient<void>( // DELETE typically returns 204 No Content
    `/users/agents/${agentId}/tenants/${tenantName}/app_keys/${appName}`,
    {
      method: "DELETE",
    }
  );
}

/**
 * Upserts (updates or creates) service secrets for a given tenant.
 * @param tenantId The ID of the tenant.
 * @param agentId The ID of the working agent performing the operation (for X-Agent-ID header).
 * @param payload The service name and secrets data.
 * @returns The updated tenant information.
 */
export async function updateProvider(
  provider: string,
  agentId: string,     // New parameter
  tenantName: string   // New parameter
): Promise<ReturnMessage> { 
    const session = await getSession();

    const payload = {
        // Use the 'provider' argument passed to the function,
        // as session.provider is not a defined property on the Session type.
        provider_id: provider,
        tenant_name: tenantName,
        agent_id: agentId,

        token: { accessToken: session?.accessToken } // The user's current session token


    };


    logger.info("payload for updateProvider", payload);

    return apiClient<ReturnMessage>(
        `/oauth/update_credential/providers/${provider}`,
        {
            method: "PUT",
            body: JSON.stringify(payload),
            // X-Agent-ID header is handled by apiClient based on its options or defaults.
            // If this specific endpoint requires a different X-Agent-ID than the default (PORTAL_AGENT_ID),
            // then the `xAgentId` option would need to be passed to `apiClient` here.
            // For now, assuming default handling is fine or `agentId` in payload is sufficient.
        }
    );
}

export interface AuthProvider {
  provider_id: string;
  type: string;
  client_id: string;
  options?: Record<string, any> | null;
}

export async function getAuthProviders(tenantName: string): Promise<AuthProvider[]> {
  return apiClient<AuthProvider[]>(`/users/tenants/${tenantName}/auth_providers`);
}

// Auth Provider Management API Functions
export interface AuthProviderCreatePayload {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  type: string;
  client_id: string;
  client_secret: string;
  is_built_in: boolean;
  options?: Record<string, any> | null;
}

export interface AuthProviderUpdatePayload {
  provider_name: string;
  provider_type: string;
  type: string;
  client_id: string;
  client_secret: string;
  is_built_in: boolean;
  options?: Record<string, any> | null;
}

export interface AuthProviderDetails {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  type: string;
  client_id: string;
  client_secret: string;
  is_built_in: boolean;
  options?: Record<string, any> | null;
}

export async function createAuthProvider(
  tenantName: string,
  payload: AuthProviderCreatePayload
): Promise<AuthProviderDetails> {
  return apiClient<AuthProviderDetails>(`/users/tenants/${tenantName}/auth_providers`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

export async function updateAuthProvider(
  tenantName: string,
  providerId: string,
  payload: AuthProviderUpdatePayload
): Promise<AuthProviderDetails> {
  return apiClient<AuthProviderDetails>(`/users/tenants/${tenantName}/auth_providers/${providerId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export async function deleteAuthProvider(
  tenantName: string,
  providerId: string
): Promise<void> {
  return apiClient<void>(`/users/tenants/${tenantName}/auth_providers/${providerId}`, {
    method: 'DELETE',
  });
}

export async function getAuthProvidersWithSecrets(tenantName: string): Promise<AuthProviderDetails[]> {
  return apiClient<AuthProviderDetails[]>(`/users/tenants/${tenantName}/auth_providers_with_secrets`);
}

export interface ProviderTokenResponse {
  id: string;
  provider_id: string;
  tenant_name: string;
  token: Record<string, any>;
  username?: string | null;
  agent_id?: string | null;
  created_at: string;
  updated_at: string;
}

export async function getSpecificProviderToken(
  tenantName: string,
  providerId: string,
  agentId: string,
): Promise<ProviderTokenResponse> {
  return apiClient<ProviderTokenResponse>(
    `/provider_tokens/tenants/${tenantName}/providers/${providerId}/agents/${agentId}`
  );
}

// --- Agent Management API Functions ---

export interface AgentInfo {
  agent_id: string;
  name?: string | null;
  active_tenant_name?: string | null;
  roles?: string[] | null;
  role?: string | null;  // Role from user_agent relationship
  context?: Record<string, any> | null;  // Context from user_agent relationship
}

export interface UserInfo {
  username: string;
  email?: string | null;
  roles?: string[] | null;
}

export interface RoleInfo {
  name: string;
  label: string;
  description?: string | null;
}

export interface UpdateRoleAgentPayload {
  agent_id: string;
  role_names: string[];
}

/**
 * Fetches all agents for a specific tenant.
 */
export async function getAllAgents(tenantName: string): Promise<AgentInfo[]> {
  return apiClient<AgentInfo[]>(`/users/tenants/${tenantName}/agents`);
}

/**
 * Fetches all agents associated with a specific username in a tenant.
 */
export async function getAgentsByUsername(tenantName: string, username: string): Promise<AgentInfo[]> {
  return apiClient<AgentInfo[]>(`/users/tenants/${tenantName}/users/${username}/agents`);
}

/**
 * Fetches all users for a specific tenant.
 */
export async function getAllUsers(tenantName: string): Promise<UserInfo[]> {
  return apiClient<UserInfo[]>(`/users/tenants/${tenantName}/users`);
}

/**
 * Fetches all roles for a specific tenant.
 */
export async function getAllRoles(tenantName: string): Promise<RoleInfo[]> {
  return apiClient<RoleInfo[]>(`/users/tenants/${tenantName}/roles`);
}

/**
 * Updates roles for a specific agent in a tenant.
 */
export async function updateAgentRoles(
  tenantName: string,
  agentId: string,
  roleNames: string[]
): Promise<void> {
  const payload: UpdateRoleAgentPayload = {
    agent_id: agentId,
    role_names: roleNames,
  };
  return apiClient<void>(`/users/tenants/${tenantName}/agents/${agentId}/roles`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export interface UpdateRoleUserPayload {
  username: string;
  role_names: string[];
}

/**
 * Updates roles for a specific user in a tenant.
 */
export async function updateUserRoles(
  tenantName: string,
  username: string,
  roleNames: string[]
): Promise<void> {
  const payload: UpdateRoleUserPayload = {
    username: username,
    role_names: roleNames,
  };
  return apiClient<void>(`/users/tenants/${tenantName}/users/${username}/roles`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

// --- Create and Delete Agent API Functions ---

export interface CreateAgentPayload {
  agent_id: string;
  email?: string | null;
  password: string;
  tenant_name?: string | null;
  name?: string | null;
}

export interface CreateAgentResponse {
  agent_id: string;
  name: string;
  email?: string | null;
  active_tenant_name: string;
  created_at: string;
  message: string;
}

/**
 * Creates a new agent for a specific user in a tenant.
 */
export async function createAgentByUser(
  tenantName: string,
  username: string,
  payload: CreateAgentPayload
): Promise<CreateAgentResponse> {
  return apiClient<CreateAgentResponse>(`/users/tenants/${tenantName}/users/${username}/agents`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Deletes an agent for a specific user in a tenant.
 */
export async function deleteAgentByUser(
  tenantName: string,
  username: string,
  agentId: string
): Promise<void> {
  return apiClient<void>(`/users/tenants/${tenantName}/users/${username}/agents/${agentId}`, {
    method: 'DELETE',
  });
}

// --- Create and Delete User API Functions ---

export interface CreateUserPayload {
  username: string;
  email?: string | null;
  password: string;
  tenant_name?: string | null;
}

export interface CreateUserResponse {
  username: string;
  email?: string | null;
  active_tenant_name: string;
  message: string;
}

/**
 * Creates a new user in a specific tenant.
 */
export async function createUser(
  tenantName: string,
  payload: CreateUserPayload
): Promise<CreateUserResponse> {
  return apiClient<CreateUserResponse>(`/users/tenants/${tenantName}/users`, {
    method: 'POST',
    body: JSON.stringify(payload),
  });
}

/**
 * Deletes a user from a specific tenant.
 */
export async function deleteUser(
  tenantName: string,
  username: string
): Promise<void> {
  return apiClient<void>(`/users/tenants/${tenantName}/users/${username}`, {
    method: 'DELETE',
  });
}

// --- Domain Management API Functions ---

export interface DomainInfo {
  id: string; // UUID as string
  name: string;
  label: string;
  description?: string | null;
  scope?: string | null;
  domain_entities?: any[] | null;
  domain_purposes?: string | null;
  value_metrics?: any[] | null;
  created_at?: string | null;
  workflows?: any[] | null;
  services?: any[] | null;
}

export interface CapabilityInfo {
  id: string;
  name: string;
  label: string;
  description?: string | null;
  business_context?: any[] | null;
  business_processes?: any[] | null;
  outcome?: string | null;
  business_intent?: any[] | null;
  created_at?: string | null;
}

export interface SkillInfo {
  name: string;
  label: string;
  description?: string | null;
  operational_entities?: any[] | null;
  operational_procedures?: any[] | null;
  operational_intent?: string | null;
  preconditions?: any[] | null;
  postconditions?: any[] | null;
  proficiency?: string | null;
}

export interface DomainWithCapabilities {
  id: string;
  name: string;
  label: string;
  description?: string | null;
  scope?: string | null;
  domain_entities?: any[] | null;
  domain_purposes?: string | null;
  value_metrics?: any[] | null;
  created_at?: string | null;
  capabilities: CapabilityInfo[];
}



export interface AgentProfileInfo {
  agent_id: string;
  context?: Record<string, any> | null;
}

export interface UpdateAgentProfilePayload {
  context?: Record<string, any> | null;
}

/**
 * Fetches all domains for a specific tenant.
 * @param tenantName Tenant name.
 */
export async function getAllDomains(): Promise<DomainInfo[]> {
  return apiClient<DomainInfo[]>(`/domains/domains`);
}

/**
 * Fetches capabilities available to the current user's active agent.
 * This endpoint is user-based and tenant-aware through IAM.
 */
export async function getAllCapabilities(): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>("/domains/capabilities");
}

/**
 * Fetches all skills for a specific tenant.
 * @param tenantName Tenant name.
 */
export async function getAllSkills(tenantName: string): Promise<SkillInfo[]> {
  return apiClient<SkillInfo[]>(`/tools/tenants/${tenantName}/skills`);
}


/**
 * Fetches all domains with their associated capabilities for a specific tenant.
 * @param tenantName Tenant name.
 */
export async function getDomainsWithCapabilities(tenantName: string): Promise<DomainWithCapabilities[]> {
  return apiClient<DomainWithCapabilities[]>(`/domains/tenants/${tenantName}/domains-with-capabilities`);
}

/**
 * Fetches the agent profile for a specific agent in a tenant.
 */
export async function getAgentProfile(tenantName: string, agentId: string): Promise<AgentProfileInfo> {
  return apiClient<AgentProfileInfo>(`/users/tenants/${tenantName}/agent-profile/${agentId}`);
}

/**
 * Updates the agent profile for a specific agent in a tenant.
 */
export async function updateAgentProfile(
  tenantName: string,
  agentId: string,
  payload: UpdateAgentProfilePayload
): Promise<AgentProfileInfo> {
  return apiClient<AgentProfileInfo>(`/users/tenants/${tenantName}/agent-profile/${agentId}`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

export interface CapabilitySearchResult {
  name: string;
  label: string;
  description?: string | null;
  intent?: string | null;
  similarity: number;
}

/**
 * Query capabilities using vector search for current user's active agent.
 */
export async function queryCapabilitiesByVector(
  query: string,
  limit: number = 10
): Promise<CapabilitySearchResult[]> {
  return apiClient<CapabilitySearchResult[]>(`/domains/capabilities/query?query=${encodeURIComponent(query)}&limit=${limit}`);
}

/**
 * Search capabilities by query string for a specific tenant.
 * @param tenantName Tenant name.
 * @param query Search query string.
 * @param limit Maximum number of results.
 */
export async function searchCapabilities(
  tenantName: string,
  query: string,
  limit: number = 10
): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>(`/domains/tenants/${tenantName}/capabilities/search?query=${encodeURIComponent(query)}&limit=${limit}`);
}

/**
 * Get capabilities available to current user's active agent.
 */
export async function getUserCapabilities(): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>("/domains/capabilities");
}

// --- User-Agent Relationship Management API Functions ---

export interface UserAgentRelationship {
  username: string;
  role?: string | null;
  context?: Record<string, any> | null;
}

export interface UpsertUserAgentPayload {
  username: string;
  role?: string;
  context?: Record<string, any> | null;
}

/**
 * Get all users associated with a specific agent.
 */
export async function getUsersForAgent(agentId: string): Promise<UserAgentRelationship[]> {
  return apiClient<UserAgentRelationship[]>(`/users/agents/${agentId}/users`);
}

/**
 * Create or update a user-agent relationship.
 */
export async function upsertUserAgentRelationship(
  agentId: string,
  payload: UpsertUserAgentPayload
): Promise<UserAgentRelationship> {
  return apiClient<UserAgentRelationship>(`/users/agents/${agentId}/users`, {
    method: 'PUT',
    body: JSON.stringify(payload),
  });
}

/**
 * Remove a user-agent relationship.
 */
export async function removeUserFromAgent(
  agentId: string,
  username: string
): Promise<void> {
  return apiClient<void>(`/users/agents/${agentId}/users/${username}`, {
    method: 'DELETE',
  });
}

/**
 * Fetches skills for a specific capability in a tenant.
 * @param tenantName Tenant name.
 * @param capabilityName Capability name.
 */
export async function getSkillsByCapability(tenantName: string, capabilityName: string): Promise<SkillInfo[]> {
  return apiClient<SkillInfo[]>(`/tools/tenants/${tenantName}/capabilities/${capabilityName}/skills`);
}

/**
 * Fetches capabilities for a specific skill in a tenant.
 * @param tenantName Tenant name.
 * @param skillName Skill name.
 */
export async function getCapabilitiesBySkill(tenantName: string, skillName: string): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>(`/tools/tenants/${tenantName}/skills/${skillName}/capabilities`);
}

/**
 * Fetches domains for a specific capability in a tenant.
 * @param tenantName Tenant name.
 * @param capabilityName Capability name.
 */
export async function getDomainsByCapability(tenantName: string, capabilityName: string): Promise<DomainInfo[]> {
  return apiClient<DomainInfo[]>(`/domains/tenants/${tenantName}/capabilities/${capabilityName}/domains`);
}

/**
 * Fetches skills for a specific MCP tool in a tenant.
 * @param tenantName Tenant name.
 * @param toolId Tool ID.
 */
export async function getSkillsForMcpTool(tenantName: string, toolId: string): Promise<string[]> {
  return apiClient<string[]>(`/tools/tenants/${tenantName}/mcp-tools/${toolId}/skills`);
}

/**
 * Fetches capabilities for a specific domain in a tenant.
 * @param tenantName Tenant name.
 * @param domainName Domain name.
 */
export async function getCapabilitiesByDomain(tenantName: string, domainName: string): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>(`/domains/tenants/${tenantName}/domains/${encodeURIComponent(domainName)}/capabilities`);
}

/**
 * Fetches MCP tools for a specific capability in a tenant.
 * @param tenantName Tenant name.
 * @param capabilityName Capability name.
 */
export async function getMcpToolsByCapability(tenantName: string, capabilityName: string): Promise<McpToolInfo[]> {
  return apiClient<McpToolInfo[]>(`/tools/tenants/${tenantName}/capabilities/${encodeURIComponent(capabilityName)}/mcp-tools`);
}

/**
 * Fetches MCP tools for a specific skill in a tenant.
 * @param tenantName Tenant name.
 * @param skillName Skill name.
 */
export async function getMcpToolsBySkill(tenantName: string, skillName: string): Promise<McpToolInfo[]> {
  return apiClient<McpToolInfo[]>(`/tools/tenants/${tenantName}/skills/${skillName}/mcp-tools`);
}

// --- MCP Tools Search API Functions ---

export interface McpToolInfo {
  id: string;
  name: string;
  description?: string | null;
  document?: Record<string, any> | null;
  meta_data?: Record<string, any> | null;
  agent_id?: string | null;
  tenant: string;
  cosine_similarity?: number | null;
}

// Tool filter schema types matching tool_filter_schema.json
export interface ToolFilterCapability {
  name: string;
  skills?: string[];
}

export interface ToolFilterDomain {
  name: string;
  capabilities?: ToolFilterCapability[];
}

export interface ToolFilterRole {
  name: string;
  domains?: ToolFilterDomain[];
}

export interface ToolFilter {
  tool_query?: string;
  roles?: ToolFilterRole[];
}

export interface McpToolSearchParams {
  agent_id?: string | null;
  filter?: ToolFilter | null;
  tool_query?: string | null;
  k?: number;
}

/**
 * Search MCP tools with flexible filtering options and strict tenant isolation.
 * 
 * Logic:
 * 1. All tools are filtered by tenant_name (required parameter)
 * 2. If agent_id is not provided, get all MCP tools for the tenant
 * 3. If agent_id is provided, follow the relationship chain: agent -> roles -> domains -> capabilities -> tools (within tenant)
 * 4. If filter (JSON schema) is provided, further filter tools based on the hierarchical structure
 * 5. If tool_query is provided, further narrow the tool output using vector search
 * 
 * @param tenantName Tenant name for strict isolation (REQUIRED)
 * @param params Search parameters including agent_id, filter, tool_query, and k
 * @returns Promise<McpToolInfo[]> List of matching MCP tools
 */
export async function searchMcpTools(tenantName: string, params: McpToolSearchParams = {}): Promise<McpToolInfo[]> {
  return apiClient<McpToolInfo[]>(`/tools/mcp-tools/search?tenant_name=${encodeURIComponent(tenantName)}`, {
    method: 'POST',
    body: JSON.stringify(params),
  });
}

/**
 * Get MCP tools for a specific agent (legacy endpoint).
 * This is a simplified wrapper around the search endpoint for backward compatibility.
 */
export async function getMcpToolsForAgent(
  agentId: string,
  toolQuery?: string,
  k?: number
): Promise<McpToolInfo[]> {
  const searchParams = new URLSearchParams();
  
  if (toolQuery) searchParams.append('tool_query', toolQuery);
  if (k) searchParams.append('k', k.toString());
  
  const queryString = searchParams.toString();
  const endpoint = queryString 
    ? `/tools/mcp-tools/agent/${agentId}?${queryString}` 
    : `/tools/mcp-tools/agent/${agentId}`;
  
  return apiClient<McpToolInfo[]>(endpoint);
}

/**
 * Get all MCP tools (admin endpoint).
 * Simplified to remove domain_names and capability_names parameters.
 */
export async function getAllMcpToolsAdmin(
  toolQuery?: string,
  k?: number
): Promise<McpToolInfo[]> {
  const searchParams = new URLSearchParams();
  
  if (toolQuery) searchParams.append('tool_query', toolQuery);
  if (k) searchParams.append('k', k.toString());
  
  const queryString = searchParams.toString();
  const endpoint = queryString 
    ? `/tools/mcp-tools/admin?${queryString}` 
    : '/tools/mcp-tools/admin';
  
  return apiClient<McpToolInfo[]>(endpoint);
}

// --- Role-based Hierarchical Filter API Functions ---

export interface RoleHierarchyItem {
  role: {
    name: string;
    label: string;
    description?: string | null;
  };
  domains: Array<{
    id: string;
    name: string;
    label: string;
    description?: string | null;
    capabilities: CapabilityInfo[];
  }>;
}

/**
 * Get domains associated with a specific role in a tenant.
 */
export async function getDomainsByRole(tenantName: string, roleName: string): Promise<DomainInfo[]> {
  return apiClient<DomainInfo[]>(`/users/tenants/${tenantName}/roles/${roleName}/domains`);
}

/**
 * Get roles associated with a specific domain in a tenant.
 */
export async function getRolesByDomain(tenantName: string, domainName: string): Promise<RoleInfo[]> {
  return apiClient<RoleInfo[]>(`/users/tenants/${tenantName}/domains/${domainName}/roles`);
}

/**
 * Get domains accessible to an agent through its assigned roles in a tenant.
 */
export async function getDomainsByAgentRoles(tenantName: string, agentId: string): Promise<DomainInfo[]> {
  return apiClient<DomainInfo[]>(`/users/tenants/${tenantName}/agent-roles/${agentId}/domains`);
}

/**
 * Get the complete role → domain → capability hierarchy for an agent in a tenant.
 * This is used for building hierarchical filters restricted by agent roles.
 */
export async function getAgentRoleHierarchy(tenantName: string, agentId: string): Promise<RoleHierarchyItem[]> {
  return apiClient<RoleHierarchyItem[]>(`/users/tenants/${tenantName}/agent-roles/${agentId}/hierarchy`);
}

/**
 * Get only the roles accessible to an agent (for on-demand loading) in a tenant.
 */
export async function getAgentRoles(tenantName: string, agentId: string): Promise<RoleInfo[]> {
  return apiClient<RoleInfo[]>(`/users/tenants/${tenantName}/agent-roles/${agentId}/roles`);
}

// --- Chat API Types and Functions ---

export interface ChatMessage {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
  metadata?: Record<string, any>;
}

export interface CreateChatSessionRequest {
  agent_id?: string;
}

export interface CreateChatSessionResponse {
  session_id: string;
  thread_id: string;
  user_id: string;
  agent_id?: string;
  created_at: string;
  message: string;
}

export interface ChatMessageRequest {
  session_id: string;
  message: string;
}

export interface ChatMessageResponse {
  session_id: string;
  user_message: string;
  agent_response: string;
  messages: Array<{
    role: string;
    content: string;
    [key: string]: any;
  }>;
}

export interface ChatSessionInfo {
  session_id: string;
  user_id: string;
  agent_id?: string;
  thread_id: string;
  created_at: string;
  last_accessed: string;
  metadata: Record<string, any>;
}

export interface DeleteChatSessionResponse {
  session_id: string;
  message: string;
}

/**
 * Create a new chat session
 */
export async function createChatSession(
  agentId?: string,
  requestAgentId?: string
): Promise<CreateChatSessionResponse> {
  return apiClient<CreateChatSessionResponse>('/agents/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({ agent_id: agentId }),
    xAgentId: requestAgentId,
  });
}

/**
 * Send a message to the agent
 */
export async function sendChatMessage(
  sessionId: string,
  message: string,
  agentId?: string
): Promise<ChatMessageResponse> {
  return apiClient<ChatMessageResponse>('/agents/chat/message', {
    method: 'POST',
    body: JSON.stringify({
      session_id: sessionId,
      message: message,
    }),
    xAgentId: agentId,
  });
}

/**
 * Get session information
 */
export async function getChatSession(
  sessionId: string,
  agentId?: string
): Promise<ChatSessionInfo> {
  return apiClient<ChatSessionInfo>(`/agents/chat/sessions/${sessionId}`, {
    method: 'GET',
    xAgentId: agentId,
  });
}

/**
 * List all user sessions
 */
export async function listChatSessions(
  agentId?: string
): Promise<ChatSessionInfo[]> {
  return apiClient<ChatSessionInfo[]>('/agents/chat/sessions', {
    method: 'GET',
    xAgentId: agentId,
  });
}

/**
 * Delete a chat session
 */
export async function deleteChatSession(
  sessionId: string,
  agentId?: string
): Promise<DeleteChatSessionResponse> {
  return apiClient<DeleteChatSessionResponse>(`/agents/chat/sessions/${sessionId}`, {
    method: 'DELETE',
    xAgentId: agentId,
  });
}

/**
 * Get domains for a specific role that an agent has access to in a tenant (for on-demand loading).
 */
export async function getAgentRoleDomains(tenantName: string, agentId: string, roleName: string): Promise<DomainInfo[]> {
  return apiClient<DomainInfo[]>(`/users/tenants/${tenantName}/agent-roles/${agentId}/roles/${roleName}/domains`);
}

/**
 * Get capabilities for a specific domain within a role that an agent has access to in a tenant (for on-demand loading).
 */
export async function getAgentRoleDomainCapabilities(
  tenantName: string,
  agentId: string, 
  roleName: string, 
  domainName: string
): Promise<CapabilityInfo[]> {
  return apiClient<CapabilityInfo[]>(`/users/tenants/${tenantName}/agent-roles/${agentId}/roles/${roleName}/domains/${domainName}/capabilities`);
}


// --- Tool Annotation API Functions ---

export interface ToolAnnotationRequest {
  name: string;
  description: string;
  inputSchema: Record<string, any>;
}

export interface ToolAnnotationResponse {
  annotation_result?: Record<string, any> | null;
  success: boolean;
  error_message?: string | null;
}

/**
 * Annotate a tool using LLM to generate enhanced metadata from name, description, and inputSchema.
 */
export async function annotateToolByLLM(
  request: ToolAnnotationRequest
): Promise<ToolAnnotationResponse> {
  return apiClient<ToolAnnotationResponse>('/tools/annotate', {
    method: 'POST',
    body: JSON.stringify(request),
  });
}

// --- Domain Tool Count API Functions ---

export interface DomainToolCount {
  name: string;
  label: string;
  description?: string | null;
  tool_count: number;
}

export interface CapabilityToolSkillCount {
  name: string;
  label: string;
  description?: string | null;
  tool_count: number;
  skill_count: number;
}

/**
 * Get all domains with their tool counts for a specific tenant.
 * If agent_id is provided, only returns domains associated with that agent.
 * @param tenantName Tenant name.
 * @param agentId Optional agent ID to filter domains.
 */
export async function getDomainsWithToolCount(tenantName: string, agentId?: string): Promise<DomainToolCount[]> {
  const queryString = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : '';
  return apiClient<DomainToolCount[]>(`/domains/tenants/${tenantName}/tool-counts${queryString}`);
}

/**
 * Get all capabilities for a domain with their tool and skill counts for a specific tenant.
 * @param tenantName Tenant name.
 * @param domainName Domain name.
 */
export async function getCapabilitiesWithToolSkillCount(tenantName: string, domainName: string): Promise<CapabilityToolSkillCount[]> {
  return apiClient<CapabilityToolSkillCount[]>(`/domains/tenants/${tenantName}/domains/${encodeURIComponent(domainName)}/capabilities/tool-skill-counts`);
}

// --- Workflow API Functions ---

export interface DomainToolCountInStep {
  name: string;
  label: string;
  tool_count: number;
}

export interface WorkflowStepToolCount {
  id: string;
  name: string;
  label: string;
  step_order: number;
  intent?: string;
  description?: string;
  tool_count: number;
  domains: DomainToolCountInStep[];
}

export interface WorkflowToolCount {
  id: string;
  name: string;
  label: string;
  description?: string;
  tool_count: number;
  workflow_steps: WorkflowStepToolCount[];
}

export interface WorkflowsWithTotalCount {
  total_mcp_tool_count: number;
  workflows: WorkflowToolCount[];
}

/**
 * Get all workflows with their tool counts and workflow steps with tool counts for a specific tenant.
 * @param tenantName Tenant name.
 */
export async function getWorkflowsWithToolCount(tenantName: string): Promise<WorkflowsWithTotalCount> {
  return apiClient<WorkflowsWithTotalCount>(`/domains/tenants/${tenantName}/workflows/tool-counts`);
}

// --- Role with Domains and Tool Counts API Functions ---

export interface RoleWithDomainsAndToolsInfo {
  role_name: string;
  role_label: string;
  role_description: string;
  role_type?: string | null;
  tool_count: number;
  domains: DomainToolCount[]; // Reuse existing DomainToolCount type
}

/**
 * Get roles with their associated domains and tool counts.
 * If agent_id is provided, returns only roles for that specific agent.
 * If agent_id is not provided, returns all roles in the system.
 * 
 * The hierarchy is: Role → Domain → Capability → Skill → Tool
 * To get the full hierarchy, use these existing APIs:
 * - getRolesWithToolCounts(agentId) for roles and domains
 * - getCapabilitiesWithToolSkillCount(domainName) for capabilities
 * - getSkillsByCapability(capabilityName) for skills
 * - getMcpToolsBySkill(skillName) for tools
 */
export async function getRolesWithToolCounts(agentId?: string): Promise<RoleWithDomainsAndToolsInfo[]> {
  const queryString = agentId ? `?agent_id=${encodeURIComponent(agentId)}` : '';
  return apiClient<RoleWithDomainsAndToolsInfo[]>(`/users/roles-with-tool-counts${queryString}`);
}
