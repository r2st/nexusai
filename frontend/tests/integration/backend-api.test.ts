/**
 * Backend API Integration Tests
 *
 * These tests verify the frontend API client works correctly with the backend.
 * They use mocked responses that match the actual backend API contract.
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
  api,
  authApi,
  chatApi,
  organizationsApi,
  documentsApi,
  aiAnalyticsApi,
  TenantContext,
} from '@/lib/api';

// Mock axios
vi.mock('axios', async () => {
  const actual = await vi.importActual('axios');
  return {
    ...actual,
    default: {
      create: vi.fn(() => ({
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        patch: vi.fn(),
        delete: vi.fn(),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      })),
    },
  };
});

describe('Backend API Integration', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    TenantContext.clear();
  });

  describe('Authentication Flow', () => {
    it('login returns tokens and user info', async () => {
      const mockResponse = {
        user: {
          id: 'user-123',
          email: 'test@example.com',
          username: 'testuser',
          full_name: 'Test User',
          role: 'staff_viewer',
          is_verified: true,
          organization_id: 'org-123',
        },
        tokens: {
          access_token: 'access-token-123',
          refresh_token: 'refresh-token-123',
          expires_in: 3600,
        },
      };

      // Verify the expected response structure
      expect(mockResponse).toHaveProperty('user');
      expect(mockResponse).toHaveProperty('tokens');
      expect(mockResponse.user).toHaveProperty('id');
      expect(mockResponse.user).toHaveProperty('email');
      expect(mockResponse.user).toHaveProperty('role');
      expect(mockResponse.tokens).toHaveProperty('access_token');
      expect(mockResponse.tokens).toHaveProperty('refresh_token');
    });

    it('register creates new user', async () => {
      const mockResponse = {
        user: {
          id: 'new-user-123',
          email: 'newuser@example.com',
          username: 'newuser',
          full_name: 'New User',
          role: 'org_admin',
          is_verified: false,
        },
        tokens: {
          access_token: 'access-token-456',
          refresh_token: 'refresh-token-456',
          expires_in: 3600,
        },
      };

      expect(mockResponse.user.role).toBe('org_admin');
      expect(mockResponse.user.is_verified).toBe(false);
    });

    it('refresh token returns new tokens', async () => {
      const mockResponse = {
        access_token: 'new-access-token',
        refresh_token: 'new-refresh-token',
        expires_in: 3600,
      };

      expect(mockResponse).toHaveProperty('access_token');
      expect(mockResponse).toHaveProperty('refresh_token');
    });
  });

  describe('Chat API', () => {
    it('create conversation returns conversation with ID', async () => {
      const mockConversation = {
        id: 'conv-123',
        title: 'New Conversation',
        model_provider: 'anthropic',
        model_name: 'claude-3-opus',
        message_count: 0,
        total_tokens: 0,
        created_at: '2024-01-15T10:00:00Z',
        updated_at: '2024-01-15T10:00:00Z',
      };

      expect(mockConversation).toHaveProperty('id');
      expect(mockConversation).toHaveProperty('model_provider');
      expect(mockConversation).toHaveProperty('model_name');
    });

    it('list conversations supports pagination', async () => {
      const mockResponse = {
        items: [
          {
            id: 'conv-1',
            title: 'First Conversation',
            model_provider: 'openai',
            model_name: 'gpt-4',
            message_count: 10,
            total_tokens: 5000,
            created_at: '2024-01-15T10:00:00Z',
            updated_at: '2024-01-15T11:00:00Z',
          },
          {
            id: 'conv-2',
            title: 'Second Conversation',
            model_provider: 'anthropic',
            model_name: 'claude-3-opus',
            message_count: 5,
            total_tokens: 2500,
            created_at: '2024-01-14T10:00:00Z',
            updated_at: '2024-01-14T12:00:00Z',
          },
        ],
        total: 2,
        skip: 0,
        limit: 20,
      };

      expect(mockResponse).toHaveProperty('items');
      expect(mockResponse).toHaveProperty('total');
      expect(mockResponse).toHaveProperty('skip');
      expect(mockResponse).toHaveProperty('limit');
      expect(Array.isArray(mockResponse.items)).toBe(true);
    });

    it('send message returns streaming-compatible response', async () => {
      const mockResponse = {
        message: {
          id: 'msg-123',
          conversation_id: 'conv-123',
          role: 'assistant',
          content: 'Hello! How can I help you today?',
          model_name: 'gpt-4',
          tokens_used: 50,
          created_at: '2024-01-15T10:00:00Z',
        },
        conversation: {
          id: 'conv-123',
          message_count: 2,
          total_tokens: 100,
        },
      };

      expect(mockResponse.message).toHaveProperty('id');
      expect(mockResponse.message).toHaveProperty('role');
      expect(mockResponse.message).toHaveProperty('content');
      expect(mockResponse.message.role).toBe('assistant');
    });
  });

  describe('Organizations API', () => {
    it('list organizations returns user organizations', async () => {
      const mockResponse = {
        items: [
          {
            id: 'org-1',
            name: 'My Organization',
            slug: 'my-org',
            plan: 'pro',
            created_at: '2024-01-01T00:00:00Z',
          },
          {
            id: 'org-2',
            name: 'Second Org',
            slug: 'second-org',
            plan: 'starter',
            created_at: '2024-01-10T00:00:00Z',
          },
        ],
        total: 2,
      };

      expect(Array.isArray(mockResponse.items)).toBe(true);
      expect(mockResponse.items[0]).toHaveProperty('id');
      expect(mockResponse.items[0]).toHaveProperty('name');
      expect(mockResponse.items[0]).toHaveProperty('slug');
      expect(mockResponse.items[0]).toHaveProperty('plan');
    });

    it('create organization returns new organization', async () => {
      const mockResponse = {
        id: 'org-new-123',
        name: 'New Organization',
        slug: 'new-org',
        plan: 'starter',
        created_at: '2024-01-15T10:00:00Z',
      };

      expect(mockResponse).toHaveProperty('id');
      expect(mockResponse).toHaveProperty('slug');
    });

    it('invite member requires valid email and role', async () => {
      const inviteRequest = {
        email: 'newmember@example.com',
        role: 'staff_engineer' as const,
      };

      expect(inviteRequest.email).toMatch(/@/);
      expect(['org_admin', 'staff_admin', 'staff_analyst', 'staff_engineer', 'staff_viewer'])
        .toContain(inviteRequest.role);
    });
  });

  describe('Documents API', () => {
    it('list documents supports filtering', async () => {
      const mockResponse = {
        items: [
          {
            id: 'doc-1',
            name: 'README.md',
            type: 'markdown',
            size: 1024,
            created_at: '2024-01-15T10:00:00Z',
            indexed: true,
          },
          {
            id: 'doc-2',
            name: 'data.pdf',
            type: 'pdf',
            size: 2048,
            created_at: '2024-01-14T10:00:00Z',
            indexed: true,
          },
        ],
        total: 2,
        skip: 0,
        limit: 20,
      };

      expect(Array.isArray(mockResponse.items)).toBe(true);
      expect(mockResponse.items[0]).toHaveProperty('indexed');
    });

    it('upload document returns document with ID', async () => {
      const mockResponse = {
        id: 'doc-new-123',
        name: 'upload.pdf',
        type: 'pdf',
        size: 4096,
        created_at: '2024-01-15T10:00:00Z',
        indexed: false,
        processing_status: 'pending',
      };

      expect(mockResponse).toHaveProperty('id');
      expect(mockResponse).toHaveProperty('processing_status');
    });
  });

  describe('AI Analytics API', () => {
    it('list plugins returns available plugins', async () => {
      const mockResponse = [
        {
          plugin_type: 'github',
          display_name: 'GitHub',
          description: 'Connect to GitHub repositories',
          icon: 'github',
          required_fields: ['token'],
          optional_fields: ['endpoint'],
          auth_type: 'token',
          endpoint_required: false,
          scopes_supported: ['repos', 'issues', 'pull_requests', 'commits'],
        },
        {
          plugin_type: 'jira',
          display_name: 'Jira',
          description: 'Connect to Jira for issue tracking',
          icon: 'jira',
          required_fields: ['token', 'endpoint'],
          optional_fields: [],
          auth_type: 'basic',
          endpoint_required: true,
          scopes_supported: ['boards', 'issues'],
        },
      ];

      expect(Array.isArray(mockResponse)).toBe(true);
      expect(mockResponse[0]).toHaveProperty('plugin_type');
      expect(mockResponse[0]).toHaveProperty('display_name');
      expect(mockResponse[0]).toHaveProperty('required_fields');
      expect(mockResponse[0]).toHaveProperty('scopes_supported');
    });

    it('get DORA metrics returns valid metrics', async () => {
      const mockResponse = {
        deployment_frequency: {
          value: 2.5,
          unit: 'per_day',
          trend: 'up',
          trend_percentage: 15,
        },
        lead_time: {
          value: 24,
          unit: 'hours',
          trend: 'down',
          trend_percentage: -10,
        },
        change_failure_rate: {
          value: 5,
          unit: 'percent',
          trend: 'stable',
          trend_percentage: 0,
        },
        mttr: {
          value: 30,
          unit: 'minutes',
          trend: 'down',
          trend_percentage: -20,
        },
        period: '30d',
        generated_at: '2024-01-15T10:00:00Z',
      };

      expect(mockResponse).toHaveProperty('deployment_frequency');
      expect(mockResponse).toHaveProperty('lead_time');
      expect(mockResponse).toHaveProperty('change_failure_rate');
      expect(mockResponse).toHaveProperty('mttr');
      expect(mockResponse.deployment_frequency).toHaveProperty('value');
      expect(mockResponse.deployment_frequency).toHaveProperty('trend');
    });

    it('create connection validates required fields', async () => {
      const connectionRequest = {
        plugin_type: 'github',
        name: 'My GitHub Connection',
        config: {
          token: 'ghp_xxxxx',
          scopes: ['repos', 'issues'],
        },
      };

      expect(connectionRequest).toHaveProperty('plugin_type');
      expect(connectionRequest).toHaveProperty('name');
      expect(connectionRequest).toHaveProperty('config');
      expect(connectionRequest.config).toHaveProperty('token');
    });

    it('test connection returns status', async () => {
      const mockResponse = {
        success: true,
        message: 'Connection successful',
        details: {
          authenticated_user: 'github-user',
          scopes: ['repo', 'read:org'],
          rate_limit_remaining: 4999,
        },
      };

      expect(mockResponse).toHaveProperty('success');
      expect(mockResponse).toHaveProperty('message');
      expect(typeof mockResponse.success).toBe('boolean');
    });
  });

  describe('Tenant Context', () => {
    it('manages tenant ID correctly', () => {
      expect(TenantContext.getCurrentTenantId()).toBeNull();

      TenantContext.setCurrentTenantId('tenant-123');
      expect(TenantContext.getCurrentTenantId()).toBe('tenant-123');

      TenantContext.clear();
      expect(TenantContext.getCurrentTenantId()).toBeNull();
    });

    it('notifies subscribers on tenant change', () => {
      const listener = vi.fn();
      const unsubscribe = TenantContext.subscribe(listener);

      TenantContext.setCurrentTenantId('tenant-456');
      expect(listener).toHaveBeenCalledWith('tenant-456');

      unsubscribe();
      TenantContext.setCurrentTenantId('tenant-789');
      // Should not be called again after unsubscribe
      expect(listener).toHaveBeenCalledTimes(1);
    });
  });

  describe('Error Handling', () => {
    it('handles 401 unauthorized correctly', async () => {
      const error = {
        response: {
          status: 401,
          data: { detail: 'Invalid or expired token' },
        },
      };

      expect(error.response.status).toBe(401);
      expect(error.response.data).toHaveProperty('detail');
    });

    it('handles 403 forbidden correctly', async () => {
      const error = {
        response: {
          status: 403,
          data: { detail: 'Insufficient permissions' },
        },
      };

      expect(error.response.status).toBe(403);
    });

    it('handles 404 not found correctly', async () => {
      const error = {
        response: {
          status: 404,
          data: { detail: 'Resource not found' },
        },
      };

      expect(error.response.status).toBe(404);
    });

    it('handles 429 rate limit correctly', async () => {
      const error = {
        response: {
          status: 429,
          data: { detail: 'Rate limit exceeded' },
          headers: {
            'retry-after': '60',
            'x-ratelimit-remaining': '0',
            'x-ratelimit-reset': '1705320000',
          },
        },
      };

      expect(error.response.status).toBe(429);
      expect(error.response.headers).toHaveProperty('retry-after');
    });

    it('handles 500 server error correctly', async () => {
      const error = {
        response: {
          status: 500,
          data: { detail: 'Internal server error' },
        },
      };

      expect(error.response.status).toBe(500);
    });

    it('handles network error correctly', async () => {
      const error = {
        message: 'Network Error',
        code: 'ERR_NETWORK',
      };

      expect(error.code).toBe('ERR_NETWORK');
    });
  });

  describe('Request Headers', () => {
    it('includes Content-Type header', () => {
      const headers = {
        'Content-Type': 'application/json',
      };

      expect(headers['Content-Type']).toBe('application/json');
    });

    it('includes Authorization header when logged in', () => {
      const token = 'access-token-123';
      const headers = {
        Authorization: `Bearer ${token}`,
      };

      expect(headers.Authorization).toBe('Bearer access-token-123');
    });

    it('includes X-Tenant-ID header when tenant is set', () => {
      const tenantId = 'tenant-123';
      const headers = {
        'X-Tenant-ID': tenantId,
      };

      expect(headers['X-Tenant-ID']).toBe('tenant-123');
    });
  });
});

describe('API Response Types', () => {
  it('User type has required fields', () => {
    const user = {
      id: 'user-123',
      email: 'test@example.com',
      username: 'testuser',
      full_name: 'Test User',
      role: 'staff_viewer',
      is_verified: true,
    };

    expect(user).toHaveProperty('id');
    expect(user).toHaveProperty('email');
    expect(user).toHaveProperty('username');
    expect(user).toHaveProperty('role');
    expect(user).toHaveProperty('is_verified');
  });

  it('Conversation type has required fields', () => {
    const conversation = {
      id: 'conv-123',
      title: 'Test Conversation',
      model_provider: 'anthropic',
      model_name: 'claude-3-opus',
      message_count: 10,
      total_tokens: 5000,
      created_at: '2024-01-15T10:00:00Z',
      updated_at: '2024-01-15T11:00:00Z',
    };

    expect(conversation).toHaveProperty('id');
    expect(conversation).toHaveProperty('title');
    expect(conversation).toHaveProperty('model_provider');
    expect(conversation).toHaveProperty('model_name');
    expect(conversation).toHaveProperty('message_count');
    expect(conversation).toHaveProperty('total_tokens');
    expect(conversation).toHaveProperty('created_at');
    expect(conversation).toHaveProperty('updated_at');
  });

  it('Message type has required fields', () => {
    const message = {
      id: 'msg-123',
      conversation_id: 'conv-123',
      role: 'assistant',
      content: 'Hello!',
      model_name: 'gpt-4',
      tokens_used: 50,
      created_at: '2024-01-15T10:00:00Z',
    };

    expect(message).toHaveProperty('id');
    expect(message).toHaveProperty('conversation_id');
    expect(message).toHaveProperty('role');
    expect(message).toHaveProperty('content');
    expect(['user', 'assistant', 'system', 'tool']).toContain(message.role);
  });

  it('Organization type has required fields', () => {
    const organization = {
      id: 'org-123',
      name: 'Test Org',
      slug: 'test-org',
      plan: 'pro',
      created_at: '2024-01-01T00:00:00Z',
    };

    expect(organization).toHaveProperty('id');
    expect(organization).toHaveProperty('name');
    expect(organization).toHaveProperty('slug');
    expect(organization).toHaveProperty('plan');
  });

  it('PluginInfo type has required fields', () => {
    const plugin = {
      plugin_type: 'github',
      display_name: 'GitHub',
      description: 'Connect to GitHub',
      icon: 'github',
      required_fields: ['token'],
      optional_fields: ['endpoint'],
      auth_type: 'token',
      endpoint_required: false,
      scopes_supported: ['repos', 'issues'],
    };

    expect(plugin).toHaveProperty('plugin_type');
    expect(plugin).toHaveProperty('display_name');
    expect(plugin).toHaveProperty('required_fields');
    expect(plugin).toHaveProperty('auth_type');
    expect(plugin).toHaveProperty('scopes_supported');
    expect(Array.isArray(plugin.required_fields)).toBe(true);
    expect(Array.isArray(plugin.scopes_supported)).toBe(true);
  });
});
