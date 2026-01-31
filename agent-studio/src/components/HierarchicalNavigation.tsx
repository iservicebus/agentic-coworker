import React, { useState, useEffect } from 'react';
import { 
  getAllDomains, 
  getCapabilitiesByDomain, 
  getSkillsByCapability, 
  getMcpToolsBySkill,
  DomainInfo,
  CapabilityInfo,
  SkillInfo,
  McpToolInfo
} from '@/lib/apiClient';
import { getTenantFromCookie } from '@/lib/tenantUtils';

// In the new model, categories → domains, operations → skills.
// We keep internal type names for stability but update UI text to reflect
// domain → capability → skill → tool.

interface BreadcrumbItem {
  type: 'domain' | 'capability' | 'skill' | 'tool';
  name: string;
  label: string;
}

const HierarchicalNavigation: React.FC = () => {
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityInfo[]>([]);
  const [skills, setSkills] = useState<SkillInfo[]>([]);
  const [tools, setTools] = useState<McpToolInfo[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<'domains' | 'capabilities' | 'skills' | 'tools'>('domains');
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [selectedCapability, setSelectedCapability] = useState<string | null>(null);
  const [selectedSkill, setSelectedSkill] = useState<string | null>(null);

  // Fetch domains on component mount
  useEffect(() => {
    fetchDomains();
  }, []);

  const fetchDomains = async () => {
    setLoading(true);
    setError(null);
    try {
     
      console.log('HierarchicalNavigation: Fetching domains...');
      const data = await getAllDomains();
      console.log('HierarchicalNavigation: Domains received:', data);
      setDomains(data);
      setCurrentView('domains');
      setBreadcrumb([]);
    } catch (err) {
      console.error('HierarchicalNavigation: Error fetching domains:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchCapabilities = async (domainName: string) => {
    setLoading(true);
    setError(null);
    try {
      const tenantName = getTenantFromCookie();
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      const data = await getCapabilitiesByDomain(tenantName, domainName);
      setCapabilities(data);
      setCurrentView('capabilities');
      setSelectedDomain(domainName);
      
      // Update breadcrumb
      const domain = domains.find(c => c.name === domainName);
      setBreadcrumb([
        { type: 'domain', name: domainName, label: domain?.label || domainName }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchSkills = async (capabilityName: string) => {
    setLoading(true);
    setError(null);
    try {
      const tenantName = getTenantFromCookie();
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      const data = await getSkillsByCapability(tenantName, capabilityName);
      setSkills(data);
      setCurrentView('skills');
      setSelectedCapability(capabilityName);
      
      // Update breadcrumb
      const capability = capabilities.find(c => c.name === capabilityName);
      setBreadcrumb(prev => [
        ...prev,
        { type: 'capability', name: capabilityName, label: capability?.label || capabilityName }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchTools = async (skillName: string) => {
    setLoading(true);
    setError(null);
    try {
      const tenantName = getTenantFromCookie();
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      const data = await getMcpToolsBySkill(tenantName, skillName);
      setTools(data);
      setCurrentView('tools');
      setSelectedSkill(skillName);
      
      // Update breadcrumb
      setBreadcrumb(prev => [
        ...prev,
        { type: 'skill', name: skillName, label: skillName }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const navigateToBreadcrumb = (index: number) => {
    const item = breadcrumb[index];
    const newBreadcrumb = breadcrumb.slice(0, index + 1);
    setBreadcrumb(newBreadcrumb);

    if (item.type === 'domain') {
      fetchCapabilities(item.name);
    } else if (item.type === 'capability') {
      fetchSkills(item.name);
    } else if (item.type === 'skill') {
      fetchTools(item.name);
    }
  };

  const goBack = () => {
    if (breadcrumb.length === 0) {
      return;
    }
    
    if (currentView === 'capabilities') {
      fetchDomains();
    } else if (currentView === 'skills') {
      fetchCapabilities(selectedDomain!);
    } else if (currentView === 'tools') {
      fetchSkills(selectedCapability!);
    }
  };

  const renderBreadcrumb = () => (
    <nav className="flex mb-4" aria-label="Breadcrumb">
      <ol className="inline-flex items-center space-x-1 md:space-x-3">
        <li className="inline-flex items-center">
          <button
            onClick={fetchDomains}
            className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-blue-600"
          >
            Domains
          </button>
        </li>
        {breadcrumb.map((item, index) => (
          <li key={`${item.type}-${item.name}`}>
            <div className="flex items-center">
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
              <button
                onClick={() => navigateToBreadcrumb(index)}
                className="ml-1 text-sm font-medium text-gray-700 hover:text-blue-600 md:ml-2"
              >
                {item.label}
              </button>
            </div>
          </li>
        ))}
      </ol>
    </nav>
  );

  const renderDomains = () => (
    <div className="space-y-2">
      <h2 className="text-xl font-semibold mb-4 text-gray-900">Domains</h2>
      {domains.map((domain) => (
        <div
          key={domain.id}
          className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer bg-white shadow-sm"
          onClick={() => fetchCapabilities(domain.name)}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">{domain.label}</h3>
              {domain.description && (
                <p className="text-sm text-gray-700 mt-1">{domain.description}</p>
              )}
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  );

  const renderCapabilities = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Capabilities</h2>
        <button
          onClick={goBack}
          className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
        >
          ← Back to Domains
        </button>
      </div>
      {capabilities.map((capability) => (
        <div
          key={capability.id}
          className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer bg-white shadow-sm"
          onClick={() => fetchSkills(capability.name)}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">{capability.label}</h3>
              {capability.description && (
                <p className="text-sm text-gray-700 mt-1">{capability.description}</p>
              )}
              {(capability as any).intent && (
                <p className="text-xs text-blue-700 mt-1">Intent: {(capability as any).intent}</p>
              )}
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  );

  const renderSkills = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">Skills</h2>
        <button
          onClick={goBack}
          className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
        >
          ← Back to Capabilities
        </button>
      </div>
      {skills.map((skill) => (
        <div
          key={skill.name}
          className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer bg-white shadow-sm"
          onClick={() => fetchTools(skill.name)}
        >
          <div className="flex items-center justify-between">
            <div>
              <h3 className="font-medium text-gray-900">{skill.name}</h3>
              {skill.description && (
                <p className="text-sm text-gray-700 mt-1">{skill.description}</p>
              )}
            </div>
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
              <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
            </svg>
          </div>
        </div>
      ))}
    </div>
  );

  const renderTools = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">MCP Tools</h2>
        <button
          onClick={goBack}
          className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
        >
          ← Back to Skills
        </button>
      </div>
      {tools.length === 0 ? (
        <div className="p-4 text-center text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
          No tools found for this skill.
        </div>
      ) : (
        tools.map((tool) => (
          <div
            key={tool.id}
            className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm"
          >
            <div>
              <h3 className="font-medium text-gray-900">{tool.name}</h3>
              {tool.description && (
                <p className="text-sm text-gray-700 mt-1">{tool.description}</p>
              )}
              <div className="flex space-x-4 mt-2 text-xs text-gray-600">
                <span>Agent: {tool.agent_id}</span>
                <span>Tenant: {tool.tenant}</span>
              </div>
            </div>
          </div>
        ))
      )}
    </div>
  );

  if (loading) {
    return (
      <div className="flex items-center justify-center p-8 bg-white rounded-lg">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
        <span className="ml-3 text-gray-700">Loading...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 bg-red-50 border border-red-200 rounded-lg">
        <p className="text-red-800">Error: {error}</p>
        <button
          onClick={fetchDomains}
          className="mt-2 text-sm text-red-600 hover:text-red-800 bg-red-100 px-3 py-1 rounded"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="bg-white min-h-screen">
      <div className="bg-white p-6 rounded-lg shadow-sm">
        {renderBreadcrumb()}
        
        {currentView === 'domains' && renderDomains()}
        {currentView === 'capabilities' && renderCapabilities()}
        {currentView === 'skills' && renderSkills()}
        {currentView === 'tools' && renderTools()}
      </div>
    </div>
  );
};

export default HierarchicalNavigation;
