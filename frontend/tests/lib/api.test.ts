/**
 * API module tests
 * Tests for TenantContext, axios interceptors, and API methods
 */

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import axios from 'axios';

// Mock axios before importing the module
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  };
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance),
      post: vi.fn(),
    },
  };
});

// Import after mocking
import { TenantContext, api, authApi, chatApi, documentsApi, organizationsApi } from '@/lib/api';

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

describe('TenantContext', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  describe('getCurrentTenantId', () => {
    it('returns null when no tenant is set', () => {
      expect(TenantContext.getCurrentTenantId()).toBeNull();
    });

    it('returns tenant id when set', () => {
      localStorageMock.store['current_tenant_id'] = 'org-123';
      expect(TenantContext.getCurrentTenantId()).toBe('org-123');
    });
  });

  describe('setCurrentTenantId', () => {
    it('sets tenant id in localStorage', () => {
      TenantContext.setCurrentTenantId('org-456');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('current_tenant_id', 'org-456');
    });

    it('removes tenant id when null is passed', () => {
      TenantContext.setCurrentTenantId(null);
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('current_tenant_id');
    });

    it('notifies listeners on tenant change', () => {
      const listener = vi.fn();
      TenantContext.subscribe(listener);

      TenantContext.setCurrentTenantId('org-789');
      expect(listener).toHaveBeenCalledWith('org-789');
    });
  });

  describe('subscribe', () => {
    it('adds listener and returns unsubscribe function', () => {
      const listener = vi.fn();
      const unsubscribe = TenantContext.subscribe(listener);

      TenantContext.setCurrentTenantId('org-1');
      expect(listener).toHaveBeenCalledTimes(1);

      unsubscribe();
      TenantContext.setCurrentTenantId('org-2');
      expect(listener).toHaveBeenCalledTimes(1); // Not called again
    });

    it('supports multiple listeners', () => {
      const listener1 = vi.fn();
      const listener2 = vi.fn();

      TenantContext.subscribe(listener1);
      TenantContext.subscribe(listener2);

      TenantContext.setCurrentTenantId('org-multi');
      expect(listener1).toHaveBeenCalledWith('org-multi');
      expect(listener2).toHaveBeenCalledWith('org-multi');
    });
  });

  describe('clear', () => {
    it('clears the tenant context', () => {
      TenantContext.setCurrentTenantId('org-clear');
      TenantContext.clear();
      expect(localStorageMock.removeItem).toHaveBeenCalledWith('current_tenant_id');
    });
  });
});

describe('API Instance', () => {
  beforeEach(() => {
    localStorageMock.clear();
    vi.clearAllMocks();
  });

  it('exports api instance', () => {
    expect(api).toBeDefined();
    expect(api.get).toBeDefined();
    expect(api.post).toBeDefined();
  });

  it('has interceptors configured', () => {
    expect(api.interceptors).toBeDefined();
    expect(api.interceptors.request).toBeDefined();
    expect(api.interceptors.response).toBeDefined();
  });

  it('api instance has required methods', () => {
    expect(typeof api.get).toBe('function');
    expect(typeof api.post).toBe('function');
    expect(typeof api.put).toBe('function');
    expect(typeof api.delete).toBe('function');
  });
});

