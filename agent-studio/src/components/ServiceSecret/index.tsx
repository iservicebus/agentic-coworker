"use client";

import React, { useState, useEffect } from 'react';
import { getServiceSecret, upsertServiceSecrets, deleteServiceSecret, getAllApplications, ApplicationInfo } from '@/lib/apiClient';

interface ServiceSecretProps {
  appName?: string;
  secrets?: Record<string, any>;
  onSaveSuccess?: (appName: string) => void;
  onDeleteSuccess?: (appName: string) => void;
  isNew?: boolean;
  onCancel?: () => void;
  agentId?: string;
  tenantName?: string;
}

const ServiceSecret: React.FC<ServiceSecretProps> = ({
  appName: initialAppName = '',
  secrets: initialSecrets = {},
  onSaveSuccess,
  onDeleteSuccess,
  isNew = false,
  onCancel,
  agentId,
  tenantName,
}) => {
  const [isEditing, setIsEditing] = useState(isNew);
  const [appName, setAppName] = useState(initialAppName);
  const [secretsText, setSecretsText] = useState(JSON.stringify(initialSecrets, null, 2));
  const [isSaving, setIsSaving] = useState(false);
  const [availableApplications, setAvailableApplications] = useState<ApplicationInfo[]>([]);
  const [isLoadingApplications, setIsLoadingApplications] = useState(false);

  useEffect(() => {
    const fetchApplications = async () => {
      if (isNew && !initialAppName) {
        setIsLoadingApplications(true);
        try {
          const applications = await getAllApplications(tenantName||'');
          setAvailableApplications(applications);
        } catch (error) {
          console.error("Failed to fetch applications:", error);
        } finally {
          setIsLoadingApplications(false);
        }
      }
    };

    fetchApplications();
  }, [isNew, initialAppName]);

  useEffect(() => {
    const fetchSecrets = async () => {
      if (isNew && appName && agentId && tenantName) {
        try {
          const fetchedSecrets = await getServiceSecret(
            agentId,
            tenantName,
            appName
          );
          if (fetchedSecrets && fetchedSecrets[appName]) {
            setSecretsText(JSON.stringify(fetchedSecrets[appName], null, 2));
          }
        } catch (error) {
          console.error("Failed to fetch service secrets:", error);
        }
      }
    };

    fetchSecrets();
  }, [isNew, appName, agentId, tenantName]);

  const handleSave = async () => {
    if (!tenantName || !agentId) {
      alert("Cannot save secrets: missing critical data (tenant name, or agent ID).");
      return;
    }
    if (!appName) {
        alert("App Name is required to save secrets.");
        return;
    }

    let secretsToSave;
    try {
      secretsToSave = JSON.parse(secretsText);
    } catch (parseError: any) {
      alert(`Invalid JSON format for secrets: ${parseError.message}`);
      return;
    }

    setIsSaving(true);
    try {
      await upsertServiceSecrets(
        agentId,
        tenantName,
        { app_name: appName, secrets: secretsToSave }
      );
      alert("App secrets updated successfully!");
      if (onSaveSuccess) {
        onSaveSuccess(appName);
      }
      if (!isNew) {
        setIsEditing(false);
      }
    } catch (err: any) {
      const message = err.message || "Failed to update app secrets.";
      console.error("Failed to update service secrets:", err);
      alert(`Error updating service secrets: ${message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!tenantName || !agentId) {
      alert("Cannot delete secret: missing critical data (tenant name, or agent ID).");
      return;
    }

    const confirmed = window.confirm(
      `Are you sure you want to delete the secrets for app "${appName}"? This action cannot be undone.`
    );
    if (!confirmed) return;

    setIsSaving(true);
    try {
      await deleteServiceSecret(
        agentId,
        tenantName,
        appName
      );
      alert(`Secrets for app '${appName}' deleted successfully!`);
      if (onDeleteSuccess) {
        onDeleteSuccess(appName);
      }
    } catch (err: any) {
      const message = err.message || `Failed to delete secrets for app '${appName}'.`;
      console.error(`Failed to delete secrets for app '${appName}':`, err);
      alert(`Error deleting service secrets: ${message}`);
    } finally {
      setIsSaving(false);
    }
  };

  const handleCancel = () => {
    if (isNew) {
        onCancel?.();
    } else {
        setIsEditing(false);
        setAppName(initialAppName);
        setSecretsText(JSON.stringify(initialSecrets, null, 2));
    }
  }

  const renderAppName = () => {
    if (isNew) {
      return (
        <div>
          <label htmlFor="newAppName" className="block text-sm font-medium text-gray-700 mb-1">
            App Name
          </label>
          {isLoadingApplications ? (
            <div className="w-full p-2 border rounded-md shadow-sm bg-gray-100 text-gray-500">
              Loading applications...
            </div>
          ) : availableApplications.length > 0 ? (
            <select
              id="newAppName"
              value={appName}
              onChange={(e) => setAppName(e.target.value)}
              className="w-full p-2 border rounded-md shadow-sm focus:ring-indigo-500 focus:border-indigo-500 text-gray-900"
              disabled={!!initialAppName}
            >
              <option value="">Select an application</option>
              {availableApplications.map((app) => (
                <option key={app.app_name} value={app.app_name}>
                  {app.app_note ? `${app.app_name} - ${app.app_note}` : app.app_name}
                </option>
              ))}
            </select>
          ) : (
            <div className="w-full p-2 border rounded-md shadow-sm bg-gray-100 text-gray-500">
              No applications available. Please contact your administrator to add applications.
            </div>
          )}
        </div>
      )
    }
    return <strong className="text-lg text-gray-800">{appName}</strong>
  }

  return (
    <div className="p-3 border rounded-md shadow-sm bg-gray-50">
      <div className="flex justify-between items-center mb-2">
        {/* Show app name if available, otherwise show "New App Secret" for new entries */}
        {isNew && !appName ? (
          <strong className="text-lg text-gray-800">New App Secret</strong>
        ) : (
          <strong className="text-lg text-gray-800">{appName}</strong>
        )}
        {!isEditing && !isNew && (
          <button
            onClick={() => setIsEditing(true)}
            className="px-3 py-1 bg-blue-500 text-white rounded hover:bg-blue-600 text-sm"
          >
            Edit
          </button>
        )}
      </div>

      {isEditing ? (
        <div className="space-y-3">
          {/* Show app name selection only if it's new and no appName was provided */}
          {isNew && !initialAppName && <div className="mb-3">{renderAppName()}</div>}
          {/* Show app name display if appName is provided (from ToolDefinitionUI) */}
          {isNew && initialAppName && (
            <div className="mb-3">
              <label className="block text-sm font-medium text-gray-700 mb-1">
                App Name
              </label>
              <div className="w-full p-2 border rounded-md shadow-sm bg-gray-100 text-gray-900 font-medium">
                {initialAppName}
              </div>
            </div>
          )}
          <div>
            <label htmlFor="secretsText" className="block text-sm font-medium text-gray-700 mb-1">
              Secrets (JSON format)
            </label>
            <textarea
              id="secretsText"
              value={secretsText}
              onChange={(e) => setSecretsText(e.target.value)}
              rows={8}
              className="w-full p-2 border rounded font-mono text-sm bg-white text-gray-900"
              placeholder='{ "api_key": "your_key", "url": "https://example.com/api" }'
            />
          </div>
          <div className="mt-2 space-x-2">
            <button
              onClick={handleSave}
              className="px-4 py-2 bg-green-500 text-white rounded hover:bg-green-600"
              disabled={isSaving}
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
            <button
              onClick={handleCancel}
              className="px-4 py-2 bg-gray-300 rounded hover:bg-gray-400"
            >
              Cancel
            </button>
            {!isNew && (
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-red-500 text-white rounded hover:bg-red-600"
                disabled={isSaving}
              >
                {isSaving ? "Deleting..." : "Delete"}
              </button>
            )}
          </div>
        </div>
      ) : (
        <pre className="bg-gray-100 p-2 rounded text-sm text-gray-700 overflow-x-auto">
          {JSON.stringify(initialSecrets, null, 2)}
        </pre>
      )}
    </div>
  );
};

export default ServiceSecret;
