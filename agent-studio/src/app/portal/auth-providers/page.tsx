'use client';

import React, { useState, useEffect } from 'react';
import { useUserData } from "@/lib/contexts/UserDataContext";
import { 
  getAuthProvidersWithSecrets, 
  createAuthProvider, 
  updateAuthProvider, 
  deleteAuthProvider,
  AuthProviderDetails,
  AuthProviderCreatePayload,
  AuthProviderUpdatePayload
} from '@/lib/apiClient';
import { providerMap } from '@/lib/providers/providerMap';
import Layout from '@/components/Layout';
import styles from './AuthProvidersPage.module.css';
import { getTenantFromCookie } from '@/lib/tenantUtils';

interface AuthProviderFormData {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  type: string;
  client_id: string;
  client_secret: string;
  is_built_in: boolean;
  options?: Record<string, any> | null;
}

const AuthProvidersPage: React.FC = () => {
  const { userData, isLoading: userLoading } = useUserData();
  const [providers, setProviders] = useState<AuthProviderDetails[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [editingProviderId, setEditingProviderId] = useState<string | null>(null);
  const [tenantName, setTenantName] = useState<string | null>(null);
  const [formData, setFormData] = useState<AuthProviderFormData>({
    provider_id: '',
    provider_name: '',
    provider_type: '',
    type: 'oauth',
    client_id: '',
    client_secret: '',
    is_built_in: false,
    options: null
  });
  const [showClientSecret, setShowClientSecret] = useState(false);

  // Get valid provider types from providerMap
  const validProviderTypes = Object.keys(providerMap);

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);

  useEffect(() => {
    if (tenantName) {
      fetchProviders();
    }
  }, [tenantName]);

  const fetchProviders = async () => {
    if (!tenantName) return;
    
    try {
      setLoading(true);
      const response = await getAuthProvidersWithSecrets(tenantName);
      setProviders(response);
      setError(null);
    } catch (err) {
      console.error('Error fetching auth providers:', err);
      setError('Failed to fetch auth providers');
    } finally {
      setLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!tenantName) return;

    try {
      if (editingProviderId) {
        // Update existing provider
        const updatePayload: AuthProviderUpdatePayload = {
          provider_name: formData.provider_name,
          provider_type: formData.provider_type,
          type: formData.type,
          client_id: formData.client_id,
          client_secret: formData.client_secret,
          is_built_in: formData.is_built_in,
          options: formData.options
        };
        await updateAuthProvider(tenantName, formData.provider_id, updatePayload);
        setEditingProviderId(null);
      } else {
        // Create new provider
        const createPayload: AuthProviderCreatePayload = {
          provider_id: formData.provider_id,
          provider_name: formData.provider_name,
          provider_type: formData.provider_type,
          type: formData.type,
          client_id: formData.client_id,
          client_secret: formData.client_secret,
          is_built_in: formData.is_built_in,
          options: formData.options
        };
        await createAuthProvider(tenantName, createPayload);
        setShowCreateForm(false);
      }
      
      // Reset form
      setFormData({
        provider_id: '',
        provider_name: '',
        provider_type: '',
        type: 'oauth',
        client_id: '',
        client_secret: '',
        is_built_in: false,
        options: null
      });
      
      // Refresh the list
      await fetchProviders();
    } catch (err) {
      console.error('Error saving auth provider:', err);
      setError('Failed to save auth provider');
    }
  };

  const handleEdit = (provider: AuthProviderDetails) => {
    if (editingProviderId === provider.provider_id) {
      // Cancel editing
      setEditingProviderId(null);
      setFormData({
        provider_id: '',
        provider_name: '',
        provider_type: '',
        type: 'oauth',
        client_id: '',
        client_secret: '',
        is_built_in: false,
        options: null
      });
    } else {
      // Start editing
      setEditingProviderId(provider.provider_id);
      setShowCreateForm(false); // Close create form if open
      setFormData({
        provider_id: provider.provider_id,
        provider_name: provider.provider_name,
        provider_type: provider.provider_type,
        type: provider.type,
        client_id: provider.client_id,
        client_secret: provider.client_secret,
        is_built_in: provider.is_built_in,
        options: provider.options
      });
    }
  };

  const handleDelete = async (providerId: string) => {
    if (!confirm('Are you sure you want to delete this auth provider?')) return;
    if (!tenantName) return;
    
    try {
      await deleteAuthProvider(tenantName, providerId);
      await fetchProviders(); // Refresh the list
    } catch (err) {
      console.error('Error deleting auth provider:', err);
      setError('Failed to delete auth provider');
    }
  };

  const handleCreateNew = () => {
    if (showCreateForm) {
      // Cancel create
      setShowCreateForm(false);
      setFormData({
        provider_id: '',
        provider_name: '',
        provider_type: '',
        type: 'oauth',
        client_id: '',
        client_secret: '',
        is_built_in: false,
        options: null
      });
    } else {
      // Start create
      setShowCreateForm(true);
      setEditingProviderId(null); // Close any edit forms
      setFormData({
        provider_id: '',
        provider_name: '',
        provider_type: '',
        type: 'oauth',
        client_id: '',
        client_secret: '',
        is_built_in: false,
        options: null
      });
    }
  };

  const renderForm = (isCreate: boolean = false) => (
    <div className={styles.formContainer}>
      <form onSubmit={handleSubmit} className={styles.form}>
        <div className={styles.formRow}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Provider ID *</label>
            <input
              type="text"
              value={formData.provider_id}
              onChange={(e) => setFormData({ ...formData, provider_id: e.target.value })}
              className={styles.input}
              required
              disabled={!isCreate} // Don't allow editing provider_id
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Provider Name *</label>
            <input
              type="text"
              value={formData.provider_name}
              onChange={(e) => setFormData({ ...formData, provider_name: e.target.value })}
              className={styles.input}
              required
            />
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Provider Type *</label>
            <select
              value={formData.provider_type}
              onChange={(e) => setFormData({ ...formData, provider_type: e.target.value })}
              className={styles.select}
              required
            >
              <option value="">Select provider type</option>
              {validProviderTypes.map(type => (
                <option key={type} value={type}>{type}</option>
              ))}
            </select>
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Type *</label>
            <select
              value={formData.type}
              onChange={(e) => setFormData({ ...formData, type: e.target.value })}
              className={styles.select}
              required
            >
              <option value="oauth">OAuth</option>
              <option value="oidc">OIDC</option>
              <option value="credentials">Credentials</option>
            </select>
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formGroup}>
            <label className={styles.label}>Client ID *</label>
            <input
              type="text"
              value={formData.client_id}
              onChange={(e) => setFormData({ ...formData, client_id: e.target.value })}
              className={styles.input}
              required
            />
          </div>
          <div className={styles.formGroup}>
            <label className={styles.label}>Client Secret *</label>
            <div className={styles.passwordInputContainer}>
              <input
                type={showClientSecret ? "text" : "password"}
                value={formData.client_secret}
                onChange={(e) => setFormData({ ...formData, client_secret: e.target.value })}
                className={styles.passwordInput}
                required
              />
              <button
                type="button"
                onClick={() => setShowClientSecret(!showClientSecret)}
                className={styles.passwordToggle}
                title={showClientSecret ? "Hide password" : "Show password"}
              >
                {showClientSecret ? (
                  // Eye slash icon (hide)
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M17.94 17.94A10.07 10.07 0 0 1 12 20c-7 0-11-8-11-8a18.45 18.45 0 0 1 5.06-5.94M9.9 4.24A9.12 9.12 0 0 1 12 4c7 0 11 8 11 8a18.5 18.5 0 0 1-2.16 3.19m-6.72-1.07a3 3 0 1 1-4.24-4.24"/>
                    <line x1="1" y1="1" x2="23" y2="23"/>
                  </svg>
                ) : (
                  // Eye icon (show)
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                    <circle cx="12" cy="12" r="3"/>
                  </svg>
                )}
              </button>
            </div>
          </div>
        </div>

        <div className={styles.formRow}>
          <div className={styles.formGroup}>
            <label className={styles.checkboxLabel}>
              <input
                type="checkbox"
                checked={formData.is_built_in}
                onChange={(e) => setFormData({ ...formData, is_built_in: e.target.checked })}
                className={styles.checkbox}
              />
              Built-in Provider
            </label>
          </div>
        </div>

        <div className={styles.formGroup}>
          <label className={styles.label}>Options (JSON)</label>
          <textarea
            value={formData.options ? JSON.stringify(formData.options, null, 2) : ''}
            onChange={(e) => {
              try {
                const options = e.target.value ? JSON.parse(e.target.value) : null;
                setFormData({ ...formData, options });
              } catch {
                // Invalid JSON, keep the text as is for user to fix
              }
            }}
            className={styles.textarea}
            rows={3}
            placeholder='{"key": "value"}'
          />
        </div>

        <div className={styles.formActions}>
          <button
            type="button"
            onClick={isCreate ? handleCreateNew : () => setEditingProviderId(null)}
            className={styles.cancelButton}
          >
            Cancel
          </button>
          <button
            type="submit"
            className={styles.submitButton}
          >
            {isCreate ? 'Create' : 'Update'}
          </button>
        </div>
      </form>
    </div>
  );

  if (userLoading) {
    return (
      <Layout>
        <div className={styles.container}>
          <p>Loading user data...</p>
        </div>
      </Layout>
    );
  }

  if (!tenantName) {
    return (
      <Layout>
        <div className={styles.container}>
          <p className={styles.error}>No active tenant found</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className={styles.container}>
        <h1 className={styles.title}>Auth Providers</h1>
        <p className={styles.subtitle}>
          Manage authentication providers for tenant: {tenantName}
        </p>
        
        {error && <p className={styles.error}>Error: {error}</p>}

        <div className={styles.providerListContainer}>
          <div className={styles.header}>
            <h2 className={styles.subTitle}>
              Available Providers ({providers.length})
            </h2>
            <button
              onClick={handleCreateNew}
              className={styles.addButton}
            >
              {showCreateForm ? 'Cancel' : 'Add Provider'}
            </button>
          </div>

          {showCreateForm && renderForm(true)}

          {loading && providers.length === 0 ? (
            <p>Loading providers...</p>
          ) : providers.length === 0 && !loading ? (
            <p>No auth providers configured</p>
          ) : (
            <ul className={styles.providerList}>
              {providers.map((provider) => (
                <li key={provider.provider_id} className={styles.providerListItem}>
                  <div className={styles.providerHeader}>
                    <div className={styles.providerInfo}>
                      <div className={styles.providerName}>
                        {provider.provider_name}
                      </div>
                      <div className={styles.providerDetails}>
                        {provider.provider_id} ({provider.provider_type}) - {provider.type}
                        {provider.is_built_in && <span className={styles.builtInBadge}>Built-in</span>}
                      </div>
                    </div>
                    <div className={styles.providerActions}>
                      <button
                        onClick={() => handleEdit(provider)}
                        className={styles.editButton}
                      >
                        {editingProviderId === provider.provider_id ? 'Cancel' : 'Edit'}
                      </button>
                      <button
                        onClick={() => handleDelete(provider.provider_id)}
                        className={styles.deleteButton}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                  {editingProviderId === provider.provider_id && renderForm(false)}
                </li>
              ))}
            </ul>
          )}

          <button 
            onClick={fetchProviders} 
            disabled={loading} 
            className={styles.refreshButton}
          >
            {loading ? 'Refreshing...' : 'Refresh List'}
          </button>
        </div>
      </div>
    </Layout>
  );
};

export default AuthProvidersPage;
