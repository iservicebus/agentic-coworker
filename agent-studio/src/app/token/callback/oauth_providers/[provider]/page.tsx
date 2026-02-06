"use client";

import React, { useEffect, useState, Suspense } from "react";
import { updateProvider } from "@/lib/apiClient";
import { useParams, useSearchParams } from 'next/navigation';
import { useUserData } from "@/lib/contexts/UserDataContext"; // Import useUserData
import { logger } from "@/lib/logger";
import { getSession } from "next-auth/react";
import styles from './AuthCallback.module.css';
import { getTenantFromCookie } from '@/lib/tenantUtils';

function AuthCallbackContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const providerName = params.provider as string; // Renamed to avoid conflict with AgentDataContext provider
  const agentIdFromQuery = searchParams.get('agent_id');
  const { userData, isLoading: isUserDataLoading, error: userDataError } = useUserData();
  const [message, setMessage] = useState<string>("Processing callback...");
  const [accessToken, setAccessToken] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);

  const [isError, setIsError] = useState<boolean>(false);
  const [correlationId] = useState(() => typeof window !== "undefined" ? crypto.randomUUID() : "");
  // Get tenant from cookie on component mount
  const tenantName = getTenantFromCookie() ||'';

  useEffect(() => {
    if (correlationId) { // Only log if correlationId is generated
        logger.info(`OAuth Flow: Callback Received`, {
            task: "GenerateOAuthToken",
            correlationId: correlationId,
            provider: providerName,
            step: "callbackReceived",
            status: "SUCCESS",
            details: "Callback page loaded."
        });
    }

    if (isUserDataLoading) {
      setMessage("Loading user data...");
      return;
    }

    if (userDataError) {
      logger.error(`OAuth Flow: User Data Failed`, {
        task: "GenerateOAuthToken",
        correlationId: correlationId,
        provider: providerName,
        step: "userDataLoad",
        status: "FAILURE",
        details: userDataError
      });
      setMessage(`Error loading user data: ${userDataError}. Cannot update provider credentials.`);
      setIsError(true);
      setIsLoading(false);
      return;
    }
    logger.info(" user data in call back", userData)
    // Use agent_id from query parameter if available, otherwise fall back to userData
    const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromQuery;
    if (!agentId ) {
      logger.error(`OAuth Flow: User Data Invalid`, {
        task: "GenerateOAuthToken",
        correlationId: correlationId,
        provider: providerName,
        step: "userDataLoad",
        status: "FAILURE",
        details: "Missing agent ID or tenant name in userData."
      });
      setMessage("Missing agent ID or tenant name. Cannot update provider credentials.");
      setIsError(true);
      setIsLoading(false);
      return;
    }

    if (providerName) {
      const handleUpdate = async () => {
        try {
          const response = await updateProvider(
            providerName,
            agentId, // Use agentId from query or userData
            tenantName     // Non-null assertion due to check above
          );



          const successMessage = (typeof response === 'string' ? response : response?.message) || `Successfully updated credentials for ${providerName}.`;

          logger.info(`OAuth Flow: Credential Update Success`, {
            task: "GenerateOAuthToken",
            correlationId: correlationId,
            provider: providerName,
            step: "updateProvider",
            status: "SUCCESS",
            agentId: agentId,
            tenantName: tenantName,
            details: successMessage
          });
          const session = await getSession();
          const sessionAccessToken = session?.accessToken; // The user's current session token
          setMessage(successMessage);
          setAccessToken(sessionAccessToken || null);
          setIsError(false);
          setIsLoading(false);
        } catch (err: any) {
          logger.error(`OAuth Flow: Credential Update Failed`, {
            task: "GenerateOAuthToken",
            correlationId: correlationId,
            provider: providerName,
            step: "updateProvider",
            status: "FAILURE",
            agentId: agentId,
            tenantName: tenantName,
            details: err
          });
          console.error("Failed to update provider credentials:", err);
          let errorMessage = `An error occurred while updating credentials for ${providerName}.`;
          if (err && typeof err.message === 'string' && err.message) {
            errorMessage = err.message;
          } else if (typeof err === 'string' && err) {
            errorMessage = err;
          }
          if (errorMessage === `An error occurred while updating credentials for ${providerName}.`) {
             setMessage(errorMessage + " Please check the console for more details.");
          } else {
             setMessage(errorMessage);
          }
          setIsError(true);
          setIsLoading(false);
        }
      };
      handleUpdate();
    } else {
      logger.error(`OAuth Flow: Callback Failed`, {
        task: "GenerateOAuthToken",
        correlationId: correlationId,
        provider: "unknown",
        step: "callbackReceived",
        status: "FAILURE",
        details: "Provider name not specified in URL."
      });
      setMessage("Provider name not specified in the URL.");
      setIsError(true);
      setIsLoading(false);
    }
  }, [providerName, userData, isUserDataLoading, userDataError, correlationId, agentIdFromQuery]); // Added dependencies

  const copyToClipboard = async (text: string) => {
    try {
      await navigator.clipboard.writeText(text);
    } catch (err) {
      console.error('Failed to copy text: ', err);
    }
  };

  return (
    <div className={styles.container}>
      <div className={`${styles.message} ${isError ? styles.errorMessage : styles.successMessage}`}>
        {message}
      </div>
      
      {accessToken && !isError && (
        <div className={styles.tokenContainer}>
          <div className={styles.tokenLabel}>Access Token:</div>
          <div className={styles.tokenValue}>{accessToken}</div>
          <button 
            className={styles.copyButton}
            onClick={() => copyToClipboard(accessToken)}
            title="Copy access token to clipboard"
          >
            Copy Token
          </button>
        </div>
      )}
      
      {!isError && !isLoading && (
        <button 
          className={`${styles.actionText} ${styles.success} ${styles.closeButton}`}
          onClick={() => window.close()}
          title="Close this window"
        >
          Close Window
        </button>
      )}
      
      {isError && !isLoading && (
        <div className={`${styles.actionText} ${styles.error}`}>
          Please try initiating the OAuth flow again or contact support if the issue persists.
        </div>
      )}
    </div>
  );
}

// useSearchParams should be used within a Suspense boundary
export default function AuthCallbackPage() {
    return (
      <Suspense fallback={
        <div className={styles.container}>
          <div className={`${styles.message} ${styles.loadingText}`}>Loading...</div>
        </div>
      }>
        <AuthCallbackContent />
      </Suspense>
    );
  }
