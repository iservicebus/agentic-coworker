'use client';

import React, { useState, useEffect, useCallback } from 'react';
import ToolDefinitionUI from '@/components/ToolDefinitionUI';
import {
  listStagingServices,
  updateStagingService,
  StagingServiceResponse,
  ToolDefinition,
} from '@/lib/apiClient';
import styles from './StagingServicesPage.module.css';
import Layout from '@/components/Layout'; // Assuming Layout component path
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';


const StagingServicesPage: React.FC = () => {
  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const [tenantName, setTenantName] = useState<string | null>(null);
  const userRoles = userData?.roles || [];
  const isAdmin = userRoles.includes("administrator");

  // Get tenant from cookie on component mount
  useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantName(tenant);
  }, []);

  const [services, setServices] = useState<StagingServiceResponse[]>([]);
  const [editingServiceId, setEditingServiceId] = useState<string | null>(null);
  const [editedToolJson, setEditedToolJson] = useState<string>('');
  const [originalToolJson, setOriginalToolJson] = useState<string>('{}');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSaving, setIsSaving] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchServices = useCallback(async () => {
    if (!tenantName) return;
    setIsLoading(true);
    setError(null);
    try {
      const fetchedServices = await listStagingServices(tenantName);
      setServices(fetchedServices || []);
    } catch (err) {
      console.error("Failed to fetch staging services:", err);
      setError(err instanceof Error ? err.message : 'Failed to fetch staging services.');
      setServices([]);
    } finally {
      setIsLoading(false);
    }
  }, [tenantName]);

  useEffect(() => {
    if (tenantName ) {
      fetchServices();
    }
  }, [fetchServices, tenantName]);

  const handleToggleView = (serviceId: string) => {
    if (editingServiceId === serviceId) {
      setEditingServiceId(null);
      setEditedToolJson('');
      setOriginalToolJson('{}');
    } else {
      const serviceToEdit = services.find(s => s.id === serviceId);
      if (serviceToEdit) {
        setEditingServiceId(serviceId);
        try {

          const stagingDataWithId = {
            id: serviceId, // Include the ID for update operations
            ...serviceToEdit.service_data || {}, // Spread the document content
          };

          const serviceJson = JSON.stringify(stagingDataWithId || {}, null, 2);
          setEditedToolJson(serviceJson);
          setOriginalToolJson(serviceJson);
        } catch (e) {
          console.error("Error stringifying service_data:", e);
          setEditedToolJson('{}');
          setOriginalToolJson('{}');
          setError("Failed to parse service data for editing.");
        }
      }
    }
  };

  const handleEditedToolJsonChange = (json: string) => {
    setEditedToolJson(json);
  };

  const handleSaveService = async () => {
    if (!editingServiceId || !tenantName ) return;
    
    // Find the service to get its ID for the API call
    const serviceToSave = services.find(s => s.id === editingServiceId);
    if (!serviceToSave) {
      setError("Cannot save: Service not found.");
      return;
    }

    setIsSaving(true);
    setError(null);
    try {
      
      let serviceDataToSave: ToolDefinition;
      try {
        serviceDataToSave = JSON.parse(editedToolJson);
      } catch (e) {
        console.error("Invalid JSON in editor:", e);
        setError("Cannot save: The edited service data is not valid JSON.");
        setIsSaving(false);
        return;
      }
      const updatedService = await updateStagingService(
        tenantName,
        serviceToSave.id, // Use service ID instead of name
        serviceDataToSave
      );

      setServices((prevServices) =>
        prevServices.map((s) => (s.id === updatedService.id ? updatedService : s))
      );
      setEditingServiceId(null); 
      setEditedToolJson('');
      setOriginalToolJson('{}');
      // await fetchServices(); // Optionally re-fetch all
    } catch (err) {
      console.error("Failed to save staging service:", err);
      setError(err instanceof Error ? err.message : 'Failed to save staging service.');
    } finally {
      setIsSaving(false);
    }
  };

  if (isUserLoading) {
    return <div className={styles.container}><p>Loading user data...</p></div>;
  }

  if (userError) {
    return <div className={styles.container}><p>Error loading user data: {userError}</p></div>;
  }

  if (!tenantName) {
    return <div className={styles.container}><p>Tenant is not selected.</p></div>;
  }

  if (isLoading && services.length === 0) {
    return <div className={styles.container}><p>Loading staging services...</p></div>;
  }

  return (
    <Layout>
    <div className={styles.container}>
      <h1 className={styles.title}>Staging Services for Tenant: {tenantName} </h1>
      
      {error && <p className={styles.error}>Error: {error}</p>}

      <div className={styles.serviceListContainer}> {/* Using serviceListContainer for the main content area */}
        <h2 className={styles.subTitle}>Available Services ({services.length})</h2>
        {services.length === 0 && !isLoading && <p>No staging services found for this tenant.</p>}
        {isLoading && services.length > 0 && <p>Refreshing service list...</p>}
        <ul className={styles.serviceList}>
          {services.map((service) => (
            <li key={service.id} className={`${styles.serviceListItem} ${editingServiceId === service.id ? styles.selected : ''}`}>
              <div className={styles.serviceHeader}>
                <span>{service.name || service.service_data?.name || 'Unnamed Service'} (ID: {service.id})</span>
                <button
                  onClick={() => handleToggleView(service.id)}
                  disabled={isSaving && editingServiceId === service.id}
                  className={styles.editButton}
                >
                  {editingServiceId === service.id ? 'Cancel' : 'Edit Details'}
                </button>
              </div>
              {editingServiceId === service.id && (
                <div className={styles.inlineEditorContainer}>
                  {/* Sub-title for the editor can be here if desired */}
                  {/* <h3 className={styles.editorTitle}>Editing: {service.name || service.service_data?.name}</h3> */}
                  <ToolDefinitionUI
                    editedToolJson={editedToolJson}
                    originalToolJson={originalToolJson}
                    onEditedToolJsonChange={handleEditedToolJsonChange}
                    onSaveToStaging={handleSaveService}
                    isLoading={isSaving}
                    pageType="staging"
                    serviceId={service.id}
                    onDeleteSuccess={() => {
                      setEditingServiceId(null);
                      setOriginalToolJson('{}');
                      fetchServices();
                    }}
                    tenantName={tenantName}
                    isAdminMode={isAdmin}
                  />
                </div>
              )}
            </li>
          ))}
        </ul>
        <button onClick={fetchServices} disabled={isLoading || isSaving} className={styles.refreshButton}>
          {isLoading ? 'Refreshing...' : 'Refresh List'}
        </button>
      </div>
    </div>
    </Layout>
  );
};

export default StagingServicesPage;
