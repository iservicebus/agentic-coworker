'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'next/navigation';
import { getAuthProviders, AuthProvider, fetchUserLoginData } from '@/lib/apiClient';
import styles from './ProviderTokensPage.module.css';
import Layout from '@/components/Layout';
import ProviderToken from '@/components/ProviderToken';
import { useSession } from 'next-auth/react';

const ProviderTokensPage: React.FC = () => {
  const searchParams = useSearchParams();
  const tenantName = "default";
  const [providers, setProviders] = useState<AuthProvider[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [selectedProvider, setSelectedProvider] = useState<AuthProvider | null>(null);
  const { data: session } = useSession();
  const [agentId, setAgentId] = useState<string>('');

  // Get agent_id from URL query parameter
  const agentIdFromUrl = searchParams.get('agent_id')|| null;

  useEffect(() => {
    const getAgentId = async () => {
      if (session) {
        // Otherwise, fetch from user data
        const userData = await fetchUserLoginData();
        let id=userData?.user_type === "agent" ? userData.username : agentIdFromUrl;
        if (id)
          setAgentId(id);
      } else if (agentIdFromUrl){
        setAgentId(agentIdFromUrl);

      }
    };
    getAgentId();
  }, [session, agentIdFromUrl]);

  const fetchProviders = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedProviders = await getAuthProviders(tenantName);
      setProviders(fetchedProviders || []);
    } catch (err) {
      console.error("Failed to fetch auth providers:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch auth providers.');
      setProviders([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProviders();
  }, [fetchProviders]);

  const handleShowToken = (provider: AuthProvider) => {
    if (selectedProvider?.provider_id === provider.provider_id) {
      setSelectedProvider(null);
    } else {
      setSelectedProvider(provider);
    }
  };

  const handleTokenAction = () => {
    setSelectedProvider(null);
  };

  if (isLoading && providers.length === 0) {
    return <div className={styles.container}><p>Loading auth providers...</p></div>;
  }

  return (
    <Layout>
      <div className={styles.container}>
        <h1 className={styles.title}>Auth Providers</h1>
        
        {error && <p className={styles.error}>Error: {error}</p>}

        <div className={styles.providerListContainer}>
          <h2 className={styles.subTitle}>Available Providers ({providers.length})</h2>
          {providers.length === 0 && !isLoading && <p>No auth providers found.</p>}
          {isLoading && providers.length > 0 && <p>Refreshing provider list...</p>}
          <ul className={styles.providerList}>
            {providers.map((provider) => (
              <li key={provider.provider_id} className={styles.providerListItem}>
                <div className={styles.providerHeader}>
                  <span>{provider.provider_id}</span>
                  <button
                    onClick={() => handleShowToken(provider)}
                    className={styles.showTokenButton}
                  >
                    {selectedProvider?.provider_id === provider.provider_id ? 'Hide Token' : 'Show Token'}
                  </button>
                </div>
                {selectedProvider?.provider_id === provider.provider_id && agentId && (
                  <ProviderToken
                    providerId={provider.provider_id}
                    tenantName={tenantName}
                    agentId={agentId}
                    onTokenAction={handleTokenAction}
                  />
                )}
              </li>
            ))}
          </ul>
          <button onClick={fetchProviders} disabled={isLoading} className={styles.refreshButton}>
            {isLoading ? 'Refreshing...' : 'Refresh List'}
          </button>
        </div>
      </div>
    </Layout>
  );
};

export default ProviderTokensPage;
