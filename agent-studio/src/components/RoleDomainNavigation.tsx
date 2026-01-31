import React, { useState, useEffect } from 'react';
import { 
  getAgentRoles,
  getAgentRoleDomains,
  getAgentRoleDomainCapabilities,
  getAllRoles,
  getDomainsByRole,
  getAllDomains,
  getRolesByDomain,
  RoleInfo,
  DomainInfo,
  CapabilityInfo
} from '@/lib/apiClient';
import { useUserData } from "@/lib/contexts/UserDataContext";

interface BreadcrumbItem {
  type: 'roles' | 'role' | 'domains' | 'domain' | 'capabilities';
  name: string;
  label: string;
}

interface RoleDomainNavigationProps {
  isAdminMode?: boolean;
  agentId?: string;
  tenantName?: string;
}

const RoleDomainNavigation: React.FC<RoleDomainNavigationProps> = ({ isAdminMode = false, agentId, tenantName }) => {
  const { userData } = useUserData();
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [domains, setDomains] = useState<DomainInfo[]>([]);
  const [capabilities, setCapabilities] = useState<CapabilityInfo[]>([]);
  const [breadcrumb, setBreadcrumb] = useState<BreadcrumbItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentView, setCurrentView] = useState<'roles' | 'domains' | 'capabilities'>('roles');
  const [selectedRole, setSelectedRole] = useState<string | null>(null);
  const [selectedDomain, setSelectedDomain] = useState<string | null>(null);
  const [navigationDirection, setNavigationDirection] = useState<'role-to-domain' | 'domain-to-role'>('role-to-domain');

  // Fetch initial data on component mount or when navigation mode changes
  useEffect(() => {
    if (isAdminMode || agentId) {
      if (navigationDirection === 'role-to-domain') {
        fetchRoles();
      } else {
        fetchDomains();
      }
    }
  }, [agentId, isAdminMode, navigationDirection]);

  const fetchRoles = async () => {
    setLoading(true);
    setError(null);
    try {
      let data: RoleInfo[];
      
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      if (isAdminMode) {
        console.log('RoleDomainNavigation: Fetching all roles (admin mode) for tenant:', tenantName);
        data = await getAllRoles(tenantName);
        console.log('RoleDomainNavigation: All roles received:', data);
      } else {
        if (!agentId) return;
        console.log('RoleDomainNavigation: Fetching roles for agent:', agentId, 'in tenant:', tenantName);
        data = await getAgentRoles(tenantName, agentId);
        console.log('RoleDomainNavigation: Agent roles received:', data);
      }
      
      setRoles(data);
      setCurrentView('roles');
      setBreadcrumb([]);
    } catch (err) {
      console.error('RoleDomainNavigation: Error fetching roles:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchDomains = async () => {
    setLoading(true);
    setError(null);
    try {
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      console.log('RoleDomainNavigation: Fetching all domains for tenant:', tenantName);
      const data = await getAllDomains();
      console.log('RoleDomainNavigation: All domains received:', data);
      
      setDomains(data);
      setCurrentView('domains');
      setBreadcrumb([]);
    } catch (err) {
      console.error('RoleDomainNavigation: Error fetching domains:', err);
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchRolesForDomain = async (domainName: string) => {
    setLoading(true);
    setError(null);
    try {
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      console.log('RoleDomainNavigation: Fetching roles for domain:', domainName, 'in tenant:', tenantName);
      const data = await getRolesByDomain(tenantName, domainName);
      console.log('RoleDomainNavigation: Roles for domain received:', data);
      
      setRoles(data);
      setCurrentView('roles');
      setSelectedDomain(domainName);
      
      // Update breadcrumb
      const domain = domains.find(d => d.name === domainName);
      setBreadcrumb([
        { type: 'domain', name: domainName, label: domain?.label || domainName }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchDomainsForRole = async (roleName: string) => {
    setLoading(true);
    setError(null);
    try {
      let data: DomainInfo[];
      
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      if (isAdminMode) {
        console.log('RoleDomainNavigation: Fetching domains for role (admin mode):', roleName, 'in tenant:', tenantName);
        data = await getDomainsByRole(tenantName, roleName);
        console.log('RoleDomainNavigation: Domains for role received:', data);
      } else {
        if (!agentId) return;
        console.log('RoleDomainNavigation: Fetching domains for agent role:', agentId, roleName, 'in tenant:', tenantName);
        data = await getAgentRoleDomains(tenantName, agentId, roleName);
        console.log('RoleDomainNavigation: Agent role domains received:', data);
      }
      
      setDomains(data);
      setCurrentView('domains');
      setSelectedRole(roleName);
      
      // Update breadcrumb
      const role = roles.find(r => r.name === roleName);
      setBreadcrumb([
        { type: 'role', name: roleName, label: role?.label || roleName }
      ]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'An error occurred');
    } finally {
      setLoading(false);
    }
  };

  const fetchCapabilitiesForRoleDomain = async (domainName: string) => {
    if (!agentId || !selectedRole) return;
    
    setLoading(true);
    setError(null);
    try {
      if (!tenantName) {
        setError('No tenant name provided');
        return;
      }
      
      const data = await getAgentRoleDomainCapabilities(tenantName, agentId, selectedRole, domainName);
      setCapabilities(data);
      setCurrentView('capabilities');
      setSelectedDomain(domainName);
      
      // Update breadcrumb
      const domain = domains.find(d => d.name === domainName);
      setBreadcrumb(prev => [
        ...prev,
        { type: 'domain', name: domainName, label: domain?.label || domainName }
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

    if (item.type === 'role') {
      fetchDomainsForRole(item.name);
    } else if (item.type === 'domain') {
      fetchCapabilitiesForRoleDomain(item.name);
    }
  };

  const goBack = () => {
    if (breadcrumb.length === 0) {
      return;
    }
    
    if (currentView === 'domains') {
      if (navigationDirection === 'role-to-domain') {
        fetchRoles();
      } else {
        fetchDomains();
      }
    } else if (currentView === 'roles') {
      if (navigationDirection === 'domain-to-role') {
        fetchDomains();
      }
    } else if (currentView === 'capabilities') {
      if (selectedRole) {
        fetchDomainsForRole(selectedRole);
      }
    }
  };

  const handleNavigationDirectionChange = (direction: 'role-to-domain' | 'domain-to-role') => {
    setNavigationDirection(direction);
    setSelectedRole(null);
    setSelectedDomain(null);
    setBreadcrumb([]);
    
    if (direction === 'role-to-domain') {
      setCurrentView('roles');
    } else {
      setCurrentView('domains');
    }
  };

  const renderBreadcrumb = () => (
    <nav className="flex mb-4" aria-label="Breadcrumb">
      <ol className="inline-flex items-center space-x-1 md:space-x-3">
        <li className="inline-flex items-center">
          <button
            onClick={navigationDirection === 'role-to-domain' ? fetchRoles : fetchDomains}
            className="inline-flex items-center text-sm font-medium text-gray-700 hover:text-blue-600"
          >
            {navigationDirection === 'role-to-domain' ? 'Roles' : 'Domains'}
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

  const renderRoles = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          {navigationDirection === 'domain-to-role' 
            ? `Roles with access to: ${selectedDomain}` 
            : (isAdminMode ? 'All System Roles' : 'Your Roles')
          }
        </h2>
        {breadcrumb.length > 0 && (
          <button
            onClick={goBack}
            className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
          >
            ← Back to Domains
          </button>
        )}
      </div>
      {!Array.isArray(roles) || roles.length === 0 ? (
        <div className="p-4 text-center text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
          {navigationDirection === 'domain-to-role' 
            ? 'No roles have access to this domain.' 
            : (isAdminMode ? 'No roles found in the system.' : 'No roles assigned to this agent.')
          }
        </div>
      ) : (
        roles.map((role) => (
          <div
            key={role.name}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer bg-white shadow-sm"
            onClick={() => {
              if (navigationDirection === 'role-to-domain') {
                fetchDomainsForRole(role.name);
              }
              // In domain-to-role mode, roles are end points, so no further navigation
            }}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{role.label}</h3>
                {role.description && (
                  <p className="text-sm text-gray-700 mt-1">{role.description}</p>
                )}
                <p className="text-xs text-blue-700 mt-1">Role: {role.name}</p>
              </div>
              {navigationDirection === 'role-to-domain' && (
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
                </svg>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderDomains = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          {navigationDirection === 'role-to-domain' 
            ? `Domains for Role: ${selectedRole}` 
            : 'All Domains'
          }
        </h2>
        {breadcrumb.length > 0 && (
          <button
            onClick={goBack}
            className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
          >
            ← Back to {navigationDirection === 'role-to-domain' ? 'Roles' : 'Domains'}
          </button>
        )}
      </div>
      {!Array.isArray(domains) || domains.length === 0 ? (
        <div className="p-4 text-center text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
          {navigationDirection === 'role-to-domain' 
            ? 'No domains available for this role.' 
            : 'No domains found in the system.'
          }
        </div>
      ) : (
        domains.map((domain) => (
          <div
            key={domain.id}
            className="p-4 border border-gray-200 rounded-lg hover:bg-gray-50 cursor-pointer bg-white shadow-sm"
            onClick={() => {
              if (navigationDirection === 'role-to-domain') {
                fetchCapabilitiesForRoleDomain(domain.name);
              } else {
                fetchRolesForDomain(domain.name);
              }
            }}
          >
            <div className="flex items-center justify-between">
              <div>
                <h3 className="font-medium text-gray-900">{domain.label}</h3>
                {domain.description && (
                  <p className="text-sm text-gray-700 mt-1">{domain.description}</p>
                )}
                <p className="text-xs text-green-700 mt-1">Domain: {domain.name}</p>
              </div>
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5 text-gray-400">
                <path strokeLinecap="round" strokeLinejoin="round" d="M8.25 4.5l7.5 7.5-7.5 7.5" />
              </svg>
            </div>
          </div>
        ))
      )}
    </div>
  );

  const renderCapabilities = () => (
    <div className="space-y-2">
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold text-gray-900">
          Capabilities for {selectedRole} → {selectedDomain}
        </h2>
        <button
          onClick={goBack}
          className="text-sm text-blue-600 hover:text-blue-800 bg-blue-50 px-3 py-1 rounded"
        >
          ← Back to Domains
        </button>
      </div>
      {!Array.isArray(capabilities) || capabilities.length === 0 ? (
        <div className="p-4 text-center text-gray-500 bg-gray-50 rounded-lg border border-gray-200">
          No capabilities available for this role-domain combination.
        </div>
      ) : (
        capabilities.map((capability) => (
          <div
            key={capability.id}
            className="p-4 border border-gray-200 rounded-lg bg-white shadow-sm"
          >
            <div>
              <h3 className="font-medium text-gray-900">{capability.label}</h3>
              {capability.description && (
                <p className="text-sm text-gray-700 mt-1">{capability.description}</p>
              )}
              {capability.outcome && (
                <p className="text-xs text-purple-700 mt-1">Outcome: {capability.outcome}</p>
              )}
              <p className="text-xs text-orange-700 mt-1">Capability: {capability.name}</p>
            </div>
          </div>
        ))
      )}
    </div>
  );

  if (!isAdminMode && !agentId) {
    return (
      <div className="p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
        <p className="text-yellow-800">No active agent found. Please select a working agent.</p>
      </div>
    );
  }

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
          onClick={fetchRoles}
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
        {/* Navigation Direction Toggle */}
        <div className="mb-6">
          <div className="flex space-x-1 bg-gray-100 p-1 rounded-lg w-fit">
            <button
              onClick={() => handleNavigationDirectionChange('role-to-domain')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                navigationDirection === 'role-to-domain'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Role → Domain
            </button>
            <button
              onClick={() => handleNavigationDirectionChange('domain-to-role')}
              className={`px-4 py-2 text-sm font-medium rounded-md transition-colors ${
                navigationDirection === 'domain-to-role'
                  ? 'bg-white text-blue-600 shadow-sm'
                  : 'text-gray-600 hover:text-gray-900'
              }`}
            >
              Domain → Role
            </button>
          </div>
          <p className="text-sm text-gray-500 mt-2">
            {navigationDirection === 'role-to-domain' 
              ? 'Start with roles and navigate to their associated domains.'
              : 'Start with domains and see which roles have access to them.'
            }
          </p>
        </div>

        {renderBreadcrumb()}
        
        {currentView === 'roles' && renderRoles()}
        {currentView === 'domains' && renderDomains()}
        {currentView === 'capabilities' && renderCapabilities()}
      </div>
    </div>
  );
};

export default RoleDomainNavigation;
