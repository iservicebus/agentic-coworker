'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { 
  getAllAgents, 
  getAgentsByUsername, 
  getAllRoles, 
  getAllUsers,
  updateAgentRoles, 
  createAgentByUser, 
  deleteAgentByUser, 
  getUsersForAgent,
  upsertUserAgentRelationship,
  removeUserFromAgent,
  AgentInfo, 
  RoleInfo, 
  CreateAgentPayload,
  UserInfo,
  UserAgentRelationship 
} from '@/lib/apiClient';
import Layout from '@/components/Layout';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';

const AgentsPage: React.FC = () => {
  const searchParams = useSearchParams();
  const mode = searchParams.get('mode') || 'user'; // 'user' or 'admin'
  
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const [tenantId, setTenantId] = useState<string | null>(null);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantId(tenant);
  }, []);

  const [agents, setAgents] = useState<AgentInfo[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [selectedAgent, setSelectedAgent] = useState<string | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Create Agent Dialog State
  const [showCreateDialog, setShowCreateDialog] = useState<boolean>(false);
  const [createAgentData, setCreateAgentData] = useState<CreateAgentPayload>({
    agent_id: '',
    email: '',
    password: '',
    tenant_name: tenantId || '',
    name: '',
  });
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  // View Users Dialog State
  const [showUsersDialog, setShowUsersDialog] = useState<boolean>(false);
  const [selectedAgentForUsers, setSelectedAgentForUsers] = useState<string | null>(null);
  const [agentUsers, setAgentUsers] = useState<UserAgentRelationship[]>([]);
  const [allUsers, setAllUsers] = useState<UserInfo[]>([]);
  const [isLoadingUsers, setIsLoadingUsers] = useState<boolean>(false);
  const [usersError, setUsersError] = useState<string | null>(null);
  const [newUserUsername, setNewUserUsername] = useState<string>('');
  const [newUserRole, setNewUserRole] = useState<string>('member');

  const fetchAgents = useCallback(async () => {
    if (!userData?.username || !tenantId) return;
    
    setIsLoading(true);
    setError(null);
    try {
      // Check user type - only human users can manage agents
      if (userData.user_type === 'agent') {
        setError('You are logged in as an agent. Please login as a human user to manage agents.');
        setAgents([]);
        return;
      }
      
      let fetchedAgents: AgentInfo[];
      
      if (mode === 'admin') {
        // Admin mode: fetch all agents in the system
        fetchedAgents = await getAllAgents(tenantId);
      } else {
        // User mode: fetch agents by username (user's own agents)
        fetchedAgents = await getAgentsByUsername(tenantId, userData.username);
      }
      
      setAgents(fetchedAgents || []);
    } catch (err) {
      console.error("Failed to fetch agents:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch agents.');
      setAgents([]);
    } finally {
      setIsLoading(false);
    }
  }, [userData?.username, userData?.user_type, mode, tenantId]);

  const fetchRoles = useCallback(async () => {
    if (!tenantId) return;
    
    try {
      const fetchedRoles = await getAllRoles(tenantId);
      setRoles(fetchedRoles || []);
    } catch (err) {
      console.error("Failed to fetch roles:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch roles.');
      setRoles([]);
    }
  }, [tenantId]);

  useEffect(() => {
    fetchAgents();
    fetchRoles();
  }, [fetchAgents, fetchRoles, tenantId]);

  // Update tenant_name when tenantId changes
  useEffect(() => {
    if (tenantId) {
      setCreateAgentData(prev => ({ ...prev, tenant_name: tenantId }));
    }
  }, [tenantId]);

  const handleAgentSelect = (agentId: string) => {
    if (selectedAgent === agentId) {
      setSelectedAgent(null);
      setSelectedRoles([]);
    } else {
      setSelectedAgent(agentId);
      // Pre-populate with current roles
      const agent = agents.find(a => a.agent_id === agentId);
      setSelectedRoles(agent?.roles || []);
      setError(null);
      setSuccessMessage(null);
    }
  };

  const handleRoleToggle = (roleName: string) => {
    setSelectedRoles(prev => 
      prev.includes(roleName) 
        ? prev.filter(r => r !== roleName)
        : [...prev, roleName]
    );
  };

  const handleUpdateRoles = async () => {
    if (!selectedAgent || !tenantId) return;

    setIsUpdating(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await updateAgentRoles(tenantId, selectedAgent, selectedRoles);
      setSuccessMessage(`Roles updated successfully for agent ${selectedAgent}`);
      setSelectedAgent(null);
      setSelectedRoles([]);
      // Refresh the agents list to show updated roles
      await fetchAgents();
    } catch (err) {
      console.error("Failed to update agent roles:", err);
      setError(err instanceof Error ? err.message : 'Failed to update agent roles.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCreateAgent = async () => {
    if (!userData?.username || !tenantId) return;

    // Validation
    if (!createAgentData.agent_id || !createAgentData.password) {
      setCreateError('Agent ID and Password are required');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const response = await createAgentByUser(tenantId, userData.username, createAgentData);
      setSuccessMessage(response.message);
      setShowCreateDialog(false);
      // Reset form
      setCreateAgentData({
        agent_id: '',
        email: '',
        password: '',
        tenant_name: tenantId || '',
        name: '',
      });
      // Refresh agents list
      await fetchAgents();
    } catch (err) {
      console.error("Failed to create agent:", err);
      setCreateError(err instanceof Error ? err.message : 'Failed to create agent.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!userData?.username || !tenantId) return;
    
    if (!confirm(`Are you sure you want to delete agent "${agentId}"? This action cannot be undone.`)) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await deleteAgentByUser(tenantId, userData.username, agentId);
      setSuccessMessage(`Agent "${agentId}" deleted successfully`);
      // Refresh agents list
      await fetchAgents();
    } catch (err) {
      console.error("Failed to delete agent:", err);
      setError(err instanceof Error ? err.message : 'Failed to delete agent.');
    } finally {
      setIsLoading(false);
    }
  };

  // User Management Handler Functions
  const handleViewUsers = async (agentId: string) => {
    if (!tenantId) return;
    
    setSelectedAgentForUsers(agentId);
    setShowUsersDialog(true);
    setIsLoadingUsers(true);
    setUsersError(null);
    setNewUserUsername('');
    setNewUserRole('member');

    try {
      // Fetch users for this agent
      const users = await getUsersForAgent(agentId);
      setAgentUsers(users);

      // Fetch all users in the system for the dropdown
      const allUsersData = await getAllUsers(tenantId);
      setAllUsers(allUsersData);
    } catch (err) {
      console.error("Failed to fetch users for agent:", err);
      setUsersError(err instanceof Error ? err.message : 'Failed to fetch users.');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const handleAddUser = async () => {
    if (!selectedAgentForUsers || !newUserUsername) return;

    setIsLoadingUsers(true);
    setUsersError(null);

    try {
      await upsertUserAgentRelationship(selectedAgentForUsers, {
        username: newUserUsername,
        role: newUserRole,
        context: null,
      });

      // Refresh the users list
      const users = await getUsersForAgent(selectedAgentForUsers);
      setAgentUsers(users);

      // Reset form
      setNewUserUsername('');
      setNewUserRole('member');
      setSuccessMessage(`User "${newUserUsername}" added to agent successfully`);
    } catch (err) {
      console.error("Failed to add user to agent:", err);
      setUsersError(err instanceof Error ? err.message : 'Failed to add user.');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const handleRemoveUser = async (username: string) => {
    if (!selectedAgentForUsers) return;

    if (!confirm(`Are you sure you want to remove user "${username}" from this agent?`)) {
      return;
    }

    setIsLoadingUsers(true);
    setUsersError(null);

    try {
      await removeUserFromAgent(selectedAgentForUsers, username);

      // Refresh the users list
      const users = await getUsersForAgent(selectedAgentForUsers);
      setAgentUsers(users);

      setSuccessMessage(`User "${username}" removed from agent successfully`);
    } catch (err) {
      console.error("Failed to remove user from agent:", err);
      setUsersError(err instanceof Error ? err.message : 'Failed to remove user.');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  const handleUpdateUserRole = async (username: string, newRole: string) => {
    if (!selectedAgentForUsers) return;

    setIsLoadingUsers(true);
    setUsersError(null);

    try {
      await upsertUserAgentRelationship(selectedAgentForUsers, {
        username: username,
        role: newRole,
        context: null,
      });

      // Refresh the users list
      const users = await getUsersForAgent(selectedAgentForUsers);
      setAgentUsers(users);

      setSuccessMessage(`Role updated for user "${username}" successfully`);
    } catch (err) {
      console.error("Failed to update user role:", err);
      setUsersError(err instanceof Error ? err.message : 'Failed to update user role.');
    } finally {
      setIsLoadingUsers(false);
    }
  };

  if (isUserLoading) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-100 p-4 sm:p-6 md:p-8">
          <div className="max-w-6xl mx-auto bg-white shadow-xl rounded-lg p-6 sm:p-8 md:p-10">
            <p>Loading user data...</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (userError) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-100 p-4 sm:p-6 md:p-8">
          <div className="max-w-6xl mx-auto bg-white shadow-xl rounded-lg p-6 sm:p-8 md:p-10">
            <p className="text-red-600">Error loading user data: {userError}</p>
          </div>
        </div>
      </Layout>
    );
  }

  if (!tenantId) {
    return (
      <Layout>
        <div className="min-h-screen bg-gray-100 p-4 sm:p-6 md:p-8">
          <div className="max-w-6xl mx-auto bg-white shadow-xl rounded-lg p-6 sm:p-8 md:p-10">
            <p>Tenant not selected.</p>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-100 p-4 sm:p-6 md:p-8">
        <div className="max-w-6xl mx-auto bg-white shadow-xl rounded-lg p-6 sm:p-8 md:p-10">
          <header className="mb-8">
            <div className="flex justify-between items-center mb-3">
              <h1 className="text-4xl font-bold text-gray-800">
                {mode === 'admin' ? 'Agent Administration' : 'Agent Access Management'}
              </h1>
              {mode === 'user' && (
                <button
                  onClick={() => setShowCreateDialog(true)}
                  className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors font-semibold"
                >
                  + Create Agent
                </button>
              )}
            </div>
            <p className="text-lg text-gray-600">
              {mode === 'admin' 
                ? `View and manage all agents across all users in the system`
                : `Manage agent permissions and role assignments for tenant: ${tenantId}`
              }
            </p>
          </header>

          {/* Display general page errors or success messages */}
          {error && !selectedAgent && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">Error: {error}</p>
            </div>
          )}
          {successMessage && !selectedAgent && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-600">{successMessage}</p>
            </div>
          )}

          {/* Create Agent Dialog */}
          {showCreateDialog && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Create New Agent</h2>
                
                {createError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-600 text-sm">{createError}</p>
                  </div>
                )}

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Agent ID <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={createAgentData.agent_id}
                      onChange={(e) => setCreateAgentData({ ...createAgentData, agent_id: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="e.g., agent-dev-001"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Display Name
                    </label>
                    <input
                      type="text"
                      value={createAgentData.name || ''}
                      onChange={(e) => setCreateAgentData({ ...createAgentData, name: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="e.g., Development Agent"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={createAgentData.email || ''}
                      onChange={(e) => setCreateAgentData({ ...createAgentData, email: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="agent@example.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={createAgentData.password}
                      onChange={(e) => setCreateAgentData({ ...createAgentData, password: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="Enter password"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Tenant
                    </label>
                    <input
                      type="text"
                      value={createAgentData.tenant_name || ''}
                      disabled
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-200 text-gray-700 cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">Defaults to your active tenant</p>
                  </div>
                </div>

                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={handleCreateAgent}
                    disabled={isCreating}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isCreating ? 'Creating...' : 'Create Agent'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateDialog(false);
                      setCreateError(null);
                      setCreateAgentData({
                        agent_id: '',
                        email: '',
                        password: '',
                        tenant_name: tenantId || '',
                        name: '',
                      });
                    }}
                    disabled={isCreating}
                    className="flex-1 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 transition-colors"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Agents List - Full Width Rows */}
          <div className="bg-gray-50 rounded-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4 border-b pb-2">
              Agents ({agents.length})
            </h2>
            
            {isLoading && agents.length === 0 && <p>Loading agents...</p>}
            {agents.length === 0 && !isLoading && <p>No agents found.</p>}
            
            <div className="space-y-3">
              {agents.map((agent) => (
                <div key={agent.agent_id} className="w-full">
                  <div
                    className={`flex flex-col sm:flex-row items-start sm:items-center justify-between w-full p-4 rounded-lg border transition-colors ${
                      selectedAgent === agent.agent_id
                        ? 'bg-indigo-50 border-indigo-300'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800">
                        {agent.name || agent.agent_id}
                      </h3>
                      <p className="text-sm text-gray-600">ID: {agent.agent_id}</p>
                      {agent.active_tenant_name && (
                        <p className="text-sm text-gray-500">
                          Active Tenant: {agent.active_tenant_name}
                        </p>
                      )}
                      {/* Display current roles */}
                      {agent.roles && agent.roles.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 mb-1">Current Roles:</p>
                          <div className="flex flex-wrap gap-1">
                            {agent.roles.map((role) => (
                              <span
                                key={role}
                                className="inline-block px-2 py-1 text-xs bg-blue-100 text-blue-800 rounded-full"
                              >
                                {role}
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                      {(!agent.roles || agent.roles.length === 0) && (
                        <p className="text-xs text-gray-400 mt-2">No roles assigned</p>
                      )}
                    </div>
                    <div className="mt-3 sm:mt-0 flex gap-2 flex-wrap">
                      <button
                        onClick={() => handleAgentSelect(agent.agent_id)}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                      >
                        Role Change
                      </button>
                      <button
                        onClick={() => handleViewUsers(agent.agent_id)}
                        className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 transition-colors"
                      >
                        View Users
                      </button>
                      {mode === 'admin' && (
                        <button
                          onClick={() => handleDeleteAgent(agent.agent_id)}
                          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                          Delete
                        </button>
                      )}
                      {mode === 'user' && agent.role === 'owner' && (
                        <button
                          onClick={() => handleDeleteAgent(agent.agent_id)}
                          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                  {/* Inline Role Management UI */}
                  {selectedAgent === agent.agent_id && (
                    <div className="mt-2 mb-4 p-4 bg-indigo-50 rounded-md border border-indigo-200">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-sm text-indigo-700">
                          Managing roles for agent: <strong>{agent.agent_id}</strong>
                        </p>
                        <button
                          onClick={() => {
                            setSelectedAgent(null);
                            setSelectedRoles([]);
                            setError(null);
                            setSuccessMessage(null);
                          }}
                          className="px-2 py-1 text-xs bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
                        >
                          Close
                        </button>
                      </div>
                      {/* Display specific errors/success for the current editing session */}
                      {error && selectedAgent && (
                        <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded-md">
                          <p className="text-red-600">Error: {error}</p>
                        </div>
                      )}
                      {successMessage && selectedAgent && (
                        <div className="mb-2 p-2 bg-green-50 border border-green-200 rounded-md">
                          <p className="text-green-600">{successMessage}</p>
                        </div>
                      )}
                      <div className="space-y-2 mb-4">
                        <h3 className="font-medium text-gray-700">Available Roles:</h3>
                        {roles.map((role) => (
                          <label
                            key={role.name}
                            className="flex items-start space-x-3 p-2 bg-white rounded-md border hover:bg-gray-50 cursor-pointer"
                          >
                            <input
                              type="checkbox"
                              checked={selectedRoles.includes(role.name)}
                              onChange={() => handleRoleToggle(role.name)}
                              className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500 border-gray-300 rounded"
                            />
                            <div>
                              <div className="font-medium text-gray-800">{role.label}</div>
                              <div className="text-sm text-gray-600">{role.name}</div>
                              {role.description && (
                                <div className="text-sm text-gray-500 mt-1">{role.description}</div>
                              )}
                            </div>
                          </label>
                        ))}
                      </div>
                      <div className="flex space-x-3">
                        <button
                          onClick={async () => {
                            await handleUpdateRoles();
                            // Hide role management UI after update
                            setSelectedAgent(null);
                            setSelectedRoles([]);
                            setError(null);
                            setSuccessMessage(null);
                          }}
                          disabled={isUpdating}
                          className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 disabled:opacity-50 transition-colors"
                        >
                          {isUpdating ? 'Updating...' : 'Update Roles'}
                        </button>
                        <button
                          onClick={() => {
                            setSelectedAgent(null);
                            setSelectedRoles([]);
                            setError(null);
                            setSuccessMessage(null);
                          }}
                          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 transition-colors"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              ))}
            </div>
            <button
              onClick={fetchAgents}
              disabled={isLoading}
              className="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Refreshing...' : 'Refresh Agents'}
            </button>
          </div>

          {/* View Users Dialog */}
          {showUsersDialog && selectedAgentForUsers && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                  <h2 className="text-2xl font-bold text-gray-800">
                    Manage Users for Agent: {selectedAgentForUsers}
                  </h2>
                  <button
                    onClick={() => {
                      setShowUsersDialog(false);
                      setSelectedAgentForUsers(null);
                      setAgentUsers([]);
                      setAllUsers([]);
                      setUsersError(null);
                    }}
                    className="px-3 py-1 text-gray-600 hover:text-gray-800"
                  >
                    ✕
                  </button>
                </div>

                {usersError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-600 text-sm">{usersError}</p>
                  </div>
                )}

                {/* Current Users List */}
                <div className="mb-6">
                  <h3 className="text-lg font-semibold text-gray-700 mb-3">
                    Current Users ({agentUsers.length})
                  </h3>
                  {isLoadingUsers && agentUsers.length === 0 ? (
                    <p className="text-gray-500">Loading users...</p>
                  ) : agentUsers.length === 0 ? (
                    <p className="text-gray-500">No users associated with this agent.</p>
                  ) : (
                    <div className="space-y-2">
                      {agentUsers.map((userRel) => (
                        <div
                          key={userRel.username}
                          className="flex items-center justify-between p-3 bg-gray-50 rounded-md border"
                        >
                          <div className="flex-1">
                            <p className="font-medium text-gray-800">{userRel.username}</p>
                            <p className="text-sm text-gray-600">
                              Role: <span className="font-semibold">{userRel.role || 'N/A'}</span>
                            </p>
                          </div>
                          <div className="flex gap-2">
                            <select
                              value={userRel.role || 'member'}
                              onChange={(e) => handleUpdateUserRole(userRel.username, e.target.value)}
                              disabled={isLoadingUsers}
                              className="px-3 py-1 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                            >
                              <option value="owner">Owner</option>
                              <option value="member">Member</option>
                              <option value="viewer">Viewer</option>
                            </select>
                            <button
                              onClick={() => handleRemoveUser(userRel.username)}
                              disabled={isLoadingUsers}
                              className="px-3 py-1 bg-red-600 text-white rounded-md hover:bg-red-700 disabled:opacity-50 text-sm"
                            >
                              Remove
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>

                {/* Add New User Form */}
                <div className="border-t pt-4">
                  <h3 className="text-lg font-semibold text-gray-700 mb-3">Add New User</h3>
                  <div className="flex gap-3">
                    <select
                      value={newUserUsername}
                      onChange={(e) => setNewUserUsername(e.target.value)}
                      disabled={isLoadingUsers}
                      className="flex-1 px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">Select a user...</option>
                      {allUsers
                        .filter(u => !agentUsers.some(au => au.username === u.username))
                        .map((user) => (
                          <option key={user.username} value={user.username}>
                            {user.username} {user.email ? `(${user.email})` : ''}
                          </option>
                        ))}
                    </select>
                    <select
                      value={newUserRole}
                      onChange={(e) => setNewUserRole(e.target.value)}
                      disabled={isLoadingUsers}
                      className="px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="owner">Owner</option>
                      <option value="member">Member</option>
                      <option value="viewer">Viewer</option>
                    </select>
                    <button
                      onClick={handleAddUser}
                      disabled={isLoadingUsers || !newUserUsername}
                      className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700 disabled:opacity-50"
                    >
                      Add
                    </button>
                  </div>
                </div>

                <div className="mt-6 flex justify-end">
                  <button
                    onClick={() => {
                      setShowUsersDialog(false);
                      setSelectedAgentForUsers(null);
                      setAgentUsers([]);
                      setAllUsers([]);
                      setUsersError(null);
                    }}
                    className="px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300"
                  >
                    Close
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* Available Roles Summary */}
          <div className="mt-8 bg-gray-50 rounded-lg p-6">
            <h2 className="text-xl font-semibold text-gray-700 mb-4">
              Available Roles Summary ({roles.length})
            </h2>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {roles.map((role) => (
                <div key={role.name} className="bg-white p-4 rounded-md border">
                  <h3 className="font-medium text-gray-800">{role.label}</h3>
                  <p className="text-sm text-gray-600 mt-1">{role.name}</p>
                  {role.description && (
                    <p className="text-sm text-gray-500 mt-2">{role.description}</p>
                  )}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </Layout>
  );
};

export default AgentsPage;
