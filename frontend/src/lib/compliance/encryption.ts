/**
 * Data Encryption Utilities
 *
 * Client-side encryption utilities for protecting sensitive data.
 * Uses Web Crypto API for AES-256-GCM encryption.
 *
 * Note: For production HIPAA/SOC2 compliance, encryption should primarily
 * occur server-side. These utilities are for client-side data protection
 * and secure data handling.
 */

// =============================================================================
// ENCRYPTION CONFIGURATION
// =============================================================================

const ALGORITHM = 'AES-GCM';
const KEY_LENGTH = 256;
const IV_LENGTH = 12; // 96 bits for GCM
const TAG_LENGTH = 128; // Authentication tag length in bits
const SALT_LENGTH = 16;
const PBKDF2_ITERATIONS = 100000;

// =============================================================================
// KEY DERIVATION
// =============================================================================

/**
 * Derive an encryption key from a password using PBKDF2
 */
export async function deriveKey(
  password: string,
  salt: Uint8Array
): Promise<CryptoKey> {
  const encoder = new TextEncoder();
  const keyMaterial = await crypto.subtle.importKey(
    'raw',
    encoder.encode(password),
    'PBKDF2',
    false,
    ['deriveBits', 'deriveKey']
  );

  return crypto.subtle.deriveKey(
    {
      name: 'PBKDF2',
      salt: salt.buffer as ArrayBuffer,
      iterations: PBKDF2_ITERATIONS,
      hash: 'SHA-256',
    },
    keyMaterial,
    { name: ALGORITHM, length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt']
  );
}

/**
 * Generate a random encryption key
 */
export async function generateKey(): Promise<CryptoKey> {
  return crypto.subtle.generateKey(
    { name: ALGORITHM, length: KEY_LENGTH },
    true,
    ['encrypt', 'decrypt']
  );
}

/**
 * Export a key to raw bytes (for secure storage)
 */
export async function exportKey(key: CryptoKey): Promise<Uint8Array> {
  const exported = await crypto.subtle.exportKey('raw', key);
  return new Uint8Array(exported);
}

/**
 * Import a key from raw bytes
 */
export async function importKey(keyData: Uint8Array): Promise<CryptoKey> {
  return crypto.subtle.importKey(
    'raw',
    keyData.buffer as ArrayBuffer,
    { name: ALGORITHM, length: KEY_LENGTH },
    false,
    ['encrypt', 'decrypt']
  );
}

// =============================================================================
// ENCRYPTION / DECRYPTION
// =============================================================================

export interface EncryptedData {
  ciphertext: string; // Base64 encoded
  iv: string; // Base64 encoded
  salt?: string; // Base64 encoded (if password-derived key)
  tag?: string; // GCM tag is included in ciphertext
}

/**
 * Encrypt data using AES-256-GCM
 */
export async function encrypt(
  plaintext: string,
  key: CryptoKey
): Promise<EncryptedData> {
  const encoder = new TextEncoder();
  const iv = crypto.getRandomValues(new Uint8Array(IV_LENGTH));

  const ciphertext = await crypto.subtle.encrypt(
    {
      name: ALGORITHM,
      iv,
      tagLength: TAG_LENGTH,
    },
    key,
    encoder.encode(plaintext)
  );

  return {
    ciphertext: arrayBufferToBase64(ciphertext),
    iv: arrayBufferToBase64(iv),
  };
}

/**
 * Decrypt data using AES-256-GCM
 */
export async function decrypt(
  encryptedData: EncryptedData,
  key: CryptoKey
): Promise<string> {
  const decoder = new TextDecoder();
  const ciphertext = base64ToArrayBuffer(encryptedData.ciphertext);
  const iv = base64ToArrayBuffer(encryptedData.iv);

  const plaintext = await crypto.subtle.decrypt(
    {
      name: ALGORITHM,
      iv,
      tagLength: TAG_LENGTH,
    },
    key,
    ciphertext
  );

  return decoder.decode(plaintext);
}

/**
 * Encrypt data with a password (derives key internally)
 */
export async function encryptWithPassword(
  plaintext: string,
  password: string
): Promise<EncryptedData> {
  const salt = crypto.getRandomValues(new Uint8Array(SALT_LENGTH));
  const key = await deriveKey(password, salt);
  const encrypted = await encrypt(plaintext, key);

  return {
    ...encrypted,
    salt: arrayBufferToBase64(salt),
  };
}

/**
 * Decrypt data with a password
 */
export async function decryptWithPassword(
  encryptedData: EncryptedData,
  password: string
): Promise<string> {
  if (!encryptedData.salt) {
    throw new Error('Salt is required for password-based decryption');
  }

  const salt = base64ToArrayBuffer(encryptedData.salt);
  const key = await deriveKey(password, new Uint8Array(salt));

  return decrypt(encryptedData, key);
}

// =============================================================================
// HASHING
// =============================================================================

/**
 * Generate a SHA-256 hash of data
 */
export async function hash(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest('SHA-256', encoder.encode(data));
  return arrayBufferToBase64(hashBuffer);
}

/**
 * Generate a SHA-512 hash of data
 */
export async function hashSHA512(data: string): Promise<string> {
  const encoder = new TextEncoder();
  const hashBuffer = await crypto.subtle.digest('SHA-512', encoder.encode(data));
  return arrayBufferToBase64(hashBuffer);
}

/**
 * Generate HMAC for data integrity
 */
export async function hmac(data: string, secret: string): Promise<string> {
  const encoder = new TextEncoder();

  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['sign']
  );

  const signature = await crypto.subtle.sign('HMAC', key, encoder.encode(data));
  return arrayBufferToBase64(signature);
}

