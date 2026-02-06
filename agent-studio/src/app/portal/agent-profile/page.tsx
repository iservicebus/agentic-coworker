"use client";

import React, { useEffect, useState, useCallback } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useUserData } from "@/lib/contexts/UserDataContext";
import { 
  getAgentProfile,
  AgentProfileInfo
} from "@/lib/apiClient";
import Layout from '@/components/Layout';
import HierarchicalToolFilter from '@/components/HierarchicalToolFilter';
import { getTenantFromCookie } from '@/lib/tenantUtils';

export default function AgentProfilePage() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { userData, isLoading, error } = useUserData();
  
  // Get agent_id from URL parameter or fall back to userData
  const agentIdFromUrl = searchParams.get('agent_id');
  const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromUrl;
  const [updateError, setUpdateError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);


  // Get tenant from cookie on component mount
    const tenantName = getTenantFromCookie();


  // Agent profile state
  const [agentProfile, setAgentProfile] = useState<AgentProfileInfo | null>(null);

  const fetchAgentProfileData = useCallback(async (agentId: string) => {
    try {
      const profile = await getAgentProfile(tenantName||'', agentId);
      setAgentProfile(profile);
    } catch (err) {
      console.error("Failed to fetch agent profile:", err);
      setUpdateError(err instanceof Error ? err.message : 'Failed to fetch agent profile.');
    }
  }, []);

  useEffect(() => {
    if (!isLoading && !userData && !error) {
      // Redirect or handle unauthenticated state
    }
  }, [isLoading, userData, error, router]);

  useEffect(() => {
    if (agentId) {
      fetchAgentProfileData(agentId);
    }
  }, [agentId, fetchAgentProfileData]);

  if (isLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-4 text-center">Loading agent profile...</div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="container mx-auto p-4">
          <p className="text-red-500 bg-red-100 p-3 rounded mb-4">Error loading agent data: {error}</p>
        </div>
      </Layout>
    );
  }

  if (!userData && !isLoading) {
    return (
      <Layout>
        <div className="container mx-auto p-4">
          <p className="text-gray-900">No agent data available or user not authenticated.</p>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="min-h-screen bg-gray-100 p-4 sm:p-6 md:p-8">
        <div className="max-w-4xl mx-auto bg-white shadow-xl rounded-lg p-6 sm:p-8 md:p-10">
          <header className="mb-8">
            <h1 className="text-4xl font-bold text-gray-800 mb-3">
              Agent Profile
            </h1>
            <p className="text-lg text-gray-600">
              Set up initial tool filter for agent to get tool list via MCP server
            </p>
          </header>

          {/* Display update messages */}
          {updateError && (
            <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-md">
              <p className="text-red-600">Error: {updateError}</p>
            </div>
          )}
          {successMessage && (
            <div className="mb-6 p-4 bg-green-50 border border-green-200 rounded-md">
              <p className="text-green-600">{successMessage}</p>
            </div>
          )}

          {/* Role Tool Hierarchy Section */}
          {agentId && (
            <div className="mt-8">
              <HierarchicalToolFilter
                agentId={agentId}
                tenantName={tenantName || undefined}
                showSaveButton={true}
                showLoadButton={false}
                collapsible={false}
                autoLoadFilter={true}
                showToolQuery={true}
                title="Tool Filter"
                onFilterSaved={() => {
                  // Refresh agent profile after filter is saved
                  if (agentId) {
                    fetchAgentProfileData(agentId);
                  }
                  setSuccessMessage('Tool filter has been updated!');
                  setTimeout(() => setSuccessMessage(null), 3000);
                }}
              />
            </div>
          )}


        </div>
      </div>
    </Layout>
  );
}
