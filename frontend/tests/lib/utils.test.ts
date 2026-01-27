/**
 * Utils library tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { cn, formatDate, formatRelativeTime, formatFileSize, truncate, generateId } from '@/lib/utils';

describe('cn (class name merger)', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar');
  });

  it('handles conditional classes', () => {
    expect(cn('base', true && 'included', false && 'excluded')).toBe('base included');
  });

  it('merges tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4');
  });

  it('handles undefined and null values', () => {
    expect(cn('base', undefined, null, 'end')).toBe('base end');
  });

  it('handles arrays of classes', () => {
    expect(cn(['foo', 'bar'], 'baz')).toBe('foo bar baz');
  });
});

describe('formatDate', () => {
  it('formats a date string', () => {
    // Use a full ISO string with time to avoid timezone issues
    const result = formatDate('2024-06-15T12:00:00Z');
    // Just check that it contains the month and year
    expect(result).toMatch(/Jun.*2024/);
  });

  it('formats a Date object', () => {
    const date = new Date(2024, 5, 15, 12, 0, 0); // June 15, 2024 at noon
    const result = formatDate(date);
    expect(result).toMatch(/Jun.*15.*2024/);
  });

  it('handles ISO date strings', () => {
    const result = formatDate('2024-12-25T10:30:00Z');
    expect(result).toMatch(/Dec.*2024/);
  });
});

describe('formatRelativeTime', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('returns "just now" for recent times', () => {
    const now = new Date('2024-06-15T12:00:00Z');
    vi.setSystemTime(now);
    
    const tenSecondsAgo = new Date('2024-06-15T11:59:50Z');
    expect(formatRelativeTime(tenSecondsAgo)).toBe('just now');
  });

  it('returns minutes ago', () => {
    const now = new Date('2024-06-15T12:00:00Z');
    vi.setSystemTime(now);
    
    const fiveMinutesAgo = new Date('2024-06-15T11:55:00Z');
    expect(formatRelativeTime(fiveMinutesAgo)).toBe('5m ago');
  });

  it('returns hours ago', () => {
    const now = new Date('2024-06-15T12:00:00Z');
    vi.setSystemTime(now);
    
    const twoHoursAgo = new Date('2024-06-15T10:00:00Z');
    expect(formatRelativeTime(twoHoursAgo)).toBe('2h ago');
  });

  it('returns days ago', () => {
    const now = new Date('2024-06-15T12:00:00Z');
    vi.setSystemTime(now);
    
    const threeDaysAgo = new Date('2024-06-12T12:00:00Z');
    expect(formatRelativeTime(threeDaysAgo)).toBe('3d ago');
  });

  it('returns formatted date for older dates', () => {
    const now = new Date('2024-06-15T12:00:00Z');
    vi.setSystemTime(now);
    
    const twoWeeksAgo = new Date('2024-06-01T12:00:00Z');
    const result = formatRelativeTime(twoWeeksAgo);
    expect(result).toMatch(/Jun 1, 2024/);
  });
});

describe('formatFileSize', () => {
  it('formats 0 bytes', () => {
    expect(formatFileSize(0)).toBe('0 Bytes');
  });

  it('formats bytes', () => {
    expect(formatFileSize(500)).toBe('500 Bytes');
  });

  it('formats kilobytes', () => {
    expect(formatFileSize(1024)).toBe('1 KB');
    expect(formatFileSize(2048)).toBe('2 KB');
    expect(formatFileSize(1536)).toBe('1.5 KB');
  });

  it('formats megabytes', () => {
    expect(formatFileSize(1048576)).toBe('1 MB');
    expect(formatFileSize(5242880)).toBe('5 MB');
  });

  it('formats gigabytes', () => {
    expect(formatFileSize(1073741824)).toBe('1 GB');
  });
});

describe('truncate', () => {
  it('returns original string if shorter than length', () => {
    expect(truncate('hello', 10)).toBe('hello');
  });

  it('returns original string if equal to length', () => {
    expect(truncate('hello', 5)).toBe('hello');
  });

  it('truncates and adds ellipsis if longer than length', () => {
    expect(truncate('hello world', 5)).toBe('hello...');
  });

  it('handles empty string', () => {
    expect(truncate('', 5)).toBe('');
  });

  it('handles length of 0', () => {
    expect(truncate('hello', 0)).toBe('...');
  });
});

describe('generateId', () => {
  it('returns a string', () => {
    const id = generateId();
    expect(typeof id).toBe('string');
  });

  it('returns a non-empty string', () => {
    const id = generateId();
    expect(id.length).toBeGreaterThan(0);
  });

  it('generates unique ids', () => {
    const ids = new Set(Array.from({ length: 100 }, () => generateId()));
    expect(ids.size).toBe(100);
  });
});
