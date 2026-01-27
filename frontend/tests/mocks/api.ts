/**
 * Mock for API calls
 * Provides mock responses for auth and chat APIs
 */

import { vi } from 'vitest';

// Mock user data
export const mockUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'staff_admin' as const,
  organization_id: 'org-123',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Mock organization data
export const mockOrganization = {
  id: 'org-123',
  name: 'Test Organization',
  slug: 'test-org',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Mock tokens
export const mockTokens = {
  access_token: 'mock-access-token',
  refresh_token: 'mock-refresh-token',
  token_type: 'bearer',
  expires_in: 3600,
};

// Mock login response
export const mockLoginResponse = {
  user: mockUser,
  tokens: mockTokens,
};

// Mock conversation
export const mockConversation = {
  id: 'conv-123',
  title: 'Test Conversation',
  model_provider: 'anthropic',
  model_name: 'claude-3-5-sonnet',
  message_count: 0,
  total_tokens: 0,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

// Mock message
export const mockMessage = {
  id: 'msg-123',
  role: 'assistant' as const,
  content: 'Hello! How can I help you today?',
  model_name: 'claude-3-5-sonnet',
  created_at: '2024-01-01T00:00:00Z',
};

// Auth API mock
export const mockAuthApi = {
  login: vi.fn().mockResolvedValue(mockLoginResponse),
  register: vi.fn().mockResolvedValue(mockLoginResponse),
  logout: vi.fn().mockResolvedValue(undefined),
  refreshToken: vi.fn().mockResolvedValue(mockTokens),
  getCurrentUser: vi.fn().mockResolvedValue(mockUser),
};

// Organizations API mock
export const mockOrganizationsApi = {
  list: vi.fn().mockResolvedValue([mockOrganization]),
  get: vi.fn().mockResolvedValue(mockOrganization),
  switchTo: vi.fn().mockResolvedValue(undefined),
};

// Chat API mock
export const mockChatApi = {
  listConversations: vi.fn().mockResolvedValue([mockConversation]),
  getConversation: vi.fn().mockResolvedValue(mockConversation),
  createConversation: vi.fn().mockResolvedValue(mockConversation),
  deleteConversation: vi.fn().mockResolvedValue(undefined),
  getMessages: vi.fn().mockResolvedValue([mockMessage]),
};

// Reset all API mocks
export function resetApiMocks() {
  Object.values(mockAuthApi).forEach((mock) => mock.mockClear());
  Object.values(mockOrganizationsApi).forEach((mock) => mock.mockClear());
  Object.values(mockChatApi).forEach((mock) => mock.mockClear());
}

// Helper to make login fail
export function setLoginToFail(errorMessage = 'Invalid credentials') {
  mockAuthApi.login.mockRejectedValue(new Error(errorMessage));
}

// Helper to make login succeed
export function setLoginToSucceed(response = mockLoginResponse) {
  mockAuthApi.login.mockResolvedValue(response);
}
