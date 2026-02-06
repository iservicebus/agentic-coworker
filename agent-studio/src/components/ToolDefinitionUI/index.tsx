import React, { useState, useEffect, useCallback } from 'react';
import styles from './ToolDefinitionUI.module.css';
import StaticInputStructuredEditor from './StaticInputStructuredEditor';
import InputSchemaStructuredEditor from './InputSchemaStructuredEditor'; // Import the new component
import ServiceSecret from '../ServiceSecret';
import ToolTestUI from '../ToolTestUI';
import { registerMcpService, deleteMcpService, deleteStagingService, getAuthProviders, AuthProvider, annotateToolByLLM, ToolAnnotationResponse } from '@/lib/apiClient';
import { McpService } from '@/types/mcp';
import { useUserData } from "@/lib/contexts/UserDataContext";

interface ToolDefinition {
  name?: string;
  description?: string;
  appName?: string;
  transport?: string;
  tool_type?: string; // Added tool_type field
  staticInput?: object;
  inputSchema?: object;
  auth?: { provider?: string }; // Added auth field
  [key: string]: any; // Allow other properties
}

interface ToolDefinitionUIProps {
  editedToolJson: string;
  originalToolJson?: string;
  onEditedToolJsonChange: (json: string) => void;
  onSaveToStaging: () => Promise<void>;
  isLoading: boolean;
  pageType: 'mcp' | 'staging';
  serviceId?: string;
  onDeleteSuccess?: () => void;
  onRegisterSuccess?: () => void;
  tenantName?: string;
  agentId?: string;
  isAdminMode?: boolean;
}

