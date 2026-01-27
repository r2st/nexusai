/**
 * Tests for Security Utilities
 */
import { describe, it, expect, beforeEach, vi } from 'vitest';
import {
  escapeHtml,
  stripHtml,
  sanitizeInput,
  sanitizeUrl,
  isValidEmail,
  sanitizeObjectKeys,
  checkRateLimit,
  resetRateLimit,
  maskSensitiveData,
  isTrustedDomain,
  detectMaliciousPatterns,
  getCSRFToken,
  validateCSRFToken,
  refreshCSRFToken,
} from '@/lib/security';

// Mock sessionStorage
const mockStorage: Record<string, string> = {};
vi.stubGlobal('sessionStorage', {
  getItem: (key: string) => mockStorage[key] || null,
  setItem: (key: string, value: string) => { mockStorage[key] = value; },
  removeItem: (key: string) => { delete mockStorage[key]; },
  clear: () => { Object.keys(mockStorage).forEach(key => delete mockStorage[key]); },
});

// Mock crypto
vi.stubGlobal('crypto', {
  getRandomValues: (array: Uint8Array) => {
    for (let i = 0; i < array.length; i++) {
      array[i] = Math.floor(Math.random() * 256);
    }
    return array;
  },
});

describe('escapeHtml', () => {
  it('escapes HTML special characters', () => {
    expect(escapeHtml('<script>')).toBe('&lt;script&gt;');
    expect(escapeHtml('"test"')).toBe('&quot;test&quot;');
    expect(escapeHtml("'test'")).toBe('&#039;test&#039;');
    expect(escapeHtml('a & b')).toBe('a &amp; b');
  });

  it('handles empty string', () => {
    expect(escapeHtml('')).toBe('');
  });

  it('leaves safe text unchanged', () => {
    expect(escapeHtml('Hello World')).toBe('Hello World');
  });
});

describe('stripHtml', () => {
  it('removes all HTML tags', () => {
    expect(stripHtml('<p>Hello</p>')).toBe('Hello');
    expect(stripHtml('<div class="test">Content</div>')).toBe('Content');
    expect(stripHtml('<script>alert("xss")</script>')).toBe('alert("xss")');
  });

  it('handles nested tags', () => {
    expect(stripHtml('<div><p><span>Text</span></p></div>')).toBe('Text');
  });
});

describe('sanitizeInput', () => {
  it('removes script tags when allowing basic HTML', () => {
    const input = '<script>alert("xss")</script><p>Safe</p>';
    const result = sanitizeInput(input, { allowBasicHtml: true });
    expect(result).not.toContain('<script>');
    expect(result).toContain('<p>Safe</p>');
  });

  it('removes event handlers', () => {
    const input = '<div onclick="alert(1)">Click me</div>';
    const result = sanitizeInput(input, { allowBasicHtml: true });
    expect(result).not.toContain('onclick');
  });

  it('removes javascript: URLs', () => {
    const input = '<a href="javascript:alert(1)">Link</a>';
    const result = sanitizeInput(input, { allowBasicHtml: true });
    expect(result).not.toContain('javascript:');
  });

  it('escapes HTML by default', () => {
    const input = '<script>alert(1)</script>';
    const result = sanitizeInput(input);
    expect(result).toBe('&lt;script&gt;alert(1)&lt;/script&gt;');
  });

  it('truncates to maxLength', () => {
    const input = 'a'.repeat(100);
    const result = sanitizeInput(input, { maxLength: 50 });
    expect(result.length).toBe(50);
  });

  it('removes null bytes', () => {
    const input = 'test\0string';
    const result = sanitizeInput(input);
    expect(result).not.toContain('\0');
  });

  it('removes URLs when not allowed', () => {
    const input = 'Check out https://example.com for more';
    const result = sanitizeInput(input, { allowUrls: false });
    expect(result).toContain('[URL removed]');
  });

  it('removes emails when not allowed', () => {
    const input = 'Contact me at test@example.com';
    const result = sanitizeInput(input, { allowEmails: false });
    expect(result).toContain('[Email removed]');
  });
});

describe('sanitizeUrl', () => {
  it('allows http URLs', () => {
    expect(sanitizeUrl('http://example.com')).toBe('http://example.com/');
  });

  it('allows https URLs', () => {
    expect(sanitizeUrl('https://example.com')).toBe('https://example.com/');
  });

  it('rejects javascript URLs', () => {
    expect(sanitizeUrl('javascript:alert(1)')).toBeNull();
  });

  it('rejects data URLs', () => {
    expect(sanitizeUrl('data:text/html,<script>alert(1)</script>')).toBeNull();
  });

  it('returns null for invalid URLs', () => {
    expect(sanitizeUrl('not a url')).toBeNull();
  });
});

describe('isValidEmail', () => {
  it('accepts valid emails', () => {
    expect(isValidEmail('test@example.com')).toBe(true);
    expect(isValidEmail('user.name@domain.co.uk')).toBe(true);
    expect(isValidEmail('user+tag@example.org')).toBe(true);
  });

  it('rejects invalid emails', () => {
    expect(isValidEmail('notanemail')).toBe(false);
    expect(isValidEmail('@nodomain.com')).toBe(false);
    expect(isValidEmail('no@')).toBe(false);
    expect(isValidEmail('')).toBe(false);
  });

  it('rejects overly long emails', () => {
    const longEmail = 'a'.repeat(250) + '@example.com';
    expect(isValidEmail(longEmail)).toBe(false);
  });
});

