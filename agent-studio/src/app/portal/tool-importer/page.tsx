'use client';

import React, { useState, ChangeEvent, FormEvent } from 'react';
// import Layout from '@/components/Layout'; // Assuming Layout component exists and is needed
import {
  convertDocToTool,
  convertOpenApiByLink,
  convertOpenApiByFile,
  convertPostmanToTool,
  addStagingService,
  ToolDefinition, // Import from apiClient
  StagingServiceResponse // Import from apiClient
} from '@/lib/apiClient'; // Assuming @ is mapped to src folder
import ToolDefinitionUI from '@/components/ToolDefinitionUI'; // Added import
import Layout from '@/components/Layout'; // Assuming Layout component path
import { useUserData } from "@/lib/contexts/UserDataContext";
import { getTenantFromCookie } from '@/lib/tenantUtils';

interface ApiError {
  message: string;
  details?: any;
}

const ToolImporterPage = () => {

  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const [tenantId, setTenantId] = React.useState<string | null>(null);
  const isAdmin = !!(userData?.roles && userData.roles.includes("administrator"));

  // Get tenant from cookie on component mount
  React.useEffect(() => {
    const tenant = getTenantFromCookie();
    setTenantId(tenant);
  }, []);



  const [activeTab, setActiveTab] = useState<'doc' | 'openapi-link' | 'openapi-file' | 'postman-file'>('doc');

  // Input states
  const [docUrl, setDocUrl] = useState('');
  const [openapiLink, setOpenapiLink] = useState('');
  const [openapiFile, setOpenapiFile] = useState<File | null>(null);
  const [postmanFile, setPostmanFile] = useState<File | null>(null);

  // Result states
  const [toolDefinitions, setToolDefinitions] = useState<ToolDefinition[]>([]);
  const [currentToolIndex, setCurrentToolIndex] = useState(0);
  const [editedToolJson, setEditedToolJson] = useState('');

  // UI states
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<ApiError | null>(null);
  const [successMessage, setSuccessMessage] = useState('');
  const successMessageRef = React.useRef<HTMLDivElement>(null);

  const ITEMS_PER_PAGE = 1; // Display one tool at a time

  // Scroll to success message when it appears
  React.useEffect(() => {
    if (successMessage && successMessageRef.current) {
      successMessageRef.current.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
  }, [successMessage]);

  const handleFileChange = (setter: React.Dispatch<React.SetStateAction<File | null>>) => (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setter(e.target.files[0]);
    } else {
      setter(null);
    }
  };

  const resetMessages = () => {
    setError(null);
    setSuccessMessage('');
  };

  const processConversionResponse = (data: ToolDefinition[]) => {
    setToolDefinitions(data);
    setCurrentToolIndex(0);
    if (data.length > 0) {
      setEditedToolJson(JSON.stringify(data[0], null, 2));
      setSuccessMessage(`Successfully converted. Found ${data.length} tool(s).`);
    } else {
      setEditedToolJson('');
      setSuccessMessage('Conversion successful, but no tools were generated.');
    }
  };

  const handleSubmitDocToTool = async (e: FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (!docUrl) {
      setError({ message: 'API Documentation URL is required.' });
      return;
    }
    setIsLoading(true);
    try {
      const results = await convertDocToTool(docUrl);
      processConversionResponse(results);
    } catch (err: any) {
      setError({ message: err.message || 'Failed to convert API Doc URL.' });
      setToolDefinitions([]);
      setEditedToolJson('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitOpenApiLink = async (e: FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (!openapiLink) {
      setError({ message: 'OpenAPI Specification URL is required.' });
      return;
    }
    setIsLoading(true);
    try {
      const results = await convertOpenApiByLink(openapiLink);
      processConversionResponse(results);
    } catch (err: any) {
      setError({ message: err.message || 'Failed to convert OpenAPI URL.' });
      setToolDefinitions([]);
      setEditedToolJson('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitOpenApiFile = async (e: FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (!openapiFile) {
      setError({ message: 'OpenAPI Specification File is required.' });
      return;
    }
    setIsLoading(true);
    try {
      const results = await convertOpenApiByFile(openapiFile);
      processConversionResponse(results);
    } catch (err: any) {
      setError({ message: err.message || 'Failed to convert OpenAPI file.' });
      setToolDefinitions([]);
      setEditedToolJson('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSubmitPostmanFile = async (e: FormEvent) => {
    e.preventDefault();
    resetMessages();
    if (!postmanFile) {
      setError({ message: 'Postman Collection File is required.' });
      return;
    }
    setIsLoading(true);
    try {
      const results = await convertPostmanToTool(postmanFile);
      processConversionResponse(results);
    } catch (err: any) {
      setError({ message: err.message || 'Failed to convert Postman file.' });
      setToolDefinitions([]);
      setEditedToolJson('');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSaveToStaging = async () => {
    resetMessages();
    if (!editedToolJson) {
      setError({ message: 'No tool data to save.' });
      return;
    }
    let serviceData: ToolDefinition;
    try {
      serviceData = JSON.parse(editedToolJson);
    } catch (parseError) {
      setError({ message: 'Invalid JSON format in the editor.', details: parseError });
      return;
    }

    if (!serviceData.name || typeof serviceData.name !== 'string') {
        setError({ message: 'Tool data must have a "name" field of type string.' });
        return;
    }

    if (!tenantId) {
      setError({ message: 'Tenant not selected.' });
      return;
    }

    setIsLoading(true);
    try {
      const response = await addStagingService(tenantId, serviceData);
      setSuccessMessage(`Tool "${response.name}" (ID: ${response.id}) saved successfully to staging for tenant "${tenantId}".`);
      // Optionally, clear the current tool or refresh list of staged tools if displaying them
    } catch (err: any) {
      setError({ message: err.message || 'Failed to save tool to staging.' });
    } finally {
      setIsLoading(false);
    }
  };

  const handleNextTool = () => {
    if (currentToolIndex < toolDefinitions.length - 1) {
      const nextIndex = currentToolIndex + 1;
      setCurrentToolIndex(nextIndex);
      setEditedToolJson(JSON.stringify(toolDefinitions[nextIndex], null, 2));
    }
  };

  const handlePreviousTool = () => {
    if (currentToolIndex > 0) {
      const prevIndex = currentToolIndex - 1;
      setCurrentToolIndex(prevIndex);
      setEditedToolJson(JSON.stringify(toolDefinitions[prevIndex], null, 2));
    }
  };

  const renderForm = () => {
    switch (activeTab) {
      case 'doc':
        return (
          <form key="doc-form" onSubmit={handleSubmitDocToTool} className="space-y-4">
            <div>
              <label htmlFor="docUrl" className="block text-sm font-medium text-gray-700 dark:text-gray-700">
                API Documentation URL
              </label>
              <input
                type="url"
                name="docUrl"
                id="docUrl"
                value={docUrl}
                onChange={(e) => setDocUrl(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-neutral-900 bg-white"
                placeholder="https://api.example.com/docs"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Converting...' : 'Convert from Doc URL'}
            </button>
          </form>
        );
      case 'openapi-link':
        return (
          <form key="openapi-link-form" onSubmit={handleSubmitOpenApiLink} className="space-y-4">
            <div>
              <label htmlFor="openapiLink" className="block text-sm font-medium text-gray-700 dark:text-gray-700">
                OpenAPI Specification URL
              </label>
              <input
                type="url"
                name="openapiLink"
                id="openapiLink"
                value={openapiLink}
                onChange={(e) => setOpenapiLink(e.target.value)}
                className="mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-indigo-500 focus:border-indigo-500 sm:text-sm text-neutral-900 bg-white"
                placeholder="https://api.example.com/openapi.json"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Converting...' : 'Convert from OpenAPI URL'}
            </button>
          </form>
        );
      case 'openapi-file':
        return (
          <form key="openapi-file-form" onSubmit={handleSubmitOpenApiFile} className="space-y-4">
            <div>
              <label htmlFor="openapiFile" className="block text-sm font-medium text-gray-700 dark:text-gray-700">
                OpenAPI Specification File (.json, .yaml)
              </label>
              <input
                type="file"
                name="openapiFile"
                id="openapiFile"
                accept=".json,.yaml,.yml"
                onChange={handleFileChange(setOpenapiFile)}
                className="mt-1 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:text-gray-700 dark:file:bg-neutral-700 dark:file:text-indigo-300 dark:hover:file:bg-neutral-600"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !openapiFile}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Converting...' : 'Convert from OpenAPI File'}
            </button>
          </form>
        );
      case 'postman-file':
        return (
          <form key="postman-file-form" onSubmit={handleSubmitPostmanFile} className="space-y-4">
            <div>
              <label htmlFor="postmanFile" className="block text-sm font-medium text-gray-700 dark:text-gray-700">
                Postman Collection File (.json)
              </label>
              <input
                type="file"
                name="postmanFile"
                id="postmanFile"
                accept=".json"
                onChange={handleFileChange(setPostmanFile)}
                className="mt-1 block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-semibold file:bg-indigo-50 file:text-indigo-700 hover:file:bg-indigo-100 dark:text-gray-700 dark:file:bg-neutral-700 dark:file:text-indigo-300 dark:hover:file:bg-neutral-600"
              />
            </div>
            <button
              type="submit"
              disabled={isLoading || !postmanFile}
              className="w-full flex justify-center py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-indigo-600 hover:bg-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-500 disabled:opacity-50"
            >
              {isLoading ? 'Converting...' : 'Convert from Postman File'}
            </button>
          </form>
        );
      default:
        return null;
    }
  };

  const renderResults = () => {
    if (toolDefinitions.length === 0 && !isLoading && !error && !successMessage.includes("no tools")) {
      return null; // Don't show results section if no conversion attempted or no results yet (unless explicitly stated no tools found)
    }

    return (
      <div className="mt-8">
        <h2 className="text-xl font-semibold mb-4 text-gray-900 dark:text-gray-100">Conversion Results</h2>
        {isLoading && <p className="text-gray-700 dark:text-gray-300">Loading results...</p>}
        {toolDefinitions.length > 0 && (
          <div>
            <div className="mb-4">
              <div className="flex justify-between items-center mb-2">
                <p className="text-gray-700 dark:text-gray-300">
                  Displaying tool {currentToolIndex + 1} of {toolDefinitions.length}
                </p>
                <div className="flex space-x-2">
                  <button
                    onClick={handlePreviousTool}
                    disabled={currentToolIndex === 0 || isLoading}
                    className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
                  >
                    Previous
                  </button>
                  <button
                    onClick={handleNextTool}
                    disabled={currentToolIndex === toolDefinitions.length - 1 || isLoading}
                    className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
                  >
                    Next
                  </button>
                </div>
              </div>
              <ToolDefinitionUI
                pageType="staging"
                editedToolJson={editedToolJson}
                onEditedToolJsonChange={setEditedToolJson}
                onSaveToStaging={handleSaveToStaging}
                isLoading={isLoading}
                tenantName={tenantId || undefined}
                isAdminMode={isAdmin}
              />
            </div>
            <div className="flex justify-between items-center mb-4">
              <button
                onClick={handlePreviousTool}
                disabled={currentToolIndex === 0 || isLoading}
                className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
              >
                Previous
              </button>
              {/* Save to Staging button is now in ToolDefinitionUI */}
              <button
                onClick={handleNextTool}
                disabled={currentToolIndex === toolDefinitions.length - 1 || isLoading}
                className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-gray-600 hover:bg-gray-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-gray-500 disabled:opacity-50"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>
    );
  };

  return (
    <Layout> 
      <div className="container mx-auto p-4 md:p-8">
        <h1 className="text-2xl font-bold mb-6 text-center text-gray-900 dark:text-gray-100">API Importer</h1>

        {error && (
          <div className="mb-4 p-4 bg-red-100 border border-red-400 text-red-700 rounded">
            <p className="font-bold">Error:</p>
            <p>{error.message}</p>
            {error.details && <pre className="text-xs mt-2">{JSON.stringify(error.details, null, 2)}</pre>}
          </div>
        )}
        {successMessage && (
          <div
            ref={successMessageRef}
            className="mb-4 p-4 bg-green-100 border border-green-400 text-green-700 rounded"
          >
            {successMessage}
          </div>
        )}

        <div className="mb-6 border-b border-gray-200">
          <nav className="-mb-px flex space-x-8" aria-label="Tabs">
            {([
              { key: 'doc', label: 'API Doc URL' },
              { key: 'openapi-link', label: 'OpenAPI URL' },
              { key: 'openapi-file', label: 'OpenAPI File' },
              { key: 'postman-file', label: 'Postman Collection' },
            ] as const).map((tab) => (
              <button
                key={tab.key}
                onClick={() => { setActiveTab(tab.key); resetMessages(); setToolDefinitions([]); setEditedToolJson('');}}
                className={`${
                  activeTab === tab.key
                    ? 'border-indigo-500 text-indigo-600 dark:text-indigo-400'
                    : 'border-transparent text-gray-600 hover:text-gray-800 hover:border-gray-400 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:border-gray-500'
                } whitespace-nowrap py-4 px-1 border-b-2 font-medium text-sm`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>

        <div className="bg-white shadow-md rounded-lg p-6">
          {renderForm()}
        </div>

        {renderResults()}
      </div>
    </Layout>
  );
};

export default ToolImporterPage;
