'use client';

import React, { useState, useEffect } from 'react';
import {
  getRolesWithToolCounts,
  getCapabilitiesWithToolSkillCount,
  getSkillsByCapability,
  getMcpToolsBySkill,
  updateAgentProfile,
  RoleWithDomainsAndToolsInfo,
  DomainToolCount,
  CapabilityToolSkillCount,
  SkillInfo,
  McpToolInfo
} from '@/lib/apiClient';
import { ToolFilter } from '@/lib/apiClient';

interface RoleToolHierarchyProps {
  agentId: string;
  tenantName: string;
  onFilterSaved?: () => void;
}

const RoleToolHierarchy: React.FC<RoleToolHierarchyProps> = ({ agentId, tenantName, onFilterSaved }) => {
  
  // Data state
  const [roles, setRoles] = useState<RoleWithDomainsAndToolsInfo[]>([]);
  const [domainCapabilities, setDomainCapabilities] = useState<Record<string, CapabilityToolSkillCount[]>>({});
  const [capabilitySkills, setCapabilitySkills] = useState<Record<string, SkillInfo[]>>({});
  const [skillTools, setSkillTools] = useState<Record<string, McpToolInfo[]>>({});
  
  // Expansion state
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
  
  // Messages
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Load roles and agent profile on mount
  useEffect(() => {
    loadRoles();
    loadAgentProfile();
  }, [agentId]);

  const loadRoles = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedRoles = await getRolesWithToolCounts(agentId);
      setRoles(fetchedRoles);
    } catch (err) {
      console.error("Failed to fetch roles:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch roles.');
    } finally {
      setIsLoading(false);
    }
  };

  const loadAgentProfile = async () => {
    try {
      if (!tenantName) {
        console.error('No tenant name provided');
        return;
      }
      
      const { getAgentProfile } = await import('@/lib/apiClient');
      const profile = await getAgentProfile(tenantName, agentId);
      
      // If profile has context with filter data, populate the selections
      if (profile.context) {
        const filter = profile.context as ToolFilter;
        
        // Extract flat lists from hierarchical structure
        const roleNames = new Set<string>();
        const domains = new Set<string>();
        const capabilities = new Set<string>();
        const skills = new Set<string>();

        filter.roles?.forEach(role => {
          roleNames.add(role.name);
          
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
        
        setSelectedRoles(roleNames);
        setSelectedDomains(domains);
        setSelectedCapabilities(capabilities);
        setSelectedSkills(skills);
        
        // Save the original state for comparison
        setSavedRoles(new Set(roleNames));
        setSavedDomains(new Set(domains));
        setSavedCapabilities(new Set(capabilities));
        setSavedSkills(new Set(skills));
      }
    } catch (err) {
      console.error("Failed to load agent profile:", err);
      // Don't set error state here as this is not critical
    }
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
            setError('No tenant name provided');
            return;
          }
          
          const capabilities = await getCapabilitiesWithToolSkillCount(tenantName, domainName);
          // Filter out capabilities with zero tool count
          const filteredCapabilities = capabilities.filter(cap => cap.tool_count > 0);
          setDomainCapabilities(prev => ({ ...prev, [domainName]: filteredCapabilities }));
        } catch (err) {
          console.error(`Failed to load capabilities for domain ${domainName}:`, err);
          setError(err instanceof Error ? err.message : 'Failed to load capabilities.');
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
            setError('No tenant name provided');
            return;
          }
          
          const skills = await getSkillsByCapability(tenantName, capabilityName);
          setCapabilitySkills(prev => ({ ...prev, [capabilityName]: skills }));
        } catch (err) {
          console.error(`Failed to load skills for capability ${capabilityName}:`, err);
          setError(err instanceof Error ? err.message : 'Failed to load skills.');
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
            setError('No tenant name provided');
            return;
          }
          
          const tools = await getMcpToolsBySkill(tenantName, skillName);
          setSkillTools(prev => ({ ...prev, [skillName]: tools }));
        } catch (err) {
          console.error(`Failed to load tools for skill ${skillName}:`, err);
          setError(err instanceof Error ? err.message : 'Failed to load tools.');
        } finally {
          setLoadingStates(prev => ({ ...prev, [`skill-${skillKey}`]: false }));
        }
      }
    }
    setExpandedSkills(newExpanded);
  };

  const toggleRoleSelection = (role: RoleWithDomainsAndToolsInfo) => {
    const newSelectedRoles = new Set(selectedRoles);
    const newSelectedDomains = new Set(selectedDomains);
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedSkills = new Set(selectedSkills);
    
    if (newSelectedRoles.has(role.role_name)) {
      // Unselecting role - remove all child domains, capabilities, and skills
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
      newSelectedRoles.add(role.role_name);
    }
    
    setSelectedRoles(newSelectedRoles);
    setSelectedDomains(newSelectedDomains);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedSkills(newSelectedSkills);
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
      newSelectedDomains.add(domainName);
      // Auto-select parent role
      newSelectedRoles.add(roleName);
    }
    
    setSelectedRoles(newSelectedRoles);
    setSelectedDomains(newSelectedDomains);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedSkills(newSelectedSkills);
  };

  const toggleCapabilitySelection = (capabilityName: string, domainName: string) => {
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedDomains = new Set(selectedDomains);
    const newSelectedSkills = new Set(selectedSkills);
    
    if (newSelectedCapabilities.has(capabilityName)) {
      // Unselecting capability - remove all child skills
      newSelectedCapabilities.delete(capabilityName);
      
      // Find and remove all skills under this capability
      const capSkills = capabilitySkills[capabilityName] || [];
      capSkills.forEach(skill => {
        newSelectedSkills.delete(skill.name);
      });
    } else {
      newSelectedCapabilities.add(capabilityName);
      // Auto-select parent domain
      newSelectedDomains.add(domainName);
    }
    
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedDomains(newSelectedDomains);
    setSelectedSkills(newSelectedSkills);
  };

  const toggleSkillSelection = (skillName: string, capabilityName: string, domainName: string) => {
    const newSelectedSkills = new Set(selectedSkills);
    const newSelectedCapabilities = new Set(selectedCapabilities);
    const newSelectedDomains = new Set(selectedDomains);
    
    if (newSelectedSkills.has(skillName)) {
      newSelectedSkills.delete(skillName);
    } else {
      newSelectedSkills.add(skillName);
      // Auto-select parent capability and domain
      newSelectedCapabilities.add(capabilityName);
      newSelectedDomains.add(domainName);
    }
    
    setSelectedSkills(newSelectedSkills);
    setSelectedCapabilities(newSelectedCapabilities);
    setSelectedDomains(newSelectedDomains);
  };

  // Check if selections have changed from saved state
  const hasChanges = () => {
    const domainsChanged = 
      selectedDomains.size !== savedDomains.size ||
      Array.from(selectedDomains).some(d => !savedDomains.has(d));
    
    const capabilitiesChanged = 
      selectedCapabilities.size !== savedCapabilities.size ||
      Array.from(selectedCapabilities).some(c => !savedCapabilities.has(c));
    
    const skillsChanged = 
      selectedSkills.size !== savedSkills.size ||
      Array.from(selectedSkills).some(s => !savedSkills.has(s));
    
    return domainsChanged || capabilitiesChanged || skillsChanged;
  };

  const handleSaveFilter = async () => {
    setIsSavingFilter(true);
    setError(null);
    setSuccessMessage(null);

    try {
      // Build hierarchical structure from flat selections
      // This component doesn't use the hierarchical ToolFilter structure properly
      // For now, just save the flat selections as a simple object
      const filterData = {
        tool_query: "",
        domains: Array.from(selectedDomains),
        capabilities: Array.from(selectedCapabilities),
        skills: Array.from(selectedSkills)
      };

      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      await updateAgentProfile(tenantName, agentId, { context: filterData as any });
      
      // Update saved state after successful save
      setSavedDomains(new Set(selectedDomains));
      setSavedCapabilities(new Set(selectedCapabilities));
      setSavedSkills(new Set(selectedSkills));
      
      setSuccessMessage('Tool filter saved successfully!');
      if (onFilterSaved) {
        onFilterSaved();
      }
    } catch (err: any) {
      setError(err.message || 'Failed to save filter.');
    } finally {
      setIsSavingFilter(false);
    }
  };

  const clearAllSelections = () => {
    setSelectedDomains(new Set());
    setSelectedCapabilities(new Set());
    setSelectedSkills(new Set());
  };

  if (isLoading) {
    return (
      <div className="p-4 border border-gray-200 rounded-lg">
        <div className="flex items-center justify-center">
          <div className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
          <span className="ml-2 text-sm text-gray-600">Loading role hierarchy...</span>
        </div>
      </div>
    );
  }

  if (error && roles.length === 0) {
    return (
      <div className="p-4 border border-red-200 bg-red-50 rounded-lg">
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
    <div className="space-y-4">
      {/* Header with save button */}
      <div className="flex items-center justify-between p-4 bg-gray-50 rounded-lg border border-gray-200">
        <div>
          <h3 className="text-lg font-semibold text-gray-800">Role Tool Hierarchy</h3>
          <p className="text-sm text-gray-600 mt-1">
            Select domains, capabilities, and skills to build your tool filter
          </p>
        </div>
        <div className="flex items-center space-x-2">
          {(selectedDomains.size > 0 || selectedCapabilities.size > 0 || selectedSkills.size > 0) && (
            <>
              <div className="text-xs text-gray-500 flex items-center space-x-2">
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
              <button
                onClick={clearAllSelections}
                className="text-sm text-gray-600 hover:text-gray-800 px-3 py-1 border border-gray-300 rounded"
              >
                Clear
              </button>
            </>
          )}
          <button
            onClick={handleSaveFilter}
            disabled={isSavingFilter || !hasChanges()}
            className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed text-sm"
          >
            {isSavingFilter ? 'Saving...' : 'Save Filter'}
          </button>
        </div>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-3 bg-red-50 border border-red-200 rounded">
          <p className="text-red-600 text-sm">{error}</p>
        </div>
      )}
      {successMessage && (
        <div className="p-3 bg-green-50 border border-green-200 rounded">
          <p className="text-green-600 text-sm">{successMessage}</p>
        </div>
      )}

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
                  {roles.length > 1 ? (
                    <label className="flex items-center flex-1 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={selectedRoles.has(role.role_name)}
                        onChange={() => toggleRoleSelection(role)}
                        className="rounded border-gray-300 text-blue-600 focus:ring-blue-500 mr-2"
                      />
                      <div className="flex-1">
                        <h4 className="text-sm font-semibold text-gray-900">{role.role_label}</h4>
                        <p className="text-xs text-gray-600 mt-1">{role.role_description}</p>
                      </div>
                    </label>
                  ) : (
                    <div className="flex-1">
                      <h4 className="text-sm font-semibold text-gray-900">{role.role_label}</h4>
                      <p className="text-xs text-gray-600 mt-1">{role.role_description}</p>
                    </div>
                  )}
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
                                    onChange={() => toggleCapabilitySelection(capability.name, domain.name)}
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
                                            onChange={() => toggleSkillSelection(skill.name, capability.name, domain.name)}
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
  );
};

export default RoleToolHierarchy;
