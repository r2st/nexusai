/**
 * Mock localStorage for tests
 */

import { vi } from 'vitest';

class LocalStorageMock {
  private store: Record<string, string> = {};

  getItem(key: string): string | null {
    return this.store[key] || null;
  }

  setItem(key: string, value: string): void {
    this.store[key] = value;
  }

  removeItem(key: string): void {
    delete this.store[key];
  }

  clear(): void {
    this.store = {};
  }

  get length(): number {
    return Object.keys(this.store).length;
  }

  key(index: number): string | null {
    const keys = Object.keys(this.store);
    return keys[index] || null;
  }
}

// Create spied localStorage mock
export function createLocalStorageMock() {
  const mock = new LocalStorageMock();
  return {
    getItem: vi.fn((key: string) => mock.getItem(key)),
    setItem: vi.fn((key: string, value: string) => mock.setItem(key, value)),
    removeItem: vi.fn((key: string) => mock.removeItem(key)),
    clear: vi.fn(() => mock.clear()),
    get length() {
      return mock.length;
    },
    key: vi.fn((index: number) => mock.key(index)),
    _mock: mock, // Access to underlying mock for testing
  };
}

// Setup localStorage mock globally
export function setupLocalStorageMock() {
  const mockStorage = createLocalStorageMock();
  Object.defineProperty(window, 'localStorage', {
    value: mockStorage,
    writable: true,
  });
  return mockStorage;
}

// Helper to set auth tokens in localStorage
export function setAuthTokens(
  accessToken = 'mock-access-token',
  refreshToken = 'mock-refresh-token'
) {
  localStorage.setItem('access_token', accessToken);
  localStorage.setItem('refresh_token', refreshToken);
}

// Helper to clear auth tokens from localStorage
export function clearAuthTokens() {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
}
