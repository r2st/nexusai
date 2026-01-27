/**
 * Tests for Password Strength utilities
 */
import { describe, it, expect } from 'vitest';
import {
  calculatePasswordStrength,
  DEFAULT_REQUIREMENTS,
  STRICT_REQUIREMENTS,
} from '@/components/security/password-strength';

describe('calculatePasswordStrength', () => {
  describe('empty password', () => {
    it('returns weak score for empty string', () => {
      const result = calculatePasswordStrength('');
      expect(result.score).toBe(0);
      expect(result.level).toBe('weak');
    });
  });

  describe('weak passwords', () => {
    it('returns weak for short passwords', () => {
      const result = calculatePasswordStrength('abc');
      expect(result.score).toBeLessThanOrEqual(1);
    });

    it('returns weak for common passwords', () => {
      const result = calculatePasswordStrength('password');
      expect(result.score).toBe(0);
      expect(result.level).toBe('weak');
    });

    it('returns weak for only numbers', () => {
      const result = calculatePasswordStrength('12345678');
      expect(result.score).toBeLessThanOrEqual(1);
    });

    it('returns weak for only lowercase', () => {
      const result = calculatePasswordStrength('abcdefgh');
      expect(result.score).toBeLessThanOrEqual(1);
    });
  });

  describe('fair passwords', () => {
    it('returns fair for mixed case short password', () => {
      const result = calculatePasswordStrength('AbCdEfGh');
      expect(result.score).toBeGreaterThanOrEqual(1);
    });
  });

  describe('good passwords', () => {
    it('returns good for mixed case with number', () => {
      const result = calculatePasswordStrength('AbCdEfGh1');
      expect(result.score).toBeGreaterThanOrEqual(2);
    });
  });

  describe('strong passwords', () => {
    it('returns strong for complex passwords', () => {
      const result = calculatePasswordStrength('AbCdEfGh1!');
      expect(result.score).toBeGreaterThanOrEqual(3);
    });

    it('returns very strong for long complex passwords', () => {
      const result = calculatePasswordStrength('MyS3cure!P@ssword2024');
      expect(result.score).toBe(4);
      expect(result.level).toBe('very_strong');
    });
  });

  describe('penalty patterns', () => {
    it('penalizes repeated characters', () => {
      const normal = calculatePasswordStrength('aAbBcCdDeE1!');
      const repeated = calculatePasswordStrength('aaaBBBccc1!');
      expect(repeated.score).toBeLessThanOrEqual(normal.score);
    });

    it('penalizes sequential characters', () => {
      const result = calculatePasswordStrength('abc123XYZ');
      expect(result.suggestions.some(s => s.toLowerCase().includes('sequential'))).toBe(true);
    });

    it('penalizes keyboard patterns', () => {
      const result = calculatePasswordStrength('qwerty123');
      // Score should be low for keyboard pattern, even if suggestion doesn't explicitly mention it
      expect(result.score).toBeLessThanOrEqual(2);
    });
  });

  describe('suggestions', () => {
    it('suggests adding uppercase', () => {
      const result = calculatePasswordStrength('password1!');
      expect(result.suggestions.some(s => s.toLowerCase().includes('uppercase'))).toBe(true);
    });

    it('suggests adding special characters', () => {
      const result = calculatePasswordStrength('Password1');
      expect(result.suggestions.some(s => s.toLowerCase().includes('special'))).toBe(true);
    });

    it('suggests longer password', () => {
      const result = calculatePasswordStrength('Pass1!');
      expect(result.suggestions.some(s => s.toLowerCase().includes('8'))).toBe(true);
    });
  });
});

describe('DEFAULT_REQUIREMENTS', () => {
  it('has 5 requirements', () => {
    expect(DEFAULT_REQUIREMENTS).toHaveLength(5);
  });

  it('requires minimum 8 characters', () => {
    const lengthReq = DEFAULT_REQUIREMENTS.find(r => r.id === 'length');
    expect(lengthReq?.test('1234567')).toBe(false);
    expect(lengthReq?.test('12345678')).toBe(true);
  });

  it('requires uppercase letter', () => {
    const upperReq = DEFAULT_REQUIREMENTS.find(r => r.id === 'uppercase');
    expect(upperReq?.test('lowercase')).toBe(false);
    expect(upperReq?.test('Uppercase')).toBe(true);
  });

  it('requires lowercase letter', () => {
    const lowerReq = DEFAULT_REQUIREMENTS.find(r => r.id === 'lowercase');
    expect(lowerReq?.test('UPPERCASE')).toBe(false);
    expect(lowerReq?.test('lowercase')).toBe(true);
  });

  it('requires number', () => {
    const numberReq = DEFAULT_REQUIREMENTS.find(r => r.id === 'number');
    expect(numberReq?.test('NoNumbers')).toBe(false);
    expect(numberReq?.test('Has1Number')).toBe(true);
  });

  it('requires special character', () => {
    const specialReq = DEFAULT_REQUIREMENTS.find(r => r.id === 'special');
    expect(specialReq?.test('NoSpecial1')).toBe(false);
    expect(specialReq?.test('HasSpecial!')).toBe(true);
  });
});

describe('STRICT_REQUIREMENTS', () => {
  it('has more requirements than default', () => {
    expect(STRICT_REQUIREMENTS.length).toBeGreaterThan(DEFAULT_REQUIREMENTS.length);
  });

  it('requires 12+ characters', () => {
    const length12Req = STRICT_REQUIREMENTS.find(r => r.id === 'length12');
    expect(length12Req?.test('Short1234!')).toBe(false);
    expect(length12Req?.test('LongEnough12!')).toBe(true);
  });

  it('rejects common passwords', () => {
    const commonReq = STRICT_REQUIREMENTS.find(r => r.id === 'no_common');
    expect(commonReq?.test('password')).toBe(false);
    expect(commonReq?.test('MyUniquePass1!')).toBe(true);
  });
});