/**
 * Verify HMAC
 */
export async function verifyHmac(
  data: string,
  signature: string,
  secret: string
): Promise<boolean> {
  const encoder = new TextEncoder();

  const key = await crypto.subtle.importKey(
    'raw',
    encoder.encode(secret),
    { name: 'HMAC', hash: 'SHA-256' },
    false,
    ['verify']
  );

  return crypto.subtle.verify(
    'HMAC',
    key,
    base64ToArrayBuffer(signature),
    encoder.encode(data)
  );
}

// =============================================================================
// SECURE RANDOM
// =============================================================================

/**
 * Generate cryptographically secure random bytes
 */
export function secureRandom(length: number): Uint8Array {
  return crypto.getRandomValues(new Uint8Array(length));
}

/**
 * Generate a secure random string (URL-safe base64)
 */
export function secureRandomString(length: number): string {
  const bytes = secureRandom(Math.ceil((length * 3) / 4));
  return arrayBufferToBase64(bytes)
    .replace(/\+/g, '-')
    .replace(/\//g, '_')
    .replace(/=/g, '')
    .slice(0, length);
}

/**
 * Generate a secure random UUID (v4)
 */
export function secureUUID(): string {
  return crypto.randomUUID();
}

// =============================================================================
// DATA MASKING
// =============================================================================

/**
 * Mask sensitive data for display
 */
export function maskData(data: string, type: 'email' | 'phone' | 'ssn' | 'card' | 'token'): string {
  switch (type) {
    case 'email': {
      const [local, domain] = data.split('@');
      if (!domain) return '***';
      const maskedLocal = local.length > 2
        ? `${local[0]}***${local[local.length - 1]}`
        : '***';
      return `${maskedLocal}@${domain}`;
    }
    case 'phone': {
      const digits = data.replace(/\D/g, '');
      if (digits.length < 4) return '***';
      return `***-***-${digits.slice(-4)}`;
    }
    case 'ssn': {
      const digits = data.replace(/\D/g, '');
      if (digits.length < 4) return '***-**-****';
      return `***-**-${digits.slice(-4)}`;
    }
    case 'card': {
      const digits = data.replace(/\D/g, '');
      if (digits.length < 4) return '**** **** **** ****';
      return `**** **** **** ${digits.slice(-4)}`;
    }
    case 'token': {
      if (data.length <= 8) return '***';
      return `${data.slice(0, 4)}...${data.slice(-4)}`;
    }
    default:
      return '***';
  }
}

/**
 * Redact sensitive fields from an object
 */
export function redactSensitiveFields<T extends Record<string, unknown>>(
  obj: T,
  sensitiveFields: string[]
): T {
  const result = { ...obj } as Record<string, unknown>;

  for (const field of sensitiveFields) {
    if (field in result) {
      const value = result[field];
      if (typeof value === 'string') {
        result[field] = '[REDACTED]';
      } else if (value !== null && value !== undefined) {
        result[field] = '[REDACTED]';
      }
    }
  }

  return result as T;
}

// =============================================================================
// PHI/PII PROTECTION (HIPAA/GDPR)
// =============================================================================

export const SENSITIVE_FIELD_PATTERNS = {
  // HIPAA PHI identifiers
  phi: [
    'ssn', 'social_security', 'mrn', 'medical_record',
    'health_plan_id', 'diagnosis', 'treatment', 'medication',
    'patient_id', 'dob', 'date_of_birth',
  ],
  // GDPR PII
  pii: [
    'email', 'phone', 'address', 'name', 'first_name', 'last_name',
    'ip_address', 'device_id', 'location', 'birth_date',
  ],
  // Financial
  financial: [
    'card_number', 'credit_card', 'bank_account', 'routing_number',
    'cvv', 'pin', 'tax_id',
  ],
  // Credentials
  credentials: [
    'password', 'secret', 'api_key', 'token', 'private_key',
    'access_token', 'refresh_token', 'auth_token',
  ],
};

/**
 * Check if a field name is sensitive
 */
export function isSensitiveField(fieldName: string): boolean {
  const lowerField = fieldName.toLowerCase();
  const allPatterns = [
    ...SENSITIVE_FIELD_PATTERNS.phi,
    ...SENSITIVE_FIELD_PATTERNS.pii,
    ...SENSITIVE_FIELD_PATTERNS.financial,
    ...SENSITIVE_FIELD_PATTERNS.credentials,
  ];

  return allPatterns.some(pattern =>
    lowerField.includes(pattern) || pattern.includes(lowerField)
  );
}

/**
 * Auto-redact sensitive fields from an object
 */
export function autoRedactSensitive<T extends Record<string, unknown>>(obj: T): T {
  const result = { ...obj };

  for (const key of Object.keys(result)) {
    if (isSensitiveField(key)) {
      result[key as keyof T] = '[REDACTED]' as T[keyof T];
    } else if (typeof result[key] === 'object' && result[key] !== null) {
      result[key as keyof T] = autoRedactSensitive(
        result[key] as Record<string, unknown>
      ) as T[keyof T];
    }
  }

  return result;
}

// =============================================================================
// SECURE STORAGE
// =============================================================================

const STORAGE_KEY_PREFIX = 'nexus_secure_';

/**
 * Securely store data in localStorage with encryption
 */
export async function secureStore(
  key: string,
  value: string,
  encryptionKey: CryptoKey
): Promise<void> {
  const encrypted = await encrypt(value, encryptionKey);
  localStorage.setItem(
    `${STORAGE_KEY_PREFIX}${key}`,
    JSON.stringify(encrypted)
  );
}

/**
 * Retrieve and decrypt data from localStorage
 */
export async function secureRetrieve(
  key: string,
  encryptionKey: CryptoKey
): Promise<string | null> {
  const stored = localStorage.getItem(`${STORAGE_KEY_PREFIX}${key}`);
  if (!stored) return null;

  try {
    const encrypted = JSON.parse(stored) as EncryptedData;
    return await decrypt(encrypted, encryptionKey);
  } catch {
    return null;
  }
}

/**
 * Remove secure data from localStorage
 */
export function secureRemove(key: string): void {
  localStorage.removeItem(`${STORAGE_KEY_PREFIX}${key}`);
}

/**
 * Clear all secure storage
 */
export function secureClearAll(): void {
  const keysToRemove: string[] = [];

  for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    if (key?.startsWith(STORAGE_KEY_PREFIX)) {
      keysToRemove.push(key);
    }
  }

  keysToRemove.forEach(key => localStorage.removeItem(key));
}

