"use client";

import React, { useState, useEffect } from "react";
import { useSearchParams } from 'next/navigation';
import { useUserData } from "@/lib/contexts/UserDataContext";
import {
  getServiceSecrets,
} from "@/lib/apiClient";
import Layout from '@/components/Layout';
import ServiceSecret from '@/components/ServiceSecret';
import { getTenantFromCookie } from '@/lib/tenantUtils';

export default function ServiceSecretsPage() {
  const searchParams = useSearchParams();
  const { userData, isLoading, error } = useUserData();
  const [pageError, setPageError] = useState<string | null>(null);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [serviceSecrets, setServiceSecrets] = useState<Record<string, Record<string, any>>>({});
  const [showAddServiceForm, setShowAddServiceForm] = useState<boolean>(false);
  const [tenantName, setTenantName] = useState<string | null>(null);

  const agentIdFromUrl = searchParams.get('agent_id');
  const agentId = userData?.user_type === "agent" ? userData.username : agentIdFromUrl;

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);

  const fetchServiceSecrets = async () => {
    if (agentId && tenantName) {
      try {
        const secrets = await getServiceSecrets(
          agentId,
          tenantName
        );
        setServiceSecrets(secrets);
      } catch (err: any) {
        setPageError(err.message);
      }
    }
  };

  useEffect(() => {
    if (!isLoading && userData && agentId && tenantName) {
      fetchServiceSecrets();
    }
  }, [isLoading, userData, agentId, tenantName]);

  const handleSaveSuccess = async () => {
    await fetchServiceSecrets();
    setShowAddServiceForm(false);
  };

  const handleDeleteSuccess = async () => {
    await fetchServiceSecrets();
  };

  if (isLoading) {
    return <div className="container mx-auto p-4 text-center">Loading service secrets...</div>;
  }

  if (error) {
    return (
        <Layout>
            <div className="container mx-auto p-4">
                <p className="text-red-500 bg-red-100 p-3 rounded mb-4">Error loading data: {error}</p>
            </div>
        </Layout>
    );
  }

  if (!userData && !isLoading) {
    return (
        <Layout>
            <div className="container mx-auto p-4">
                <p className="text-gray-900">No data available or user not authenticated.</p>
            </div>
        </Layout>
    );
  }

  return (
    <Layout>
      <div className="container mx-auto p-4">
        {pageError && <p className="text-red-500 bg-red-100 p-3 rounded mb-4">Error: {pageError}</p>}
        
        <div className="mb-6 p-4 border rounded-lg shadow-md bg-white">
          <h2 className="text-xl font-semibold mb-2 text-gray-900">App Secrets</h2>
          {Object.keys(serviceSecrets).length > 0 ? (
            <ul className="space-y-4">
              {Object.entries(serviceSecrets).map(([appName, secrets]) => (
                <ServiceSecret
                  key={appName}
                  appName={appName}
                  secrets={secrets}
                  onSaveSuccess={handleSaveSuccess}
                  onDeleteSuccess={handleDeleteSuccess}
                  agentId={agentId || undefined}
                  tenantName={tenantName || undefined}
                />
              ))}
            </ul>
          ) : (
            <p className="text-gray-700">No app secrets configured for this tenant.</p>
          )}

          <div className="mt-6">
            <button
              onClick={() => setShowAddServiceForm(!showAddServiceForm)}
              className="px-4 py-2 bg-indigo-600 text-white rounded hover:bg-indigo-700"
            >
              {showAddServiceForm ? "Cancel Adding App" : "Add Secrets for New App"}
            </button>
          </div>

          {showAddServiceForm && (
            <ServiceSecret
              isNew={true}
              onSaveSuccess={handleSaveSuccess}
              onCancel={() => setShowAddServiceForm(false)}
              agentId={agentId || undefined}
              tenantName={tenantName || undefined}
            />
          )}
        </div>
      </div>
    </Layout>
  );
}
