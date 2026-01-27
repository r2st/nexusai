/**
 * Mock for next/navigation
 * Used to mock router in tests
 */

import { vi } from 'vitest';

export const mockRouter = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};

export const mockSearchParams = new URLSearchParams();

export const mockParams = {};

// Mock useRouter
export const useRouter = vi.fn(() => mockRouter);

// Mock useSearchParams
export const useSearchParams = vi.fn(() => mockSearchParams);

// Mock useParams
export const useParams = vi.fn(() => mockParams);

// Mock usePathname
export const usePathname = vi.fn(() => '/');

// Reset all mocks
export function resetNavigationMocks() {
  mockRouter.push.mockClear();
  mockRouter.replace.mockClear();
  mockRouter.back.mockClear();
  mockRouter.forward.mockClear();
  mockRouter.refresh.mockClear();
  mockRouter.prefetch.mockClear();
  useRouter.mockClear();
  useSearchParams.mockClear();
  useParams.mockClear();
  usePathname.mockClear();
}

// Helper to set search params for a test
export function setMockSearchParams(params: Record<string, string>) {
  const newParams = new URLSearchParams(params);
  useSearchParams.mockReturnValue(newParams);
  return newParams;
}

// Helper to set pathname for a test
export function setMockPathname(pathname: string) {
  usePathname.mockReturnValue(pathname);
}

// Helper to set params for a test
export function setMockParams(params: Record<string, string>) {
  useParams.mockReturnValue(params);
}
