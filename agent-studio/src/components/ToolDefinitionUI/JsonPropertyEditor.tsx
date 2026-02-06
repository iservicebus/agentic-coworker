import React, { useState } from 'react'; // Added useState
import styles from './ToolDefinitionUI.module.css'; // Reuse styles

// Define more specific types for clarity
export interface JsonSchemaProperty {
  type?: 'string' | 'number' | 'integer' | 'boolean' | 'object' | 'array';
  description?: string;
  properties?: { [key: string]: JsonSchemaProperty };
  items?: JsonSchemaProperty | boolean; // boolean for tuple validation which we might not support in UI
  required?: string[];
  enum?: (string | number)[];
  default?: any;
  [key: string]: any; // Allow other schema keywords
}

export interface JsonPropertyEditorProps {
  propertyName: string;
  propertySchema: JsonSchemaProperty;
  path: string[]; // e.g., ['properties', 'user', 'properties', 'name']
  onSchemaChange: (path: string[], newSchema: JsonSchemaProperty) => void;
  onRemoveProperty: (path: string[], propertyName: string) => void;
  onAddProperty: (path: string[]) => void; // Path to the parent 'properties' object
  onPropertyNameChange?: (path: string[], oldName: string, newName: string) => void; // Optional for now
}

const JsonPropertyEditor: React.FC<JsonPropertyEditorProps> = ({
  propertyName,
  propertySchema,
  path,
  onSchemaChange,
  onRemoveProperty,
  onAddProperty,
  onPropertyNameChange,
}) => {
  // Define root properties that are created by default
  const defaultRootProperties = ['path', 'query', 'headers', 'body'];
  const isDefaultRootProperty = path.length === 1 && path[0] === 'properties' && defaultRootProperties.includes(propertyName);
  const currentType = propertySchema.type || 'string';
  const [isEditingName, setIsEditingName] = useState(false);
  const [editingName, setEditingName] = useState(propertyName);

  // Update editingName when propertyName changes
  React.useEffect(() => {
    setEditingName(propertyName);
  }, [propertyName]);

  const handleInputChange = (field: keyof JsonSchemaProperty, value: any) => {
    const newSchema = { ...propertySchema, [field]: value };
    // If type changes to object, ensure properties exists. If from object, maybe clear properties?
    if (field === 'type') {
      if (value === 'object' && !newSchema.properties) {
        newSchema.properties = {};
      } else if (value === 'array' && !newSchema.items) {
        newSchema.items = { type: 'string' as 'string' }; // Default item type, cast for type safety
      }
      // Consider clearing 'properties' or 'items' if type changes away from object/array
    }
    
    onSchemaChange(path.concat(propertyName), newSchema);
  };

  const handleEnumChange = (index: number, value: string | number) => {
    const newEnum = [...(propertySchema.enum || [])];
    newEnum[index] = value;
    handleInputChange('enum', newEnum.filter(e => e !== undefined && e !== null && e !== '')); // Filter out empty strings
  };

  const addEnumValue = () => {
    const newEnum = [...(propertySchema.enum || []), ''];
    handleInputChange('enum', newEnum);
  };

  const removeEnumValue = (index: number) => {
    const newEnum = (propertySchema.enum || []).filter((_, i) => i !== index);
    handleInputChange('enum', newEnum.length > 0 ? newEnum : undefined);
  };

  
  const handleNestedSchemaChange = (nestedPath: string[], newNestedSchema: JsonSchemaProperty) => {
    // This function is called by child JsonPropertyEditors
    // The 'nestedPath' will be relative to the current property's 'properties' or 'items'
    // We need to reconstruct the full path from the root schema
    onSchemaChange(nestedPath, newNestedSchema);
  };

  const handleRemoveNestedProperty = (parentPropertiesPath: string[], nestedPropertyName: string) => {
    onRemoveProperty(parentPropertiesPath, nestedPropertyName);
  };
  
  const handleAddNestedProperty = (parentPropertiesPath: string[]) => {
    onAddProperty(parentPropertiesPath);
  };

  const handlePropertyNameSave = () => {
    if (editingName.trim() && editingName !== propertyName && onPropertyNameChange) {
      onPropertyNameChange(path, propertyName, editingName.trim());
    }
    setIsEditingName(false);
  };

  const handlePropertyNameCancel = () => {
    setEditingName(propertyName);
    setIsEditingName(false);
  };


  return (
    <div className={styles.jsonPropertyEditor}>
      <div className={styles.propertyHeader}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          {/* Only show property name for default root properties */}
          {isDefaultRootProperty && (
            <strong className={styles.propertyName}>{propertyName}:</strong>
          )}
        </div>
        <div>
          <button 
            onClick={() => onRemoveProperty(path, propertyName)} 
            className={`${styles.removeButton} ${styles.propertyRemoveButton}`}
          >
            Remove Property
          </button>
        </div>
      </div>

      {/* Property Name Field - Only for nested properties, not for default root properties */}
      {onPropertyNameChange && !isDefaultRootProperty && (
        <div className={styles.fieldGroupInline}>
          <label className={styles.fieldLabel}>Name:</label>
          <input
            type="text"
            value={editingName}
            onChange={(e) => setEditingName(e.target.value)}
            onBlur={() => {
              if (editingName.trim() && editingName !== propertyName) {
                onPropertyNameChange(path, propertyName, editingName.trim());
              }
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && editingName.trim() && editingName !== propertyName) {
                onPropertyNameChange(path, propertyName, editingName.trim());
              }
            }}
            className={styles.input}
            placeholder="Enter property name"
          />
        </div>
      )}

      <div className={styles.fieldGroupInline}>
        <label className={styles.fieldLabel}>Type:</label>
        <select
          value={currentType}
          onChange={(e) => handleInputChange('type', e.target.value as JsonSchemaProperty['type'])}
          className={styles.select}
        >
          <option value="string">String</option>
          <option value="number">Number</option>
          <option value="integer">Integer</option>
          <option value="boolean">Boolean</option>
          <option value="object">Object</option>
          <option value="array">Array</option>
        </select>
      </div>

      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>Description:</label>
        <textarea
          value={propertySchema.description || ''}
          onChange={(e) => handleInputChange('description', e.target.value)}
          className={styles.textarea}
          rows={2}
        />
      </div>

      {currentType === 'object' && (
        <div className={styles.nestedProperties}>
          <h5 className={styles.nestedHeader}>Properties of '{propertyName}':</h5>
          {propertySchema.properties && Object.entries(propertySchema.properties).map(([key, nestedProp]) => (
            <JsonPropertyEditor
              key={key}
              propertyName={key}
              propertySchema={nestedProp}
              path={path.concat(propertyName, 'properties')}
              onSchemaChange={handleNestedSchemaChange}
              onRemoveProperty={handleRemoveNestedProperty}
              onAddProperty={handleAddNestedProperty}
              onPropertyNameChange={onPropertyNameChange}
            />
          ))}
          <button 
            onClick={() => handleAddNestedProperty(path.concat(propertyName, 'properties'))}
            className={styles.addButton}
          >
            Add Nested Property to '{propertyName}'
          </button>
        </div>
      )}

      {currentType === 'array' && propertySchema.items && typeof propertySchema.items === 'object' && (
        <div className={styles.nestedProperties}>
          <h5 className={styles.nestedHeader}>Items Schema for '{propertyName}':</h5>
          <JsonPropertyEditor
            propertyName="items" // Special name for array items schema
            propertySchema={propertySchema.items as JsonSchemaProperty} // Cast needed
            path={path.concat(propertyName)} // Path to the 'items' object itself
            onSchemaChange={(itemPath, newItemSchema) => {
              // itemPath here will be path.concat(propertyName, 'items')
              // We need to update propertySchema.items
              const newSchema = { ...propertySchema, items: newItemSchema };
              onSchemaChange(path.concat(propertyName), newSchema);
            }}
            onRemoveProperty={() => { /* Removing 'items' schema means changing array type or making it typeless */ 
              const newSchema = { ...propertySchema, items: { type: 'string' as 'string' } }; // Revert to default or handle differently
              onSchemaChange(path.concat(propertyName), newSchema);
            }}
            onAddProperty={(parentPropertyPath) => { /* Adding property to 'items' if it's an object */
                if(typeof propertySchema.items === 'object' && propertySchema.items.type === 'object') {
                    onAddProperty(parentPropertyPath.concat('properties'));
                }
            }}
          />
        </div>
      )}
      {/* UI for 'default' value */}
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>Default Value:</label>
        <input
          type={currentType === 'number' || currentType === 'integer' ? 'number' : 'text'}
          value={propertySchema.default === undefined ? '' : String(propertySchema.default)}
          onChange={(e) => {
            let val: any = e.target.value;
            if (currentType === 'number' || currentType === 'integer') val = parseFloat(val);
            else if (currentType === 'boolean') val = val.toLowerCase() === 'true';
            if (e.target.value === '') val = undefined; // Allow unsetting default
            handleInputChange('default', val);
          }}
          className={styles.input}
          placeholder="Enter default value (optional)"
        />
      </div>

      {/* UI for 'enum' values */}
      <div className={styles.fieldGroup}>
        <label className={styles.fieldLabel}>Enum Values (Allowed Values):</label>
        {(propertySchema.enum || []).map((enumVal, index) => (
          <div key={index} className={styles.listItem}>
            <input
              type={currentType === 'number' || currentType === 'integer' ? 'number' : 'text'}
              value={enumVal}
              onChange={(e) => handleEnumChange(index, currentType === 'number' || currentType === 'integer' ? parseFloat(e.target.value) : e.target.value)}
              className={styles.input}
              placeholder={`Enum value ${index + 1}`}
            />
            <button onClick={() => removeEnumValue(index)} className={styles.removeButton}>Remove</button>
          </div>
        ))}
        <button onClick={addEnumValue} className={styles.addButton}>Add Enum Value</button>
      </div>
      
      {/* TODO: UI for 'required' array if type is 'object' (can be part of advanced or separate) */}
    </div>
  );
};

export default JsonPropertyEditor;
