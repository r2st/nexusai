import axios, { type AxiosError, type AxiosInstance, type InternalAxiosRequestConfig } from 'axios';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';

// =============================================================================
// TENANT CONTEXT MANAGEMENT
// =============================================================================

/**
 * Tenant context for multi-tenant data isolation.
 * This ensures all API requests are scoped to the correct organization.
 */
class TenantContext {
  private static STORAGE_KEY = 'current_tenant_id';
  private static listeners: ((tenantId: string | null) => void)[] = [];

  /**
   * Get the current tenant/organization ID.
   */
  static getCurrentTenantId(): string | null {
    if (typeof window === 'undefined') return null;
    return localStorage.getItem(this.STORAGE_KEY);
  }

  /**
   * Set the current tenant/organization ID.
   * This will be automatically included in all API requests.
   */
  static setCurrentTenantId(tenantId: string | null): void {
    if (typeof window === 'undefined') return;

    if (tenantId) {
      localStorage.setItem(this.STORAGE_KEY, tenantId);
    } else {
      localStorage.removeItem(this.STORAGE_KEY);
    }

    // Notify listeners of tenant change
    this.listeners.forEach(listener => listener(tenantId));
  }

  /**
   * Subscribe to tenant changes.
   * Returns unsubscribe function.
   */
  static subscribe(listener: (tenantId: string | null) => void): () => void {
    this.listeners.push(listener);
    return () => {
      this.listeners = this.listeners.filter(l => l !== listener);
    };
  }

  /**
   * Clear tenant context (e.g., on logout).
   */
  static clear(): void {
    this.setCurrentTenantId(null);
  }
}

export { TenantContext };

// =============================================================================
// AXIOS INSTANCE
// =============================================================================

// Create axios instance
export const api: AxiosInstance = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for auth AND tenant context
api.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    if (typeof window !== 'undefined') {
      // Add auth token
      const token = localStorage.getItem('access_token');
      if (token) {
        config.headers.Authorization = `Bearer ${token}`;
      }

      // Add tenant context header for multi-tenant isolation
      const tenantId = TenantContext.getCurrentTenantId();
      if (tenantId) {
        config.headers['X-Tenant-ID'] = tenantId;
      }
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  async (error: AxiosError) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        try {
          const response = await axios.post(`${API_BASE_URL}/auth/refresh`, {
            refresh_token: refreshToken,
          });
          const { access_token, refresh_token } = response.data;
          localStorage.setItem('access_token', access_token);
          localStorage.setItem('refresh_token', refresh_token);

          // Retry original request
          if (error.config) {
            error.config.headers.Authorization = `Bearer ${access_token}`;
            return axios(error.config);
          }
        } catch {
          // Refresh failed, clear tokens
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        }
      }
    }
    return Promise.reject(error);
  }
);

// API types
export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: string;
  is_verified: boolean;
  organization_id?: string | null;
}

