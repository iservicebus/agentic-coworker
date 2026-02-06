'use client';

import React, { useState, useEffect, useCallback } from 'react';
import { getSpecificProviderToken, ProviderTokenResponse, ApiError } from '@/lib/apiClient';
import styles from './ProviderToken.module.css';
import { useRouter } from 'next/navigation';

interface ProviderTokenProps {
  providerId: string;
  tenantName: string;
  agentId: string;
  onTokenAction: () => void;
}

const ProviderToken: React.FC<ProviderTokenProps> = ({ providerId, tenantName, agentId, onTokenAction }) => {
  const [token, setToken] = useState<ProviderTokenResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const router = useRouter();

  const fetchToken = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const fetchedToken = await getSpecificProviderToken(tenantName, providerId, agentId);
      setToken(fetchedToken);
    } catch (err) {
      // Check for 404 error using the status code property instead of message parsing
      const apiError = err as ApiError;
      if (apiError.status === 404) {
        setToken(null);
      } else {
        console.error(`Failed to fetch token for provider ${providerId}:`, err);
        setError(err instanceof Error ? err.message : 'Failed to fetch token.');
      }
    } finally {
      setIsLoading(false);
    }
  }, [providerId, tenantName, agentId]);

  useEffect(() => {
    fetchToken();
  }, [fetchToken]);

  const handleButtonClick = () => {
    window.open(`/token/start/oauth_providers/${providerId}?agent_id=${agentId}`, '_blank');
    onTokenAction();
  };

  return (
    <div className={styles.container}>
      {isLoading && <p>Loading token...</p>}
      {error && <p className={styles.error}>Error: {error}</p>}
      {!isLoading && !error && (
        <div>
          <button onClick={handleButtonClick} className={styles.button}>
            {token ? 'Refresh Token' : 'Get Token'}
          </button>
          {token && (
            <div className={styles.tokenInfo}>
              <pre>{JSON.stringify(token, null, 2)}</pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ProviderToken;
