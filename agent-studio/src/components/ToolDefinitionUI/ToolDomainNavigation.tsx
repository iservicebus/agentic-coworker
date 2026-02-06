import React, { useState, useEffect } from 'react';
import { 
  getSkillsForMcpTool,
  getCapabilitiesBySkill,
  getDomainsByCapability,
  DomainInfo,
  CapabilityInfo
} from '@/lib/apiClient';

interface NavigationState {
  level: 'tool' | 'skills' | 'capabilities' | 'domains';
  selectedSkill?: string;
  selectedCapability?: CapabilityInfo;
}

interface ToolDomainNavigationProps {
  toolId?: string;
  toolName?: string; // Keep for display purposes
  tenantName: string;
  className?: string;
}

export const ToolDomainNavigation: React.FC<ToolDomainNavigationProps> = ({
  toolId,
  toolName,
  tenantName,
  className = ''
}) => {
  const [skillNames, setSkillNames] = useState<string[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityInfo[]>([]);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  const [navigationState, setNavigationState] = useState<NavigationState>({
    level: 'tool'
  });

  const [isExpanded, setIsExpanded] = useState(false);

  // Auto-discover skills for this specific tool when expanded
  const loadSkillsForTool = async () => {
    if (!toolId) {
      setError('Tool ID is required to fetch skills');
      return;
    }
    
    try {
      setLoading(true);
      setError(null);
      
      console.log('Loading skills for tool ID:', toolId);
      
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      // Get skills specifically for this tool via ToolSkill relationship
      const toolSkills = await getSkillsForMcpTool(tenantName, toolId);
      console.log('Received skills:', toolSkills);
      
      // Ensure we always have an array
      const skillsArray = Array.isArray(toolSkills) ? toolSkills : [];
      setSkillNames(skillsArray);
      
      setNavigationState({ level: 'skills' });
    } catch (err) {
      console.error('Error loading skills for tool ID:', toolId, err);
      setError(`Failed to load skills for this tool: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setSkillNames([]); // Ensure it's always an array even on error
    } finally {
      setLoading(false);
    }
  };

  // Load capabilities for a specific skill
  const loadCapabilitiesForSkill = async (skillName: string) => {
    try {
      setLoading(true);
      setError(null);
      
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      // Use the API to get capabilities by skill using CapabilitySkill relationship table
      const capabilities = await getCapabilitiesBySkill(tenantName, skillName);
      
      setCapabilities(capabilities || []);
      
      setNavigationState({
        level: 'capabilities',
        selectedSkill: skillName
      });
    } catch (err) {
      setError('Failed to load capabilities for this skill');
      console.error('Error loading capabilities:', err);
    } finally {
      setLoading(false);
    }
  };

  // Load domains for a specific capability
  const loadDomainsForCapability = async (capability: CapabilityInfo) => {
    try {
      setLoading(true);
      setError(null);
      
      console.log('Loading domains for capability:', capability.name, capability);
      console.log('Capability full object:', JSON.stringify(capability, null, 2));
      
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      // Get domains specifically for this capability via DomainCapability relationship
      const capabilityDomains = await getDomainsByCapability(tenantName, capability.name);
      console.log('Received domains for capability:', capabilityDomains);
      console.log('Domains array length:', capabilityDomains?.length || 0);
      
      // Ensure we always have an array
      const domainsArray = Array.isArray(capabilityDomains) ? capabilityDomains : [];
      console.log('Final domains array:', domainsArray);
      setDomains(domainsArray);
      
      setNavigationState({
        ...navigationState,
        level: 'domains',
        selectedCapability: capability
      });
    } catch (err) {
      console.error('Error loading domains for capability:', capability.name, err);
      setError(`Failed to load domains for this capability: ${err instanceof Error ? err.message : 'Unknown error'}`);
      setDomains([]); // Ensure it's always an array even on error
    } finally {
      setLoading(false);
    }
  };

  const handleExpand = () => {
    if (!isExpanded) {
      setIsExpanded(true);
      loadSkillsForTool();
    } else {
      setIsExpanded(false);
      setNavigationState({ level: 'tool' });
      setSkillNames([]);
      setCapabilities([]);
      setDomains([]);
    }
  };

  const handleSkillClick = async (skillName: string) => {
    // Directly load capabilities for this skill
    loadCapabilitiesForSkill(skillName);
  };

  const handleCapabilityClick = (capability: CapabilityInfo) => {
    loadDomainsForCapability(capability);
  };

  const handleBackToSkills = () => {
    setNavigationState({ level: 'skills' });
    setCapabilities([]);
    setDomains([]);
  };

  const handleBackToCapabilities = () => {
    if (navigationState.selectedSkill) {
      setNavigationState({
        level: 'capabilities',
        selectedSkill: navigationState.selectedSkill
      });
      setDomains([]);
    }
  };

  // Render hierarchical path breadcrumb
  const renderHierarchicalPath = () => {
    const pathItems = [];
    
    // Always start with tool
    pathItems.push(
      <span key="tool" className="font-medium text-blue-600">
        {toolName || 'Tool'}
      </span>
    );

    // Add skill name directly
    if (navigationState.selectedSkill) {
      pathItems.push(
        <span key="arrow1" className="mx-2 text-gray-400">→</span>,
        <span key="selected-skill" className="font-medium text-green-600">
          {navigationState.selectedSkill}
        </span>
      );
    }

    // Add capability label directly
    if (navigationState.selectedCapability) {
      pathItems.push(
        <span key="arrow2" className="mx-2 text-gray-400">→</span>,
        <span key="selected-cap" className="font-medium text-purple-600">
          {navigationState.selectedCapability.label}
        </span>
      );
    }

    return (
      <div className="text-sm text-gray-600 mb-3 p-2 bg-gray-50 rounded">
        <strong>Path:</strong> {pathItems}
      </div>
    );
  };

  if (loading) {
    return (
      <div className={`border border-gray-200 rounded-lg bg-white p-4 ${className}`}>
        <div className="flex items-center">
          <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600 mr-2"></div>
          <span className="text-sm text-gray-600">Loading...</span>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`border border-red-200 rounded-lg bg-red-50 p-4 ${className}`}>
        <p className="text-red-800 text-sm">Error: {error}</p>
        <button
          onClick={() => {
            setError(null);
            setNavigationState({ level: 'tool' });
            setIsExpanded(false);
          }}
          className="mt-2 text-xs text-red-600 hover:text-red-800 bg-red-100 px-2 py-1 rounded"
        >
          Reset
        </button>
      </div>
    );
  }

  return (
    <div className={`border border-gray-200 rounded-lg bg-white ${className}`}>
      {/* Collapsed Header - Always visible */}
      <div className="p-3 border-b border-gray-200">
        <button
          onClick={handleExpand}
          className="flex items-center text-sm text-gray-700 hover:text-blue-600 w-full text-left"
        >
          <svg 
            xmlns="http://www.w3.org/2000/svg" 
            fill="none" 
            viewBox="0 0 24 24" 
            strokeWidth={1.5} 
            stroke="currentColor" 
            className={`w-4 h-4 mr-2 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
          >
            <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 8.25l-7.5 7.5-7.5-7.5" />
          </svg>
          Navigate domain path for tool: <strong className="ml-1">{toolName || 'Unknown Tool'}</strong>
        </button>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="p-4">
          {/* Show hierarchical path */}
          {renderHierarchicalPath()}

          {/* Skills Level */}
          {navigationState.level === 'skills' && (
            <div>
              <h4 className="font-medium text-gray-900 mb-3">Skills for {toolName}</h4>
              {skillNames.length === 0 ? (
                <p className="text-sm text-gray-500">No skills found for this tool.</p>
              ) : (
                <div className="space-y-2">
                  {skillNames.map((skillName) => (
                    <div
                      key={skillName}
                      className="p-3 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                      onClick={() => handleSkillClick(skillName)}
                    >
                      <div className="flex items-center justify-between">
                        <div>
                          <h5 className="font-medium text-gray-900">{skillName}</h5>
                        </div>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-gray-400">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Capabilities Level */}
          {navigationState.level === 'capabilities' && (
            <div>
              <div className="flex items-center mb-3">
                <button
                  onClick={handleBackToSkills}
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center mr-4"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 mr-1">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
                  </svg>
                  Back to Skills
                </button>
                <h4 className="font-medium text-gray-900">
                  Capabilities for: {navigationState.selectedSkill}
                </h4>
              </div>
              {capabilities.length === 0 ? (
                <p className="text-sm text-gray-500">No capabilities found for this skill.</p>
              ) : (
                <div className="space-y-2">
                  {capabilities.map((capability) => (
                    <div
                      key={capability.id}
                      className="p-3 border border-gray-200 rounded hover:bg-gray-50 cursor-pointer"
                      onClick={() => handleCapabilityClick(capability)}
                    >
                      <div className="flex items-center justify-between">
                        <h5 className="font-medium text-gray-900">{capability.label}</h5>
                        <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-gray-400">
                          <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                        </svg>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Domains Level */}
          {navigationState.level === 'domains' && (
            <div>
              <div className="flex items-center mb-3">
                <button
                  onClick={handleBackToCapabilities}
                  className="text-sm text-blue-600 hover:text-blue-800 flex items-center mr-4"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 mr-1">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M10.5 19.5L3 12m0 0l7.5-7.5M3 12h18" />
                  </svg>
                  Back to Capabilities
                </button>
                <h4 className="font-medium text-gray-900">
                  Domains for: {navigationState.selectedCapability?.label}
                </h4>
              </div>
              {domains.length === 0 ? (
                <p className="text-sm text-gray-500">No domains found.</p>
              ) : (
                <div className="space-y-2">
                  {domains.map((domain) => (
                    <div
                      key={domain.id}
                      className="p-3 border border-gray-200 rounded bg-gray-50"
                    >
                      <h5 className="font-medium text-gray-900">{domain.label}</h5>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolDomainNavigation;