// =============================================================================
// UTILITIES
// =============================================================================

function arrayBufferToBase64(buffer: ArrayBuffer | Uint8Array): string {
  const bytes = buffer instanceof Uint8Array ? buffer : new Uint8Array(buffer);
  let binary = '';
  for (let i = 0; i < bytes.byteLength; i++) {
    binary += String.fromCharCode(bytes[i]);
  }
  return btoa(binary);
}

function base64ToArrayBuffer(base64: string): ArrayBuffer {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i++) {
    bytes[i] = binary.charCodeAt(i);
  }
  return bytes.buffer;
}

// =============================================================================
// KEY ROTATION HELPERS
// =============================================================================

export interface KeyRotationInfo {
  keyId: string;
  createdAt: string;
  expiresAt: string;
  status: 'active' | 'rotating' | 'expired';
}

/**
 * Check if a key needs rotation
 */
export function needsKeyRotation(keyInfo: KeyRotationInfo): boolean {
  const expiresAt = new Date(keyInfo.expiresAt);
  const warningThreshold = 7 * 24 * 60 * 60 * 1000; // 7 days before expiry

  return Date.now() > expiresAt.getTime() - warningThreshold;
}

/**
 * Generate key rotation schedule
 */
export function generateKeyRotationSchedule(
  rotationDays: number = 90
): KeyRotationInfo {
  const now = new Date();
  const expiresAt = new Date(now.getTime() + rotationDays * 24 * 60 * 60 * 1000);

  return {
    keyId: secureUUID(),
    createdAt: now.toISOString(),
    expiresAt: expiresAt.toISOString(),
    status: 'active',
  };
}
