'use client';

import React, { useState, useEffect } from 'react';
import {
  getRolesWithToolCounts,
  getCapabilitiesWithToolSkillCount,
  getSkillsByCapability,
  getMcpToolsBySkill,
  getAgentProfile,
  updateAgentProfile,
  RoleWithDomainsAndToolsInfo,
  CapabilityToolSkillCount,
  SkillInfo,
  McpToolInfo,
  ToolFilter,
  ToolFilterRole,
  ToolFilterDomain,
  ToolFilterCapability
} from '@/lib/apiClient';
import { useUserData } from "@/lib/contexts/UserDataContext";

interface HierarchicalToolFilterProps {
  agentId?: string;                    // undefined = admin mode, string = agent-specific
  tenantName?: string;                 // tenant name to use for API calls
  showSaveButton?: boolean;            // true for pages that allow saving
  showLoadButton?: boolean;            // true for agent tool list page
  collapsible?: boolean;               // true for tool lists, false for agent profile
  title?: string;                      // "Role Tool Hierarchy" or "Filters"
  autoLoadFilter?: boolean;            // true for agent profile (auto-load on mount)
  showToolQuery?: boolean;             // true to show tool query input (default: true)
  showRoleDescription?: boolean;       // true to show role descriptions (default: true)

  // Callbacks
  onFilterChange?: (filter: ToolFilter) => void;  // for tool list pages
  onFilterSaved?: () => void;                     // after successful save
  onFilterLoaded?: () => void;                    // after successful load

  className?: string;
}

