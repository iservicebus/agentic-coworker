import React, { useState, useEffect, useCallback } from 'react';
import styles from './ToolDefinitionUI.module.css'; // Reuse styles
import JsonPropertyEditor, { JsonSchemaProperty } from './JsonPropertyEditor';
import { set, get, unset } from 'lodash-es'; // For deep object manipulation

interface InputSchema {
  type?: 'object'; // Typically 'object' at the root
  description?: string;
  properties?: { [key: string]: JsonSchemaProperty };
  required?: string[];
  [key: string]: any;
}

interface InputSchemaStructuredEditorProps {
  initialValue: InputSchema;
  onChange: (newValue: InputSchema) => void;
}

const InputSchemaStructuredEditor: React.FC<InputSchemaStructuredEditorProps> = ({ initialValue, onChange }) => {
  const [schema, setSchema] = useState<InputSchema>(initialValue);

  // Function to ensure required root properties exist
  const ensureRequiredRootProperties = (schemaToUpdate: InputSchema): InputSchema => {
    const requiredProperties = ['path', 'query', 'headers', 'body'];
    const updatedSchema = { ...schemaToUpdate };
    
    // Ensure properties object exists
    if (!updatedSchema.properties) {
      updatedSchema.properties = {};
    }
    
    // Add missing required properties
    requiredProperties.forEach(propName => {
      if (!updatedSchema.properties![propName]) {
        updatedSchema.properties![propName] = {
          type: 'object',
          description: `${propName.charAt(0).toUpperCase() + propName.slice(1)} parameters`,
          properties: {}
        };
      }
    });
    
    return updatedSchema;
  };

  useEffect(() => {
    // When initialValue changes, ensure required properties exist
    const schemaWithRequiredProps = ensureRequiredRootProperties(initialValue);
    setSchema(schemaWithRequiredProps);
    
    // If we added properties, notify parent
    if (JSON.stringify(schemaWithRequiredProps) !== JSON.stringify(initialValue)) {
      onChange(schemaWithRequiredProps);
    }
  }, [initialValue, onChange]);

  const handleDescriptionChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const newSchema = { ...schema, description: e.target.value };
    setSchema(newSchema);
    onChange(newSchema);
  };

  const handleSchemaChangeAtPath = useCallback((path: string[], newPropertySchema: JsonSchemaProperty) => {
    setSchema(prevSchema => {
      const newSchema = { ...prevSchema };
      set(newSchema, path, newPropertySchema); // from lodash, path like ['properties', 'user', 'properties', 'name']
      onChange(newSchema);
      return newSchema;
    });
  }, [onChange]);

  const handleRemovePropertyByPath = useCallback((path: string[], propertyName: string) => {
    setSchema(prevSchema => {
      const newSchema = { ...prevSchema };
      const propertyPath = path.concat(propertyName);
      unset(newSchema, propertyPath); // from lodash

      // Also remove from 'required' array if it exists there
      const parentPath = path.slice(0, -1); // Path to the object containing the 'properties'
      const parentObject = get(newSchema, parentPath, {}) as JsonSchemaProperty;
      if (parentObject.required && parentObject.required.includes(propertyName)) {
        const newRequired = parentObject.required.filter(req => req !== propertyName);
        set(newSchema, parentPath.concat('required'), newRequired.length > 0 ? newRequired : undefined);
      }
      
      onChange(newSchema);
      return newSchema;
    });
  }, [onChange]);

  const handleAddPropertyToPath = useCallback((pathToProperties: string[]) => {
    // pathToProperties is like ['properties'] or ['properties', 'user', 'properties']
    setSchema(prevSchema => {
      const newSchema = { ...prevSchema };
      const newPropertyName = `newProperty${Date.now()}`; // Simple unique name
      const propertiesObject = get(newSchema, pathToProperties, {});
      
      const updatedProperties = {
        ...propertiesObject,
        [newPropertyName]: { type: 'string' as 'string', description: '' }
      };
      set(newSchema, pathToProperties, updatedProperties);
      onChange(newSchema);
      return newSchema;
    });
  }, [onChange]);

  const handlePropertyNameChange = useCallback((path: string[], oldName: string, newName: string) => {
    setSchema(prevSchema => {
      const newSchema = { ...prevSchema };
      const parentPath = path.slice(0, -1); // Remove the property name from path
      const parentObject = get(newSchema, parentPath, {});
      
      if (parentObject[oldName]) {
        // Copy the property with the new name
        parentObject[newName] = parentObject[oldName];
        // Remove the old property
        delete parentObject[oldName];
        
        // Update required array if the property was required
        const grandParentPath = parentPath.slice(0, -1);
        const grandParentObject = get(newSchema, grandParentPath, {}) as JsonSchemaProperty;
        if (grandParentObject.required && grandParentObject.required.includes(oldName)) {
          const newRequired = grandParentObject.required.map(req => req === oldName ? newName : req);
          set(newSchema, grandParentPath.concat('required'), newRequired);
        }
        
        set(newSchema, parentPath, parentObject);
      }
      
      onChange(newSchema);
      return newSchema;
    });
  }, [onChange]);
  
  const handleRequiredChange = (propertyName: string, isChecked: boolean) => {
    setSchema(prevSchema => {
      const currentRequired = prevSchema.required || [];
      let newRequired: string[];
      if (isChecked) {
        newRequired = [...currentRequired, propertyName];
      } else {
        newRequired = currentRequired.filter(req => req !== propertyName);
      }
      const newSchema = { ...prevSchema, required: newRequired.length > 0 ? newRequired : undefined };
      onChange(newSchema);
      return newSchema;
    });
  };


  return (
    <div className={styles.structuredEditorContainer}>
      <div className={styles.fieldGroup}>
        <label htmlFor="inputschema-description" className={styles.fieldLabel}>Overall Schema Description:</label>
        <textarea
          id="inputschema-description"
          value={schema.description || ''}
          onChange={handleDescriptionChange}
          className={styles.textarea}
          rows={2}
        />
      </div>

      <h4 className={styles.subHeader}>Root Properties</h4>
      {schema.properties && Object.entries(schema.properties).map(([key, propSchema]) => (
        <JsonPropertyEditor
          key={key}
          propertyName={key}
          propertySchema={propSchema}
          path={['properties']} // Path to the 'properties' object itself
          onSchemaChange={handleSchemaChangeAtPath}
          onRemoveProperty={handleRemovePropertyByPath}
          onAddProperty={handleAddPropertyToPath}
          onPropertyNameChange={handlePropertyNameChange}
        />
      ))}
      <button 
        onClick={() => handleAddPropertyToPath(['properties'])} 
        className={styles.addButton}
      >
        Add Root Property
      </button>

      {schema.properties && Object.keys(schema.properties).length > 0 && (
        <div className={styles.fieldGroup}>
          <h4 className={styles.subHeader}>Required Root Properties</h4>
          {Object.keys(schema.properties).map(propName => (
            <div key={propName} className={styles.checkboxItem}>
              <input
                type="checkbox"
                id={`required-${propName}`}
                checked={schema.required?.includes(propName) || false}
                onChange={(e) => handleRequiredChange(propName, e.target.checked)}
              />
              <label htmlFor={`required-${propName}`}>{propName}</label>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};

export default InputSchemaStructuredEditor;
