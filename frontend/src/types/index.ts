// =============================================================================
// CORE TYPES FOR SOFTWARE INTELLIGENCE PLATFORM
// =============================================================================

// -----------------------------------------------------------------------------
// User & Authentication Types
// -----------------------------------------------------------------------------

export type UserRole = 'org_admin' | 'staff_admin' | 'staff_analyst' | 'staff_engineer' | 'staff_viewer';

export interface User {
  id: string;
  email: string;
  username: string;
  full_name: string | null;
  role: UserRole;
  is_verified: boolean;
  organization_id: string | null;
  avatar_url?: string;
  created_at: string;
  updated_at: string;
}

export interface StaffInvite {
  id: string;
  email: string;
  role: UserRole;
  organization_id: string;
  invited_by: string;
  token: string;
  expires_at: string;
  accepted_at: string | null;
  created_at: string;
}

// -----------------------------------------------------------------------------
// Organization Types
// -----------------------------------------------------------------------------

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  logo_url: string | null;
  settings: OrganizationSettings;
  tier: 'free' | 'pro' | 'enterprise';
  max_members: number;
  max_projects: number;
  is_active: boolean;
  owner_id: string;
  created_at: string;
  updated_at: string;
}

export interface OrganizationSettings {
  default_model?: string;
  allowed_models?: string[];
  features_enabled?: string[];
  security_settings?: {
    require_2fa?: boolean;
    session_timeout_minutes?: number;
    allowed_domains?: string[];
  };
}

export interface OrganizationMember {
  id: string;
  user_id: string;
  organization_id: string;
  role: UserRole;
  invited_by: string | null;
  joined_at: string;
  is_active: boolean;
  user?: User;
}

// -----------------------------------------------------------------------------
// Chat & Message Types
// -----------------------------------------------------------------------------

export type MessageRole = 'user' | 'assistant' | 'system' | 'tool';

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  created_at: string;
  attachments?: MessageAttachment[];
  tool_events?: ToolEvent[];
  metadata?: MessageMetadata;
}

export interface MessageAttachment {
  type: 'repo' | 'pr' | 'incident' | 'document' | 'file';
  id: string;
  name: string;
  url?: string;
  metadata?: Record<string, unknown>;
}

export interface ToolEvent {
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  started_at: string;
  completed_at?: string;
  duration_ms?: number;
}

export interface MessageMetadata {
  model_name?: string;
  model_provider?: string;
  tokens_used?: number;
  latency_ms?: number;
  time_to_first_token_ms?: number;
}

export interface Conversation {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  system_prompt?: string;
  message_count: number;
  total_tokens: number;
  context?: ConversationContext;
  created_at: string;
  updated_at: string;
}

export interface ConversationContext {
  repo?: RepoContext;
  pr?: PRContext;
  incident?: IncidentContext;
  timeframe?: TimeframeContext;
  filters?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Context Panel Types
// -----------------------------------------------------------------------------

export interface RepoContext {
  id: string;
  name: string;
  full_name: string;
  url: string;
  default_branch: string;
  language?: string;
  last_commit?: string;
}

export interface PRContext {
  id: string;
  number: number;
  title: string;
  url: string;
  state: 'open' | 'closed' | 'merged';
  author: string;
  created_at: string;
  files_changed?: number;
  additions?: number;
  deletions?: number;
}

export interface IncidentContext {
  id: string;
  title: string;
  severity: 'critical' | 'high' | 'medium' | 'low';
  status: 'investigating' | 'identified' | 'monitoring' | 'resolved';
  started_at: string;
  resolved_at?: string;
  affected_services?: string[];
}

export interface TimeframeContext {
  start: string;
  end: string;
  preset?: 'last_hour' | 'last_24h' | 'last_7d' | 'last_30d' | 'custom';
}

// -----------------------------------------------------------------------------
// Quick Action Types
// -----------------------------------------------------------------------------

export interface QuickAction {
  id: string;
  label: string;
  description?: string;
  icon: string;
  action: QuickActionType;
  category: 'repo' | 'pr' | 'incident' | 'deploy' | 'analytics' | 'general';
  requiredContext?: ('repo' | 'pr' | 'incident')[];
}

export type QuickActionType =
  | 'connect_repo'
  | 'analyze_pr'
  | 'find_root_cause'
  | 'summarize_deploy_risk'
  | 'generate_test_plan'
  | 'analyze_dora'
  | 'review_code'
  | 'create_workflow'
  | 'custom';

// -----------------------------------------------------------------------------
// Streaming Types
// -----------------------------------------------------------------------------

export interface StreamingState {
  isStreaming: boolean;
  content: string;
  toolEvents: ToolEvent[];
  timeToFirstToken?: number;
  startTime?: number;
}

// -----------------------------------------------------------------------------
// API Response Types
// -----------------------------------------------------------------------------

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  has_more: boolean;
}

export interface ApiError {
  code: string;
  message: string;
  details?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Permission Types
// -----------------------------------------------------------------------------

export interface Permission {
  resource: string;
  actions: ('create' | 'read' | 'update' | 'delete')[];
}

export const ROLE_PERMISSIONS: Record<UserRole, Permission[]> = {
  org_admin: [
    { resource: '*', actions: ['create', 'read', 'update', 'delete'] },
  ],
  staff_admin: [
    { resource: 'users', actions: ['create', 'read', 'update'] },
    { resource: 'conversations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'documents', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'agents', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'integrations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'analytics', actions: ['read'] },
    { resource: 'settings', actions: ['read', 'update'] },
  ],
  staff_analyst: [
    { resource: 'conversations', actions: ['create', 'read'] },
    { resource: 'documents', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
    { resource: 'agents', actions: ['read'] },
  ],
  staff_engineer: [
    { resource: 'conversations', actions: ['create', 'read', 'update', 'delete'] },
    { resource: 'documents', actions: ['create', 'read', 'update'] },
    { resource: 'agents', actions: ['create', 'read', 'update'] },
    { resource: 'integrations', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
  ],
  staff_viewer: [
    { resource: 'conversations', actions: ['read'] },
    { resource: 'documents', actions: ['read'] },
    { resource: 'analytics', actions: ['read'] },
  ],
};