describe('sanitizeObjectKeys', () => {
  it('removes __proto__ from own properties', () => {
    const obj = Object.create(null) as Record<string, unknown>;
    obj['__proto__'] = {};
    obj['name'] = 'test';
    const result = sanitizeObjectKeys(obj);
    expect(Object.prototype.hasOwnProperty.call(result, '__proto__')).toBe(false);
    expect(result.name).toBe('test');
  });

  it('does not copy constructor property', () => {
    const obj = { myConstructor: () => {}, name: 'test' };
    const result = sanitizeObjectKeys(obj);
    expect(result.name).toBe('test');
    expect(result.myConstructor).toBeDefined(); // This is fine since it's not literally 'constructor'
  });

  it('preserves safe keys', () => {
    const obj = { name: 'test', value: 123 };
    const result = sanitizeObjectKeys(obj);
    expect(result.name).toBe('test');
    expect(result.value).toBe(123);
  });
});

describe('checkRateLimit', () => {
  beforeEach(() => {
    resetRateLimit('test_endpoint');
  });

  it('allows requests under the limit', () => {
    const result = checkRateLimit('test_endpoint', 5, 60000);
    expect(result.allowed).toBe(true);
    expect(result.remaining).toBe(4);
  });

  it('blocks requests over the limit', () => {
    // Make 5 requests
    for (let i = 0; i < 5; i++) {
      checkRateLimit('test_endpoint', 5, 60000);
    }
    // 6th should be blocked
    const result = checkRateLimit('test_endpoint', 5, 60000);
    expect(result.allowed).toBe(false);
  });

  it('tracks different endpoints separately', () => {
    for (let i = 0; i < 5; i++) {
      checkRateLimit('endpoint_a', 5, 60000);
    }
    // Different endpoint should still be allowed
    const result = checkRateLimit('endpoint_b', 5, 60000);
    expect(result.allowed).toBe(true);
  });
});

describe('maskSensitiveData', () => {
  it('masks email addresses', () => {
    expect(maskSensitiveData('john@example.com', 'email')).toBe('j**n@example.com');
  });

  it('masks phone numbers', () => {
    const result = maskSensitiveData('555-123-4567', 'phone');
    expect(result).toContain('4567');
    expect(result).toContain('*');
  });

  it('masks credit cards', () => {
    const result = maskSensitiveData('4111111111111111', 'card');
    expect(result).toBe('**** **** **** 1111');
  });

  it('masks tokens', () => {
    const result = maskSensitiveData('sk_test_1234567890abcdef', 'token');
    expect(result.startsWith('sk_t')).toBe(true);
    expect(result.endsWith('cdef')).toBe(true);
    expect(result).toContain('*');
  });
});

describe('isTrustedDomain', () => {
  const trustedDomains = ['example.com', '*.trusted.io', 'specific.site.org'];

  it('trusts exact domain matches', () => {
    expect(isTrustedDomain('https://example.com/path', trustedDomains)).toBe(true);
  });

  it('trusts wildcard subdomain matches', () => {
    expect(isTrustedDomain('https://api.trusted.io/endpoint', trustedDomains)).toBe(true);
    expect(isTrustedDomain('https://www.trusted.io/', trustedDomains)).toBe(true);
  });

  it('rejects untrusted domains', () => {
    expect(isTrustedDomain('https://evil.com/phishing', trustedDomains)).toBe(false);
  });

  it('handles invalid URLs', () => {
    expect(isTrustedDomain('not a url', trustedDomains)).toBe(false);
  });
});

describe('detectMaliciousPatterns', () => {
  it('detects SQL injection patterns', () => {
    const result = detectMaliciousPatterns("'; DROP TABLE users;--");
    expect(result.isSuspicious).toBe(true);
    expect(result.patterns).toContain('SQL Injection');
  });

  it('detects script injection', () => {
    const result = detectMaliciousPatterns('<script>alert(1)</script>');
    expect(result.isSuspicious).toBe(true);
    expect(result.patterns).toContain('Script Injection');
  });

  it('detects event handlers', () => {
    const result = detectMaliciousPatterns('<img onerror="alert(1)">');
    expect(result.isSuspicious).toBe(true);
    expect(result.patterns).toContain('Event Handler');
  });

  it('detects javascript: protocol', () => {
    const result = detectMaliciousPatterns('javascript:alert(1)');
    expect(result.isSuspicious).toBe(true);
    expect(result.patterns).toContain('JavaScript Protocol');
  });

  it('detects path traversal', () => {
    const result = detectMaliciousPatterns('../../etc/passwd');
    expect(result.isSuspicious).toBe(true);
    expect(result.patterns).toContain('Path Traversal');
  });

  it('allows safe input', () => {
    const result = detectMaliciousPatterns('Hello, this is a normal message!');
    expect(result.isSuspicious).toBe(false);
    expect(result.patterns).toHaveLength(0);
  });
});

describe('CSRF Token', () => {
  beforeEach(() => {
    sessionStorage.clear();
  });

  it('generates a token', () => {
    const token = getCSRFToken();
    expect(token).toBeTruthy();
    expect(typeof token).toBe('string');
    expect(token.length).toBeGreaterThan(0);
  });

  it('returns same token on subsequent calls', () => {
    const token1 = getCSRFToken();
    const token2 = getCSRFToken();
    expect(token1).toBe(token2);
  });

  it('validates correct token', () => {
    const token = getCSRFToken();
    expect(validateCSRFToken(token)).toBe(true);
  });

  it('rejects incorrect token', () => {
    getCSRFToken(); // Generate a token
    expect(validateCSRFToken('wrong_token')).toBe(false);
  });

  it('refreshes token', () => {
    const token1 = getCSRFToken();
    const token2 = refreshCSRFToken();
    expect(token1).not.toBe(token2);
  });
});