const ToolDefinitionUI: React.FC<ToolDefinitionUIProps> = ({
  editedToolJson,
  originalToolJson,
  onEditedToolJsonChange,
  onSaveToStaging,
  isLoading,
  pageType,
  serviceId,
  onDeleteSuccess,
  onRegisterSuccess,
  tenantName: propTenantName,
  agentId: propAgentId,
  isAdminMode = false,
}) => {

  const { userData, isLoading: isUserLoading, error: userError } = useUserData();
  const tenantName = propTenantName || '';
  const agentId = propAgentId;
  const [parsedTool, setParsedTool] = useState<ToolDefinition>({});
  
  const [nameValue, setNameValue] = useState('');
  const [descriptionValue, setDescriptionValue] = useState('');
  const [appNameValue, setAppNameValue] = useState('');
  const [toolTypeValue, setToolTypeValue] = useState('general'); // Added for tool_type
  const [staticInputValue, setStaticInputValue] = useState(''); // Stores stringified JSON for staticInput
  const [inputSchemaValue, setInputSchemaValue] = useState(''); // Stores stringified JSON for inputSchema
  const [authProviderValue, setAuthProviderValue] = useState(''); // Added for auth provider

  const [isNameDescriptionEditing, setIsNameDescriptionEditing] = useState(false);
  const [isAppNameEditing, setIsAppNameEditing] = useState(false);
  const [isToolTypeEditing, setIsToolTypeEditing] = useState(false); // Added for tool_type editing state
  const [isStaticInputEditing, setIsStaticInputEditing] = useState(false);
  const [isInputSchemaEditing, setIsInputSchemaEditing] = useState(false);
  const [isAuthEditing, setIsAuthEditing] = useState(false); // Added for auth editing state

  const [staticInputEditUIMode, setStaticInputEditUIMode] = useState<'structured' | 'raw'>('structured');
  const [inputSchemaEditUIMode, setInputSchemaEditUIMode] = useState<'structured' | 'raw'>('structured');

  const [staticInputError, setStaticInputError] = useState<string | null>(null);
  const [inputSchemaError, setInputSchemaError] = useState<string | null>(null);
  const [nameError, setNameError] = useState<string | null>(null);
  const [isRegisteringMcp, setIsRegisteringMcp] = useState(false);
  const [showServiceSecret, setShowServiceSecret] = useState(false);
  const [showTestUI, setShowTestUI] = useState(false);
  const [savedToolJson, setSavedToolJson] = useState<string>('');
  const [availableProviders, setAvailableProviders] = useState<AuthProvider[]>([]);
  const [isLoadingProviders, setIsLoadingProviders] = useState(false);

  // Annotation state
  const [isAnnotating, setIsAnnotating] = useState(false);
  const [annotationResult, setAnnotationResult] = useState<ToolAnnotationResponse | null>(null);
  const [showAnnotationResult, setShowAnnotationResult] = useState(false);

  const updateParentJson = useCallback((updatedToolData: ToolDefinition) => {
    try {
      const newJson = JSON.stringify(updatedToolData, null, 2);
      onEditedToolJsonChange(newJson);
    } catch (error) {
      console.error("Failed to stringify tool data:", error);
    }
  }, [onEditedToolJsonChange]);

  useEffect(() => {
    if (!savedToolJson && editedToolJson) {
      setSavedToolJson(editedToolJson);
    }
    try {
      if (editedToolJson) {
        const parsed = JSON.parse(editedToolJson) as ToolDefinition;
        let toolDataToProcess = { ...parsed };
        let changed = false;

        if (toolDataToProcess.transport !== 'http') {
          toolDataToProcess.transport = 'http';
          changed = true;
        }
        
        // Debug logging to see what's in the parsed tool data
        console.log('Parsed tool data from editedToolJson:', {
          name: toolDataToProcess.name,
          id: toolDataToProcess.id,
          hasId: !!toolDataToProcess.id,
          fullData: toolDataToProcess
        });
        
        setParsedTool(toolDataToProcess);
        setNameValue(toolDataToProcess.name || '');
        setDescriptionValue(toolDataToProcess.description || '');
        setAppNameValue(toolDataToProcess.appName || '');
        setToolTypeValue(toolDataToProcess.tool_type || 'general'); // Initialize tool_type
        setStaticInputValue(toolDataToProcess.staticInput ? JSON.stringify(toolDataToProcess.staticInput, null, 2) : '{}');
        setInputSchemaValue(toolDataToProcess.inputSchema ? JSON.stringify(toolDataToProcess.inputSchema, null, 2) : '{}');
        setAuthProviderValue(toolDataToProcess.auth?.provider || ''); // Initialize auth provider
        
        if (changed) {
          updateParentJson(toolDataToProcess);
        }
      } else {
        const defaultTool: ToolDefinition = { transport: 'http' };
        setParsedTool(defaultTool);
        setNameValue('');
        setDescriptionValue('');
        setAppNameValue('');
        setStaticInputValue('{}');
        setInputSchemaValue('{}');
        setAuthProviderValue(''); // Reset auth provider
        updateParentJson(defaultTool);
      }
    } catch (error) {
      console.error("Error parsing editedToolJson:", error);
      const errorTool: ToolDefinition = { transport: 'http' };
      setParsedTool(errorTool);
      setNameValue('');
      setDescriptionValue('');
      setAppNameValue('');
      setStaticInputValue('{}');
      setInputSchemaValue('{}');
      setAuthProviderValue(''); // Reset auth provider on error
    }
  }, [editedToolJson, updateParentJson]);

  // Fetch available providers when component mounts or tenantName changes
  useEffect(() => {
    const fetchProviders = async () => {
      if (!tenantName) return;
      
      setIsLoadingProviders(true);
      try {
        const providers = await getAuthProviders(tenantName);
        setAvailableProviders(providers || []);
      } catch (error) {
        console.error('Failed to fetch auth providers:', error);
        setAvailableProviders([]);
      } finally {
        setIsLoadingProviders(false);
      }
    };

    fetchProviders();
  }, [tenantName]);

  const handleRegisterToMcp = async () => {
    if (!editedToolJson || staticInputError || inputSchemaError || nameError) {
      alert('Cannot register: Please ensure the tool definition is valid and all fields are correctly formatted.');
      return;
    }

    // Validate name before registering
    if (!validateName(parsedTool.name || '')) {
      alert('Cannot register: Name must contain only letters, numbers, underscores, dots, and hyphens.');
      return;
    }

    setIsRegisteringMcp(true);
    try {
      // Use parsedTool state directly as it reflects the latest changes made within the UI
      const toolDataToRegister: McpService = { ...parsedTool } as McpService; 

      if (!toolDataToRegister.name) {
          alert('Service name is required for registration.');
          setIsRegisteringMcp(false);
          return;
      }

      // For MCP services, if there's an existing ID in the original JSON, preserve it
      // This ensures the backend will update instead of insert
      if (pageType === 'mcp' && originalToolJson) {
        try {
          const originalTool = JSON.parse(originalToolJson);
          if (originalTool.id) {
            toolDataToRegister.id = originalTool.id;
          }
        } catch (e) {
          // If we can't parse originalToolJson, continue without the ID
          console.warn('Could not parse originalToolJson to extract ID:', e);
        }
      }

      // Also check if the current editedToolJson has an ID and preserve it
      if (!toolDataToRegister.id) {
        try {
          const currentTool = JSON.parse(editedToolJson);
          if (currentTool.id) {
            toolDataToRegister.id = currentTool.id;
          }
        } catch (e) {
          // If we can't parse editedToolJson, continue without the ID
          console.warn('Could not parse editedToolJson to extract ID:', e);
        }
      }

      // Debug logging to verify ID is being set
      console.log('Tool data being sent to backend:', {
        name: toolDataToRegister.name,
        id: toolDataToRegister.id,
        hasId: !!toolDataToRegister.id,
        fullPayload: toolDataToRegister
      });

      const response = await registerMcpService(toolDataToRegister, tenantName);
      alert(`Service "${response.service_name}" registered successfully: ${response.message}`);
      setSavedToolJson(editedToolJson);
      if (onRegisterSuccess) {
        onRegisterSuccess();
      }
    } catch (error: any) {
      console.error('Failed to register to MCP:', error);
      alert(`Failed to register to MCP: ${error.message || 'Unknown error'}`);
    } finally {
      setIsRegisteringMcp(false);
    }
  };

  const handleDelete = async () => {
    if (pageType === 'mcp') {
      if (!serviceId || !tenantName) {
        alert('Service ID or tenant not found.');
        return;
      }
      if (window.confirm(`Are you sure you want to delete the MCP service with ID "${serviceId}"?`)) {
        try {
          await deleteMcpService(tenantName, serviceId);
          alert('MCP service deleted successfully.');
          if (onDeleteSuccess) onDeleteSuccess();
        } catch (error: any) {
          alert(`Failed to delete MCP service: ${error.message}`);
        }
      }
    } else {
      if (!serviceId || !tenantName) {
        alert('Service ID or tenant not found.');
        return;
      }
      if (window.confirm(`Are you sure you want to delete the staging service with ID "${serviceId}"?`)) {
        try {
          await deleteStagingService(tenantName, serviceId);
          alert('Staging service deleted successfully.');
          if (onDeleteSuccess) onDeleteSuccess();
        } catch (error: any) {
          alert(`Failed to delete staging service: ${error.message}`);
        }
      }
    }
  };

  const handleAnnotateRecommendation = async () => {
    if (!nameValue.trim() || !descriptionValue.trim()) {
      alert('Please provide both name and description before requesting annotation.');
      return;
    }

    let inputSchema: Record<string, any>;
    try {
      inputSchema = inputSchemaValue ? JSON.parse(inputSchemaValue) : {};
    } catch (e) {
      alert('Invalid JSON format in Input Schema. Please fix it before requesting annotation.');
      return;
    }

    setIsAnnotating(true);
    setAnnotationResult(null);
    setShowAnnotationResult(false);

    try {
      const response = await annotateToolByLLM({
        name: nameValue.trim(),
        description: descriptionValue.trim(),
        inputSchema: inputSchema
      });

      setAnnotationResult(response);
      setShowAnnotationResult(true);
    } catch (error: any) {
      console.error('Failed to get annotation:', error);
      alert(`Failed to get annotation: ${error.message || 'Unknown error'}`);
    } finally {
      setIsAnnotating(false);
    }
  };

  const handleReplaceWithAnnotation = () => {
    if (!annotationResult?.success || !annotationResult.annotation_result) {
      alert('No valid annotation result available to replace with.');
      return;
    }

    // Extract the enhanced name and description from annotation result
    const enhancedName = annotationResult.annotation_result.name || nameValue;
    const enhancedDescription = annotationResult.annotation_result.description || descriptionValue;

    // Update the input values
    setNameValue(enhancedName);
    setDescriptionValue(enhancedDescription);

    // Hide the annotation result
    setShowAnnotationResult(false);
    setAnnotationResult(null);
  };

  const validateName = (name: string): boolean => {
    const namePattern = /^[a-zA-Z0-9_\.-]+$/;
    if (!name.trim()) {
      setNameError('Name is required.');
      return false;
    }
    if (!namePattern.test(name)) {
      setNameError('Name can only contain letters, numbers, underscores, dots, and hyphens.');
      return false;
    }
    setNameError(null);
    return true;
  };

  const handleSaveField = (field: keyof ToolDefinition) => {
    let newParsedToolData = { ...parsedTool, transport: 'http' };
    let isValid = true;

    if (field === 'name') {
      if (!validateName(nameValue)) {
        isValid = false;
      } else {
        newParsedToolData.name = nameValue;
      }
    } else if (field === 'description') {
      newParsedToolData.description = descriptionValue;
    } else if (field === 'appName') {
      newParsedToolData.appName = appNameValue;
    } else if (field === 'tool_type') {
      newParsedToolData.tool_type = toolTypeValue;
    } else if (field === 'staticInput') {
      try {
        newParsedToolData.staticInput = staticInputValue ? JSON.parse(staticInputValue) : undefined;
        setStaticInputError(null);
      } catch (e) {
        setStaticInputError('Invalid JSON format for Static Input.');
        isValid = false;
      }
    } else if (field === 'inputSchema') {
      try {
        newParsedToolData.inputSchema = inputSchemaValue ? JSON.parse(inputSchemaValue) : undefined;
        setInputSchemaError(null);
      } catch (e) {
        setInputSchemaError('Invalid JSON format for Input Schema.');
        isValid = false;
      }
    } else if (field === 'auth') {
      if (authProviderValue.trim() === '') {
        // If provider is empty, remove the auth object
        const { auth, ...rest } = newParsedToolData; // eslint-disable-line @typescript-eslint/no-unused-vars
        newParsedToolData = rest;
      } else {
        newParsedToolData.auth = { provider: authProviderValue.trim() };
      }
    }
    
    if (isValid) {
      setParsedTool(newParsedToolData);
      updateParentJson(newParsedToolData);
      // Exit editing mode for the saved field
      if (field === 'name' || field === 'description') setIsNameDescriptionEditing(false);
      else if (field === 'appName') setIsAppNameEditing(false);
      else if (field === 'tool_type') setIsToolTypeEditing(false);
      else if (field === 'staticInput') setIsStaticInputEditing(false);
      else if (field === 'inputSchema') setIsInputSchemaEditing(false);
      else if (field === 'auth') setIsAuthEditing(false);
    }
  };

  const renderEditableBlock = (
    label: string,
    // valueForViewMode: string, // This is the stringified JSON for pre/p tags
    currentEditingValue: string, // This is the state variable (nameValue, descriptionValue, staticInputValue, inputSchemaValue)
    onEditingValueChange: (val: string) => void, // This is the setter for the state variable
    isEditing: boolean,
    setIsEditing: (editing: boolean) => void,
    fieldKey: keyof ToolDefinition,
    errorForField: string | null,
    isJsonField = false
  ) => {
    const isStructuredModeRelevant = isJsonField; // Structured mode only for JSON fields
    const currentUIMode = fieldKey === 'staticInput' ? staticInputEditUIMode : inputSchemaEditUIMode;
    const setUIMode = fieldKey === 'staticInput' ? setStaticInputEditUIMode : setInputSchemaEditUIMode;

    // Determine value for view mode based on parsedTool
    let viewDisplayValue: string;
    if (fieldKey === 'name') viewDisplayValue = parsedTool.name || 'Not set';
    else if (fieldKey === 'description') viewDisplayValue = parsedTool.description || 'Not set';
    else if (fieldKey === 'appName') viewDisplayValue = parsedTool.appName || 'Not set';
    else if (fieldKey === 'staticInput') viewDisplayValue = parsedTool.staticInput ? JSON.stringify(parsedTool.staticInput, null, 2) : '{}';
    else if (fieldKey === 'inputSchema') viewDisplayValue = parsedTool.inputSchema ? JSON.stringify(parsedTool.inputSchema, null, 2) : '{}';
    else viewDisplayValue = 'Not set';


    return (
      <div className={styles.block}>
        <div className={styles.blockHeader}>
          <h3>{label}</h3>
          <div className={styles.blockControls}>
            {isStructuredModeRelevant && isEditing && (
              <div className={styles.modeToggle}>
                <button
                  onClick={() => setUIMode('structured')}
                  className={`${styles.modeButton} ${currentUIMode === 'structured' ? styles.activeMode : ''}`}
                  disabled={currentUIMode === 'structured'}
                >
                  UI
                </button>
                <button
                  onClick={() => setUIMode('raw')}
                  className={`${styles.modeButton} ${currentUIMode === 'raw' ? styles.activeMode : ''}`}
                  disabled={currentUIMode === 'raw'}
                >
                  JSON
                </button>
              </div>
            )}
            {isEditing ? (
              <>
                <button
                  onClick={() => handleSaveField(fieldKey)}
                  className={styles.editButton} // Assuming styles.editButton can be used for "Save"
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setIsEditing(false);
                    // Reset values to what's in parsedTool to discard un-saved changes
                    if (fieldKey === 'name') onEditingValueChange(parsedTool.name || '');
                    else if (fieldKey === 'description') onEditingValueChange(parsedTool.description || '');
                    else if (fieldKey === 'appName') onEditingValueChange(parsedTool.appName || '');
                    else if (fieldKey === 'staticInput') {
                      onEditingValueChange(parsedTool.staticInput ? JSON.stringify(parsedTool.staticInput, null, 2) : '{}');
                      setStaticInputError(null); // Clear any errors
                    } else if (fieldKey === 'inputSchema') {
                      onEditingValueChange(parsedTool.inputSchema ? JSON.stringify(parsedTool.inputSchema, null, 2) : '{}');
                      setInputSchemaError(null); // Clear any errors
                    }
                  }}
                  className={styles.cancelButton} // You'll need to define styles.cancelButton
                  style={{ marginLeft: '8px' }} // Basic spacing, ideally handle in CSS
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  // When starting to edit, populate the editing state with current values from parsedTool
                  if (fieldKey === 'name') onEditingValueChange(parsedTool.name || '');
                  else if (fieldKey === 'description') onEditingValueChange(parsedTool.description || '');
                  else if (fieldKey === 'appName') onEditingValueChange(parsedTool.appName || '');
                  else if (fieldKey === 'staticInput') {
                    onEditingValueChange(parsedTool.staticInput ? JSON.stringify(parsedTool.staticInput, null, 2) : '{}');
                    setStaticInputEditUIMode('structured'); // Default to UI mode
                  } else if (fieldKey === 'inputSchema') {
                    onEditingValueChange(parsedTool.inputSchema ? JSON.stringify(parsedTool.inputSchema, null, 2) : '{}');
                    setInputSchemaEditUIMode('structured'); // Default to UI mode
                  }
                  setIsEditing(true);
                }}
                className={styles.editButton}
              >
                {fieldKey === 'appName' ? 'Overwrite' : 'Edit'}
              </button>
            )}
          </div>
        </div>
        {isEditing ? (
          isJsonField ? (
            currentUIMode === 'raw' ? (
              <textarea
                value={currentEditingValue}
                onChange={(e) => onEditingValueChange(e.target.value)}
                rows={10}
                className={`${styles.textarea} ${errorForField ? styles.textareaError : ''}`}
              />
            ) : (
              // Placeholder for Structured Editor
              fieldKey === 'staticInput' ? (
                <StaticInputStructuredEditor
                  initialValue={parsedTool.staticInput || {}}
                  onChange={(updatedStaticInputObject) => {
                    const newStaticInputString = JSON.stringify(updatedStaticInputObject, null, 2);
                    onEditingValueChange(newStaticInputString); // Updates staticInputValue
                    // Also update parsedTool directly here for consistency if save is not immediate
                    // setParsedTool(prev => ({...prev, staticInput: updatedStaticInputObject}));
                  }}
                />
              ) : (  // fieldKey === 'inputSchema'
                <InputSchemaStructuredEditor
                  initialValue={parsedTool.inputSchema || { type: 'object', properties: {} }}
                  onChange={(updatedInputSchemaObject) => {
                    const newInputSchemaString = JSON.stringify(updatedInputSchemaObject, null, 2);
                    onEditingValueChange(newInputSchemaString); // Updates inputSchemaValue
                  }}
                />
              )
            )
          ) : label === 'Description' ? (
            <textarea
              value={currentEditingValue}
              onChange={(e) => onEditingValueChange(e.target.value)}
              rows={5}
              className={styles.textarea}
            />
          ) : ( // For 'Name' or other simple text fields
            <input
              type="text"
              value={currentEditingValue}
              onChange={(e) => onEditingValueChange(e.target.value)}
              className={styles.input}
            />
          )
        ) : ( // View mode
          isJsonField ? (
            <pre className={styles.preformattedText}>{viewDisplayValue}</pre>
          ) : (
            <p className={styles.displayValue}>{viewDisplayValue}</p>
          )
        )}
        {errorForField && isEditing && (!isJsonField || currentUIMode === 'raw') && <p className={styles.errorMessage}>{errorForField}</p>}
      </div>
    );
  };

  return (
    <div className={styles.container}>
      {/* Combined Name & Description Section */}
      <div className={styles.block}>
        <div className={styles.blockHeader}>
          <h3>Name & Description</h3>
          <div className={styles.blockControls}>
            {isNameDescriptionEditing ? (
              <>
                <button
                  onClick={() => {
                    // Validate name before saving
                    if (!validateName(nameValue)) {
                      return; // Don't save if validation fails
                    }
                    
                    // Save both name and description
                    let newParsedToolData = { ...parsedTool, transport: 'http' };
                    newParsedToolData.name = nameValue;
                    newParsedToolData.description = descriptionValue;
                    
                    setParsedTool(newParsedToolData);
                    updateParentJson(newParsedToolData);
                    setIsNameDescriptionEditing(false);
                  }}
                  className={styles.editButton}
                >
                  Save
                </button>
                <button
                onClick={() => {
                  setIsNameDescriptionEditing(false);
                  // Reset values to what's in parsedTool to discard un-saved changes
                  setNameValue(parsedTool.name || '');
                  setDescriptionValue(parsedTool.description || '');
                  setNameError(null); // Clear error on cancel
                }}
                  className={styles.cancelButton}
                  style={{ marginLeft: '8px' }}
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => {
                  // When starting to edit, populate the editing state with current values from parsedTool
                  setNameValue(parsedTool.name || '');
                  setDescriptionValue(parsedTool.description || '');
                  setIsNameDescriptionEditing(true);
                }}
                className={styles.editButton}
              >
                Edit
              </button>
            )}
          </div>
        </div>
        {isNameDescriptionEditing ? (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <label className={styles.fieldLabel}>Name:</label>
              <input
                type="text"
                value={nameValue}
                onChange={(e) => setNameValue(e.target.value)}
                className={`${styles.input} ${nameError ? styles.textareaError : ''}`}
                placeholder="Enter tool name"
              />
              {nameError && <p className={styles.errorMessage}>{nameError}</p>}
            </div>
            <div>
              <label className={styles.fieldLabel}>Description:</label>
              <textarea
                value={descriptionValue}
                onChange={(e) => setDescriptionValue(e.target.value)}
                rows={5}
                className={styles.textarea}
                placeholder="Enter tool description"
              />
            </div>
            
            {/* Annotation Button */}
            <div style={{ marginTop: '1rem' }}>
              <button
                onClick={handleAnnotateRecommendation}
                disabled={isAnnotating || !nameValue.trim() || !descriptionValue.trim()}
                className={styles.editButton}
                style={{ 
                  backgroundColor: '#8b5cf6', 
                  borderColor: '#8b5cf6',
                  opacity: (isAnnotating || !nameValue.trim() || !descriptionValue.trim()) ? 0.6 : 1
                }}
              >
                {isAnnotating ? 'Getting Annotation...' : 'Recommend Annotation'}
              </button>
              
              {/* Progress Indicator */}
              {isAnnotating && (
                <div style={{ marginTop: '0.5rem', display: 'flex', alignItems: 'center' }}>
                  <div style={{
                    width: '16px',
                    height: '16px',
                    border: '2px solid #e5e7eb',
                    borderTop: '2px solid #8b5cf6',
                    borderRadius: '50%',
                    animation: 'spin 1s linear infinite',
                    marginRight: '8px'
                  }}></div>
                  <span style={{ fontSize: '0.875rem', color: '#6b7280' }}>
                    Processing annotation request...
                  </span>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div>
            <div style={{ marginBottom: '1rem' }}>
              <label className={styles.fieldLabel}>Name:</label>
              <p className={styles.displayValue}>{parsedTool.name || 'Not set'}</p>
            </div>
            <div>
              <label className={styles.fieldLabel}>Description:</label>
              <p className={styles.displayValue}>{parsedTool.description || 'Not set'}</p>
            </div>
          </div>
        )}
      </div>

      {/* Annotation Results Section */}
      {showAnnotationResult && annotationResult && (
        <div className={styles.block}>
          <div className={styles.blockHeader}>
            <h3>Annotation Results</h3>
            <div className={styles.blockControls}>
              {annotationResult.success && annotationResult.annotation_result && (
                <button
                  onClick={handleReplaceWithAnnotation}
                  className={styles.editButton}
                  style={{ 
                    backgroundColor: '#10b981', 
                    borderColor: '#10b981'
                  }}
                >
                  Replace with Annotation
                </button>
              )}
              <button
                onClick={() => {
                  setShowAnnotationResult(false);
                  setAnnotationResult(null);
                }}
                className={styles.cancelButton}
                style={{ marginLeft: '8px' }}
              >
                Close
              </button>
            </div>
          </div>
          
          {annotationResult.success ? (
            <div>
              {annotationResult.annotation_result && (
                <div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label className={styles.fieldLabel}>Enhanced Name:</label>
                    <p className={styles.displayValue}>
                      {annotationResult.annotation_result.name || 'No enhanced name provided'}
                    </p>
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label className={styles.fieldLabel}>Enhanced Description:</label>
                    <p className={styles.displayValue}>
                      {annotationResult.annotation_result.description || 'No enhanced description provided'}
                    </p>
                  </div>
                  
                  {/* Show full annotation result if available */}
                  {Object.keys(annotationResult.annotation_result).length > 2 && (
                    <div style={{ marginTop: '1rem' }}>
                      <label className={styles.fieldLabel}>Full Annotation Result:</label>
                      <pre className={styles.preformattedText}>
                        {JSON.stringify(annotationResult.annotation_result, null, 2)}
                      </pre>
                    </div>
                  )}
                </div>
              )}
            </div>
          ) : (
            <div>
              <p style={{ color: '#dc2626', marginBottom: '1rem' }}>
                Annotation failed: {annotationResult.error_message || 'Unknown error'}
              </p>
              <div style={{ marginBottom: '1rem' }}>
                <label className={styles.fieldLabel}>Original Name:</label>
                <p className={styles.displayValue}>{nameValue}</p>
              </div>
              <div>
                <label className={styles.fieldLabel}>Original Description:</label>
                <p className={styles.displayValue}>{descriptionValue}</p>
              </div>
            </div>
          )}
        </div>
      )}
      
      {/* Tool Type Section - Only show Edit button if admin */}
      <div className={styles.block}>
        <div className={styles.blockHeader}>
          <h3>Tool Type</h3>
          <div className={styles.blockControls}>
            {isAdminMode && (
              <>
                {isToolTypeEditing ? (
                  <>
                    <button
                      onClick={() => handleSaveField('tool_type')}
                      className={styles.editButton}
                    >
                      Save
                    </button>
                    <button
                      onClick={() => {
                        setToolTypeValue(parsedTool.tool_type || 'general');
                        setIsToolTypeEditing(false);
                      }}
                      className={styles.cancelButton}
                      style={{ marginLeft: '8px' }}
                    >
                      Cancel
                    </button>
                  </>
                ) : (
                  <button
                    onClick={() => {
                      setToolTypeValue(parsedTool.tool_type || 'general');
                      setIsToolTypeEditing(true);
                    }}
                    className={styles.editButton}
                  >
                    Edit
                  </button>
                )}
              </>
            )}
          </div>
        </div>
        {isToolTypeEditing ? (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <label htmlFor="toolTypeSelect" className={styles.fieldLabel} style={{ marginRight: '8px' }}>Type:</label>
            <select
              id="toolTypeSelect"
              value={toolTypeValue}
              onChange={(e) => setToolTypeValue(e.target.value)}
              className={styles.input}
              style={{ flexGrow: 1 }}
            >
              <option value="general">General</option>
              <option value="system">System</option>
            </select>
          </div>
        ) : (
          <p className={styles.displayValue}>
            {parsedTool.tool_type || 'general'}
          </p>
        )}
      </div>

      {/* Auth Section */}
      <div className={styles.block}>
        <div className={styles.blockHeader}>
        <div>
          <h3>OAuth Provider</h3>
          <p className={styles.displayValue}>
          If your application API is protected with OAuth, please add the OAuth provider here
          </p>
    </div>
          <div className={styles.blockControls}>
            {isAuthEditing ? (
              <>
                <button
                  onClick={() => handleSaveField('auth')}
                  className={styles.editButton}
                >
                  Save
                </button>
                <button
                  onClick={() => {
                    setAuthProviderValue(parsedTool.auth?.provider || '');
                    setIsAuthEditing(false);
                  }}
                  className={styles.cancelButton}
                  style={{ marginLeft: '8px' }}
                >
                  Cancel
                </button>
                {/* Show delete if editing an existing provider or if there's text in the input during add */}
                {(parsedTool.auth?.provider || authProviderValue.trim() !== '') && (
                  <button
                    onClick={() => {
                      setAuthProviderValue(''); // Clear the input field for UI consistency if editing is reopened

                      // Directly update the parsedTool state to remove the auth field
                      const newToolState = { ...parsedTool };
                      delete newToolState.auth; // Remove the auth property
                      
                      setParsedTool(newToolState);
                      updateParentJson(newToolState);
                      setIsAuthEditing(false); // Exit editing mode
                    }}
                    className={styles.deleteButton} // Ensure styles.deleteButton is defined
                    style={{ marginLeft: '8px', backgroundColor: '#dc3545', color: 'white' }}
                  >
                    Delete
                  </button>
                )}
              </>
            ) : (
              <button
                onClick={() => {
                  setAuthProviderValue(parsedTool.auth?.provider || '');
                  setIsAuthEditing(true);
                }}
                className={styles.editButton}
              >
                {parsedTool.auth?.provider ? 'Edit' : 'Add Provider'}
              </button>
            )}
          </div>
        </div>
        {isAuthEditing ? (
          <div style={{ display: 'flex', alignItems: 'center' }}>
            <label htmlFor="authProviderSelect" className={styles.nameLabel} style={{ marginRight: '8px' }}>Provider:</label>
            {isLoadingProviders ? (
              <div style={{ flexGrow: 1, padding: '8px' }}>Loading providers...</div>
            ) : (
              <select
                id="authProviderSelect"
                value={authProviderValue}
                onChange={(e) => setAuthProviderValue(e.target.value)}
                className={styles.input}
                style={{ flexGrow: 1 }}
              >
                <option value="">Select a provider...</option>
                {availableProviders.map((provider) => (
                  <option key={provider.provider_id} value={provider.provider_id}>
                    {provider.provider_id}
                  </option>
                ))}
              </select>
            )}
          </div>
        ) : parsedTool.auth?.provider ? (
          <p className={styles.displayValue}>
            provider: {parsedTool.auth.provider}
          </p>
        ) : (
          <p className={styles.displayValue}>No authorization provider set.</p>
        )}
      </div>

      {renderEditableBlock('Static Input', staticInputValue, setStaticInputValue, isStaticInputEditing, setIsStaticInputEditing, 'staticInput', staticInputError, true)}
      {agentId && (
      <div className={styles.block}>
        <div className={styles.blockHeader}>
          <h3>Application API Keys</h3>
        </div>
        <p className={styles.displayValue}>
        If your application API keys are not yet added, you can add them here. If they are already added, you can update them as needed. The left-side menu, 'App API Keys,' lists all the keys.          {parsedTool.staticInput && /(authorization|api key|token)/i.test(JSON.stringify(parsedTool.staticInput)) &&
            <span style={{ color: 'red', marginLeft: '5px' }}>
              Note: If your application API credentials are currently in the static input, please remove them from there and add them here instead.
            </span>
          }
        </p>

        <button
          onClick={() => setShowServiceSecret(true)}
          className={styles.editButton}
          style={{ marginTop: '10px' }}
        >
          Add API Keys
        </button>
        {showServiceSecret && (
          <div style={{ marginTop: '20px' }}>
            <ServiceSecret
              appName={appNameValue}
              isNew={true}
              onSaveSuccess={() => setShowServiceSecret(false)}
              onDeleteSuccess={() => setShowServiceSecret(false)}
              onCancel={() => setShowServiceSecret(false)}
              agentId={agentId}
              tenantName={tenantName}
            />
          </div>
        )}
      </div>
      )}
      {renderEditableBlock('Input Schema', inputSchemaValue, setInputSchemaValue, isInputSchemaEditing, setIsInputSchemaEditing, 'inputSchema', inputSchemaError, true)}
      
      <div className={styles.block}>
        <h3>Transport</h3>
        <p className={styles.displayValue}>http (default, not editable)</p>
      </div>

      <div className="mt-6 flex justify-end space-x-3">
        {pageType === 'mcp' && (
          <button
            onClick={async () => {
              if (isInputSchemaEditing || isStaticInputEditing || isAuthEditing || isAppNameEditing || isNameDescriptionEditing) {
                alert('Please save all changes before testing.');
                return;
              }
              
              if (originalToolJson !== editedToolJson) {
                alert('You have unpublished changes. Please register the service to the MCP before testing.');
                return;
              }

              setShowTestUI(!showTestUI);
            }}
            className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-yellow-600 hover:bg-yellow-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-yellow-500 disabled:opacity-50"
          >
            {showTestUI ? 'Hide Test' : 'Test'}
          </button>
        )}
        <button
          onClick={async () => {
            // Validate name before saving
            if (!validateName(parsedTool.name || '')) {
              alert('Cannot save: Name must contain only letters, numbers, underscores, dots, and hyphens.');
              return;
            }
            await onSaveToStaging();
            setSavedToolJson(editedToolJson);
          }}
          disabled={isLoading || isRegisteringMcp || !editedToolJson || !!staticInputError || !!inputSchemaError || !!nameError}
          className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-green-600 hover:bg-green-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-green-500 disabled:opacity-50"
        >
          {isLoading ? 'Saving...' : 'Save to Staging'}
        </button>
        <button
          onClick={handleRegisterToMcp}
          disabled={isLoading || isRegisteringMcp || !editedToolJson || !!staticInputError || !!inputSchemaError || !!nameError}
          className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {isRegisteringMcp ? 'Registering...' : 'Register to MCP'}
        </button>
        <button
          onClick={handleDelete}
          disabled={isLoading || isRegisteringMcp}
          className="py-2 px-4 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-red-600 hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-500 disabled:opacity-50"
        >
          {pageType === 'mcp' ? 'Delete MCP Service' : 'Delete Staging Service'}
        </button>
      </div>
      {showTestUI && <ToolTestUI toolDefinition={parsedTool} agentId={agentId} />}
    </div>
  );
};

export default ToolDefinitionUI;