export interface Token {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface AuthResponse {
  user: User;
  tokens: Token;
}

export interface Conversation {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  role: 'system' | 'user' | 'assistant';
  content: string;
  model_name: string | null;
  created_at: string;
  widgets?: Array<{
    type: 'dora' | 'space' | 'insights' | 'pipeline_progress';
    [key: string]: unknown;
  }>;
  tool_calls?: Array<{
    name: string;
    args?: Record<string, unknown>;
    status?: 'queued' | 'running' | 'completed' | 'failed';
    id?: string;
  }>;
  tool_results?: Array<{
    name?: string;
    output?: string;
    success?: boolean;
    id?: string;
  }>;
}

export interface Document {
  id: string;
  original_filename: string;
  file_size: number;
  mime_type: string;
  document_type: string;
  status: string;
  chunk_count: number;
  created_at: string;
}

export interface SearchResult {
  id: string;
  document_id: string;
  content: string;
  chunk_index: number;
  filename: string;
  similarity: number;
}

// Auth API
export const authApi = {
  register: async (data: {
    email: string;
    username: string;
    password: string;
    full_name?: string;
  }): Promise<AuthResponse> => {
    const response = await api.post('/auth/register', data);
    return response.data;
  },

  login: async (email: string, password: string): Promise<AuthResponse> => {
    const response = await api.post('/auth/login', { email, password });
    return response.data;
  },

  refresh: async (refreshToken: string): Promise<Token> => {
    const response = await api.post('/auth/refresh', {
      refresh_token: refreshToken,
    });
    return response.data;
  },

  forgotPassword: async (email: string): Promise<void> => {
    await api.post('/auth/forgot-password', { email });
  },

  resetPassword: async (token: string, newPassword: string): Promise<void> => {
    await api.post('/auth/reset-password', {
      token,
      new_password: newPassword,
    });
  },
};

// Chat API
export const chatApi = {
  createConversation: async (data: {
    title?: string;
    model_provider?: string;
    model_name?: string;
    system_prompt?: string;
  }): Promise<Conversation> => {
    const response = await api.post('/chat/conversations', data);
    return response.data;
  },

  listConversations: async (limit = 50, offset = 0): Promise<Conversation[]> => {
    const response = await api.get('/chat/conversations', {
      params: { limit, offset },
    });
    return response.data;
  },

  getConversation: async (id: string): Promise<Conversation> => {
    const response = await api.get(`/chat/conversations/${id}`);
    return response.data;
  },

  getMessages: async (conversationId: string): Promise<Message[]> => {
    const response = await api.get(`/chat/conversations/${conversationId}/messages`);
    return response.data;
  },

  sendMessage: async (
    conversationId: string,
    message: string,
    options?: {
      temperature?: number;
      max_tokens?: number;
      stream?: boolean;
      use_mcp?: boolean;
      mcp_servers?: Array<{
        name?: string;
        transport?: string;
        url?: string;
        command?: string;
        args?: string[];
        env?: Record<string, string>;
        headers?: Record<string, string>;
        timeout_seconds?: number;
      }>;
    }
  ): Promise<Response | { message: Message; conversation: Conversation }> => {
    const stream = options?.stream ?? true;

    if (stream) {
      // Return fetch response for streaming
      const token = localStorage.getItem('access_token');
      const tenantId = TenantContext.getCurrentTenantId();

      const headers: Record<string, string> = {
        'Content-Type': 'application/json',
      };

      if (token) {
        headers['Authorization'] = `Bearer ${token}`;
      }

      // Include tenant context for streaming requests
      if (tenantId) {
        headers['X-Tenant-ID'] = tenantId;
      }

      return fetch(`${API_BASE_URL}/chat/conversations/${conversationId}/chat`, {
        method: 'POST',
        headers,
        body: JSON.stringify({
          message,
          temperature: options?.temperature ?? 0.7,
          max_tokens: options?.max_tokens ?? 4096,
          stream: true,
          use_mcp: options?.use_mcp ?? true,
          mcp_servers: options?.mcp_servers ?? [],
        }),
      });
    }

    const response = await api.post(`/chat/conversations/${conversationId}/chat`, {
      message,
      temperature: options?.temperature ?? 0.7,
      max_tokens: options?.max_tokens ?? 4096,
      stream: false,
      use_mcp: options?.use_mcp ?? true,
      mcp_servers: options?.mcp_servers ?? [],
    });
    return response.data;
  },

  deleteConversation: async (id: string): Promise<void> => {
    await api.delete(`/chat/conversations/${id}`);
  },
};

// Documents API
export const documentsApi = {
  upload: async (file: File): Promise<Document> => {
    const formData = new FormData();
    formData.append('file', file);

    const response = await api.post('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  process: async (documentId: string): Promise<Document> => {
    const response = await api.post(`/documents/${documentId}/process`);
    return response.data;
  },

  list: async (limit = 50, offset = 0): Promise<Document[]> => {
    const response = await api.get('/documents', {
      params: { limit, offset },
    });
    return response.data;
  },

  get: async (id: string): Promise<Document> => {
    const response = await api.get(`/documents/${id}`);
    return response.data;
  },

  search: async (
    query: string,
    limit = 10,
    similarityThreshold = 0.7
  ): Promise<SearchResult[]> => {
    const response = await api.post('/documents/search', {
      query,
      limit,
      similarity_threshold: similarityThreshold,
    });
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/documents/${id}`);
  },
};

// Agent Types
export interface Agent {
  id: string;
  name: string;
  description: string | null;
  system_prompt: string | null;
  capabilities: string[];
  tools_config: Record<string, unknown>;
  mcp_servers: Record<string, unknown>[];
  actions_config: Record<string, unknown>[];
  model_provider: string;
  model_name: string;
  temperature: number;
  max_tokens: number;
  is_public: boolean;
  is_active: boolean;
  owner_id: string;
  organization_id: string | null;
  metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface AgentExecution {
  id: string;
  agent_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input_message: string | null;
  output_message: string | null;
  steps: Record<string, unknown>[];
  tool_calls: Record<string, unknown>[];
  tokens_used: number;
  execution_time_ms: number | null;
  error: string | null;
  started_at: string;
  completed_at: string | null;
}

// Knowledge Graph Types
export interface KnowledgeGraphStats {
  total_nodes: number;
  total_relationships: number;
  node_labels: Record<string, number>;
  relationship_types: Record<string, number>;
}

export interface DiscoveryResult {
  tables: string[];
  metrics: string[];
  dora_entities: string[];
  query_suggestion: string;
}

// DevOps Types
export interface DORAAnalysis {
  project_id: string;
  period_days: number;
  metrics: {
    deployment_frequency: { value: number; level: string; trend: string };
    lead_time: { value: number; level: string; trend: string };
    mttr: { value: number; level: string; trend: string };
    change_failure_rate: { value: number; level: string; trend: string };
  };
  overall_level: string;
  recommendations: string[];
  insights: string[];
}

export interface WorkflowExecution {
  workflow_id: string;
  workflow_type: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  steps: {
    step_number: number;
    agent_name: string;
    status: string;
    started_at: string | null;
    completed_at: string | null;
  }[];
  final_output: Record<string, unknown> | null;
  started_at: string;
  completed_at: string | null;
}

// OpenAPI Action Types
export interface OpenAPIAction {
  id: string;
  action_id: string;
  name: string;
  description: string | null;
  base_url: string;
  auth_type: 'none' | 'api_key' | 'bearer' | 'basic' | 'oauth2';
  operations: {
    operation_id: string;
    name: string;
    method: string;
    path: string;
    description: string | null;
  }[];
  is_enabled: boolean;
  created_at: string;
}

// Agents API
export const agentsApi = {
  list: async (limit = 50, offset = 0, includePublic = false): Promise<Agent[]> => {
    const response = await api.get('/agents', {
      params: { limit, offset, include_public: includePublic },
    });
    return response.data;
  },

  get: async (id: string): Promise<Agent> => {
    const response = await api.get(`/agents/${id}`);
    return response.data;
  },

  create: async (data: {
    name: string;
    description?: string;
    system_prompt?: string;
    capabilities?: string[];
    model_provider?: string;
    model_name?: string;
    temperature?: number;
    max_tokens?: number;
    is_public?: boolean;
  }): Promise<Agent> => {
    const response = await api.post('/agents', data);
    return response.data;
  },

  update: async (id: string, data: Partial<Agent>): Promise<Agent> => {
    const response = await api.put(`/agents/${id}`, data);
    return response.data;
  },

  delete: async (id: string): Promise<void> => {
    await api.delete(`/agents/${id}`);
  },

  execute: async (
    id: string,
    message: string,
    context?: Record<string, unknown>
  ): Promise<AgentExecution> => {
    const response = await api.post(`/agents/${id}/execute`, {
      message,
      context,
    });
    return response.data;
  },

  getExecutions: async (id: string, limit = 20): Promise<AgentExecution[]> => {
    const response = await api.get(`/agents/${id}/executions`, {
      params: { limit },
    });
    return response.data;
  },
};

// Knowledge Graph API
export const knowledgeGraphApi = {
  getStats: async (): Promise<KnowledgeGraphStats> => {
    const response = await api.get('/knowledge-graph/stats');
    return response.data;
  },

  discover: async (query: string): Promise<DiscoveryResult> => {
    const response = await api.post('/knowledge-graph/discover', { query });
    return response.data;
  },

  getTables: async (): Promise<{ tables: string[] }> => {
    const response = await api.get('/knowledge-graph/tables');
    return response.data;
  },

  getMetrics: async (): Promise<{ metrics: string[] }> => {
    const response = await api.get('/knowledge-graph/metrics');
    return response.data;
  },

  syncFromPostgres: async (): Promise<{ synced_entities: number }> => {
    const response = await api.post('/knowledge-graph/sync');
    return response.data;
  },
};

// DevOps Agents API
export const devopsApi = {
  analyzeDORA: async (
    projectId: string,
    periodDays = 30
  ): Promise<DORAAnalysis> => {
    const response = await api.post('/devops/dora/analyze', {
      project_id: projectId,
      period_days: periodDays,
    });
    return response.data;
  },

  analyzeAdoption: async (
    organizationId: string,
    periodDays = 30
  ): Promise<Record<string, unknown>> => {
    const response = await api.post('/devops/adoption/analyze', {
      organization_id: organizationId,
      period_days: periodDays,
    });
    return response.data;
  },

  createWorkflow: async (
    workflowType: string,
    params: Record<string, unknown>
  ): Promise<WorkflowExecution> => {
    const response = await api.post('/devops/workflows', {
      workflow_type: workflowType,
      ...params,
    });
    return response.data;
  },

  getWorkflow: async (workflowId: string): Promise<WorkflowExecution> => {
    const response = await api.get(`/devops/workflows/${workflowId}`);
    return response.data;
  },

  listWorkflows: async (limit = 20): Promise<WorkflowExecution[]> => {
    const response = await api.get('/devops/workflows', {
      params: { limit },
    });
    return response.data;
  },
};

// OpenAPI Actions API
export const actionsApi = {
  list: async (limit = 50, offset = 0): Promise<OpenAPIAction[]> => {
    const response = await api.get('/actions', {
      params: { limit, offset },
    });
    return response.data;
  },

  get: async (actionId: string): Promise<OpenAPIAction> => {
    const response = await api.get(`/actions/${actionId}`);
    return response.data;
  },

  register: async (data: {
    action_id: string;
    name: string;
    base_url: string;
    auth_type?: string;
    operations: Record<string, unknown>[];
    description?: string;
  }): Promise<OpenAPIAction> => {
    const response = await api.post('/actions/register', data);
    return response.data;
  },

  registerFromSpec: async (specUrl: string): Promise<OpenAPIAction> => {
    const response = await api.post('/actions/register/openapi', {
      spec_url: specUrl,
    });
    return response.data;
  },

  execute: async (
    actionId: string,
    operationId: string,
    params?: Record<string, unknown>
  ): Promise<Record<string, unknown>> => {
    const response = await api.post(`/actions/${actionId}/execute`, {
      operation_id: operationId,
      parameters: params,
    });
    return response.data;
  },

  delete: async (actionId: string): Promise<void> => {
    await api.delete(`/actions/${actionId}`);
  },
};

// =============================================================================
// ORGANIZATION (TENANT) API
// =============================================================================

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  settings: Record<string, unknown>;
  tier: 'free' | 'pro' | 'enterprise';
  max_members: number;
  max_projects: number;
  is_active: boolean;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  organization_id: string;
  role: 'owner' | 'admin' | 'member';
  invited_by: string | null;
  joined_at: string;
  is_active: boolean;
  user?: User;
}

export const organizationsApi = {
  /**
   * List organizations the current user belongs to.
   */
  list: async (): Promise<Organization[]> => {
    const response = await api.get('/organizations');
    return response.data;
  },

  /**
   * Get a specific organization by ID.
   */
  get: async (id: string): Promise<Organization> => {
    const response = await api.get(`/organizations/${id}`);
    return response.data;
  },

  /**
   * Create a new organization.
   */
  create: async (data: {
    name: string;
    slug?: string;
    description?: string;
  }): Promise<Organization> => {
    const response = await api.post('/organizations', data);
    return response.data;
  },

  /**
   * Update an organization.
   */
  update: async (id: string, data: Partial<Organization>): Promise<Organization> => {
    const response = await api.put(`/organizations/${id}`, data);
    return response.data;
  },

  /**
   * Delete an organization.
   */
  delete: async (id: string): Promise<void> => {
    await api.delete(`/organizations/${id}`);
  },

  /**
   * List members of an organization.
   */
  listMembers: async (orgId: string): Promise<OrganizationMember[]> => {
    const response = await api.get(`/organizations/${orgId}/members`);
    return response.data;
  },

  /**
   * Invite a user to an organization.
   */
  inviteMember: async (
    orgId: string,
    email: string,
    role: 'admin' | 'member' = 'member'
  ): Promise<OrganizationMember> => {
    const response = await api.post(`/organizations/${orgId}/members/invite`, {
      email,
      role,
    });
    return response.data;
  },

  /**
   * Remove a member from an organization.
   */
  removeMember: async (orgId: string, userId: string): Promise<void> => {
    await api.delete(`/organizations/${orgId}/members/${userId}`);
  },

  /**
   * Update a member's role in an organization.
   */
  updateMemberRole: async (
    orgId: string,
    userId: string,
    role: 'admin' | 'member'
  ): Promise<OrganizationMember> => {
    const response = await api.put(`/organizations/${orgId}/members/${userId}`, {
      role,
    });
    return response.data;
  },

  /**
   * Switch to a different organization context.
   * This updates the tenant context for all subsequent API calls.
   */
  switchTo: (orgId: string): void => {
    TenantContext.setCurrentTenantId(orgId);
  },

  /**
   * Get the current organization ID.
   */
  getCurrentId: (): string | null => {
    return TenantContext.getCurrentTenantId();
  },
};

// =============================================================================
// TRIALS API
// =============================================================================

export interface TrialStatus {
  trial_status: string;
  is_trial_active: boolean;
  trial_started_at: string | null;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  can_access_features: boolean;
  current_tier: string;
  max_members: number;
  max_projects: number;
  was_extended: boolean;
}

export interface TrialStatistics {
  active: number;
  expired: number;
  converted: number;
  expiring_soon: number;
  conversion_rate: number;
  total_trials: number;
}

export interface OrganizationTrial {
  id: string;
  name: string;
  slug: string;
  tier: string;
  trial_status: string;
  trial_started_at: string | null;
  trial_ends_at: string | null;
  trial_days_remaining: number;
  current_member_count: number;
  current_project_count: number;
}

export const trialsApi = {
  /**
   * Get trial status for an organization.
   */
  getStatus: async (orgId: string): Promise<TrialStatus> => {
    const response = await api.get(`/trials/${orgId}/trial`);
    return response.data;
  },

  /**
   * Start a trial for an organization.
   */
  startTrial: async (orgId: string): Promise<TrialStatus> => {
    const response = await api.post(`/trials/${orgId}/trial/start`);
    return response.data;
  },

  /**
   * List all trials (admin only).
   */
  listAll: async (
    status?: string,
    limit = 100,
    offset = 0
  ): Promise<OrganizationTrial[]> => {
    const response = await api.get('/trials/admin/trials', {
      params: { status, limit, offset },
    });
    return response.data;
  },

  /**
   * Get trial statistics (admin only).
   */
  getStatistics: async (): Promise<TrialStatistics> => {
    const response = await api.get('/trials/admin/trials/statistics');
    return response.data;
  },

  /**
   * Extend a trial (admin only).
   */
  extend: async (
    orgId: string,
    days: number,
    reason: string
  ): Promise<{ message: string; new_end_date: string; days_added: number }> => {
    const response = await api.post(`/trials/admin/trials/${orgId}/extend`, {
      days,
      reason,
    });
    return response.data;
  },

  /**
   * Force expire a trial (admin only).
   */
  expire: async (orgId: string): Promise<{ message: string }> => {
    const response = await api.post(`/trials/admin/trials/${orgId}/expire`);
    return response.data;
  },
};

// =============================================================================
// SUBSCRIPTIONS API
// =============================================================================

export interface UsageSummary {
  members: {
    current: number;
    max: number;
    percentage: number;
    at_limit: boolean;
  };
  projects: {
    current: number;
    max: number;
    percentage: number;
    at_limit: boolean;
  };
  tier: string;
  can_access_features: boolean;
  trial_active: boolean;
  subscription_active: boolean;
}

export const subscriptionsApi = {
  /**
   * Get usage summary for an organization.
   */
  getUsage: async (orgId: string): Promise<UsageSummary> => {
    const response = await api.get(`/subscriptions/${orgId}/usage`);
    return response.data;
  },

  /**
   * Cancel subscription.
   */
  cancel: async (
    orgId: string,
    atPeriodEnd = true
  ): Promise<{ message: string }> => {
    const response = await api.post(`/subscriptions/${orgId}/subscription/cancel`, {
      at_period_end: atPeriodEnd,
    });
    return response.data;
  },

  /**
   * Resume subscription.
   */
  resume: async (orgId: string): Promise<{ message: string }> => {
    const response = await api.post(`/subscriptions/${orgId}/subscription/resume`);
    return response.data;
  },

  /**
   * Change tier (admin only).
   */
  changeTier: async (
    orgId: string,
    tier: string
  ): Promise<{
    message: string;
    previous_tier: string;
    new_tier: string;
    new_max_members: number;
    new_max_projects: number;
  }> => {
    const response = await api.post(`/subscriptions/admin/${orgId}/tier`, {
      tier,
    });
    return response.data;
  },

  /**
   * Refresh usage counts (admin only).
   */
  refreshUsage: async (
    orgId: string
  ): Promise<{
    message: string;
    current_member_count: number;
    current_project_count: number;
  }> => {
    const response = await api.post(`/subscriptions/admin/${orgId}/refresh-usage`);
    return response.data;
  },
};

// =============================================================================
// SETUP ASSISTANT API
// =============================================================================

export interface QuickReply {
  id: string;
  label: string;
  value: string;
  icon?: string;
  description?: string;
}

export interface SetupAction {
  action_type: string;
  label: string;
  description?: string;
  data: Record<string, unknown>;
  requires_confirmation: boolean;
  is_destructive: boolean;
}

export interface SetupMessage {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: string;
  quick_replies: QuickReply[];
  actions: SetupAction[];
  metadata: Record<string, unknown>;
  step_number?: number;
  total_steps?: number;
  progress_percent?: number;
}

export interface SetupChatResponse {
  message: SetupMessage;
  session_id: string;
  current_step?: string;
  can_go_back: boolean;
  is_complete: boolean;
  collected_data: Record<string, unknown>;
  errors: string[];
  warnings: string[];
}

export interface SetupSessionInfo {
  session_id: string;
  flow_type?: string;
  current_step?: string;
  is_active: boolean;
  message_count: number;
  collected_data: Record<string, unknown>;
}

export interface PluginInfo {
  plugin_type: string;
  display_name: string;
  description: string;
  icon: string;
  required_fields: string[];
  optional_fields: string[];
  auth_type: string;
  endpoint_required: boolean;
  scopes_supported: string[];
}

export const setupAssistantApi = {
  /**
   * Start a new setup assistant session.
   */
  startSession: async (options?: {
    flow_type?: 'connection' | 'project' | 'pipeline' | 'onboarding';
    plugin?: string;
  }): Promise<{
    session_id: string;
    message: SetupMessage;
    flow_type?: string;
    current_step?: string;
  }> => {
    const response = await api.post('/setup-assistant/sessions', options || {});
    return response.data;
  },

  /**
   * Send a message to the setup assistant.
   */
  sendMessage: async (
    sessionId: string,
    message: string,
    isQuickReply = false
  ): Promise<SetupChatResponse> => {
    const response = await api.post(`/setup-assistant/sessions/${sessionId}/messages`, {
      message,
      quick_reply: isQuickReply,
    });
    return response.data;
  },

  /**
   * Get session information.
   */
  getSession: async (sessionId: string): Promise<SetupSessionInfo> => {
    const response = await api.get(`/setup-assistant/sessions/${sessionId}`);
    return response.data;
  },

  /**
   * Get all messages in a session.
   */
  getMessages: async (sessionId: string): Promise<SetupMessage[]> => {
    const response = await api.get(`/setup-assistant/sessions/${sessionId}/messages`);
    return response.data;
  },

  /**
   * Cancel the current flow in a session.
   */
  cancelSession: async (sessionId: string): Promise<SetupChatResponse> => {
    const response = await api.post(`/setup-assistant/sessions/${sessionId}/cancel`);
    return response.data;
  },

  /**
   * Delete a session.
   */
  deleteSession: async (sessionId: string): Promise<void> => {
    await api.delete(`/setup-assistant/sessions/${sessionId}`);
  },

  /**
   * List all available plugins.
   */
  listPlugins: async (): Promise<PluginInfo[]> => {
    const response = await api.get('/setup-assistant/plugins');
    return response.data.plugins;
  },

  /**
   * Quick start connection setup for a specific plugin.
   */
  quickSetup: async (
    plugin: string
  ): Promise<{
    session_id: string;
    message: SetupMessage;
    current_step: string;
    plugin: string;
    plugin_info: PluginInfo;
  }> => {
    const response = await api.post(`/setup-assistant/quick-setup/${plugin}`);
    return response.data;
  },

  /**
   * Start the onboarding flow.
   */
  startOnboarding: async (): Promise<{
    session_id: string;
    message: SetupMessage;
    current_step: string;
    flow_type: string;
  }> => {
    const response = await api.post('/setup-assistant/onboarding');
    return response.data;
  },
};

// =============================================================================
// LLM GATEWAY API
// =============================================================================

export interface ModelsResponse {
  providers: Record<string, string[]>;
  default_model: string | null;
  default_provider: string | null;
}

export interface ProviderStatus {
  name: string;
  enabled: boolean;
  healthy: boolean;
  models: string[];
  latency_ms: number | null;
  error_rate: number;
  last_error: string | null;
}

export interface LLMHealthResponse {
  healthy: boolean;
  providers: Record<string, boolean>;
}

export const llmApi = {
  /**
   * Get available models grouped by provider.
   * Only returns models for providers that have valid API keys configured.
   */
  getModels: async (): Promise<ModelsResponse> => {
    const response = await api.get('/llm/models');
    return response.data;
  },

  /**
   * Get detailed provider status.
   */
  getProviders: async (): Promise<ProviderStatus[]> => {
    const response = await api.get('/llm/providers');
    return response.data;
  },

  /**
   * Health check for all providers.
   */
  healthCheck: async (): Promise<LLMHealthResponse> => {
    const response = await api.get('/llm/health');
    return response.data;
  },

  /**
   * Test connection to a specific provider/model.
   */
  testConnection: async (provider?: string, model?: string): Promise<{
    model: string;
    provider: string;
    content: string;
    latency_ms: number;
  }> => {
    const params: Record<string, string> = {};
    if (provider) params.provider = provider;
    if (model) params.model = model;
    const response = await api.post('/llm/test', null, { params });
    return response.data;
  },
};
