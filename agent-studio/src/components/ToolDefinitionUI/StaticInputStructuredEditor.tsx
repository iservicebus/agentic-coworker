import React, { useState, useEffect } from 'react';
import styles from './ToolDefinitionUI.module.css'; // Reuse styles

interface StaticInput {
  method?: string;
  url?: {
    protocol?: string;
    host?: string[];
    port?: string;
    path?: string[];
    query?: { [key: string]: string };
  };
  headers?: { [key: string]: string };
  [key: string]: any; // Allow other properties, but UI will focus on known ones
}

interface StaticInputStructuredEditorProps {
  initialValue: StaticInput;
  onChange: (newValue: StaticInput) => void;
}

const httpMethods = ["GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"];
const protocols = ["http", "https"];

const StaticInputStructuredEditor: React.FC<StaticInputStructuredEditorProps> = ({ initialValue, onChange }) => {
  const [method, setMethod] = useState(initialValue.method || 'GET');
  const [protocol, setProtocol] = useState(initialValue.url?.protocol || 'http');
  const [hostSegments, setHostSegments] = useState<string[]>(initialValue.url?.host || []);
  const [port, setPort] = useState(initialValue.url?.port || '');
  const [pathSegments, setPathSegments] = useState<string[]>(initialValue.url?.path || []);
  const [headers, setHeaders] = useState<{ key: string; value: string }[]>(
    Object.entries(initialValue.headers || {}).map(([key, value]) => ({ key, value }))
  );
  // State for custom top-level fields
  const [customFields, setCustomFields] = useState<{ key: string; value: string }[]>(() => {
    const { method, url, headers, ...rest } = initialValue;
    // Ensure only string values are initially set for simplicity in this UI
    return Object.entries(rest)
      .filter(([_, val]) => typeof val === 'string' || typeof val === 'number' || typeof val === 'boolean')
      .map(([key, value]) => ({ key, value: String(value) }));
  });

  // Propagate changes to parent
  useEffect(() => {
    const customFieldsObject = customFields.reduce((acc, curr) => {
      if (curr.key.trim() !== '') {
        // Attempt to parse numbers and booleans, otherwise keep as string
        let val: any = curr.value;
        if (!isNaN(parseFloat(val)) && isFinite(val as any)) {
            val = parseFloat(val);
        } else if (val.toLowerCase() === 'true') {
            val = true;
        } else if (val.toLowerCase() === 'false') {
            val = false;
        }
        acc[curr.key.trim()] = val;
      }
      return acc;
    }, {} as { [key: string]: any });

    // Start with a base that includes everything from initialValue not managed by this UI's main state
    const { 
        method: _m, url: _u, headers: _h, // these are managed by dedicated state
        ...otherInitialFields 
    } = initialValue || {};


    const combinedStaticInput: StaticInput = {
      ...otherInitialFields, // Other fields from initialValue
      ...customFieldsObject, // Custom fields added/edited in UI
      method,                 // UI managed method
      headers: headers.reduce((acc, curr) => { // UI managed headers
        if (curr.key.trim() !== '') {
          acc[curr.key.trim()] = curr.value;
        }
        return acc;
      }, {} as { [key: string]: string }),
    };

    // Construct URL object carefully
    const urlObject: StaticInput['url'] = {
      ...(initialValue?.url || {}), // Preserve existing query or other non-UI parts
      protocol,
      host: hostSegments.filter(s => s.trim() !== ''),
      port: port.trim() === '' ? undefined : port.trim(),
      path: pathSegments.filter(s => s.trim() !== ''),
    };

    // Only add url to combinedStaticInput if it has meaningful content
    if (urlObject.protocol || (urlObject.host && urlObject.host.length > 0) || urlObject.port || (urlObject.path && urlObject.path.length > 0) || (urlObject.query && Object.keys(urlObject.query).length > 0) ) {
      combinedStaticInput.url = urlObject;
    } else {
      delete combinedStaticInput.url; // Remove if empty
    }
    
    // Clean up headers if empty
    if (Object.keys(combinedStaticInput.headers || {}).length === 0) {
        delete combinedStaticInput.headers;
    }


    onChange(combinedStaticInput);
  }, [method, protocol, hostSegments, port, pathSegments, headers, customFields, onChange, initialValue]);

  const handleListChange = (setter: React.Dispatch<React.SetStateAction<string[]>>, index: number, value: string) => {
    setter(prev => prev.map((item, i) => (i === index ? value : item)));
  };

  const addListItem = (setter: React.Dispatch<React.SetStateAction<string[]>>) => {
    setter(prev => [...prev, '']);
  };

  const removeListItem = (setter: React.Dispatch<React.SetStateAction<string[]>>, index: number) => {
    setter(prev => prev.filter((_, i) => i !== index));
  };

  const handleHeaderChange = (index: number, field: 'key' | 'value', value: string) => {
    setHeaders(prev => prev.map((h, i) => (i === index ? { ...h, [field]: value } : h)));
  };

  const addHeader = () => {
    setHeaders(prev => [...prev, { key: '', value: '' }]);
  };

  const removeHeader = (index: number) => {
    setHeaders(prev => prev.filter((_, i) => i !== index));
  };

  const handleCustomFieldChange = (index: number, field: 'key' | 'value', value: string) => {
    setCustomFields(prev => prev.map((cf, i) => (i === index ? { ...cf, [field]: value } : cf)));
  };

  const addCustomField = () => {
    setCustomFields(prev => [...prev, { key: '', value: '' }]);
  };

  const removeCustomField = (index: number) => {
    setCustomFields(prev => prev.filter((_, i) => i !== index));
  };

  // Local utility function for singularization
  const singularize = (text: string): string => {
    if (text.endsWith('s')) { // Very basic singularization
      return text.substring(0, text.length - 1);
    }
    return text;
  };
  
  const renderListEditor = (label: string, items: string[], setter: React.Dispatch<React.SetStateAction<string[]>>) => (
    <div className={styles.fieldGroup}>
      <label className={styles.fieldLabel}>{label}:</label>
      {items.map((item, index) => (
        <div key={index} className={styles.listItem}>
          <input
            type="text"
            value={item}
            onChange={(e) => handleListChange(setter, index, e.target.value)}
            className={styles.input}
            placeholder={`Segment ${index + 1}`}
          />
          <button onClick={() => removeListItem(setter, index)} className={styles.removeButton}>Remove</button>
        </div>
      ))}
      <button onClick={() => addListItem(setter)} className={styles.addButton}>Add {singularize(label)}</button>
    </div>
  );


  return (
    <div className={styles.structuredEditorContainer}>
      <div className={styles.fieldGroup}>
        <label htmlFor="static-method" className={styles.fieldLabel}>Method:</label>
        <select id="static-method" value={method} onChange={(e) => setMethod(e.target.value)} className={styles.select}>
          {httpMethods.map(m => <option key={m} value={m}>{m}</option>)}
        </select>
      </div>

      <h4 className={styles.subHeader}>URL</h4>
      <div className={styles.fieldGroup}>
        <label htmlFor="static-url-protocol" className={styles.fieldLabel}>Protocol:</label>
        <select id="static-url-protocol" value={protocol} onChange={(e) => setProtocol(e.target.value)} className={styles.select}>
          {protocols.map(p => <option key={p} value={p}>{p}</option>)}
        </select>
      </div>
      {renderListEditor("Host Segments", hostSegments, setHostSegments)}
      <div className={styles.fieldGroup}>
        <label htmlFor="static-url-port" className={styles.fieldLabel}>Port:</label>
        <input id="static-url-port" type="text" value={port} onChange={(e) => setPort(e.target.value)} className={styles.input} placeholder="e.g., 8080 (optional)"/>
      </div>
      {renderListEditor("Path Segments", pathSegments, setPathSegments)}
      {/* Query parameters editor can be added later here */}


      <h4 className={styles.subHeader}>Headers</h4>
      {headers.map((header, index) => (
        <div key={index} className={styles.listItem}>
          <input
            type="text"
            value={header.key}
            onChange={(e) => handleHeaderChange(index, 'key', e.target.value)}
            className={styles.input}
            placeholder="Header Name"
          />
          <input
            type="text"
            value={header.value}
            onChange={(e) => handleHeaderChange(index, 'value', e.target.value)}
            className={styles.input}
            placeholder="Header Value"
          />
          <button onClick={() => removeHeader(index)} className={styles.removeButton}>Remove</button>
        </div>
      ))}
      <button onClick={addHeader} className={styles.addButton}>Add Header</button>

      <h4 className={styles.subHeader}>Other Custom Fields</h4>
      {customFields.map((field, index) => (
        <div key={`custom-${index}`} className={styles.listItem}>
          <input
            type="text"
            value={field.key}
            onChange={(e) => handleCustomFieldChange(index, 'key', e.target.value)}
            className={styles.input}
            placeholder="Field Name"
          />
          <input
            type="text"
            value={field.value}
            onChange={(e) => handleCustomFieldChange(index, 'value', e.target.value)}
            className={styles.input}
            placeholder="Field Value (string, number, boolean)"
          />
          <button onClick={() => removeCustomField(index)} className={styles.removeButton}>Remove</button>
        </div>
      ))}
      <button onClick={addCustomField} className={styles.addButton}>Add Custom Field</button>
      
      <p className={styles.infoText}>'body' and 'query parameters' can be edited in Raw JSON mode. Complex custom field values may also require Raw JSON mode.</p>
    </div>
  );
};

export default StaticInputStructuredEditor;
