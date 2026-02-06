'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import Layout from '@/components/Layout';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';
import HierarchicalToolView from './HierarchicalToolView';
import FlatToolView from './FlatToolView';
import {
  getDomainsWithToolCount,
  getCapabilitiesWithToolSkillCount,
  getSkillsByCapability,
  getMcpToolsByCapability,
  getMcpToolsBySkill,
  addStagingService,
  searchMcpTools,
  updateAgentProfile,
  getAgentProfile,
  DomainToolCount,
  CapabilityToolSkillCount,
  SkillInfo,
  McpToolInfo
} from '@/lib/apiClient';
import { ToolFilter } from '@/lib/apiClient';
import { filterStore } from '@/lib/filterStore';
import styles from './McpToolsPage.module.css';

const McpToolsPage: React.FC = () => {
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const searchParams = useSearchParams();
  const [tenantName, setTenantName] = useState<string | null>(null);
  
  const agentIdFromUrl = searchParams.get('agent_id');
  const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromUrl;
  // If agent_id parameter is provided, it's agent mode; otherwise check mode parameter
  const isAdminMode = agentIdFromUrl ? false : searchParams.get('mode') === 'admin';
  const isAdmin = !!(userData?.roles && userData.roles.includes("administrator"));

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);
  
  // View mode: 'hierarchical' or 'flat'
  const [pageViewMode, setPageViewMode] = useState<'hierarchical' | 'flat'>('hierarchical');
  
  // Hierarchical view state
  const [domains, setDomains] = useState<DomainToolCount[]>([]);
  const [selectedDomain, setSelectedDomain] = useState<DomainToolCount | null>(null);
  const [capabilities, setCapabilities] = useState<CapabilityToolSkillCount[]>([]);
  const [selectedCapability, setSelectedCapability] = useState<CapabilityToolSkillCount | null>(null);
  const [viewMode, setViewMode] = useState<'tools' | 'skills' | null>(null);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [tools, setTools] = useState<McpToolInfo[]>([]);
  const [selectedSkill, setSelectedSkill] = useState<SkillInfo | null>(null);
  const [skillTools, setSkillTools] = useState<McpToolInfo[]>([]);
  
  // Flat view state
  const [flatTools, setFlatTools] = useState<McpToolInfo[]>([]);
  const [toolFilter, setToolFilter] = useState<ToolFilter>({
    tool_query: '',
    roles: []
  });
  
  // Key to force HierarchicalToolFilter to remount when agent_id or mode changes
  const [filterKey, setFilterKey] = useState<string>('');
  
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  
  // Tool editing state
  const [viewingToolId, setViewingToolId] = useState<string | null>(null);
  const [editedToolJson, setEditedToolJson] = useState<string>('{}');
  const [originalToolJson, setOriginalToolJson] = useState<string>('{}');
  const [isSavingToStaging, setIsSavingToStaging] = useState<boolean>(false);

  // Fetch domains on mount and when agentId, isAdminMode, or tenantName changes
  useEffect(() => {
    if (tenantName) {
      fetchDomains();
    }
  }, [agentId, isAdminMode, tenantName]);

  const fetchDomains = async () => {
    setIsLoading(true);
    setError(null);
    try {
      if (!tenantName) {
        setError('No tenant name available');
        return;
      }
      
      const fetchedDomains = await getDomainsWithToolCount(tenantName, agentId || undefined);
      setDomains(fetchedDomains);
    } catch (err) {
      console.error("Failed to fetch domains:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch domains.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDomainClick = async (domain: DomainToolCount) => {
    setSelectedDomain(domain);
    setSelectedCapability(null);
    setViewMode(null);
    setSkills([]);
    setTools([]);
    setSelectedSkill(null);
    setSkillTools([]);
    
    setIsLoading(true);
    setError(null);
    try {
      if (!tenantName) {
        setError('No tenant name available');
        return;
      }
      
      const fetchedCapabilities = await getCapabilitiesWithToolSkillCount(tenantName, domain.name);
      setCapabilities(fetchedCapabilities);
    } catch (err) {
      console.error("Failed to fetch capabilities:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch capabilities.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCapabilityClick = (capability: CapabilityToolSkillCount) => {
    setSelectedCapability(capability);
    setViewMode(null);
    setSkills([]);
    setTools([]);
    setSelectedSkill(null);
    setSkillTools([]);
  };

  const handleViewTools = async () => {
    if (!selectedCapability || !tenantName) return;
    
    setViewMode('tools');
    setIsLoading(true);
    setError(null);
    try {
      const fetchedTools = await getMcpToolsByCapability(tenantName, selectedCapability.name);
      setTools(fetchedTools);
    } catch (err) {
      console.error("Failed to fetch tools:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tools.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleViewSkills = async () => {
    if (!selectedCapability || !tenantName) return;
    
    setViewMode('skills');
    setIsLoading(true);
    setError(null);
    try {
      const fetchedSkills = await getSkillsByCapability(tenantName, selectedCapability.name);
      setSkills(fetchedSkills);
    } catch (err) {
      console.error("Failed to fetch skills:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch skills.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSkillClick = async (skill: SkillInfo) => {
    if (!tenantName) return;
    
    setSelectedSkill(skill);
    setIsLoading(true);
    setError(null);
    try {
      const fetchedTools = await getMcpToolsBySkill(tenantName, skill.name);
      setSkillTools(fetchedTools);
    } catch (err) {
      console.error("Failed to fetch tools for skill:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tools for skill.');
    } finally {
      setIsLoading(false);
    }
  };

  const handleToggleView = (toolId: string) => {
    if (viewingToolId === toolId) {
      setViewingToolId(null);
      setEditedToolJson('{}');
      setOriginalToolJson('{}');
    } else {
      const toolToView = [...tools, ...skillTools].find(t => t.id === toolId);
      if (toolToView) {
        setViewingToolId(toolId);
        setError(null);
        setSuccessMessage(null);
        try {
          const toolDataWithId = {
            id: toolToView.id,
            ...toolToView.document || {},
            name: toolToView.document?.name || toolToView.name,
            description: toolToView.document?.description || toolToView.description,
          };
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
    let serviceData: any;
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
      if (!tenantName) {
        throw new Error("Tenant not selected.");
      }
      const response = await addStagingService(tenantName, serviceData);
      setSuccessMessage(`Tool "${response.name}" (ID: ${response.id}) saved successfully to staging.`);
      setViewingToolId(null);
      if (viewMode === 'tools') {
        handleViewTools();
      } else if (selectedSkill) {
        handleSkillClick(selectedSkill);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save tool to staging.');
    } finally {
      setIsSavingToStaging(false);
    }
  };

  const handleBack = () => {
    if (selectedSkill) {
      setSelectedSkill(null);
      setSkillTools([]);
    } else if (viewMode) {
      setViewMode(null);
      setSkills([]);
      setTools([]);
    } else if (selectedCapability) {
      setSelectedCapability(null);
    } else if (selectedDomain) {
      setSelectedDomain(null);
      setCapabilities([]);
    }
  };

  // Flat view handlers
  const handleFilterChange = useCallback((newFilter: ToolFilter) => {
    setToolFilter(newFilter);
  }, []);

  // Flat view fetch - using new filter structure
  const fetchFlatTools = useCallback(async () => {
    if (!tenantName || (!agentId && !isAdminMode)) {
      console.log('Skipping fetch - tenantName:', tenantName, 'agentId:', agentId, 'isAdminMode:', isAdminMode);
      return;
    }
    
    setIsLoading(true);
    setError(null);
    try {
      let fetchedTools: McpToolInfo[];
      
      if (isAdminMode) {
        console.log('Fetching tools in admin mode with params:', {
          tenant_name: tenantName,
          agent_id: null,
          filter: toolFilter,
          tool_query: toolFilter.tool_query,
          k: 10
        });
        // Admin mode: no agent_id, always pass filter (even if empty) to ensure proper filtering
        fetchedTools = await searchMcpTools(tenantName, {
          agent_id: null,
          filter: toolFilter,
          tool_query: toolFilter.tool_query || undefined,
          k: 10
        });
      } else {
        console.log('Fetching tools for agent with params:', {
          tenant_name: tenantName,
          agent_id: agentId,
          filter: toolFilter,
          tool_query: toolFilter.tool_query,
          k: 10
        });
        // Agent mode: use agent_id and filter
        fetchedTools = await searchMcpTools(tenantName, {
          agent_id: agentId!,
          filter: toolFilter.roles && toolFilter.roles.length > 0 ? toolFilter : undefined,
          tool_query: toolFilter.tool_query || undefined,
          k: 50
        });
      }
      
      console.log('Fetched tools:', fetchedTools);
      console.log('Fetched tools count:', fetchedTools?.length || 0);
      setFlatTools(fetchedTools || []);
    } catch (err) {
      console.error("Failed to fetch MCP tools:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch MCP tools.');
      setFlatTools([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantName, agentId, isAdminMode, toolFilter]);

  // Initial load and filter state changes - matching mcp-services
  useEffect(() => {
    if (pageViewMode === 'flat') {
      console.log('Flat view mode activated, fetching tools...');
      fetchFlatTools();
    }
  }, [pageViewMode, fetchFlatTools]);

  // Reset view state when agentId or isAdminMode changes
  useEffect(() => {
    // Reset hierarchical view state
    setSelectedDomain(null);
    setSelectedCapability(null);
    setViewMode(null);
    setSkills([]);
    setTools([]);
    setSelectedSkill(null);
    setSkillTools([]);
    setCapabilities([]);
    
    // Reset flat view state
    setFlatTools([]);
    setViewingToolId(null);
    setEditedToolJson('{}');
    setOriginalToolJson('{}');
    
    // Reset filter state
    setToolFilter({
      tool_query: '',
      roles: []
    });
    
    // Force HierarchicalToolFilter to remount by changing its key
    setFilterKey(`${agentId || 'admin'}-${isAdminMode ? 'admin' : 'agent'}-${Date.now()}`);
    
    // Refetch data based on current view mode
    if (pageViewMode === 'hierarchical') {
      fetchDomains();
    } else if (pageViewMode === 'flat') {
      fetchFlatTools();
    }
  }, [agentId, isAdminMode]);

  // Search is now handled by filter changes
  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    // No-op - search is now handled by the filter component
  };

  const handleToggleViewFlat = (toolId: string) => {
    if (viewingToolId === toolId) {
      setViewingToolId(null);
      setEditedToolJson('{}');
      setOriginalToolJson('{}');
    } else {
      const toolToView = flatTools.find(t => t.id === toolId);
      if (toolToView) {
        setViewingToolId(toolId);
        setError(null);
        setSuccessMessage(null);
        try {
          const toolDataWithId = {
            id: toolToView.id,
            ...toolToView.document || {},
            name: toolToView.document?.name || toolToView.name,
            description: toolToView.document?.description || toolToView.description,
          };
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

  return (
    <Layout>
      <div className={styles.container}>
        <h1 className={styles.title}>MCP Tools Explorer</h1>
        <p className={styles.description}>
          {agentId 
            ? `Explore domains, capabilities, skills, and MCP tools for agent: ${agentId}`
            : 'Explore all domains, capabilities, skills, and MCP tools in the system'}
        </p>

        {/* View Mode Toggle */}
        <div className={styles.viewModeToggle}>
          <button
            onClick={() => setPageViewMode('hierarchical')}
            className={pageViewMode === 'hierarchical' ? styles.activeViewButton : styles.viewButton}
          >
            Hierarchical View
          </button>
          <button
            onClick={() => setPageViewMode('flat')}
            className={pageViewMode === 'flat' ? styles.activeViewButton : styles.viewButton}
          >
            Flat View
          </button>
        </div>

        {error && <p className={styles.error}>Error: {error}</p>}

        {/* Hierarchical View */}
        {pageViewMode === 'hierarchical' && (
          <HierarchicalToolView
            domains={domains}
            selectedDomain={selectedDomain}
            onDomainClick={handleDomainClick}
            capabilities={capabilities}
            selectedCapability={selectedCapability}
            onCapabilityClick={handleCapabilityClick}
            viewMode={viewMode}
            onViewTools={handleViewTools}
            onViewSkills={handleViewSkills}
            skills={skills}
            selectedSkill={selectedSkill}
            onSkillClick={handleSkillClick}
            tools={tools}
            skillTools={skillTools}
            viewingToolId={viewingToolId}
            editedToolJson={editedToolJson}
            originalToolJson={originalToolJson}
            onToggleView={handleToggleView}
            onEditedToolJsonChange={setEditedToolJson}
            onSaveToStaging={handleSaveMcpServiceToStaging}
            isSavingToStaging={isSavingToStaging}
            onBack={handleBack}
            isLoading={isLoading}
            successMessage={successMessage}
            tenantName={tenantName || undefined}
            agentId={agentId || undefined}
            isAdminMode={isAdmin}
          />
        )}

        {/* Flat View */}
        {pageViewMode === 'flat' && (
          <FlatToolView
            tools={flatTools}
            searchQuery={toolFilter.tool_query || ''}
            onSearchQueryChange={(query) => setToolFilter({ ...toolFilter, tool_query: query })}
            onSearch={handleSearch}
            onFilterChange={handleFilterChange as any}
            filterKey={filterKey}
            viewingToolId={viewingToolId}
            editedToolJson={editedToolJson}
            originalToolJson={originalToolJson}
            onToggleView={handleToggleViewFlat}
            onEditedToolJsonChange={setEditedToolJson}
            onSaveToStaging={handleSaveMcpServiceToStaging}
            isSavingToStaging={isSavingToStaging}
            onSaveFilterToAgentProfile={handleSaveFilterToAgentProfile}
            onApplyAgentFilter={handleApplyAgentFilter}
            isSavingFilter={false}
            isLoadingAgentFilter={false}
            isLoading={isLoading}
            error={error}
            successMessage={successMessage}
            tenantName={tenantName || undefined}
            agentId={agentId || undefined}
            isAdminMode={isAdmin}
            onRefresh={fetchFlatTools}
          />
        )}
      </div>
    </Layout>
  );
};

export default McpToolsPage;
