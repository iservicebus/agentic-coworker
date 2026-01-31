import { faker } from '@faker-js/faker';
import jsf from 'json-schema-faker';

jsf.extend('faker', () => faker);
jsf.option({
  failOnInvalidTypes: true,
  failOnInvalidFormat: true,
  useDefaultValue: true,
  requiredOnly: false,
  alwaysFakeOptionals: true,
});

const supportedFormats = [
  // Standard formats from JSON Schema specification
  'date-time', 'date', 'time', 'email', 'idn-email',
  'hostname', 'idn-hostname', 'ipv4', 'ipv6', 'uri', 'uri-reference',
  'iri', 'iri-reference', 'uri-template', 'json-pointer', 'relative-json-pointer',
  'regex',
  // formats supported by json-schema-faker
  'ip-address', 'color'
];

function traverseAndClean(obj: any) {
  if (obj && typeof obj === 'object') {
    if (obj.type === 'object' && obj.additionalProperties === undefined) {
      obj.additionalProperties = false;
    }

    for (const key in obj) {
      if (obj.hasOwnProperty(key)) {
        traverseAndClean(obj[key]);
      }
    }
  }
  return obj;
}

function ensureDefaultValues(schema: any, data: any): any {
  if (!schema || !data || typeof schema !== 'object' || typeof data !== 'object') {
    return data;
  }

  // Handle object type schemas
  if (schema.type === 'object' && schema.properties) {
    const result = { ...data };
    
    for (const [key, propSchema] of Object.entries(schema.properties)) {
      const prop = propSchema as any;
      
      // Priority: default > example > generated fake data
      // If the property has a default value, always use it (highest priority)
      if (prop.default !== undefined) {
        result[key] = prop.default;
      }
      // If no default but has example value, use the example (overrides fake data)
      else if (prop.example !== undefined) {
        result[key] = prop.example;
      }
      // Handle anyOf schemas (like input_parameters and output_parameters)
      else if (prop.anyOf && Array.isArray(prop.anyOf)) {
        // Find the array schema in anyOf (ignore null type)
        const arraySchema = prop.anyOf.find((schema: any) => schema.type === 'array');
        if (arraySchema && result[key] && Array.isArray(result[key])) {
          result[key] = result[key].map((item: any) => ensureDefaultValues(arraySchema.items, item));
        }
      }
      // Recursively handle nested objects
      else if (result[key] && prop.type === 'object') {
        result[key] = ensureDefaultValues(prop, result[key]);
      }
      // Handle arrays with default values (highest priority)
      else if (prop.type === 'array' && prop.default !== undefined) {
        result[key] = prop.default;
      }
      // Handle arrays with example values (overrides fake data)
      else if (prop.type === 'array' && prop.example !== undefined) {
        result[key] = prop.example;
      }
      // Handle array items with defaults/examples
      else if (result[key] && Array.isArray(result[key]) && prop.type === 'array' && prop.items) {
        result[key] = result[key].map((item: any) => ensureDefaultValues(prop.items, item));
      }
    }
    
    return result;
  }
  
  // Handle array type schemas
  if (schema.type === 'array' && Array.isArray(data) && schema.items) {
    return data.map(item => ensureDefaultValues(schema.items, item));
  }
  
  return data;
}

export function generateSampleData(schema: any): any {
  // Deep clone and clean the schema
  const cleanedSchema = JSON.parse(JSON.stringify(schema));
  
  // Remove unsupported formats and set additionalProperties to false
  const finalSchema = traverseAndClean(cleanedSchema);

  // Another pass to remove unsupported formats, just in case
  const finalCleanedSchema = JSON.parse(JSON.stringify(finalSchema), (key, value) => {
    if (key === 'format' && typeof value === 'string' && !supportedFormats.includes(value)) {
      return undefined; // Remove unknown format
    }
    return value;
  });

  // Generate sample data using json-schema-faker
  const generatedData = jsf.generate(finalCleanedSchema);
  
  // Ensure all default values from the schema are applied
  const dataWithDefaults = ensureDefaultValues(finalCleanedSchema, generatedData);
  
  return dataWithDefaults;
}