describe('authApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('register', () => {
    it('calls POST /auth/register with correct data', async () => {
      const mockResponse = {
        data: {
          user: { id: 'user-1', email: 'test@example.com' },
          tokens: { access_token: 'token', refresh_token: 'refresh' },
        },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await authApi.register({
        email: 'test@example.com',
        username: 'testuser',
        password: 'password123',
        full_name: 'Test User',
      });

      expect(api.post).toHaveBeenCalledWith('/auth/register', {
        email: 'test@example.com',
        username: 'testuser',
        password: 'password123',
        full_name: 'Test User',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('login', () => {
    it('calls POST /auth/login with credentials', async () => {
      const mockResponse = {
        data: {
          user: { id: 'user-1' },
          tokens: { access_token: 'token' },
        },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await authApi.login('test@example.com', 'password');

      expect(api.post).toHaveBeenCalledWith('/auth/login', {
        email: 'test@example.com',
        password: 'password',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('refresh', () => {
    it('calls POST /auth/refresh with refresh token', async () => {
      const mockResponse = {
        data: { access_token: 'new-token', refresh_token: 'new-refresh' },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await authApi.refresh('old-refresh-token');

      expect(api.post).toHaveBeenCalledWith('/auth/refresh', {
        refresh_token: 'old-refresh-token',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('forgotPassword', () => {
    it('calls POST /auth/forgot-password', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await authApi.forgotPassword('test@example.com');

      expect(api.post).toHaveBeenCalledWith('/auth/forgot-password', {
        email: 'test@example.com',
      });
    });
  });

  describe('resetPassword', () => {
    it('calls POST /auth/reset-password with token and new password', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await authApi.resetPassword('reset-token', 'newPassword123');

      expect(api.post).toHaveBeenCalledWith('/auth/reset-password', {
        token: 'reset-token',
        new_password: 'newPassword123',
      });
    });
  });
});

describe('chatApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('createConversation', () => {
    it('calls POST /chat/conversations', async () => {
      const mockResponse = {
        data: { id: 'conv-1', title: 'New Chat' },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await chatApi.createConversation({
        title: 'New Chat',
        model_provider: 'openai',
        model_name: 'gpt-4',
      });

      expect(api.post).toHaveBeenCalledWith('/chat/conversations', {
        title: 'New Chat',
        model_provider: 'openai',
        model_name: 'gpt-4',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('listConversations', () => {
    it('calls GET /chat/conversations with pagination', async () => {
      const mockResponse = {
        data: [{ id: 'conv-1' }, { id: 'conv-2' }],
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await chatApi.listConversations(10, 20);

      expect(api.get).toHaveBeenCalledWith('/chat/conversations', {
        params: { limit: 10, offset: 20 },
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('uses default pagination values', async () => {
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });

      await chatApi.listConversations();

      expect(api.get).toHaveBeenCalledWith('/chat/conversations', {
        params: { limit: 50, offset: 0 },
      });
    });
  });

  describe('getConversation', () => {
    it('calls GET /chat/conversations/:id', async () => {
      const mockResponse = {
        data: { id: 'conv-123', title: 'Test' },
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await chatApi.getConversation('conv-123');

      expect(api.get).toHaveBeenCalledWith('/chat/conversations/conv-123');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('getMessages', () => {
    it('calls GET /chat/conversations/:id/messages', async () => {
      const mockResponse = {
        data: [{ id: 'msg-1', content: 'Hello' }],
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await chatApi.getMessages('conv-123');

      expect(api.get).toHaveBeenCalledWith('/chat/conversations/conv-123/messages');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('deleteConversation', () => {
    it('calls DELETE /chat/conversations/:id', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await chatApi.deleteConversation('conv-123');

      expect(api.delete).toHaveBeenCalledWith('/chat/conversations/conv-123');
    });
  });
});

describe('documentsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('list', () => {
    it('calls GET /documents with pagination', async () => {
      const mockResponse = {
        data: [{ id: 'doc-1' }],
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await documentsApi.list(25, 10);

      expect(api.get).toHaveBeenCalledWith('/documents', {
        params: { limit: 25, offset: 10 },
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('get', () => {
    it('calls GET /documents/:id', async () => {
      const mockResponse = {
        data: { id: 'doc-123', original_filename: 'test.pdf' },
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await documentsApi.get('doc-123');

      expect(api.get).toHaveBeenCalledWith('/documents/doc-123');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('search', () => {
    it('calls POST /documents/search with query', async () => {
      const mockResponse = {
        data: [{ id: 'result-1', similarity: 0.95 }],
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await documentsApi.search('test query', 5, 0.8);

      expect(api.post).toHaveBeenCalledWith('/documents/search', {
        query: 'test query',
        limit: 5,
        similarity_threshold: 0.8,
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('uses default parameters', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: [] });

      await documentsApi.search('query');

      expect(api.post).toHaveBeenCalledWith('/documents/search', {
        query: 'query',
        limit: 10,
        similarity_threshold: 0.7,
      });
    });
  });

  describe('delete', () => {
    it('calls DELETE /documents/:id', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await documentsApi.delete('doc-123');

      expect(api.delete).toHaveBeenCalledWith('/documents/doc-123');
    });
  });

  describe('process', () => {
    it('calls POST /documents/:id/process', async () => {
      const mockResponse = {
        data: { id: 'doc-123', status: 'processing' },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await documentsApi.process('doc-123');

      expect(api.post).toHaveBeenCalledWith('/documents/doc-123/process');
      expect(result).toEqual(mockResponse.data);
    });
  });
});

describe('organizationsApi', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorageMock.clear();
  });

  describe('list', () => {
    it('calls GET /organizations', async () => {
      const mockResponse = {
        data: [{ id: 'org-1', name: 'Org 1' }],
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.list();

      expect(api.get).toHaveBeenCalledWith('/organizations');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('get', () => {
    it('calls GET /organizations/:id', async () => {
      const mockResponse = {
        data: { id: 'org-123', name: 'Test Org' },
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.get('org-123');

      expect(api.get).toHaveBeenCalledWith('/organizations/org-123');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('create', () => {
    it('calls POST /organizations', async () => {
      const mockResponse = {
        data: { id: 'org-new', name: 'New Org', slug: 'new-org' },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.create({
        name: 'New Org',
        description: 'A new organization',
      });

      expect(api.post).toHaveBeenCalledWith('/organizations', {
        name: 'New Org',
        description: 'A new organization',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('update', () => {
    it('calls PUT /organizations/:id', async () => {
      const mockResponse = {
        data: { id: 'org-123', name: 'Updated Org' },
      };
      (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.update('org-123', { name: 'Updated Org' });

      expect(api.put).toHaveBeenCalledWith('/organizations/org-123', { name: 'Updated Org' });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('delete', () => {
    it('calls DELETE /organizations/:id', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await organizationsApi.delete('org-123');

      expect(api.delete).toHaveBeenCalledWith('/organizations/org-123');
    });
  });

  describe('listMembers', () => {
    it('calls GET /organizations/:id/members', async () => {
      const mockResponse = {
        data: [{ id: 'member-1', user_id: 'user-1', role: 'admin' }],
      };
      (api.get as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.listMembers('org-123');

      expect(api.get).toHaveBeenCalledWith('/organizations/org-123/members');
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('inviteMember', () => {
    it('calls POST /organizations/:id/members/invite', async () => {
      const mockResponse = {
        data: { id: 'member-new', role: 'member' },
      };
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.inviteMember('org-123', 'user@example.com', 'admin');

      expect(api.post).toHaveBeenCalledWith('/organizations/org-123/members/invite', {
        email: 'user@example.com',
        role: 'admin',
      });
      expect(result).toEqual(mockResponse.data);
    });

    it('uses default role of member', async () => {
      (api.post as ReturnType<typeof vi.fn>).mockResolvedValue({ data: {} });

      await organizationsApi.inviteMember('org-123', 'user@example.com');

      expect(api.post).toHaveBeenCalledWith('/organizations/org-123/members/invite', {
        email: 'user@example.com',
        role: 'member',
      });
    });
  });

  describe('removeMember', () => {
    it('calls DELETE /organizations/:orgId/members/:userId', async () => {
      (api.delete as ReturnType<typeof vi.fn>).mockResolvedValue({});

      await organizationsApi.removeMember('org-123', 'user-456');

      expect(api.delete).toHaveBeenCalledWith('/organizations/org-123/members/user-456');
    });
  });

  describe('updateMemberRole', () => {
    it('calls PUT /organizations/:orgId/members/:userId', async () => {
      const mockResponse = {
        data: { id: 'member-1', role: 'admin' },
      };
      (api.put as ReturnType<typeof vi.fn>).mockResolvedValue(mockResponse);

      const result = await organizationsApi.updateMemberRole('org-123', 'user-456', 'admin');

      expect(api.put).toHaveBeenCalledWith('/organizations/org-123/members/user-456', {
        role: 'admin',
      });
      expect(result).toEqual(mockResponse.data);
    });
  });

  describe('switchTo', () => {
    it('sets tenant context', () => {
      organizationsApi.switchTo('org-switch');
      expect(localStorageMock.setItem).toHaveBeenCalledWith('current_tenant_id', 'org-switch');
    });
  });

  describe('getCurrentId', () => {
    it('returns current tenant id', () => {
      localStorageMock.store['current_tenant_id'] = 'org-current';
      expect(organizationsApi.getCurrentId()).toBe('org-current');
    });

    it('returns null when no tenant set', () => {
      expect(organizationsApi.getCurrentId()).toBeNull();
    });
  });
});
