/**
 * Security Utilities
 * 
 * Contains CSRF protection, input sanitization, and other security utilities.
 */

// =============================================================================
// CSRF PROTECTION
// =============================================================================

const CSRF_TOKEN_KEY = 'csrf_token';
const CSRF_HEADER_NAME = 'X-CSRF-Token';

/**
 * Generates a cryptographically secure random token
 */
function generateToken(length: number = 32): string {
  const array = new Uint8Array(length);
  crypto.getRandomValues(array);
  return Array.from(array, (byte) => byte.toString(16).padStart(2, '0')).join('');
}

/**
 * Gets or creates a CSRF token
 */
export function getCSRFToken(): string {
  if (typeof window === 'undefined') return '';
  
  let token = sessionStorage.getItem(CSRF_TOKEN_KEY);
  if (!token) {
    token = generateToken();
    sessionStorage.setItem(CSRF_TOKEN_KEY, token);
  }
  return token;
}

/**
 * Validates a CSRF token
 */
export function validateCSRFToken(token: string): boolean {
  if (typeof window === 'undefined') return false;
  const storedToken = sessionStorage.getItem(CSRF_TOKEN_KEY);
  return storedToken !== null && storedToken === token;
}

/**
 * Creates headers with CSRF token
 */
export function getCSRFHeaders(): Record<string, string> {
  return {
    [CSRF_HEADER_NAME]: getCSRFToken(),
  };
}

/**
 * Refreshes the CSRF token
 */
export function refreshCSRFToken(): string {
  if (typeof window === 'undefined') return '';
  const token = generateToken();
  sessionStorage.setItem(CSRF_TOKEN_KEY, token);
  return token;
}

// =============================================================================
// INPUT SANITIZATION
// =============================================================================

/**
 * Escapes HTML special characters to prevent XSS
 */
export function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#039;');
}

/**
 * Strips all HTML tags from a string
 */
export function stripHtml(html: string): string {
  return html.replace(/<[^>]*>/g, '');
}

/**
 * Sanitizes a string for safe display
 * Removes dangerous patterns while preserving basic formatting
 */
export function sanitizeInput(input: string, options: SanitizeOptions = {}): string {
  const {
    allowBasicHtml = false,
    maxLength = 10000,
    allowUrls = true,
    allowEmails = true,
  } = options;

  let sanitized = input;

  // Trim to max length
  sanitized = sanitized.slice(0, maxLength);

  // Remove null bytes
  sanitized = sanitized.replace(/\0/g, '');

  // Remove control characters (except newlines and tabs)
  sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

  if (!allowBasicHtml) {
    sanitized = escapeHtml(sanitized);
  } else {
    // Allow only safe HTML tags
    const allowedTags = ['b', 'i', 'u', 'strong', 'em', 'p', 'br', 'ul', 'ol', 'li', 'a', 'code', 'pre'];
    
    // Remove script tags and event handlers
    sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
    sanitized = sanitized.replace(/on\w+\s*=\s*["'][^"']*["']/gi, '');
    sanitized = sanitized.replace(/on\w+\s*=\s*[^\s>]+/gi, '');
    
    // Remove tags not in allowlist
    sanitized = sanitized.replace(/<\/?([a-z][a-z0-9]*)\b[^>]*>/gi, (match, tag) => {
      return allowedTags.includes(tag.toLowerCase()) ? match : '';
    });
    
    // Remove javascript: URLs
    sanitized = sanitized.replace(/javascript:/gi, '');
    sanitized = sanitized.replace(/data:/gi, '');
    sanitized = sanitized.replace(/vbscript:/gi, '');
  }

  // Optionally remove URLs
  if (!allowUrls) {
    sanitized = sanitized.replace(/https?:\/\/[^\s]+/gi, '[URL removed]');
  }

  // Optionally remove emails
  if (!allowEmails) {
    sanitized = sanitized.replace(/[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}/g, '[Email removed]');
  }

  return sanitized;
}

interface SanitizeOptions {
  allowBasicHtml?: boolean;
  maxLength?: number;
  allowUrls?: boolean;
  allowEmails?: boolean;
}

/**
 * Validates and sanitizes a URL
 */
export function sanitizeUrl(url: string): string | null {
  try {
    const parsed = new URL(url);
    
    // Only allow http and https protocols
    if (!['http:', 'https:'].includes(parsed.protocol)) {
      return null;
    }
    
    return parsed.toString();
  } catch {
    return null;
  }
}

/**
 * Validates an email address format
 */
