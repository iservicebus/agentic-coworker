'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getAllUsers, getAllRoles, updateUserRoles, createUser, deleteUser, UserInfo, RoleInfo, CreateUserPayload } from '@/lib/apiClient';
import Layout from '@/components/Layout';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';

const UsersPage: React.FC = () => {
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const [tenantId, setTenantId] = useState<string | null>(null);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantId(tenant);
  }, []);

  const [users, setUsers] = useState<UserInfo[]>([]);
  const [roles, setRoles] = useState<RoleInfo[]>([]);
  const [selectedUser, setSelectedUser] = useState<string | null>(null);
  const [selectedRoles, setSelectedRoles] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isUpdating, setIsUpdating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Create User Dialog State
  const [showCreateDialog, setShowCreateDialog] = useState<boolean>(false);
  const [createUserData, setCreateUserData] = useState<CreateUserPayload>({
    username: '',
    email: '',
    password: '',
    tenant_name: tenantId || '',
  });
  const [isCreating, setIsCreating] = useState<boolean>(false);
  const [createError, setCreateError] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    if (!tenantId) return;
    
    setIsLoading(true);
    setError(null);
    try {
      const fetchedUsers = await getAllUsers(tenantId);
      setUsers(fetchedUsers || []);
    } catch (err) {
      console.error("Failed to fetch users:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch users.');
      setUsers([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantId]);

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
    fetchUsers();
    fetchRoles();
  }, [fetchUsers, fetchRoles]);

  // Update tenant_name when tenantId changes
  useEffect(() => {
    if (tenantId) {
      setCreateUserData(prev => ({ ...prev, tenant_name: tenantId }));
    }
  }, [tenantId]);

  const handleUserSelect = (username: string) => {
    if (selectedUser === username) {
      setSelectedUser(null);
      setSelectedRoles([]);
    } else {
      setSelectedUser(username);
      // Pre-populate with current roles
      const user = users.find(u => u.username === username);
      setSelectedRoles(user?.roles || []);
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
    if (!selectedUser || !tenantId) return;

    setIsUpdating(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await updateUserRoles(tenantId, selectedUser, selectedRoles);
      setSuccessMessage(`Roles updated successfully for user ${selectedUser}`);
      setSelectedUser(null);
      setSelectedRoles([]);
      // Refresh the users list to show updated roles
      await fetchUsers();
    } catch (err) {
      console.error("Failed to update user roles:", err);
      setError(err instanceof Error ? err.message : 'Failed to update user roles.');
    } finally {
      setIsUpdating(false);
    }
  };

  const handleCreateUser = async () => {
    if (!tenantId) return;
    
    // Validation
    if (!createUserData.username || !createUserData.password) {
      setCreateError('Username and Password are required');
      return;
    }

    setIsCreating(true);
    setCreateError(null);

    try {
      const response = await createUser(tenantId, createUserData);
      setSuccessMessage(response.message);
      setShowCreateDialog(false);
      // Reset form
      setCreateUserData({
        username: '',
        email: '',
        password: '',
        tenant_name: tenantId || '',
      });
      // Refresh users list
      await fetchUsers();
    } catch (err) {
      console.error("Failed to create user:", err);
      setCreateError(err instanceof Error ? err.message : 'Failed to create user.');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteUser = async (username: string) => {
    if (!tenantId) return;
    
    if (!confirm(`Are you sure you want to delete user "${username}"? This action cannot be undone.`)) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setSuccessMessage(null);

    try {
      await deleteUser(tenantId, username);
      setSuccessMessage(`User "${username}" deleted successfully`);
      // Refresh users list
      await fetchUsers();
    } catch (err) {
      console.error("Failed to delete user:", err);
      setError(err instanceof Error ? err.message : 'Failed to delete user.');
    } finally {
      setIsLoading(false);
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
                User Access Management
              </h1>
              <button
                onClick={() => setShowCreateDialog(true)}
                className="px-6 py-3 bg-green-600 text-white rounded-md hover:bg-green-700 transition-colors font-semibold"
              >
                + Create User
              </button>
            </div>
            <p className="text-lg text-gray-600">
              Manage user permissions and role assignments for tenant: {tenantId}
            </p>
          </header>

          {/* Display general page errors or success messages */}
          {error && !selectedUser && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">Error: {error}</p>
            </div>
          )}
          {successMessage && !selectedUser && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-600">{successMessage}</p>
            </div>
          )}

          {/* Create User Dialog */}
          {showCreateDialog && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white rounded-lg p-6 max-w-md w-full mx-4">
                <h2 className="text-2xl font-bold text-gray-800 mb-4">Create New User</h2>
                
                {createError && (
                  <div className="mb-4 p-3 bg-red-50 border border-red-200 rounded-md">
                    <p className="text-red-600 text-sm">{createError}</p>
                  </div>
                )}

                <div className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Username <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      value={createUserData.username}
                      onChange={(e) => setCreateUserData({ ...createUserData, username: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="e.g., john.doe"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Email
                    </label>
                    <input
                      type="email"
                      value={createUserData.email || ''}
                      onChange={(e) => setCreateUserData({ ...createUserData, email: e.target.value })}
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-50 text-gray-900 focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
                      placeholder="user@example.com"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1">
                      Password <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      value={createUserData.password}
                      onChange={(e) => setCreateUserData({ ...createUserData, password: e.target.value })}
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
                      value={createUserData.tenant_name || ''}
                      disabled
                      className="w-full px-3 py-2 border-2 border-gray-400 rounded-md bg-gray-200 text-gray-700 cursor-not-allowed"
                    />
                    <p className="text-xs text-gray-500 mt-1">Defaults to your active tenant</p>
                  </div>
                </div>

                <div className="flex space-x-3 mt-6">
                  <button
                    onClick={handleCreateUser}
                    disabled={isCreating}
                    className="flex-1 px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700 disabled:opacity-50 transition-colors"
                  >
                    {isCreating ? 'Creating...' : 'Create User'}
                  </button>
                  <button
                    onClick={() => {
                      setShowCreateDialog(false);
                      setCreateError(null);
                      setCreateUserData({
                        username: '',
                        email: '',
                        password: '',
                        tenant_name: tenantId || '',
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

          {/* Users List - Full Width Rows */}
          <div className="bg-gray-50 rounded-lg p-6">
            <h2 className="text-2xl font-semibold text-gray-700 mb-4 border-b pb-2">
              Users ({users.length})
            </h2>
            
            {isLoading && users.length === 0 && <p>Loading users...</p>}
            {users.length === 0 && !isLoading && <p>No users found.</p>}
            
            <div className="space-y-3">
              {users.map((user) => (
                <div key={user.username} className="w-full">
                  <div
                    className={`flex flex-col sm:flex-row items-start sm:items-center justify-between w-full p-4 rounded-lg border transition-colors ${
                      selectedUser === user.username
                        ? 'bg-indigo-50 border-indigo-300'
                        : 'bg-white border-gray-200 hover:bg-gray-50'
                    }`}
                  >
                    <div className="flex-1">
                      <h3 className="font-semibold text-gray-800">
                        {user.username}
                      </h3>
                      {user.email && (
                        <p className="text-sm text-gray-600">Email: {user.email}</p>
                      )}
                      {/* Display current roles */}
                      {user.roles && user.roles.length > 0 && (
                        <div className="mt-2">
                          <p className="text-xs text-gray-500 mb-1">Current Roles:</p>
                          <div className="flex flex-wrap gap-1">
                            {user.roles.map((role) => (
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
                      {(!user.roles || user.roles.length === 0) && (
                        <p className="text-xs text-gray-400 mt-2">No roles assigned</p>
                      )}
                    </div>
                    <div className="mt-3 sm:mt-0 flex gap-2">
                      <button
                        onClick={() => handleUserSelect(user.username)}
                        className="px-4 py-2 bg-indigo-600 text-white rounded-md hover:bg-indigo-700 transition-colors"
                      >
                        Manage Roles
                      </button>
                      {user.username !== userData?.username && (
                        <button
                          onClick={() => handleDeleteUser(user.username)}
                          className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700 transition-colors"
                        >
                          Delete
                        </button>
                      )}
                    </div>
                  </div>
                  {/* Inline Role Management UI */}
                  {selectedUser === user.username && (
                    <div className="mt-2 mb-4 p-4 bg-indigo-50 rounded-md border border-indigo-200">
                      <div className="flex justify-between items-center mb-2">
                        <p className="text-sm text-indigo-700">
                          Managing roles for user: <strong>{user.username}</strong>
                        </p>
                        <button
                          onClick={() => {
                            setSelectedUser(null);
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
                      {error && selectedUser && (
                        <div className="mb-2 p-2 bg-red-50 border border-red-200 rounded-md">
                          <p className="text-red-600">Error: {error}</p>
                        </div>
                      )}
                      {successMessage && selectedUser && (
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
                            setSelectedUser(null);
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
                            setSelectedUser(null);
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
              onClick={fetchUsers}
              disabled={isLoading}
              className="mt-4 px-4 py-2 bg-gray-200 text-gray-700 rounded-md hover:bg-gray-300 disabled:opacity-50 transition-colors"
            >
              {isLoading ? 'Refreshing...' : 'Refresh Users'}
            </button>
          </div>

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

export default UsersPage;
