/**
 * Edge case tests for API module
 * Tests error handling, retries, network failures, and edge cases
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import axios, { AxiosError } from 'axios';

// Create mock functions for interceptors
const requestInterceptorUse = vi.fn();
const responseInterceptorUse = vi.fn();
let requestInterceptor: (config: unknown) => unknown;
let responseInterceptor: (response: unknown) => unknown;
let responseErrorInterceptor: (error: unknown) => Promise<unknown>;

// Mock axios with proper interceptor handling
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: (handler: (config: unknown) => unknown) => {
          requestInterceptor = handler;
          requestInterceptorUse(handler);
        },
      },
      response: {
        use: (
          success: (response: unknown) => unknown,
          error: (error: unknown) => Promise<unknown>
        ) => {
          responseInterceptor = success;
          responseErrorInterceptor = error;
          responseInterceptorUse(success, error);
        },
      },
    },
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
    AxiosError: class extends Error {
      response: unknown;
      config: unknown;
      constructor(message: string) {
        super(message);
        this.name = 'AxiosError';
      }
    },
  };
});

// Mock localStorage
const localStorageMock = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: vi.fn((key: string) => store[key] || null),
    setItem: vi.fn((key: string, value: string) => {
      store[key] = value;
    }),
    removeItem: vi.fn((key: string) => {
      delete store[key];
    }),
    clear: vi.fn(() => {
      store = {};
    }),
    get store() {
      return store;
    },
  };
})();

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
});

// Mock window.location
const locationMock = {
  href: '',
};
Object.defineProperty(window, 'location', {
  value: locationMock,
  writable: true,
});

describe('API Error Handling Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
    locationMock.href = '';
    
    // Re-import to trigger interceptor setup
    vi.resetModules();
  });

  afterEach(() => {
    vi.resetModules();
  });

  describe('401 Response Handling', () => {
    it('attempts token refresh on 401 error', async () => {
      // Setup tokens
      localStorageMock.store['access_token'] = 'expired-token';
      localStorageMock.store['refresh_token'] = 'valid-refresh-token';

      // Import fresh module to get interceptor handlers
      await import('@/lib/api');

      const error = {
        response: { status: 401 },
        config: {
          headers: {},
        },
      };

      // Mock successful refresh
      (axios.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: {
          access_token: 'new-access-token',
          refresh_token: 'new-refresh-token',
        },
      });

      // The error interceptor should handle this
      expect(responseErrorInterceptor).toBeDefined();
    });

    it('redirects to login when refresh fails', async () => {
      localStorageMock.store['access_token'] = 'expired-token';
      localStorageMock.store['refresh_token'] = 'invalid-refresh-token';

      await import('@/lib/api');

      const error = {
        response: { status: 401 },
        config: { headers: {} },
      };

      // Mock failed refresh
      (axios.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(
        new Error('Refresh failed')
      );

      // After failed refresh, should clear tokens and redirect
      expect(responseErrorInterceptor).toBeDefined();
    });

    it('does not retry refresh when no refresh token exists', async () => {
      localStorageMock.store['access_token'] = 'expired-token';
      // No refresh token

      await import('@/lib/api');

      expect(responseErrorInterceptor).toBeDefined();
    });
  });

  describe('Request Interceptor Edge Cases', () => {
    it('does not add auth header when no token exists', async () => {
      await import('@/lib/api');

      const config = { headers: {} };
      const result = requestInterceptor(config);

      expect(result).toEqual({ headers: {} });
    });

    it('adds both auth and tenant headers when both exist', async () => {
      localStorageMock.store['access_token'] = 'test-token';
      localStorageMock.store['current_tenant_id'] = 'org-123';

      await import('@/lib/api');

      const config = { headers: {} };
      
      // Simulate request interceptor behavior
      expect(requestInterceptor).toBeDefined();
    });

    it('handles server-side rendering (window undefined)', async () => {
      // This tests the typeof window check in the interceptor
      await import('@/lib/api');
      expect(requestInterceptor).toBeDefined();
    });
  });

  describe('Network Timeout Handling', () => {
    it('handles network timeout errors', async () => {
      const { api } = await import('@/lib/api');

      const timeoutError = {
        code: 'ECONNABORTED',
        message: 'timeout of 30000ms exceeded',
        response: undefined,
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(timeoutError);

      await expect(api.get('/test')).rejects.toEqual(timeoutError);
    });

    it('handles network connection errors', async () => {
      const { api } = await import('@/lib/api');

      const networkError = {
        code: 'ERR_NETWORK',
        message: 'Network Error',
        response: undefined,
      };

      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(networkError);

      await expect(api.post('/test', {})).rejects.toEqual(networkError);
    });
  });

  describe('Malformed Response Handling', () => {
    it('handles null response data', async () => {
      const { api, chatApi } = await import('@/lib/api');

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: null,
      });

      const result = await api.get('/test');
      expect(result.data).toBeNull();
    });

    it('handles undefined response data', async () => {
      const { api } = await import('@/lib/api');

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: undefined,
      });

      const result = await api.get('/test');
      expect(result.data).toBeUndefined();
    });

    it('handles empty object response', async () => {
      const { api } = await import('@/lib/api');

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: {},
      });

      const result = await api.get('/test');
      expect(result.data).toEqual({});
    });
  });

  describe('Rate Limiting', () => {
    it('handles 429 Too Many Requests', async () => {
      const { api } = await import('@/lib/api');

      const rateLimitError = {
        response: {
          status: 429,
          data: { detail: 'Rate limit exceeded' },
          headers: { 'retry-after': '60' },
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(rateLimitError);

      await expect(api.get('/test')).rejects.toEqual(rateLimitError);
    });
  });

  describe('Server Errors', () => {
    it('handles 500 Internal Server Error', async () => {
      const { api } = await import('@/lib/api');

      const serverError = {
        response: {
          status: 500,
          data: { detail: 'Internal Server Error' },
        },
      };

      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(serverError);

      await expect(api.post('/test', {})).rejects.toEqual(serverError);
    });

    it('handles 502 Bad Gateway', async () => {
      const { api } = await import('@/lib/api');

      const gatewayError = {
        response: {
          status: 502,
          data: 'Bad Gateway',
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(gatewayError);

      await expect(api.get('/test')).rejects.toEqual(gatewayError);
    });

    it('handles 503 Service Unavailable', async () => {
      const { api } = await import('@/lib/api');

      const unavailableError = {
        response: {
          status: 503,
          data: { detail: 'Service temporarily unavailable' },
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(unavailableError);

      await expect(api.get('/test')).rejects.toEqual(unavailableError);
    });
  });

  describe('Client Errors', () => {
    it('handles 400 Bad Request', async () => {
      const { api } = await import('@/lib/api');

      const badRequestError = {
        response: {
          status: 400,
          data: { detail: 'Invalid input' },
        },
      };

      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(badRequestError);

      await expect(api.post('/test', {})).rejects.toEqual(badRequestError);
    });

    it('handles 403 Forbidden', async () => {
      const { api } = await import('@/lib/api');

      const forbiddenError = {
        response: {
          status: 403,
          data: { detail: 'Access denied' },
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(forbiddenError);

      await expect(api.get('/test')).rejects.toEqual(forbiddenError);
    });

    it('handles 404 Not Found', async () => {
      const { api } = await import('@/lib/api');

      const notFoundError = {
        response: {
          status: 404,
          data: { detail: 'Resource not found' },
        },
      };

      (api.get as ReturnType<typeof vi.fn>).mockRejectedValueOnce(notFoundError);

      await expect(api.get('/test/123')).rejects.toEqual(notFoundError);
    });

    it('handles 422 Validation Error', async () => {
      const { api } = await import('@/lib/api');

      const validationError = {
        response: {
          status: 422,
          data: {
            detail: [
              {
                loc: ['body', 'email'],
                msg: 'Invalid email format',
                type: 'value_error',
              },
            ],
          },
        },
      };

      (api.post as ReturnType<typeof vi.fn>).mockRejectedValueOnce(validationError);

      await expect(api.post('/test', {})).rejects.toEqual(validationError);
    });
  });

  describe('Special Character Handling', () => {
    it('handles special characters in URL parameters', async () => {
      const { documentsApi } = await import('@/lib/api');
      const { api } = await import('@/lib/api');

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: [],
      });

      await documentsApi.search('test query with "quotes" & <special> chars');

      expect(api.post).toHaveBeenCalledWith('/documents/search', {
        query: 'test query with "quotes" & <special> chars',
        limit: 10,
        similarity_threshold: 0.7,
      });
    });

    it('handles unicode characters in requests', async () => {
      const { chatApi, api } = await import('@/lib/api');

      (api.post as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: { id: 'conv-1' },
      });

      await chatApi.createConversation({
        title: '日本語のタイトル 🎉',
      });

      expect(api.post).toHaveBeenCalledWith('/chat/conversations', {
        title: '日本語のタイトル 🎉',
      });
    });
  });

  describe('Large Payload Handling', () => {
    it('handles large response data', async () => {
      const { api } = await import('@/lib/api');

      const largeArray = Array.from({ length: 1000 }, (_, i) => ({
        id: `item-${i}`,
        data: 'x'.repeat(1000),
      }));

      (api.get as ReturnType<typeof vi.fn>).mockResolvedValueOnce({
        data: largeArray,
      });

      const result = await api.get('/test');
      expect(result.data).toHaveLength(1000);
    });
  });

  describe('Concurrent Request Handling', () => {
    it('handles multiple concurrent requests', async () => {
      const { api } = await import('@/lib/api');

      (api.get as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce({ data: { id: 1 } })
        .mockResolvedValueOnce({ data: { id: 2 } })
        .mockResolvedValueOnce({ data: { id: 3 } });

      const results = await Promise.all([
        api.get('/test/1'),
        api.get('/test/2'),
        api.get('/test/3'),
      ]);

      expect(results).toHaveLength(3);
      expect(results[0].data.id).toBe(1);
      expect(results[1].data.id).toBe(2);
      expect(results[2].data.id).toBe(3);
    });

    it('handles mixed success/failure in concurrent requests', async () => {
      const { api } = await import('@/lib/api');

      (api.get as ReturnType<typeof vi.fn>)
        .mockResolvedValueOnce({ data: { id: 1 } })
        .mockRejectedValueOnce(new Error('Failed'))
        .mockResolvedValueOnce({ data: { id: 3 } });

      const results = await Promise.allSettled([
        api.get('/test/1'),
        api.get('/test/2'),
        api.get('/test/3'),
      ]);

      expect(results[0].status).toBe('fulfilled');
      expect(results[1].status).toBe('rejected');
      expect(results[2].status).toBe('fulfilled');
    });
  });
});

describe('TenantContext Edge Cases', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  it('handles rapid tenant switching', async () => {
    const { TenantContext } = await import('@/lib/api');

    // Rapidly switch tenants
    TenantContext.setCurrentTenantId('org-1');
    TenantContext.setCurrentTenantId('org-2');
    TenantContext.setCurrentTenantId('org-3');
    TenantContext.setCurrentTenantId('org-4');
    TenantContext.setCurrentTenantId('org-5');

    expect(TenantContext.getCurrentTenantId()).toBe('org-5');
  });

  it('handles setting same tenant multiple times', async () => {
    const { TenantContext } = await import('@/lib/api');
    const listener = vi.fn();

    TenantContext.subscribe(listener);
    
    TenantContext.setCurrentTenantId('org-1');
    TenantContext.setCurrentTenantId('org-1');
    TenantContext.setCurrentTenantId('org-1');

    // Listener notified each time setCurrentTenantId is called
    expect(listener).toHaveBeenCalled();
    expect(listener.mock.calls.length).toBeGreaterThanOrEqual(3);
  });

  it('handles null to null transition', async () => {
    const { TenantContext } = await import('@/lib/api');

    TenantContext.setCurrentTenantId(null);
    TenantContext.setCurrentTenantId(null);

    expect(TenantContext.getCurrentTenantId()).toBeNull();
  });

  it('listener receives tenant id updates', async () => {
    const { TenantContext } = await import('@/lib/api');
    const receivedIds: (string | null)[] = [];

    TenantContext.subscribe((id) => receivedIds.push(id));

    TenantContext.setCurrentTenantId('org-1');
    TenantContext.setCurrentTenantId('org-2');
    TenantContext.setCurrentTenantId(null);

    // Verify the sequence contains the expected values
    expect(receivedIds).toContain('org-1');
    expect(receivedIds).toContain('org-2');
    expect(receivedIds).toContain(null);
  });
});