export function isValidEmail(email: string): boolean {
  const emailRegex = /^[a-zA-Z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$/;
  return emailRegex.test(email) && email.length <= 254;
}

/**
 * Sanitizes object keys to prevent prototype pollution
 */
export function sanitizeObjectKeys<T extends Record<string, unknown>>(obj: T): T {
  const dangerousKeys = ['__proto__', 'constructor', 'prototype'];
  const sanitized = {} as T;
  
  for (const key of Object.keys(obj)) {
    if (!dangerousKeys.includes(key)) {
      sanitized[key as keyof T] = obj[key as keyof T];
    }
  }
  
  return sanitized;
}

// =============================================================================
// RATE LIMITING (Client-side)
// =============================================================================

interface RateLimitState {
  count: number;
  resetTime: number;
}

const rateLimitStates = new Map<string, RateLimitState>();

/**
 * Client-side rate limiter
 * Note: This is for UX only, actual rate limiting should be server-side
 */
export function checkRateLimit(
  key: string,
  maxRequests: number = 10,
  windowMs: number = 60000
): { allowed: boolean; remaining: number; resetIn: number } {
  const now = Date.now();
  let state = rateLimitStates.get(key);

  // Reset if window has passed
  if (!state || now > state.resetTime) {
    state = {
      count: 0,
      resetTime: now + windowMs,
    };
  }

  const remaining = Math.max(0, maxRequests - state.count - 1);
  const resetIn = Math.max(0, state.resetTime - now);

  if (state.count >= maxRequests) {
    return { allowed: false, remaining: 0, resetIn };
  }

  state.count++;
  rateLimitStates.set(key, state);

  return { allowed: true, remaining, resetIn };
}

/**
 * Resets rate limit for a specific key
 */
export function resetRateLimit(key: string): void {
  rateLimitStates.delete(key);
}

// =============================================================================
// SENSITIVE DATA HANDLING
// =============================================================================

/**
 * Masks sensitive data for display
 */
export function maskSensitiveData(data: string, type: 'email' | 'phone' | 'card' | 'token'): string {
  switch (type) {
    case 'email': {
      const [local, domain] = data.split('@');
      if (!domain) return '***';
      const maskedLocal = local.length > 2 
        ? local[0] + '*'.repeat(local.length - 2) + local[local.length - 1]
        : '*'.repeat(local.length);
      return `${maskedLocal}@${domain}`;
    }
    case 'phone': {
      const digits = data.replace(/\D/g, '');
      if (digits.length < 4) return '*'.repeat(data.length);
      return '*'.repeat(digits.length - 4) + digits.slice(-4);
    }
    case 'card': {
      const digits = data.replace(/\D/g, '');
      if (digits.length < 4) return '*'.repeat(data.length);
      return '**** **** **** ' + digits.slice(-4);
    }
    case 'token': {
      if (data.length <= 8) return '*'.repeat(data.length);
      return data.slice(0, 4) + '*'.repeat(data.length - 8) + data.slice(-4);
    }
    default:
      return '*'.repeat(data.length);
  }
}

/**
 * Securely clears sensitive data from memory
 * Note: JavaScript strings are immutable, so we can only clear arrays/objects
 */
export function secureClear(obj: Record<string, unknown>): void {
  for (const key of Object.keys(obj)) {
    if (typeof obj[key] === 'string') {
      obj[key] = '';
    } else if (typeof obj[key] === 'number') {
      obj[key] = 0;
    } else if (Array.isArray(obj[key])) {
      (obj[key] as unknown[]).length = 0;
    } else if (typeof obj[key] === 'object' && obj[key] !== null) {
      secureClear(obj[key] as Record<string, unknown>);
    }
  }
}

// =============================================================================
// CONTENT SECURITY
// =============================================================================

/**
 * Generates a nonce for inline scripts (CSP)
 */
export function generateNonce(): string {
  return generateToken(16);
}

/**
 * Validates if a URL is from a trusted domain
 */
export function isTrustedDomain(url: string, trustedDomains: string[]): boolean {
  try {
    const parsed = new URL(url);
    return trustedDomains.some((domain) => {
      if (domain.startsWith('*.')) {
        // Wildcard subdomain matching
        const baseDomain = domain.slice(2);
        return parsed.hostname === baseDomain || parsed.hostname.endsWith('.' + baseDomain);
      }
      return parsed.hostname === domain;
    });
  } catch {
    return false;
  }
}

/**
 * Detects potentially malicious patterns in user input
 */
export function detectMaliciousPatterns(input: string): {
  isSuspicious: boolean;
  patterns: string[];
} {
  const suspiciousPatterns = [
    { name: 'SQL Injection', regex: /(\b(select|insert|update|delete|drop|union|exec|execute)\b.*\b(from|into|where|table)\b)/i },
    { name: 'Script Injection', regex: /<script\b/i },
    { name: 'Event Handler', regex: /\bon\w+\s*=/i },
    { name: 'JavaScript Protocol', regex: /javascript:/i },
    { name: 'Data URI', regex: /data:\s*[^,]*;base64/i },
    { name: 'Expression Injection', regex: /\$\{.*\}/i },
    { name: 'Template Injection', regex: /\{\{.*\}\}/i },
    { name: 'Path Traversal', regex: /\.\.[\/\\]/i },
    { name: 'Null Byte', regex: /\x00/i },
    { name: 'CRLF Injection', regex: /\r\n|\r|\n/g },
  ];

  const detectedPatterns: string[] = [];

  for (const pattern of suspiciousPatterns) {
    if (pattern.regex.test(input)) {
      detectedPatterns.push(pattern.name);
    }
  }

  return {
    isSuspicious: detectedPatterns.length > 0,
    patterns: detectedPatterns,
  };
}

// =============================================================================
// RBAC (Role-Based Access Control)
// =============================================================================

export type UserRole = 'org_admin' | 'staff_admin' | 'staff_analyst' | 'staff_engineer' | 'staff_viewer';

export interface Permission {
  resource: string;
  actions: ('create' | 'read' | 'update' | 'delete')[];
}

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  org_admin: [
    { resource: '*', actions: ['create', 'read', 'update', 'delete'] },
  ],
  staff_admin: [
    { resource: 'users', actions: ['create', 'read', 'update'] },
    { resource: 'conversations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'documents', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'agents', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'integrations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'analytics', actions: ['read'] },
    { resource: 'settings', actions: ['read', 'update'] },
  ],
  staff_analyst: [
    { resource: 'conversations', actions: ['create', 'read'] },
    { resource: 'documents', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
    { resource: 'agents', actions: ['read'] },
  ],
  staff_engineer: [
    { resource: 'conversations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'documents', actions: ['create', 'read', 'update'] },
    { resource: 'agents', actions: ['create', 'read', 'update'] },
    { resource: 'integrations', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
  ],
  staff_viewer: [
    { resource: 'conversations', actions: ['read'] },
    { resource: 'documents', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
  ],
};

/**
 * Check if a user has permission to perform an action on a resource
 */
export function hasPermission(
  userRole: UserRole,
  resource: string,
  action: 'create' | 'read' | 'update' | 'delete'
): boolean {
  const permissions = ROLE_PERMISSIONS[userRole];
  if (!permissions) return false;

  for (const perm of permissions) {
    if (perm.resource === '*' && perm.actions.includes(action)) {
      return true;
    }
    if (perm.resource === resource && perm.actions.includes(action)) {
      return true;
    }
  }

  return false;
}

/**
 * Check if role is an admin role
 */
export function isAdminRole(role: UserRole): boolean {
  return role === 'org_admin' || role === 'staff_admin';
}

/**
 * Check if role is an organization owner/admin
 */
export function isOrgAdmin(role: UserRole): boolean {
  return role === 'org_admin';
}

/**
 * Get display name for a role
 */
export function getRoleDisplayName(role: UserRole): string {
  const names: Record<UserRole, string> = {
    org_admin: 'Organization Admin',
    staff_admin: 'Staff Admin',
    staff_analyst: 'Analyst',
    staff_engineer: 'Engineer',
    staff_viewer: 'Viewer',
  };
  return names[role] || role;
}

// =============================================================================
// PROMPT INJECTION PROTECTION
// =============================================================================

/**
 * System instruction delimiter to separate user content from system prompts.
 * This helps prevent prompt injection attacks.
 */
export const SYSTEM_DELIMITER = '<<<SYSTEM>>>';
export const USER_DELIMITER = '<<<USER>>>';
export const END_DELIMITER = '<<<END>>>';

/**
 * Wrap user content with delimiters to prevent prompt injection.
 */
export function wrapUserContent(content: string): string {
  return `${USER_DELIMITER}\n${content}\n${END_DELIMITER}`;
}

/**
 * Check if content contains potential prompt injection patterns.
 */
export function detectPromptInjection(content: string): {
  detected: boolean;
  patterns: string[];
  severity: 'low' | 'medium' | 'high';
} {
  const patterns: string[] = [];

  const injectionPatterns = [
    { regex: /ignore\s+(previous|above|all)\s+(instructions?|prompts?)/i, name: 'instruction_override', severity: 'high' as const },
    { regex: /you\s+are\s+now\s+/i, name: 'role_change', severity: 'high' as const },
    { regex: /disregard\s+(your|the)\s+(rules?|guidelines?)/i, name: 'rule_bypass', severity: 'high' as const },
    { regex: /pretend\s+(to\s+be|you\s+are)/i, name: 'roleplay_attack', severity: 'medium' as const },
    { regex: /system\s*:\s*/i, name: 'system_impersonation', severity: 'high' as const },
    { regex: /\[INST\]|\[\/INST\]/i, name: 'instruction_tags', severity: 'medium' as const },
    { regex: /<\|im_start\|>|<\|im_end\|>/i, name: 'chat_markers', severity: 'medium' as const },
    { regex: /###\s*(system|assistant|user)\s*:/i, name: 'role_markers', severity: 'medium' as const },
    { regex: /forget\s+(everything|all|what)/i, name: 'memory_wipe', severity: 'medium' as const },
    { regex: /new\s+(instructions?|prompt|task)/i, name: 'new_instructions', severity: 'low' as const },
  ];

  let maxSeverity: 'low' | 'medium' | 'high' = 'low';
  const severityOrder = { low: 0, medium: 1, high: 2 };

  for (const { regex, name, severity } of injectionPatterns) {
    if (regex.test(content)) {
      patterns.push(name);
      if (severityOrder[severity] > severityOrder[maxSeverity]) {
        maxSeverity = severity;
      }
    }
  }

  return {
    detected: patterns.length > 0,
    patterns,
    severity: maxSeverity,
  };
}

/**
 * Sanitize chat message content for safe rendering
 */
export function sanitizeChatContent(content: string): string {
  let sanitized = content;

  // Remove null bytes
  sanitized = sanitized.replace(/\0/g, '');

  // Normalize unicode
  sanitized = sanitized.normalize('NFC');

  // Remove potential HTML/script injections but keep markdown
  sanitized = sanitized.replace(/<script\b[^<]*(?:(?!<\/script>)<[^<]*)*<\/script>/gi, '');
  sanitized = sanitized.replace(/on\w+\s*=\s*["'][^"']*["']/gi, '');

  return sanitized;
}

// =============================================================================
// CHAT INPUT VALIDATION
// =============================================================================

export interface ChatInputValidationResult {
  isValid: boolean;
  sanitized: string;
  warnings: string[];
  errors: string[];
}

/**
 * Validate and sanitize chat input before sending to the server.
 */
export function validateChatInput(
  input: string,
  options: {
    maxLength?: number;
    minLength?: number;
    allowEmpty?: boolean;
  } = {}
): ChatInputValidationResult {
  const {
    maxLength = 32000,
    minLength = 1,
    allowEmpty = false,
  } = options;

  const warnings: string[] = [];
  const errors: string[] = [];

  // Trim the input
  let sanitized = input.trim();

  // Check for empty input
  if (!sanitized) {
    if (!allowEmpty) {
      errors.push('Message cannot be empty');
    }
    return { isValid: allowEmpty, sanitized: '', warnings, errors };
  }

  // Check minimum length
  if (sanitized.length < minLength) {
    errors.push(`Message must be at least ${minLength} characters`);
  }

  // Check maximum length
  if (sanitized.length > maxLength) {
    warnings.push(`Message truncated to ${maxLength} characters`);
    sanitized = sanitized.slice(0, maxLength);
  }

  // Check for excessive whitespace
  const originalLength = sanitized.length;
  sanitized = sanitized.replace(/\s{10,}/g, '          ');
  if (sanitized.length < originalLength) {
    warnings.push('Excessive whitespace has been collapsed');
  }

  // Remove null bytes and control characters
  sanitized = sanitized.replace(/\0/g, '');
  sanitized = sanitized.replace(/[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]/g, '');

  // Normalize unicode
  sanitized = sanitized.normalize('NFC');

  // Check for very long lines (potential abuse)
  const lines = sanitized.split('\n');
  const longLineThreshold = 10000;
  let hasLongLines = false;
  for (let i = 0; i < lines.length; i++) {
    if (lines[i].length > longLineThreshold) {
      hasLongLines = true;
      break;
    }
  }
  if (hasLongLines) {
    warnings.push('Message contains very long lines');
  }

  return {
    isValid: errors.length === 0,
    sanitized,
    warnings,
    errors,
  };
}
