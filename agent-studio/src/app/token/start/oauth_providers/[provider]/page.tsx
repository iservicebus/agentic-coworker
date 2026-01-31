"use client";

import React, { useEffect, Suspense, useState } from 'react';
import { useParams, useSearchParams } from 'next/navigation';
import { signIn } from "next-auth/react";
import { logger } from "@/lib/logger";
import { useUserData } from "@/lib/contexts/UserDataContext"; // Import useUserData

function MinimalOAuthContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const provider = params.provider as string;
  const agentIdFromQuery = searchParams.get('agent_id');
  const { userData } = useUserData();
  const [message, setMessage] = useState<string>("");
  const [isError, setIsError] = useState<boolean>(false);
  const [sampleUrl, setSampleUrl] = useState<string>("");

  useEffect(() => {
    if (provider) {
      logger.info(`OAuth Flow: Initiating`, {
        task: "GenerateOAuthToken",
        provider: provider,
        step: "initiateSignIn",
        status: "SUCCESS",
        details: `Initiating signIn with provider: ${provider}`
      });
      setMessage(`Initiating authentication with ${provider}...`);
      // The provider ID for signIn should be dynamic based on the 'provider' route parameter.
      // Assuming the 'provider' parameter (e.g., "github", "google") matches the NextAuth provider ID.
      // Use agent_id from query parameter if available, otherwise fall back to userData
      const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromQuery;
      // Check if agentId is available
      if (!agentId) {
        logger.error(`OAuth Flow: Initiation Failed`, {
          task: "GenerateOAuthToken",
          provider: provider,
          step: "initiateSignIn",
          status: "FAILURE",
          details: "Agent ID not provided."
        });
        const exampleUrl = `${window.location.origin}/token/start/oauth_providers/${provider}?agent_id=YOUR_AGENT_ID`;
        setSampleUrl(exampleUrl);
        setMessage(`Agent ID is required. Please either login using an agent user ID or add the agent_id parameter to the URL.`);
        setIsError(true);
        return;
      }
      
      const callbackUrl = `/token/callback/oauth_providers/${provider}?agent_id=${agentId}`;
      signIn(provider, { callbackUrl })
        .then(response => {
          // signIn typically redirects, so this .then() might not be reached if successful.
          // However, if it returns an error object without redirecting:
          if (response && response.error) {
            logger.error(`OAuth Flow: Initiation Failed`, {
              task: "GenerateOAuthToken",
              provider: provider,
              step: "initiateSignIn",
              status: "FAILURE",
              details: response.error
            });
            console.error("OAuth sign-in initiation error:", response.error);
            setMessage(`Failed to initiate authentication with ${provider}: ${response.error}. Please try again.`);
            setIsError(true);
          } else if (response && !response.ok && response.url === null) {
            // This case might indicate that the provider is not configured or another setup issue.
            logger.error(`OAuth Flow: Initiation Failed`, {
              task: "GenerateOAuthToken",
              provider: provider,
              step: "initiateSignIn",
              status: "FAILURE",
              details: "Response not ok and no redirect URL. Provider may be misconfigured."
            });
             console.error("OAuth sign-in initiation failed. Response not ok and no redirect URL.", response);
             setMessage(`Failed to initiate authentication with ${provider}. The provider may not be configured correctly. Please check the console.`);
             setIsError(true);
          }
          // If response.ok is true and response.url is present, a redirect is happening or has happened.
          // If response is undefined (common for successful redirect), no action needed here.
        })
        .catch(error => {
          // Catching errors if the signIn promise rejects
          logger.error(`OAuth Flow: Initiation Failed`, {
            task: "GenerateOAuthToken",
            provider: provider,
            step: "initiateSignIn",
            status: "FAILURE",
            details: error
          });
          console.error("OAuth sign-in initiation failed:", error);
          setMessage(`An unexpected error occurred while trying to sign in with ${provider}. Please check the console and try again.`);
          setIsError(true);
        });
    } else {
      logger.error(`OAuth Flow: Initiation Failed`, {
        task: "GenerateOAuthToken",
        provider: "unknown",
        step: "initiateSignIn",
        status: "FAILURE",
        details: "Provider not specified in URL."
      });
      setMessage("OAuth provider not specified in the URL.");
      setIsError(true);
    }
  }, [provider, agentIdFromQuery, userData]);

  return (
    <div className="text-center mt-20 text-lg">
      <p className={isError ? "text-red-500 font-semibold" : "text-white"}>{message}</p>
      {sampleUrl && (
        <div className="mt-4 text-sm max-w-2xl mx-auto">
          <p className="mb-2 text-gray-300 font-medium">Example URL with agent_id parameter:</p>
          <code className="bg-gray-800 text-white p-3 rounded block text-left break-all">{sampleUrl}</code>
        </div>
      )}
      {isError && !sampleUrl && <p className="text-gray-300">If the problem persists, please contact support.</p>}
      {!isError && !message.startsWith("Failed") && !message.startsWith("OAuth provider not specified") && !message.startsWith("Agent ID is required") && <p className="text-gray-300">You should be redirected shortly. If not, please ensure pop-ups are enabled and try again.</p>}
    </div>
  );
}

export default function MinimalAutoOAuthStartPage() {
  return (
    <Suspense fallback={<div className="text-center mt-20 text-lg text-white">Loading... </div>}>
      <MinimalOAuthContent />
    </Suspense>
  );
}
