import pool from './db';
import crypto from 'crypto';

export interface AuthProvider {
  provider_id: string;
  provider_name: string;
  provider_type: string;
  type: string;
  client_id: string;
  encrypted_secret: string;
  iv: string;
  is_built_in: boolean;
  options: any | null;
}

export interface AuthProviderWithSecret extends AuthProvider {
  client_secret: string;
}

const SECRET_KEY = process.env.SECRET_KEY;

if (!SECRET_KEY) {
  throw new Error('SECRET_KEY environment variable is not set.');
}

const SECRET_KEY_BYTES = Buffer.from(SECRET_KEY, 'hex');

function decrypt(encryptedHex: string, ivHex: string): string {
  const iv = Buffer.from(ivHex, 'hex');
  const encryptedData = Buffer.from(encryptedHex, 'hex');
  const authTag = encryptedData.slice(encryptedData.length - 16);
  const ciphertext = encryptedData.slice(0, encryptedData.length - 16);
  const decipher = crypto.createDecipheriv('aes-256-gcm', SECRET_KEY_BYTES, iv);
  decipher.setAuthTag(authTag);
  const decrypted = Buffer.concat([decipher.update(ciphertext), decipher.final()]);
  return decrypted.toString('utf-8');
}

export async function getAuthProviders(tenantName: string): Promise<AuthProvider[]> {
  const client = await pool.connect();
  try {
    const res = await client.query<AuthProvider>(
      'SELECT provider_id, type, client_id, encrypted_secret, iv, provider_name, provider_type, is_built_in, options FROM auth_providers WHERE tenant_name = $1',
      [tenantName]
    );
    return res.rows;
  } finally {
    client.release();
  }
}

export async function getAuthProvidersWithSecrets(tenantName: string): Promise<AuthProviderWithSecret[]> {
  const providers = await getAuthProviders(tenantName);
  return providers.map(provider => {
    const decryptedSecret = decrypt(provider.encrypted_secret, provider.iv);
    return {
      ...provider,
      client_secret: decryptedSecret,
    };
  });
}
