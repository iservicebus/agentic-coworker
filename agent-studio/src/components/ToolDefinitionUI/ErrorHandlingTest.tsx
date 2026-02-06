// This is a test component to verify error handling in ToolDefinitionUI
// This file can be removed after testing is complete

import React, { useState } from 'react';
import { registerMcpService, deleteMcpService, getAuthProviders, annotateToolByLLM } from '@/lib/apiClient';

const ErrorHandlingTest: React.FC = () => {
  const [testResult, setTestResult] = useState<string>('');

  const testRegisterMcpServiceError = async () => {
    try {
      // This should trigger an error due to invalid data
      await registerMcpService({} as any, 'invalid-tenant', true);
      setTestResult('ERROR: Should have thrown an exception');
    } catch (error: any) {
      setTestResult(`SUCCESS: Caught error - ${error.message}`);
      alert(`Register MCP Service Error Test: ${error.message}`);
    }
  };

  const testDeleteMcpServiceError = async () => {
    try {
      // This should trigger a 404 error
      await deleteMcpService('invalid-tenant', 'non-existent-service-id');
      setTestResult('ERROR: Should have thrown an exception');
    } catch (error: any) {
      setTestResult(`SUCCESS: Caught error - ${error.message}`);
      alert(`Delete MCP Service Error Test: ${error.message}`);
    }
  };

  const testGetAuthProvidersError = async () => {
    try {
      // This should trigger an error due to invalid tenant
      await getAuthProviders('non-existent-tenant-12345');
      setTestResult('ERROR: Should have thrown an exception');
    } catch (error: any) {
      setTestResult(`SUCCESS: Caught error - ${error.message}`);
      alert(`Get Auth Providers Error Test: ${error.message}`);
    }
  };

  const testAnnotateToolError = async () => {
    try {
      // This should trigger an error due to invalid data
      await annotateToolByLLM({
        name: '',
        description: '',
        inputSchema: {}
      });
      setTestResult('ERROR: Should have thrown an exception');
    } catch (error: any) {
      setTestResult(`SUCCESS: Caught error - ${error.message}`);
      alert(`Annotate Tool Error Test: ${error.message}`);
    }
  };

  return (
    <div style={{ padding: '20px', border: '1px solid #ccc', margin: '20px' }}>
      <h3>Error Handling Test Component</h3>
      <p>This component tests that API errors are properly caught and displayed.</p>
      
      <div style={{ marginBottom: '10px' }}>
        <button onClick={testRegisterMcpServiceError} style={{ marginRight: '10px' }}>
          Test Register MCP Service Error
        </button>
        <button onClick={testDeleteMcpServiceError} style={{ marginRight: '10px' }}>
          Test Delete MCP Service Error
        </button>
        <button onClick={testGetAuthProvidersError} style={{ marginRight: '10px' }}>
          Test Get Auth Providers Error
        </button>
        <button onClick={testAnnotateToolError}>
          Test Annotate Tool Error
        </button>
      </div>
      
      {testResult && (
        <div style={{ 
          padding: '10px', 
          backgroundColor: testResult.startsWith('SUCCESS') ? '#d4edda' : '#f8d7da',
          border: `1px solid ${testResult.startsWith('SUCCESS') ? '#c3e6cb' : '#f5c6cb'}`,
          borderRadius: '4px',
          marginTop: '10px'
        }}>
          <strong>Test Result:</strong> {testResult}
        </div>
      )}
      
      <div style={{ marginTop: '20px', fontSize: '12px', color: '#666' }}>
        <strong>Note:</strong> This test component can be removed after verifying error handling works correctly.
        Each button will trigger an API call that should fail and display an alert with the error message.
      </div>
    </div>
  );
};

export default ErrorHandlingTest;
