import pool from './db';

export interface Tenant {
  id: string;
  name: string;
  description: string | null;
  created_at: Date;
}

/**
 * Check if a tenant exists in the database by name
 * @param tenantName - The name of the tenant to check
 * @returns The tenant object if found, null otherwise
 */
export async function getTenantByName(tenantName: string): Promise<Tenant | null> {
  const client = await pool.connect();
  try {
    const res = await client.query<Tenant>(
      'SELECT id, name, description, created_at FROM tenants WHERE name = $1',
      [tenantName]
    );
    
    if (res.rows.length === 0) {
      return null;
    }
    
    return res.rows[0];
  } finally {
    client.release();
  }
}

/**
 * Validate if a tenant exists in the database
 * @param tenantName - The name of the tenant to validate
 * @returns true if tenant exists, false otherwise
 */
export async function validateTenantExists(tenantName: string): Promise<boolean> {
  const tenant = await getTenantByName(tenantName);
  return tenant !== null;
}

/**
 * Get all tenants from the database
 * @returns Array of all tenants
 */
export async function getAllTenants(): Promise<Tenant[]> {
  const client = await pool.connect();
  try {
    const res = await client.query<Tenant>(
      'SELECT id, name, description, created_at FROM tenants ORDER BY name'
    );
    return res.rows;
  } finally {
    client.release();
  }
}
