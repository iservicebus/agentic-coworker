'use client';

import React, { useState, useEffect, useCallback, useRef } from 'react';
import { useSearchParams } from 'next/navigation';
import ToolDefinitionUI from '@/components/ToolDefinitionUI';
import ToolDomainNavigation from '@/components/ToolDefinitionUI/ToolDomainNavigation';
import HierarchicalToolFilter from '@/components/HierarchicalToolFilter';
import { 
  listMcpServices, 
  addStagingService, 
  ToolDefinition,
  searchMcpTools,
  getMcpToolsForAgent,
  getAllMcpToolsAdmin,
  McpToolInfo,
  updateAgentProfile,
  getAgentProfile
} from '@/lib/apiClient';
import { McpServiceResponse } from '@/types/mcp';
import { ToolFilter } from '@/lib/apiClient';
import styles from './McpServicesPage.module.css';
import Layout from '@/components/Layout';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { filterStore } from '@/lib/filterStore';
import { getTenantFromCookie } from '@/lib/tenantUtils';

const McpServicesPage: React.FC = () => {
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const searchParams = useSearchParams();
  const [tenantId, setTenantId] = useState<string | null>(null);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantId(tenant);
  }, []);
  
  const agentIdFromUrl = searchParams.get('agent_id');
  const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromUrl;

  const userRoles = userData?.roles || [];
  const isAdmin = !!(userData?.roles && userData.roles.includes("administrator"));

  // Determine if this is admin mode or agent mode
  // If agent_id parameter is provided, it's agent mode; otherwise check mode parameter
  const isAdminMode = agentIdFromUrl ? false : searchParams.get('mode') === 'admin';
  const pageTitle = isAdminMode ? 'MCP Tools (Admin)' : 'Agent Tools';
  const pageDescription = isAdminMode 
    ? 'View and manage all MCP tools across all agents' 
    : agentIdFromUrl 
      ? `View MCP tools for agent: ${agentIdFromUrl}`
      : 'View MCP tools available to your agent';

  const [tools, setTools] = useState<McpToolInfo[]>([]);
  const [services, setServices] = useState<McpServiceResponse[]>([]); // Keep for legacy compatibility
  const [viewingToolId, setViewingToolId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSavingToStaging, setIsSavingToStaging] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [originalToolJson, setOriginalToolJson] = useState<string>('{}');

  // Filter state using ToolFilter
  const [toolFilter, setToolFilter] = useState<ToolFilter>({
    tool_query: '',
    roles: []
  });

  // Refs to hold current values without causing re-renders
  const tenantIdRef = useRef(tenantId);
  const agentIdRef = useRef(agentId);
  const isAdminModeRef = useRef(isAdminMode);

  // Update refs when values change
  useEffect(() => {
    tenantIdRef.current = tenantId;
  }, [tenantId]);

  useEffect(() => {
    agentIdRef.current = agentId;
  }, [agentId]);

  useEffect(() => {
    isAdminModeRef.current = isAdminMode;
  }, [isAdminMode]);

  const fetchTools = useCallback(async () => {
    if (!tenantId || (!agentId && !isAdminMode)) return;

    setIsLoading(true);
    setError(null);
    try {
      let fetchedTools: McpToolInfo[];

      if (isAdminMode) {
        // Admin mode: use searchMcpTools with filter parameters
        fetchedTools = await searchMcpTools(tenantId, {
          agent_id: null, // No agent filter for admin
          filter: toolFilter.roles && toolFilter.roles.length > 0 ? toolFilter : undefined,
          tool_query: toolFilter.tool_query || undefined,
          k: 50
        });
      } else {
        // Agent mode: use searchMcpTools with agent and filter parameters
        fetchedTools = await searchMcpTools(tenantId, {
          agent_id: agentId!,
          filter: toolFilter.roles && toolFilter.roles.length > 0 ? toolFilter : undefined,
          tool_query: toolFilter.tool_query || undefined,
          k: 50
        });
      }

      setTools(fetchedTools || []);
    } catch (err) {
      console.error("Failed to fetch MCP tools:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch MCP tools.');
      setTools([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId, agentId, isAdminMode, toolFilter]);

  // Legacy function for backward compatibility
  const fetchServices = useCallback(async () => {
    if (!tenantId) return;
    setIsLoading(true);
    setError(null);
    try {
      const fetchedServices = await listMcpServices(tenantId);
      setServices(fetchedServices || []);
    } catch (err) {
      console.error("Failed to fetch MCP services:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch MCP services.');
      setServices([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId]);

  // Stable filter change handler
  const handleFilterChange = useCallback((newFilter: ToolFilter) => {
    setToolFilter(newFilter);
  }, []);

  // Fetch tools function that uses current state values
  const fetchToolsWithFilter = useCallback(async () => {
    if (!tenantId || (!agentId && !isAdminMode)) return;

    setIsLoading(true);
    setError(null);
    try {
      let fetchedTools: McpToolInfo[];

      if (isAdminMode) {
        // Admin mode: use searchMcpTools with filter parameters
        fetchedTools = await searchMcpTools(tenantId, {
          agent_id: null, // No agent filter for admin
          filter: toolFilter.roles && toolFilter.roles.length > 0 ? toolFilter : undefined,
          tool_query: toolFilter.tool_query || undefined,
          k: 50
        });
      } else {
        // Agent mode: use searchMcpTools with agent and filter parameters
        fetchedTools = await searchMcpTools(tenantId, {
          agent_id: agentId!,
          filter: toolFilter.roles && toolFilter.roles.length > 0 ? toolFilter : undefined,
          tool_query: toolFilter.tool_query || undefined,
          k: 50
        });
      }

      setTools(fetchedTools || []);
    } catch (err) {
      console.error("Failed to fetch MCP tools:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch MCP tools.');
      setTools([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId, agentId, isAdminMode, toolFilter]); // Include all dependencies

  // Initial load and filter state changes
  useEffect(() => {
    fetchToolsWithFilter();
  }, [tenantId, agentId, isAdminMode, toolFilter, fetchToolsWithFilter]);

  const [editedToolJson, setEditedToolJson] = useState<string>('{}');

  const handleToggleView = (toolId: string) => {
    if (viewingToolId === toolId) {
      setViewingToolId(null);
      setEditedToolJson('{}'); // Reset when closing
      setOriginalToolJson('{}');
    } else {
      const toolToView = tools.find(t => t.id === toolId);
      if (toolToView) {
        setViewingToolId(toolId);
        setError(null); // Clear previous errors
        setSuccessMessage(null); // Clear previous success messages
        try {
          // Include the ID in the tool data for proper update handling
          // Merge the document with the tool's ID and other metadata
          const toolDataWithId = {
            id: toolToView.id, // Include the ID for update operations
            ...toolToView.document || {}, // Spread the document content
            // Preserve other important metadata if not already in document
            name: toolToView.document?.name || toolToView.name,
            description: toolToView.document?.description || toolToView.description,
          };
          
          // Debug logging to verify ID is being included
          console.log('Tool data being prepared for editing:', {
            toolId: toolToView.id,
            hasId: !!toolDataWithId.id,
            toolDataWithId: toolDataWithId
          });
          
          // Additional check: if ID is still null, try to get it from the tool object itself
          if (!toolDataWithId.id && toolToView.id) {
            console.warn('ID was null after merge, forcing ID assignment');
            toolDataWithId.id = toolToView.id;
          }
          
          // Final verification
          console.log('Final tool data with ID verification:', {
            originalToolId: toolToView.id,
            finalToolId: toolDataWithId.id,
            idMatch: toolToView.id === toolDataWithId.id,
            toolDataWithId: toolDataWithId
          });
          
          const toolJson = JSON.stringify(toolDataWithId, null, 2);
          setEditedToolJson(toolJson);
          setOriginalToolJson(toolJson);
        } catch (e) {
          console.error("Error stringifying tool data for view/edit:", e);
          setError("Failed to parse tool data.");
          setEditedToolJson('{}');
        }
      }
    }
  };

  const handleSaveMcpServiceToStaging = async () => {
    setError(null);
    setSuccessMessage(null);
    if (!editedToolJson) {
      setError('No tool data to save.');
      return;
    }
    let serviceData: ToolDefinition;
    try {
      serviceData = JSON.parse(editedToolJson);
    } catch (parseError: any) {
      setError(`Invalid JSON format: ${parseError.message}`);
      return;
    }

    if (!serviceData.name || typeof serviceData.name !== 'string') {
        setError('Tool data must have a "name" field of type string.');
        return;
    }

    setIsSavingToStaging(true);
    try {
      if (!tenantId) {
        throw new Error("Tenant not selected.");
      }
      const response = await addStagingService(tenantId, serviceData);
      setSuccessMessage(`Tool "${response.name}" (ID: ${response.id}) saved successfully to staging for tenant "${tenantId}".`);
      setViewingToolId(null);
      fetchTools();
    } catch (err: any) {
      setError(err.message || 'Failed to save tool to staging.');
    } finally {
      setIsSavingToStaging(false);
    }
  };

  // Save/Load filter is now handled by HierarchicalToolFilter component
  const handleSaveFilterToAgentProfile = () => {
    setSuccessMessage('Filter saved to agent profile successfully!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  const handleApplyAgentFilter = () => {
    setSuccessMessage('Agent filter applied successfully!');
    setTimeout(() => setSuccessMessage(null), 3000);
  };

  if (isUserLoading) {
    return <Layout><div className={styles.container}><p>Loading user data...</p></div></Layout>;
  }

  if (userError) {
    return <Layout><div className={styles.container}><p>Error loading user data: {userError}</p></div></Layout>;
  }

  if (!tenantId) {
    return <Layout><div className={styles.container}><p>Tenant not selected.</p></div></Layout>;
  }

  if (isLoading && tools.length === 0) {
    return <Layout><div className={styles.container}><p>Loading {pageTitle}...</p></div></Layout>;
  }

  return (
    <Layout>
      <div className={styles.container}>
        <h1 className={styles.title}>{pageTitle}</h1>
        <p className={styles.description}>{pageDescription}</p>
        
        {/* Search functionality */}
        {/* Hierarchical Tool Filter - Replaces both search and filter */}
        <div className={styles.filterContainer}>
          <HierarchicalToolFilter
            agentId={isAdminMode ? undefined : (agentId || undefined)}
            tenantName={tenantId || undefined}
            showSaveButton={!isAdminMode && !!agentId}
            showLoadButton={!isAdminMode && !!agentId}
            collapsible={true}
            autoLoadFilter={false}
            showToolQuery={true}
            showRoleDescription={false}
            title="Filters"
            onFilterChange={handleFilterChange}
            onFilterSaved={handleSaveFilterToAgentProfile}
            onFilterLoaded={handleApplyAgentFilter}
            className={styles.filter}
          />
        </div>
        
        {/* Display general page errors or success messages here */}
        {error && !viewingToolId && <p className={styles.error}>Error: {error}</p>}
        {successMessage && !viewingToolId && <p className={styles.success}>{successMessage}</p>}

        <div className={styles.serviceListContainer}>
          <h2 className={styles.subTitle}>
            Available Tools ({tools.length})
            {isAdminMode && <span className={styles.adminBadge}>Admin View</span>}
          </h2>
          {tools.length === 0 && !isLoading && <p>No MCP tools found.</p>}
          {isLoading && tools.length > 0 && <p>Refreshing tool list...</p>}
          <ul className={styles.serviceList}>
            {tools.map((tool) => (
              <li key={tool.id} className={`${styles.serviceListItem} ${viewingToolId === tool.id ? styles.selected : ''}`}>
                <div className={styles.serviceHeader}>
                  <div className={styles.toolInfo}>
                    <span className={styles.toolName}>{tool.name || 'Unnamed Tool'}</span>
                    {tool.cosine_similarity && (
                      <span className={styles.similarity}>
                        Similarity: {(tool.cosine_similarity * 100).toFixed(1)}%
                      </span>
                    )}
                  </div>
                  <button
                    onClick={() => handleToggleView(tool.id)}
                    className={viewingToolId === tool.id ? styles.cancelButton : styles.viewButton}
                  >
                    {viewingToolId === tool.id ? 'Cancel Edit' : 'View/Edit Details'}
                  </button>
                </div>
                {tool.description && (
                  <p className={styles.toolDescription}>{tool.description}</p>
                )}
                
                {/* Domain Navigation - Show in short view */}
                <div className={styles.domainNavigationContainer}>
                  <ToolDomainNavigation
                    toolId={tool.id}
                    toolName={tool.name}
                    tenantName={tenantId || ''}
                    className="w-full"
                  />
                </div>
                
                {viewingToolId === tool.id && (
                  <div className={styles.detailsContainer}>
                    {/* Display specific errors/success for the current editing session */}
                    {error && viewingToolId && <p className={styles.error}>Error: {error}</p>}
                    {successMessage && viewingToolId && <p className={styles.success}>{successMessage}</p>}
                    <ToolDefinitionUI
                      editedToolJson={editedToolJson}
                      originalToolJson={originalToolJson}
                      onEditedToolJsonChange={setEditedToolJson}
                      onSaveToStaging={handleSaveMcpServiceToStaging}
                      isLoading={isSavingToStaging}
                      pageType="mcp"
                      serviceId={tool.id}
                      onDeleteSuccess={() => {
                        setViewingToolId(null);
                        fetchTools();
                      }}
                      onRegisterSuccess={() => {
                        setViewingToolId(null);
                        fetchTools();
                      }}
                      tenantName={tenantId}
                      agentId={agentId || undefined}
                      isAdminMode={isAdmin}
                    />
                  </div>
                )}
              </li>
            ))}
          </ul>
          <button onClick={fetchTools} disabled={isLoading} className={styles.refreshButton}>
            {isLoading ? 'Refreshing...' : 'Refresh List'}
          </button>
        </div>
      </div>
    </Layout>
  );
};

export default McpServicesPage;
