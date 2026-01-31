import React, { useState, useEffect } from 'react';
import styles from './ToolTestUI.module.css';
import { validateMcpService } from '@/lib/apiClient';
import { useUserData } from '@/lib/contexts/UserDataContext';

interface ToolDefinition {
  name?: string;
  description?: string;
  appName?: string;
  transport?: string;
  staticInput?: object;
  inputSchema?: object;
  auth?: { provider?: string };
  [key: string]: any;
}

interface ToolTestUIProps {
  toolDefinition: ToolDefinition;
  agentId?: string;
}

const ToolTestUI: React.FC<ToolTestUIProps> = ({ toolDefinition, agentId: propAgentId }) => {
  const [sampleData, setSampleData] = useState('');
  const [agentId, setAgentId] = useState(propAgentId || '');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [testResult, setTestResult] = useState<any | null>(null);
  const [testError, setTestError] = useState<string | null>(null);

  // Update agentId when prop changes
  useEffect(() => {
    if (propAgentId) {
      setAgentId(propAgentId);
    }
  }, [propAgentId]);

  const handleTestService = async () => {
    if (!toolDefinition.name) {
      setTestError("Tool definition name is missing.");
      return;
    }
    try {
      const data = JSON.parse(sampleData);
      const result = await validateMcpService(toolDefinition.name, data, agentId || undefined);
      setTestResult(result);
      setTestError(null);
    } catch (e: any) {
      setTestError(e.message || "Failed to test service.");
      setTestResult(null);
    }
  };

  useEffect(() => {
    const fetchSampleData = async () => {
      if (!toolDefinition.inputSchema || Object.keys(toolDefinition.inputSchema).length === 0) {
        setSampleData('{}');
        setError(null);
        return;
      }

      setIsLoading(true);
      setError(null);
      try {
        const response = await fetch('/api/generate-sample', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(toolDefinition.inputSchema),
        });

        if (!response.ok) {
          const errorText = await response.text();
          throw new Error(errorText || 'Failed to generate sample data.');
        }

        const data = await response.json();
        setSampleData(JSON.stringify(data, null, 2));
      } catch (error: any) {
        setError(`Error: ${error.message}`);
        setSampleData('');
      } finally {
        setIsLoading(false);
      }
    };

    fetchSampleData();
  }, [toolDefinition]);

  return (
    <div className={styles.container}>
      {isLoading && <p>Generating sample data...</p>}
      {error && <p className={styles.error}>{error}</p>}
      
      {/* Agent ID Input Field */}
      <div style={{ 
        marginBottom: '1rem', 
        padding: '1rem', 
        backgroundColor: '#f3f4f6', 
        borderRadius: '8px',
        border: '1px solid #d1d5db'
      }}>
        <label htmlFor="agentIdInput" style={{ 
          display: 'block', 
          marginBottom: '0.5rem', 
          fontWeight: 'bold',
          color: '#374151',
          fontSize: '0.875rem'
        }}>
          Agent ID (Optional):
        </label>
        <input
          id="agentIdInput"
          type="text"
          value={agentId}
          onChange={(e) => setAgentId(e.target.value)}
          placeholder="Enter agent ID or leave empty"
          style={{
            width: '100%',
            padding: '0.5rem',
            border: '1px solid #9ca3af',
            borderRadius: '4px',
            fontSize: '0.875rem',
            backgroundColor: '#ffffff',
            color: '#1f2937'
          }}
        />
        <p style={{ 
          fontSize: '0.75rem', 
          color: '#6b7280', 
          marginTop: '0.5rem',
          fontStyle: 'italic'
        }}>
          If not specified, the default agent from your session will be used.
        </p>
      </div>

      <textarea
        value={sampleData}
        onChange={(e) => setSampleData(e.target.value)}
        rows={15}
        className={styles.textarea}
        placeholder={`Generated sample data will appear here...\nYou may omit the "body" field for testing, or set "body": null/None if needed.`}
        readOnly={isLoading || !!error}
      />
      <button onClick={handleTestService} className={styles.button}>
        Test MCP Service
      </button>
      {testResult && (
        <div className={styles.result}>
          <h4>Test Result:</h4>
          <JsonViewer data={testResult} />
          <details>
            <summary>Raw JSON</summary>
            <pre>{JSON.stringify(testResult, null, 2)}</pre>
          </details>
        </div>
      )}
      {testError && (
        <div className={styles.error}>
          <h4>Test Error:</h4>
          <p>{testError}</p>
        </div>
      )}
    </div>
  );
};

/**
 * Recursively renders structured JSON data as nested lists.
 */
const JsonViewer: React.FC<{ data: any }> = ({ data }) => {
  if (data === null) return <span style={{ color: '#888' }}>null</span>;
  if (Array.isArray(data)) {
    return (
      <ul style={{ paddingLeft: 20, listStyleType: 'decimal' }}>
        {data.map((item, idx) => (
          <li key={idx}><JsonViewer data={item} /></li>
        ))}
      </ul>
    );
  }
  if (typeof data === 'object') {
    return (
      <ul style={{ paddingLeft: 20, listStyleType: 'none' }}>
        {Object.entries(data).map(([key, value]) => (
          <li key={key}>
            <strong>{key}:</strong> <JsonViewer data={value} />
          </li>
        ))}
      </ul>
    );
  }
  if (typeof data === 'string') {
    return <span style={{ color: '#0a0' }}>"{data}"</span>;
  }
  if (typeof data === 'number') {
    return <span style={{ color: '#00a' }}>{data}</span>;
  }
  if (typeof data === 'boolean') {
    return <span style={{ color: '#a00' }}>{data ? 'true' : 'false'}</span>;
  }
  return <span>{String(data)}</span>;
};

export default ToolTestUI;