const HierarchicalToolFilter: React.FC<HierarchicalToolFilterProps> = ({
  agentId,
  tenantName,
  showSaveButton = false,
  showLoadButton = false,
  collapsible = false,
  title = "Filters",
  autoLoadFilter = false,
  showToolQuery = true,
  showRoleDescription = true,
  onFilterChange,
  onFilterSaved,
  onFilterLoaded,
  className = ''
}) => {
  const { userData } = useUserData();
  
  // Tool query state
  const [toolQuery, setToolQuery] = useState<string>('');
  const [savedToolQuery, setSavedToolQuery] = useState<string>('');

  // Data state
  const [roles, setRoles] = useState<RoleWithDomainsAndToolsInfo[]>([]);
  const [domainCapabilities, setDomainCapabilities] = useState<Record<string, CapabilityToolSkillCount[]>>({});
  const [capabilitySkills, setCapabilitySkills] = useState<Record<string, SkillInfo[]>>({});
  const [skillTools, setSkillTools] = useState<Record<string, McpToolInfo[]>>({});

  // Expansion state
  const [filterExpanded, setFilterExpanded] = useState(false);
  const [expandedRoles, setExpandedRoles] = useState<Set<string>>(new Set());
  const [expandedDomains, setExpandedDomains] = useState<Set<string>>(new Set());
  const [expandedCapabilities, setExpandedCapabilities] = useState<Set<string>>(new Set());
  const [expandedSkills, setExpandedSkills] = useState<Set<string>>(new Set());

  // Selection state for filter
  const [selectedRoles, setSelectedRoles] = useState<Set<string>>(new Set());
  const [selectedDomains, setSelectedDomains] = useState<Set<string>>(new Set());
  const [selectedCapabilities, setSelectedCapabilities] = useState<Set<string>>(new Set());
  const [selectedSkills, setSelectedSkills] = useState<Set<string>>(new Set());

  // Original saved state for comparison
  const [savedRoles, setSavedRoles] = useState<Set<string>>(new Set());
  const [savedDomains, setSavedDomains] = useState<Set<string>>(new Set());
  const [savedCapabilities, setSavedCapabilities] = useState<Set<string>>(new Set());
  const [savedSkills, setSavedSkills] = useState<Set<string>>(new Set());

  // Loading states
  const [isLoading, setIsLoading] = useState(false);
  const [loadingStates, setLoadingStates] = useState<Record<string, boolean>>({});
  const [isSavingFilter, setIsSavingFilter] = useState(false);
  const [isLoadingFilter, setIsLoadingFilter] = useState(false);

  // Messages
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load roles and optionally agent profile on mount
  useEffect(() => {
    const initializeFilter = async () => {
      await loadRoles();
      if (autoLoadFilter && agentId) {
        handleLoadFilter();
      }
    };
    initializeFilter();
  }, [agentId]);

  const loadRoles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedRoles = await getRolesWithToolCounts(agentId);
      // Filter out roles with zero tool count
      const filteredRoles = fetchedRoles.filter(role => role.tool_count > 0);
      setRoles(filteredRoles);
      return filteredRoles;
    } catch (err) {
      console.error("Failed to fetch roles:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch roles.');
      return [];
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadFilter = async () => {
    if (!agentId) return;

    setIsLoadingFilter(true);
    setError(null);

    try {
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      const profile = await getAgentProfile(tenantName, agentId);

      if (profile?.context) {
        const filter = profile.context as ToolFilter;

        // Apply tool query
        setToolQuery(filter.tool_query || "");
        setSavedToolQuery(filter.tool_query || "");

        // Get current roles count - fetch if not available
        let currentRolesCount = roles.length;
        if (currentRolesCount === 0) {
          const fetchedRoles = await getRolesWithToolCounts(agentId);
          const filteredRoles = fetchedRoles.filter(role => role.tool_count > 0);
          currentRolesCount = filteredRoles.length;
        }

        // Extract flat lists from hierarchical structure
        const roleNames = new Set<string>();
        const domains = new Set<string>();
        const capabilities = new Set<string>();
        const skills = new Set<string>();

        filter.roles?.forEach(role => {
          // Only populate role selection if there are multiple roles
          if (currentRolesCount > 1) {
            roleNames.add(role.name);
          }
          
          role.domains?.forEach(domain => {
            domains.add(domain.name);
            domain.capabilities?.forEach(capability => {
              capabilities.add(capability.name);
              capability.skills?.forEach(skill => {
                skills.add(skill);
              });
            });
          });
        });

        // Apply hierarchical selections
        setSelectedRoles(roleNames);
        setSelectedDomains(domains);
        setSelectedCapabilities(capabilities);
        setSelectedSkills(skills);

        // Update saved state
        setSavedRoles(new Set(roleNames));
        setSavedDomains(new Set(domains));
        setSavedCapabilities(new Set(capabilities));
        setSavedSkills(new Set(skills));

        // Notify parent with complete filter
        if (onFilterLoaded) onFilterLoaded();
        if (onFilterChange) {
          onFilterChange(filter);
        }

        setSuccessMessage('Filter loaded from agent profile!');
        setTimeout(() => setSuccessMessage(null), 3000);
      }
    } catch (err) {
      console.error('Failed to load filter:', err);
      setError(err instanceof Error ? err.message : 'Failed to load filter');
    } finally {
      setIsLoadingFilter(false);
    }
  };

  const handleSaveFilter = async () => {
    if (!agentId) return;

    setIsSavingFilter(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Build hierarchical structure independently for each role
      const toolFilterRoles: ToolFilterRole[] = [];

      // Process each role independently
      roles.forEach(role => {
        const roleName = role.role_name;
        
        // Check if this role has any selections
        let roleHasSelections = false;
        const roleDomainMap = new Map<string, Map<string, Set<string>>>();

        // Process domains under this role
        role.domains.forEach(domain => {
          if (selectedDomains.has(domain.name)) {
            roleHasSelections = true;
            
            const domainCaps = domainCapabilities[domain.name] || [];
            const selectedCapsInDomain = domainCaps.filter(cap => selectedCapabilities.has(cap.name));
            
            // If domain is selected but no capabilities in this domain are selected
            if (selectedCapsInDomain.length === 0) {
              if (!roleDomainMap.has(domain.name)) {
                roleDomainMap.set(domain.name, new Map());
              }
            } else {
              // Process selected capabilities in this domain
              selectedCapsInDomain.forEach(capability => {
                const capSkills = capabilitySkills[capability.name] || [];
                const selectedSkillsInCap = capSkills.filter(skill => selectedSkills.has(skill.name));
                
                if (!roleDomainMap.has(domain.name)) {
                  roleDomainMap.set(domain.name, new Map());
                }
                const capabilityMap = roleDomainMap.get(domain.name)!;
                
                // If capability is selected but no skills in this capability are selected
                if (selectedSkillsInCap.length === 0) {
                  if (!capabilityMap.has(capability.name)) {
                    capabilityMap.set(capability.name, new Set());
                  }
                } else {
                  // Add selected skills
                  if (!capabilityMap.has(capability.name)) {
                    capabilityMap.set(capability.name, new Set());
                  }
                  selectedSkillsInCap.forEach(skill => {
                    capabilityMap.get(capability.name)!.add(skill.name);
                  });
                }
              });
            }
          }
        });

        // If this role has selections, add it to the filter
        if (roleHasSelections) {
          const roleFilter: ToolFilterRole = {
            name: roleName,
            domains: roleDomainMap.size > 0 ? Array.from(roleDomainMap.entries()).map(([domainName, capabilityMap]) => ({
              name: domainName,
              capabilities: capabilityMap.size > 0 ? Array.from(capabilityMap.entries()).map(([capabilityName, skillSet]) => ({
                name: capabilityName,
                skills: skillSet.size > 0 ? Array.from(skillSet) : undefined
              })) : undefined
            })) : undefined
          };
          toolFilterRoles.push(roleFilter);
        } else if (selectedRoles.has(roleName)) {
          // Role is explicitly selected but has no domain selections under this role
          // Check if this role has any domains selected at all
          const hasAnyDomainInThisRole = role.domains.some(domain => selectedDomains.has(domain.name));
          
          if (!hasAnyDomainInThisRole) {
            // This role is selected but none of its domains are selected
            toolFilterRoles.push({
              name: roleName,
              domains: undefined
            });
          }
        }
      });

      const toolFilter: ToolFilter = {
        tool_query: toolQuery,
        roles: toolFilterRoles
      };

      console.log('Saving filter (independent role extraction):', JSON.stringify(toolFilter, null, 2));

      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }

      await updateAgentProfile(tenantName, agentId, { context: toolFilter });

      // Update saved state
      setSavedToolQuery(toolQuery);
      setSavedRoles(new Set(selectedRoles));
      setSavedDomains(new Set(selectedDomains));
      setSavedCapabilities(new Set(selectedCapabilities));
      setSavedSkills(new Set(selectedSkills));

      setSuccessMessage('Filter saved successfully!');
      setTimeout(() => setSuccessMessage(null), 3000);

      if (onFilterSaved) onFilterSaved();
    } catch (err) {
      console.error('Failed to save filter:', err);
      setError(err instanceof Error ? err.message : 'Failed to save filter');
    } finally {
      setIsSavingFilter(false);
    }
  };

  const hasChanges = () => {
    const queryChanged = toolQuery !== savedToolQuery;

    const rolesChanged =
      selectedRoles.size !== savedRoles.size ||
      Array.from(selectedRoles).some(r => !savedRoles.has(r));

    const domainsChanged =
      selectedDomains.size !== savedDomains.size ||
      Array.from(selectedDomains).some(d => !savedDomains.has(d));

    const capabilitiesChanged =
      selectedCapabilities.size !== savedCapabilities.size ||
      Array.from(selectedCapabilities).some(c => !savedCapabilities.has(c));

    const skillsChanged =
      selectedSkills.size !== savedSkills.size ||
      Array.from(selectedSkills).some(s => !savedSkills.has(s));

    return queryChanged || rolesChanged || domainsChanged || capabilitiesChanged || skillsChanged;
  };

  // Notify parent of filter changes
  useEffect(() => {
    if (onFilterChange) {
      // Build hierarchical structure from flat selections
      const roleMap = new Map<string, Map<string, Map<string, Set<string>>>>();

      // Determine which roles to include
      const rolesToInclude = new Set<string>();
      
      // Add explicitly selected roles
      selectedRoles.forEach(roleName => rolesToInclude.add(roleName));

      // Build hierarchy based on actual selections
      // IMPORTANT: Always include the role when a domain is selected, even in admin mode
      roles.forEach(role => {
        role.domains.forEach(domain => {
          if (selectedDomains.has(domain.name)) {
            // ALWAYS add role to include list when domain is selected
            // This ensures the role is included in the filter even in admin mode
            rolesToInclude.add(role.role_name);
            
            const domainCaps = domainCapabilities[domain.name] || [];
            const selectedCapsInDomain = domainCaps.filter(cap => selectedCapabilities.has(cap.name));
            
            // If domain is selected but no capabilities in this domain are selected
            if (selectedCapsInDomain.length === 0) {
              if (!roleMap.has(role.role_name)) {
                roleMap.set(role.role_name, new Map());
              }
              const domainMap = roleMap.get(role.role_name)!;
              if (!domainMap.has(domain.name)) {
                domainMap.set(domain.name, new Map());
              }
            } else {
              // Process selected capabilities in this domain
              selectedCapsInDomain.forEach(capability => {
                const capSkills = capabilitySkills[capability.name] || [];
                const selectedSkillsInCap = capSkills.filter(skill => selectedSkills.has(skill.name));
                
                if (!roleMap.has(role.role_name)) {
                  roleMap.set(role.role_name, new Map());
                }
                const domainMap = roleMap.get(role.role_name)!;
                if (!domainMap.has(domain.name)) {
                  domainMap.set(domain.name, new Map());
                }
                const capabilityMap = domainMap.get(domain.name)!;
                
                // If capability is selected but no skills in this capability are selected
                if (selectedSkillsInCap.length === 0) {
                  if (!capabilityMap.has(capability.name)) {
                    capabilityMap.set(capability.name, new Set());
                  }
                } else {
                  // Add selected skills
                  if (!capabilityMap.has(capability.name)) {
                    capabilityMap.set(capability.name, new Set());
                  }
                  selectedSkillsInCap.forEach(skill => {
                    capabilityMap.get(capability.name)!.add(skill.name);
                  });
                }
              });
            }
          }
        });
      });

      // Convert to ToolFilter structure
      // Include roles that are explicitly selected OR have child selections
      const toolFilterRoles = Array.from(rolesToInclude).map(roleName => {
        const domainMap = roleMap.get(roleName);
        return {
          name: roleName,
          domains: domainMap && domainMap.size > 0 ? Array.from(domainMap.entries()).map(([domainName, capabilityMap]) => ({
            name: domainName,
            capabilities: capabilityMap.size > 0 ? Array.from(capabilityMap.entries()).map(([capabilityName, skillSet]) => ({
              name: capabilityName,
              skills: skillSet.size > 0 ? Array.from(skillSet) : undefined
            })) : undefined
          })) : undefined
        };
      });

      console.log('Filter changed - sending to parent:', {
        tool_query: toolQuery,
        roles: toolFilterRoles,
        selectedRoles: Array.from(selectedRoles),
        selectedDomains: Array.from(selectedDomains),
        selectedCapabilities: Array.from(selectedCapabilities),
        selectedSkills: Array.from(selectedSkills),
        rolesToInclude: Array.from(rolesToInclude)
      });

      onFilterChange({
        tool_query: toolQuery,
        roles: toolFilterRoles
      });
    }
  }, [toolQuery, selectedRoles, selectedDomains, selectedCapabilities, selectedSkills, onFilterChange, roles, domainCapabilities, capabilitySkills]);

  const clearAllSelections = () => {
    setToolQuery('');
    setSelectedRoles(new Set());
    setSelectedDomains(new Set());
    setSelectedCapabilities(new Set());
    setSelectedSkills(new Set());
  };

  const toggleRoleExpansion = (roleName: string) => {
    const newExpanded = new Set(expandedRoles);
    if (newExpanded.has(roleName)) {
      newExpanded.delete(roleName);
    } else {
      newExpanded.add(roleName);
    }
    setExpandedRoles(newExpanded);
  };

  const toggleDomainExpansion = async (roleName: string, domainName: string) => {
    const domainKey = `${roleName}-${domainName}`;
    const newExpanded = new Set(expandedDomains);

    if (newExpanded.has(domainKey)) {
      newExpanded.delete(domainKey);
    } else {
      newExpanded.add(domainKey);

      // Load capabilities for this domain if not already loaded
      if (!domainCapabilities[domainName]) {
        setLoadingStates(prev => ({ ...prev, [`domain-${domainKey}`]: true }));
        try {
          if (!tenantName) {
            console.error('No tenant name provided');
            return;
          }
          
          const capabilities = await getCapabilitiesWithToolSkillCount(tenantName, domainName);
          // Filter out capabilities with zero tool count
          const filteredCapabilities = capabilities.filter(cap => cap.tool_count > 0);
          setDomainCapabilities(prev => ({ ...prev, [domainName]: filteredCapabilities }));
        } catch (err) {
          console.error(`Failed to load capabilities for domain ${domainName}:`, err);
        } finally {
          setLoadingStates(prev => ({ ...prev, [`domain-${domainKey}`]: false }));
        }
      }
    }
    setExpandedDomains(newExpanded);
  };

  const toggleCapabilityExpansion = async (roleName: string, domainName: string, capabilityName: string) => {
    const capKey = `${roleName}-${domainName}-${capabilityName}`;
    const newExpanded = new Set(expandedCapabilities);

    if (newExpanded.has(capKey)) {
      newExpanded.delete(capKey);
    } else {
      newExpanded.add(capKey);

      // Load skills for this capability if not already loaded
      if (!capabilitySkills[capabilityName]) {
        setLoadingStates(prev => ({ ...prev, [`capability-${capKey}`]: true }));
        try {
          if (!tenantName) {
            console.error('No tenant name provided');
            return;
          }
          
          const skills = await getSkillsByCapability(tenantName, capabilityName);
          setCapabilitySkills(prev => ({ ...prev, [capabilityName]: skills }));
        } catch (err) {
          console.error(`Failed to load skills for capability ${capabilityName}:`, err);
        } finally {
          setLoadingStates(prev => ({ ...prev, [`capability-${capKey}`]: false }));
        }
      }
    }
    setExpandedCapabilities(newExpanded);
  };

  const toggleSkillExpansion = async (roleName: string, domainName: string, capabilityName: string, skillName: string) => {
    const skillKey = `${roleName}-${domainName}-${capabilityName}-${skillName}`;
    const newExpanded = new Set(expandedSkills);

    if (newExpanded.has(skillKey)) {
      newExpanded.delete(skillKey);
    } else {
      newExpanded.add(skillKey);

      // Load tools for this skill if not already loaded
      if (!skillTools[skillName]) {
        setLoadingStates(prev => ({ ...prev, [`skill-${skillKey}`]: true }));
        try {
          if (!tenantName) {
            console.error('No tenant name provided');
            return;
          }
          
          const tools = await getMcpToolsBySkill(tenantName, skillName);
          setSkillTools(prev => ({ ...prev, [skillName]: tools }));
        } catch (err) {
          console.error(`Failed to load tools for skill ${skillName}:`, err);
        } finally {
          setLoadingStates(prev => ({ ...prev, [`skill-${skillKey}`]: false }));
        }
      }
    }
    setExpandedSkills(newExpanded);
  };

  const toggleDomainSelection = (domainName: string, roleName: string) => {
    const newSelectedDomains = new Set(selectedDomains);
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedSkills = new Set(selectedSkills);
    const newSelectedRoles = new Set(selectedRoles);

    if (newSelectedDomains.has(domainName)) {
      // Unselecting domain - remove all child capabilities and skills
      newSelectedDomains.delete(domainName);

      // Find and remove all capabilities under this domain
      const domainCaps = domainCapabilities[domainName] || [];
      domainCaps.forEach(cap => {
        newSelectedCapabilities.delete(cap.name);

        // Find and remove all skills under this capability
        const capSkills = capabilitySkills[cap.name] || [];
        capSkills.forEach(skill => {
          newSelectedSkills.delete(skill.name);
        });
      });
    } else {
      // Selecting domain - auto-select ONLY its parent role (not all roles)
      newSelectedDomains.add(domainName);
      newSelectedRoles.add(roleName);
    }

    setSelectedRoles(newSelectedRoles);
    setSelectedDomains(newSelectedDomains);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedSkills(newSelectedSkills);
  };

  const toggleCapabilitySelection = (capabilityName: string, domainName: string, roleName: string) => {
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedDomains = new Set(selectedDomains);
    const newSelectedSkills = new Set(selectedSkills);
    const newSelectedRoles = new Set(selectedRoles);

    if (newSelectedCapabilities.has(capabilityName)) {
      // Unselecting capability - remove all child skills
      newSelectedCapabilities.delete(capabilityName);

      // Find and remove all skills under this capability
      const capSkills = capabilitySkills[capabilityName] || [];
      capSkills.forEach(skill => {
        newSelectedSkills.delete(skill.name);
      });
    } else {
      // Selecting capability - auto-select ONLY its parent domain and role
      newSelectedCapabilities.add(capabilityName);
      newSelectedDomains.add(domainName);
      newSelectedRoles.add(roleName);
    }

    setSelectedRoles(newSelectedRoles);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedDomains(newSelectedDomains);
    setSelectedSkills(newSelectedSkills);
  };

  const toggleSkillSelection = (skillName: string, capabilityName: string, domainName: string, roleName: string) => {
    const newSelectedSkills = new Set(selectedSkills);
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedDomains = new Set(selectedDomains);
    const newSelectedRoles = new Set(selectedRoles);

    if (newSelectedSkills.has(skillName)) {
      newSelectedSkills.delete(skillName);
    } else {
      // Selecting skill - auto-select ONLY its parent capability, domain, and role
      newSelectedSkills.add(skillName);
      newSelectedCapabilities.add(capabilityName);
      newSelectedDomains.add(domainName);
      newSelectedRoles.add(roleName);
    }

    setSelectedRoles(newSelectedRoles);
    setSelectedSkills(newSelectedSkills);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedDomains(newSelectedDomains);
  };

  if (isLoading) {
    return (
      <div className={`p-4 border border-gray-200 rounded-lg ${className}`}>
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Loading filters...</span>
        </div>
      </div>
    );
  }

  if (error && roles.length === 0) {
    return (
      <div className={`p-4 border border-red-200 bg-red-50 rounded-lg ${className}`}>
        <p className="text-red-800 text-sm">Error: {error}</p>
        <button
          onClick={loadRoles}
          className="mt-2 text-sm text-red-600 hover:text-red-800"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className={`border border-gray-200 rounded-lg bg-white ${className}`}>
      {/* Header */}
      <div className="p-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center">
            {collapsible && (
              <button
                onClick={() => setFilterExpanded(!filterExpanded)}
                className="flex items-center text-lg font-medium text-gray-900 hover:text-gray-700 mr-2"
              >
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                  strokeWidth={1.5}
                  stroke="currentColor"
                  className={`w-5 h-5 transition-transform mr-2 ${filterExpanded ? 'rotate-90' : ''}`}
                >
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
                {title}
              </button>
            )}
            {!collapsible && <h3 className="text-lg font-semibold text-gray-800">{title}</h3>}
          </div>

          {/* Action Buttons */}
          <div className="flex items-center space-x-2">
            {/* Filter Summary */}
            {(toolQuery || selectedRoles.size > 0 || selectedDomains.size > 0 || selectedCapabilities.size > 0 || selectedSkills.size > 0) && (
              <div className="text-xs text-gray-500 flex items-center space-x-2">
                {toolQuery && (
                  <span className="bg-blue-100 text-blue-800 px-2 py-1 rounded">
                    Query: "{toolQuery.substring(0, 20)}{toolQuery.length > 20 ? '...' : ''}"
                  </span>
                )}
                {selectedRoles.size > 0 && (
                  <span className="bg-indigo-100 text-indigo-800 px-2 py-1 rounded">
                    Roles: {selectedRoles.size}
                  </span>
                )}
                {selectedDomains.size > 0 && (
                  <span className="bg-green-100 text-green-800 px-2 py-1 rounded">
                    Domains: {selectedDomains.size}
                  </span>
                )}
                {selectedCapabilities.size > 0 && (
                  <span className="bg-purple-100 text-purple-800 px-2 py-1 rounded">
                    Capabilities: {selectedCapabilities.size}
                  </span>
                )}
                {selectedSkills.size > 0 && (
                  <span className="bg-orange-100 text-orange-800 px-2 py-1 rounded">
                    Skills: {selectedSkills.size}
                  </span>
                )}
              </div>
            )}

            {/* Load Filter Button */}
            {showLoadButton && (
              <button
                onClick={handleLoadFilter}
                disabled={isLoadingFilter}
                className="px-3 py-1 bg-green-600 text-white rounded hover:bg-green-700 disabled:opacity-50 text-sm"
              >
                {isLoadingFilter ? 'Loading...' : 'Load Filter'}
              </button>
            )}

            {/* Save Filter Button */}
            {showSaveButton && (
              <button
                onClick={handleSaveFilter}
                disabled={isSavingFilter || !hasChanges()}
                className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 text-sm"
              >
                {isSavingFilter ? 'Saving...' : 'Save Filter'}
              </button>
            )}

            {/* Clear Button */}
            <button
              onClick={clearAllSelections}
              className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1 border border-gray-300 rounded"
            >
              Clear
            </button>
          </div>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="mx-4 mt-4 p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}
      {successMessage && (
        <div className="mx-4 mt-4 p-3 bg-green-50 border border-green-200 rounded">
          <p className="text-green-600 text-sm">{successMessage}</p>
        </div>
      )}

      {/* Filter Content */}
      {(!collapsible || filterExpanded) && (
        <div className="p-4 space-y-4">
          {/* Tool Query Input */}
          {showToolQuery && (
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Tool Query (Search)
              </label>
              <input
                type="text"
                value={toolQuery}
                onChange={(e) => setToolQuery(e.target.value)}
                placeholder="Search tools by description..."
                className="w-full px-3 py-2 border border-gray-300 rounded-md bg-gray-50 text-gray-900 placeholder-gray-500 focus:bg-white focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
          )}

          {/* Hierarchical Selection */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Domains, Capabilities & Skills
            </label>

            {/* Role hierarchy */}
            <div className="space-y-3">
              {roles.map((role) => (
                <div key={role.role_name} className="border border-gray-200 rounded-lg bg-white">
                  {/* Role Level */}
                  <div className="p-3 bg-gray-50 border-b border-gray-200">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center flex-1">
                        <button
                          onClick={() => toggleRoleExpansion(role.role_name)}
                          className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                        >
                          <svg
                            xmlns="http://www.w3.org/2000/svg"
                            fill="none"
                            viewBox="0 0 24 24"
                            strokeWidth={1.5}
                            stroke="currentColor"
                            className={`w-4 h-4 transition-transform ${
                              expandedRoles.has(role.role_name) ? 'rotate-90' : ''
                            }`}
                          >
                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                          </svg>
                        </button>
                        {roles.length > 1 && (
                          <input
                            type="checkbox"
                            checked={selectedRoles.has(role.role_name)}
                            onChange={() => {
                              const newSelectedRoles = new Set(selectedRoles);
                              const newSelectedDomains = new Set(selectedDomains);
                              const newSelectedCapabilities = new Set(selectedCapabilities);
                              const newSelectedSkills = new Set(selectedSkills);
                              
                              if (newSelectedRoles.has(role.role_name)) {
                                // Deselecting role - remove all child domains, capabilities, and skills
                                newSelectedRoles.delete(role.role_name);
                                
                                // Remove all domains under this role
                                role.domains.forEach(domain => {
                                  newSelectedDomains.delete(domain.name);
                                  
                                  // Remove all capabilities under this domain
                                  const domainCaps = domainCapabilities[domain.name] || [];
                                  domainCaps.forEach(cap => {
                                    newSelectedCapabilities.delete(cap.name);
                                    
                                    // Remove all skills under this capability
                                    const capSkills = capabilitySkills[cap.name] || [];
                                    capSkills.forEach(skill => {
                                      newSelectedSkills.delete(skill.name);
                                    });
                                  });
                                });
                              } else {
                                // Selecting role
                                newSelectedRoles.add(role.role_name);
                              }
                              
                              setSelectedRoles(newSelectedRoles);
                              setSelectedDomains(newSelectedDomains);
                              setSelectedCapabilities(newSelectedCapabilities);
                              setSelectedSkills(newSelectedSkills);
                            }}
                            className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
                          />
                        )}
                        <div className="flex-1">
                          <h4 className="text-sm font-semibold text-gray-900">{role.role_label}</h4>
                          {showRoleDescription && (
                            <p className="text-xs text-gray-600 mt-1">{role.role_description}</p>
                          )}
                        </div>
                      </div>
                      <span className="text-xs bg-blue-100 text-blue-800 px-2 py-1 rounded ml-2">
                        {role.tool_count} tools
                      </span>
                    </div>
                  </div>

                  {/* Domains under this role */}
                  {expandedRoles.has(role.role_name) && (
                    <div className="p-3 space-y-2">
                      {role.domains.map((domain) => (
                        <div key={domain.name} className="ml-4 border-l-2 border-gray-200 pl-3">
                          {/* Domain Level */}
                          <div className="flex items-center justify-between">
                            <div className="flex items-center flex-1">
                              <button
                                onClick={() => toggleDomainExpansion(role.role_name, domain.name)}
                                className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                                disabled={loadingStates[`domain-${role.role_name}-${domain.name}`]}
                              >
                                {loadingStates[`domain-${role.role_name}-${domain.name}`] ? (
                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                                ) : (
                                  <svg
                                    xmlns="http://www.w3.org/2000/svg"
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    strokeWidth={1.5}
                                    stroke="currentColor"
                                    className={`w-4 h-4 transition-transform ${
                                      expandedDomains.has(`${role.role_name}-${domain.name}`) ? 'rotate-90' : ''
                                    }`}
                                  >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                                  </svg>
                                )}
                              </button>
                              <label className="flex items-center flex-1 cursor-pointer">
                                <input
                                  type="checkbox"
                                  checked={selectedDomains.has(domain.name)}
                                  onChange={() => toggleDomainSelection(domain.name, role.role_name)}
                                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="ml-2 text-sm font-medium text-gray-700">{domain.label}</span>
                              </label>
                            </div>
                            <span className="text-xs bg-green-100 text-green-800 px-2 py-1 rounded ml-2">
                              {domain.tool_count} tools
                            </span>
                          </div>

                          {/* Capabilities under this domain */}
                          {expandedDomains.has(`${role.role_name}-${domain.name}`) && (
                            <div className="ml-6 mt-2 space-y-2">
                              {domainCapabilities[domain.name]?.map((capability) => (
                                <div key={capability.name} className="border-l-2 border-gray-200 pl-3">
                                  {/* Capability Level */}
                                  <div className="flex items-center justify-between">
                                    <div className="flex items-center flex-1">
                                      <button
                                        onClick={() => toggleCapabilityExpansion(role.role_name, domain.name, capability.name)}
                                        className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                                        disabled={loadingStates[`capability-${role.role_name}-${domain.name}-${capability.name}`]}
                                      >
                                        {loadingStates[`capability-${role.role_name}-${domain.name}-${capability.name}`] ? (
                                          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                                        ) : (
                                          <svg
                                            xmlns="http://www.w3.org/2000/svg"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            strokeWidth={1.5}
                                            stroke="currentColor"
                                            className={`w-4 h-4 transition-transform ${
                                              expandedCapabilities.has(`${role.role_name}-${domain.name}-${capability.name}`) ? 'rotate-90' : ''
                                            }`}
                                          >
                                            <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                                          </svg>
                                        )}
                                      </button>
                                      <label className="flex items-center flex-1 cursor-pointer">
                                        <input
                                          type="checkbox"
                                          checked={selectedCapabilities.has(capability.name)}
                                          onChange={() => toggleCapabilitySelection(capability.name, domain.name, role.role_name)}
                                          className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                        />
                                        <span className="ml-2 text-sm text-gray-700">{capability.label}</span>
                                      </label>
                                    </div>
                                    <span className="text-xs bg-purple-100 text-purple-800 px-2 py-1 rounded ml-2">
                                      {capability.tool_count} tools
                                    </span>
                                  </div>

                                  {/* Skills under this capability */}
                                  {expandedCapabilities.has(`${role.role_name}-${domain.name}-${capability.name}`) && (
                                    <div className="ml-6 mt-2 space-y-1">
                                      {capabilitySkills[capability.name]?.map((skill) => (
                                        <div key={skill.name} className="border-l-2 border-gray-200 pl-3">
                                          {/* Skill Level */}
                                          <div className="flex items-center justify-between">
                                            <div className="flex items-center flex-1">
                                              <button
                                                onClick={() => toggleSkillExpansion(role.role_name, domain.name, capability.name, skill.name)}
                                                className="flex items-center text-sm text-gray-700 hover:text-gray-900 mr-2"
                                                disabled={loadingStates[`skill-${role.role_name}-${domain.name}-${capability.name}-${skill.name}`]}
                                              >
                                                {loadingStates[`skill-${role.role_name}-${domain.name}-${capability.name}-${skill.name}`] ? (
                                                  <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-400"></div>
                                                ) : (
                                                  <svg
                                                    xmlns="http://www.w3.org/2000/svg"
                                                    fill="none"
                                                    viewBox="0 0 24 24"
                                                    strokeWidth={1.5}
                                                    stroke="currentColor"
                                                    className={`w-4 h-4 transition-transform ${
                                                      expandedSkills.has(`${role.role_name}-${domain.name}-${capability.name}-${skill.name}`) ? 'rotate-90' : ''
                                                    }`}
                                                  >
                                                    <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                                                  </svg>
                                                )}
                                              </button>
                                              <label className="flex items-center flex-1 cursor-pointer">
                                                <input
                                                  type="checkbox"
                                                  checked={selectedSkills.has(skill.name)}
                                                  onChange={() => toggleSkillSelection(skill.name, capability.name, domain.name, role.role_name)}
                                                  className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                />
                                                <span className="ml-2 text-sm text-gray-600">{skill.label}</span>
                                              </label>
                                            </div>
                                          </div>

                                          {/* Tools under this skill */}
                                          {expandedSkills.has(`${role.role_name}-${domain.name}-${capability.name}-${skill.name}`) && (
                                            <div className="ml-6 mt-1 space-y-1">
                                              {skillTools[skill.name] && skillTools[skill.name].length > 0 ? (
                                                skillTools[skill.name].map((tool) => (
                                                  <div key={tool.id} className="text-xs text-gray-600 py-1">
                                                    • {tool.name}
                                                  </div>
                                                ))
                                              ) : (
                                                <div className="text-xs text-gray-500 italic">Loading tools...</div>
                                              )}
                                            </div>
                                          )}
                                        </div>
                                      )) || (
                                        <div className="text-xs text-gray-500 italic">Loading skills...</div>
                                      )}
                                    </div>
                                  )}
                                </div>
                              )) || (
                                <div className="text-xs text-gray-500 italic">Loading capabilities...</div>
                              )}
                            </div>
                          )}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default HierarchicalToolFilter;
