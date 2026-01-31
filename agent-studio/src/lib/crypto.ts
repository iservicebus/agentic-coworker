
// After saving schema:
// npx prisma migrate dev --name init
// npx prisma generate


// 2. lib/crypto.ts
// ================

import crypto from 'crypto';

const ALGORITHM = 'aes-256-gcm';
const SECRET_KEY = process.env.SECRET_KEY!; // Must be 32-byte hex string

export function encrypt(text: string) {
  const iv = crypto.randomBytes(12);
  const cipher = crypto.createCipheriv(ALGORITHM, Buffer.from(SECRET_KEY, 'hex'), iv);
  const encrypted = Buffer.concat([cipher.update(text, 'utf8'), cipher.final()]);
  const tag = cipher.getAuthTag();
  return {
    encryptedData: Buffer.concat([encrypted, tag]).toString('hex'),
    iv: iv.toString('hex'),
  };
}

export function decrypt(encryptedHex: string, ivHex: string) {
  const iv = Buffer.from(ivHex, 'hex');
  const encrypted = Buffer.from(encryptedHex, 'hex');
  const tag = encrypted.slice(-16);
  const data = encrypted.slice(0, -16);
  const decipher = crypto.createDecipheriv(ALGORITHM, Buffer.from(SECRET_KEY, 'hex'), iv);
  decipher.setAuthTag(tag);
  const decrypted = Buffer.concat([decipher.update(data), decipher.final()]);
  return decrypted.toString('utf8');
}

