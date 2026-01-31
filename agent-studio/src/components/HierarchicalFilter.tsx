import React, { useState, useEffect, useRef } from 'react';
import { 
  getAgentRoleHierarchy,
  getAllRoles,
  getAllDomains,
  getCapabilitiesByDomain,
  getAgentRoles,
  getAgentRoleDomains,
  getAgentRoleDomainCapabilities,
  RoleHierarchyItem,
  RoleInfo,
  DomainInfo,
  CapabilityInfo
} from '@/lib/apiClient';
import { useFilterStore } from '@/lib/filterStore';
import { useUserData } from "@/lib/contexts/UserDataContext";

interface FilterState {
  selectedRoles: string[];
  selectedCategories: string[];
  selectedCapabilities: string[];
}

interface HierarchicalFilterProps {
  onFilterChange: (filter: FilterState) => void;
  isAdminMode: boolean;
  agentId?: string;
  tenantName?: string;
  className?: string;
}

const HierarchicalFilter: React.FC<HierarchicalFilterProps> = ({
  onFilterChange,
  isAdminMode,
  agentId,
  tenantName,
  className = ''
}) => {
  console.log('HierarchicalFilter render:', { isAdminMode, agentId, timestamp: Date.now() });
  
  const { userData } = useUserData();
  
  // Use the global filter store with mode-specific state
  const {
    filterState,
    updateRoles,
    updateCategories,
    updateCapabilities,
    clearAll
  } = useFilterStore(onFilterChange, isAdminMode, agentId);

  // Data states
  const [agentHierarchy, setAgentHierarchy] = useState<RoleHierarchyItem[]>([]);
  const [allRoles, setAllRoles] = useState<RoleInfo[]>([]);
  const [allDomains, setAllDomains] = useState<DomainInfo[]>([]);
  const [domainCapabilities, setDomainCapabilities] = useState<Record<string, CapabilityInfo[]>>({});
  
  // On-demand loading states for agent mode
  const [agentRoles, setAgentRoles] = useState<RoleInfo[]>([]);
  const [roleDomains, setRoleDomains] = useState<Record<string, DomainInfo[]>>({});
  const [roleDomainCapabilities, setRoleDomainCapabilities] = useState<Record<string, CapabilityInfo[]>>({});
  
  const [expandedRoles, setExpandedRoles] = useState<Set<string>>(new Set());
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());
  const [loading, setLoading] = useState(false);
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});
  const [error, setError] = useState<string | null>(null);

  // Persistent filter expansion state - survives page refreshes and component re-mounts
  const getStorageKey = () => `hierarchical-filter-expanded-${isAdminMode ? 'admin' : `agent-${agentId}`}`;
  
  const [filterExpanded, setFilterExpanded] = useState(() => {
    // Initialize from localStorage if available
    if (typeof window !== 'undefined') {
      const stored = localStorage.getItem(getStorageKey());
      return stored ? JSON.parse(stored) : false;
    }
    return false;
  });

  // Use refs to maintain expansion state across re-renders
  const filterExpandedRef = useRef(filterExpanded);
  const expandedRolesRef = useRef<Set<string>>(new Set());
  const expandedCategoriesRef = useRef<Set<string>>(new Set());

  // Load initial data when agentId or isAdminMode changes
  const prevAgentIdRef = useRef(agentId);
  const prevIsAdminModeRef = useRef(isAdminMode);
  
  useEffect(() => {
    const agentIdChanged = prevAgentIdRef.current !== agentId;
    const modeChanged = prevIsAdminModeRef.current !== isAdminMode;
    
    if (agentIdChanged || modeChanged) {
      console.log('HierarchicalFilter: Reloading data due to prop change', {
        agentIdChanged,
        modeChanged,
        oldAgentId: prevAgentIdRef.current,
        newAgentId: agentId,
        oldMode: prevIsAdminModeRef.current,
        newMode: isAdminMode
      });
      
      // Reset state when agent or mode changes
      setAgentRoles([]);
      setRoleDomains({});
      setRoleDomainCapabilities({});
      setAllRoles([]);
      setAllDomains([]);
      setDomainCapabilities({});
      setExpandedRoles(new Set());
      setExpandedCategories(new Set());
      
      // Load new data
      loadInitialData();
      
      // Update refs
      prevAgentIdRef.current = agentId;
      prevIsAdminModeRef.current = isAdminMode;
    }
  }, [agentId, isAdminMode]);
  
  // Initial load on mount
  useEffect(() => {
    loadInitialData();
  }, []);

  const loadInitialData = async () => {
    setLoading(true);
    setError(null);
    try {
      // Use tenantName prop - it's required
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      if (isAdminMode) {
        // Admin mode: load all roles and domains
        const [rolesData, domainsData] = await Promise.all([
          getAllRoles(tenantName),
          getAllDomains()
        ]);
        setAllRoles(rolesData);
        setAllDomains(domainsData);
        setAgentHierarchy([]); // Not needed in admin mode
        setAgentRoles([]); // Not needed in admin mode
      } else {
        // Agent mode: load only agent roles initially (on-demand loading)
        if (!agentId) {
          throw new Error('Agent ID is required for agent mode');
        }
        const rolesData = await getAgentRoles(tenantName, agentId);
        setAgentRoles(rolesData);
        setAgentHierarchy([]); // Not needed with on-demand loading
        setAllRoles([]); // Not needed in agent mode
        setAllDomains([]); // Not needed in agent mode
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load filter data');
    } finally {
      setLoading(false);
    }
  };

  const loadCapabilitiesForDomain = async (domainName: string) => {
    try {
      // Use tenantName prop - it's required
      if (!tenantName) {
        console.error('No tenant name provided');
        return;
      }
      
      const capabilities = await getCapabilitiesByDomain(tenantName, domainName);
      setDomainCapabilities(prev => ({
        ...prev,
        [domainName]: capabilities
      }));
    } catch (err) {
      console.error(`Failed to load capabilities for domain ${domainName}:`, err);
    }
  };

  const toggleRoleExpansion = async (roleName: string) => {
    const newExpanded = new Set(expandedRoles);
    if (newExpanded.has(roleName)) {
      newExpanded.delete(roleName);
    } else {
      newExpanded.add(roleName);
      
      // Load domains for this role on-demand (agent mode only)
      if (!isAdminMode && agentId && !roleDomains[roleName]) {
        setLoadingStates(prev => ({ ...prev, [`role-${roleName}`]: true }));
        try {
          // Use tenantName prop - it's required
          if (!tenantName) {
            throw new Error('No tenant name provided');
          }
          const domains = await getAgentRoleDomains(tenantName, agentId, roleName);
          setRoleDomains(prev => ({ ...prev, [roleName]: domains }));
        } catch (err) {
          console.error(`Failed to load domains for role ${roleName}:`, err);
        } finally {
          setLoadingStates(prev => ({ ...prev, [`role-${roleName}`]: false }));
        }
      }
    }
    setExpandedRoles(newExpanded);
    expandedRolesRef.current = newExpanded;
  };

  const toggleDomainExpansion = async (domainName: string, roleName?: string) => {
    const newExpanded = new Set(expandedCategories);
    const domainKey = roleName ? `${roleName}-${domainName}` : domainName;
    
    if (newExpanded.has(domainKey)) {
      newExpanded.delete(domainKey);
    } else {
      newExpanded.add(domainKey);
      
      if (isAdminMode) {
        // Admin mode: load capabilities for domain
        await loadCapabilitiesForDomain(domainName);
      } else if (agentId && roleName) {
        // Agent mode: load capabilities for role-domain combination on-demand
        const capabilityKey = `${roleName}-${domainName}`;
        if (!roleDomainCapabilities[capabilityKey]) {
          setLoadingStates(prev => ({ ...prev, [`domain-${capabilityKey}`]: true }));
          try {
            // Use tenantName prop - it's required
            if (!tenantName) {
              throw new Error('No tenant name provided');
            }
            const capabilities = await getAgentRoleDomainCapabilities(tenantName, agentId, roleName, domainName);
            setRoleDomainCapabilities(prev => ({ ...prev, [capabilityKey]: capabilities }));
          } catch (err) {
            console.error(`Failed to load capabilities for role ${roleName}, domain ${domainName}:`, err);
          } finally {
            setLoadingStates(prev => ({ ...prev, [`domain-${capabilityKey}`]: false }));
          }
        }
      }
    }
    setExpandedCategories(newExpanded);
    expandedCategoriesRef.current = newExpanded;
  };

  // Stable event handlers that maintain expansion state
  const handleRoleChange = (roleName: string, checked: boolean) => {
    console.log('Role change:', roleName, checked);
    updateRoles(roleName, checked);
  };

  const handleCategoryChange = (categoryName: string, checked: boolean) => {
    console.log('Category change:', categoryName, checked);
    updateCategories(categoryName, checked);
  };

  const handleCapabilityChange = (capabilityName: string, checked: boolean) => {
    console.log('Capability change:', capabilityName, checked);
    updateCapabilities(capabilityName, checked);
  };

  const clearAllFilters = () => {
    console.log('Clear all filters');
    clearAll();
  };

  const toggleFilterExpansion = () => {
    const newExpanded = !filterExpanded;
    setFilterExpanded(newExpanded);
    filterExpandedRef.current = newExpanded;
    
    // Persist the expansion state to localStorage
    if (typeof window !== 'undefined') {
      localStorage.setItem(getStorageKey(), JSON.stringify(newExpanded));
    }
  };

  const renderAgentModeHierarchy = () => {
    return (
      <div className="space-y-3">
        {agentRoles.map((role) => (
          <div key={role.name} className="border border-gray-200 rounded-lg bg-white">
            {/* Role Level */}
            <div className="p-3 bg-gray-50">
              <div className="flex items-center">
                <button
                  onClick={() => toggleRoleExpansion(role.name)}
                  className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                  disabled={loadingStates[`role-${role.name}`]}
                >
                  {loadingStates[`role-${role.name}`] ? (
                    <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                  ) : (
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      fill="none" 
                      viewBox="0 0 24 24" 
                      strokeWidth={1.5} 
                      stroke="currentColor" 
                      className={`w-4 h-4 transition-transform ${
                        expandedRoles.has(role.name) ? 'rotate-90' : ''
                      }`}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  )}
                </button>
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    checked={filterState.selectedRoles.includes(role.name)}
                    onChange={(e) => handleRoleChange(role.name, e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span className="ml-2 text-sm font-medium text-gray-900">{role.label}</span>
                </label>
              </div>
            </div>

            {/* Domains under this role (loaded on-demand) */}
            {expandedRoles.has(role.name) && (
              <div className="p-3 space-y-2 bg-white">
                {roleDomains[role.name]?.map((domain) => (
                  <div key={domain.name} className="ml-4">
                    {/* Domain Level */}
                    <div className="flex items-center">
                      <button
                        onClick={() => toggleDomainExpansion(domain.name, role.name)}
                        className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                        disabled={loadingStates[`domain-${role.name}-${domain.name}`]}
                      >
                        {loadingStates[`domain-${role.name}-${domain.name}`] ? (
                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                        ) : (
                          <svg 
                            xmlns="http://www.w3.org/2000/svg" 
                            fill="none" 
                            viewBox="0 0 24 24" 
                            strokeWidth={1.5} 
                            stroke="currentColor" 
                            className={`w-4 h-4 transition-transform ${
                              expandedCategories.has(`${role.name}-${domain.name}`) ? 'rotate-90' : ''
                            }`}
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                          </svg>
                        )}
                      </button>
                      <label className="flex items-center">
                        <input
                          type="checkbox"
                          checked={filterState.selectedCategories.includes(domain.name)}
                          onChange={(e) => handleCategoryChange(domain.name, e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm font-medium text-gray-700">{domain.label}</span>
                      </label>
                    </div>

                    {/* Capabilities under this domain (loaded on-demand) */}
                    {expandedCategories.has(`${role.name}-${domain.name}`) && (
                      <div className="ml-6 mt-2 space-y-1">
                        {roleDomainCapabilities[`${role.name}-${domain.name}`]?.map((capability) => (
                          <label key={capability.name} className="flex items-center">
                            <input
                              type="checkbox"
                              checked={filterState.selectedCapabilities.includes(capability.name)}
                              onChange={(e) => handleCapabilityChange(capability.name, e.target.checked)}
                              className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                            />
                            <span className="ml-2 text-sm text-gray-600">{capability.label}</span>
                          </label>
                        )) || (
                          <div className="text-xs text-gray-500 italic">Loading capabilities...</div>
                        )}
                      </div>
                    )}
                  </div>
                )) || (
                  <div className="ml-4 text-xs text-gray-500 italic">Loading domains...</div>
                )}
              </div>
            )}
          </div>
        ))}
      </div>
    );
  };

  const renderAdminModeFilters = () => {
    return (
      <div className="space-y-6">
        {/* Roles Section */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Roles</h4>
          <div className="space-y-2 max-h-32 overflow-y-auto border border-gray-200 rounded p-2">
            {allRoles.map((role) => (
              <label key={role.name} className="flex items-center">
                <input
                  type="checkbox"
                  checked={filterState.selectedRoles.includes(role.name)}
                  onChange={(e) => handleRoleChange(role.name, e.target.checked)}
                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                />
                <span className="ml-2 text-sm text-gray-700">{role.label}</span>
              </label>
            ))}
          </div>
        </div>

        {/* Domains & Capabilities Section */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">Domains & Capabilities</h4>
          <div className="space-y-2 max-h-64 overflow-y-auto border border-gray-200 rounded p-2">
            {allDomains.map((domain) => (
              <div key={domain.name}>
                {/* Domain Level */}
                <div className="flex items-center">
                  <button
                    onClick={() => toggleDomainExpansion(domain.name)}
                    className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                  >
                    <svg 
                      xmlns="http://www.w3.org/2000/svg" 
                      fill="none" 
                      viewBox="0 0 24 24" 
                      strokeWidth={1.5} 
                      stroke="currentColor" 
                      className={`w-4 h-4 transition-transform ${
                        expandedCategories.has(domain.name) ? 'rotate-90' : ''
                      }`}
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                    </svg>
                  </button>
                  <label className="flex items-center">
                    <input
                      type="checkbox"
                      checked={filterState.selectedCategories.includes(domain.name)}
                      onChange={(e) => handleCategoryChange(domain.name, e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span className="ml-2 text-sm font-medium text-gray-700">{domain.label}</span>
                  </label>
                </div>

                {/* Capabilities under this domain */}
                {expandedCategories.has(domain.name) && (
                  <div className="ml-6 mt-2 space-y-1">
                    {domainCapabilities[domain.name]?.map((capability) => (
                      <label key={capability.name} className="flex items-center">
                        <input
                          type="checkbox"
                          checked={filterState.selectedCapabilities.includes(capability.name)}
                          onChange={(e) => handleCapabilityChange(capability.name, e.target.checked)}
                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                        />
                        <span className="ml-2 text-sm text-gray-600">{capability.label}</span>
                      </label>
                    )) || (
                      <div className="text-xs text-gray-500 italic">Loading capabilities...</div>
                    )}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`p-4 border border-gray-200 rounded-lg ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Loading filters...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`p-4 border border-red-200 bg-red-50 rounded-lg ${className}`}>
        <p className="text-red-800 text-sm">Error: {error}</p>
        <button
          onClick={loadInitialData}
          className="mt-2 text-sm text-red-600 hover:text-red-800"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className={`border border-gray-200 rounded-lg bg-white ${className}`}>
      {/* Filter Header - Always Visible */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            <button
              onClick={toggleFilterExpansion}
              className="flex items-center text-lg font-medium text-gray-900 hover:text-gray-700 mr-2"
            >
              <svg 
                xmlns="http://www.w3.org/2000/svg" 
                fill="none" 
                viewBox="0 0 24 24" 
                strokeWidth={1.5} 
                stroke="currentColor" 
                className={`w-5 h-5 transition-transform mr-2 ${
                  filterExpanded ? 'rotate-90' : ''
                }`}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              Filters {isAdminMode && <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded ml-2">Admin</span>}
            </button>
          </div>
          <div className="flex items-center space-x-2">
            {/* Filter Summary */}
            {(filterState.selectedRoles.length > 0 || filterState.selectedCategories.length > 0 || filterState.selectedCapabilities.length > 0) && (
              <div className="text-xs text-gray-500 flex items-center space-x-2">
                {filterState.selectedRoles.length > 0 && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">Roles: {filterState.selectedRoles.length}</span>
                )}
                {filterState.selectedCategories.length > 0 && (
                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded">Domains: {filterState.selectedCategories.length}</span>
                )}
                {filterState.selectedCapabilities.length > 0 && (
                  <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">Capabilities: {filterState.selectedCapabilities.length}</span>
                )}
              </div>
            )}
            <button
              onClick={clearAllFilters}
              className="text-sm text-blue-600 hover:text-blue-800"
            >
              Clear All
            </button>
          </div>
        </div>
      </div>

      {/* Filter Content - Collapsible */}
      {filterExpanded && (
        <div className="p-4">
          {/* Render different UI based on mode */}
          {isAdminMode ? renderAdminModeFilters() : renderAgentModeHierarchy()}
        </div>
      )}
    </div>
  );
};

// Create a stable component that doesn't re-render unnecessarily
const MemoizedHierarchicalFilter = React.memo(HierarchicalFilter, (prevProps, nextProps) => {
  // Only re-render if meaningful props change
  const shouldUpdate = !(
    prevProps.isAdminMode === nextProps.isAdminMode &&
    prevProps.agentId === nextProps.agentId &&
    prevProps.className === nextProps.className
  );
  
  if (shouldUpdate) {
    console.log('HierarchicalFilter memo: allowing re-render due to prop changes');
  } else {
    console.log('HierarchicalFilter memo: preventing re-render - props unchanged');
  }
  
  return !shouldUpdate;
});

export default MemoizedHierarchicalFilter;
