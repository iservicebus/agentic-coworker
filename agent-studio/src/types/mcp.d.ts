export interface McpService {
  id?: string; // Add optional ID field for updates
  name: string;
  description?: string;
  inputSchema?: Record<string, any>;
  staticInput?: Record<string, any>;
  transport?: string;
  tool_type?: string; // Add tool_type field with default "general"
  // Allow any other properties that might come from the API
  [key: string]: any;
}

export interface McpServiceResponse extends McpService {
  // The API might return additional fields not strictly part of the definition,
  // but for now, we'll assume it aligns closely with McpService.
  // If the API wraps the service data or adds IDs, adjust here.
  // For example, if the API returns an 'id' field at the top level:
  // id?: string; 
}

export interface McpRegistrationResponse {
  message: string;
  service_name: string;
}

// ToolFilter types have been moved to @/lib/apiClient.ts to maintain a single source of truth
// Import them from there: import { ToolFilter, ToolFilterRole, ToolFilterDomain, ToolFilterCapability } from '@/lib/apiClient';

