/**
 * Admin API Module
 *
 * Provides API functions for admin operations including user management,
 * organization management, and system configuration.
 */

import { api, User, Organization, OrganizationMember } from './api';

// =============================================================================
// TYPES
// =============================================================================

export interface AdminUser extends User {
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  is_active: boolean;
  organization_count: number;
  login_count: number;
}

export interface AdminUserDetail extends AdminUser {
  organizations: {
    id: string;
    name: string;
    role: string;
    joined_at: string;
  }[];
  login_history: LoginEvent[];
  metadata: Record<string, unknown>;
}

export interface LoginEvent {
  id: string;
  ip_address: string;
  user_agent: string;
  timestamp: string;
  success: boolean;
  failure_reason?: string;
}

export interface CreateUserRequest {
  email: string;
  username: string;
  password?: string;
  full_name?: string;
  role?: 'user' | 'admin' | 'superadmin';
  is_active?: boolean;
  is_verified?: boolean;
  send_welcome_email?: boolean;
}

export interface UpdateUserRequest {
  email?: string;
  username?: string;
  full_name?: string;
  role?: 'user' | 'admin' | 'superadmin';
  is_active?: boolean;
  is_verified?: boolean;
}

export interface UserListParams {
  search?: string;
  filter?: 'all' | 'active' | 'inactive' | 'verified' | 'unverified' | 'admin';
  sort_by?: 'created_at' | 'email' | 'username' | 'last_login_at';
  sort_order?: 'asc' | 'desc';
  page?: number;
  limit?: number;
}

export interface UserListResponse {
  users: AdminUser[];
  total: number;
  page: number;
  limit: number;
  total_pages: number;
}

export interface AdminStats {
  total_users: number;
  active_users: number;
  total_organizations: number;
  active_trials: number;
  new_users_today: number;
  pending_verifications: number;
  active_sessions: number;
}

export interface SystemActivity {
  id: string;
  type: 'user_created' | 'user_deleted' | 'org_created' | 'trial_started' | 'subscription_changed' | 'login_failed';
  actor_id?: string;
  actor_email?: string;
  target_id?: string;
  target_type?: string;
  description: string;
  metadata: Record<string, unknown>;
  timestamp: string;
}

export interface AdminOrganization extends Organization {
  member_count: number;
  project_count: number;
  owner_email: string;
  trial_status?: string;
  trial_ends_at?: string;
}

export interface SystemSettings {
  registration_enabled: boolean;
  require_email_verification: boolean;
  trial_duration_days: number;
  max_login_attempts: number;
  session_timeout_minutes: number;
  password_min_length: number;
  password_require_uppercase: boolean;
  password_require_lowercase: boolean;
  password_require_number: boolean;
  password_require_special: boolean;
  smtp_configured: boolean;
  maintenance_mode: boolean;
}

export interface Role {
  id: string;
  name: string;
  description: string;
  permissions: string[];
  is_system: boolean;
  user_count: number;
  created_at: string;
}

// =============================================================================
// ADMIN USERS API
// =============================================================================

export const adminUsersApi = {
  /**
   * List all users with filtering and pagination.
   */
  list: async (params: UserListParams = {}): Promise<UserListResponse> => {
    const response = await api.get('/admin/users', { params });
    return response.data;
  },

  /**
   * Get a single user by ID.
   */
  get: async (userId: string): Promise<AdminUserDetail> => {
    const response = await api.get(`/admin/users/${userId}`);
    return response.data;
  },

  /**
   * Create a new user.
   */
  create: async (data: CreateUserRequest): Promise<AdminUser> => {
    const response = await api.post('/admin/users', data);
    return response.data;
  },

  /**
   * Update an existing user.
   */
  update: async (userId: string, data: UpdateUserRequest): Promise<AdminUser> => {
    const response = await api.put(`/admin/users/${userId}`, data);
    return response.data;
  },

  /**
   * Delete a user.
   */
  delete: async (userId: string): Promise<void> => {
    await api.delete(`/admin/users/${userId}`);
  },

  /**
   * Activate a user.
   */
  activate: async (userId: string): Promise<AdminUser> => {
    const response = await api.post(`/admin/users/${userId}/activate`);
    return response.data;
  },

  /**
   * Deactivate a user.
   */
  deactivate: async (userId: string): Promise<AdminUser> => {
    const response = await api.post(`/admin/users/${userId}/deactivate`);
    return response.data;
  },

  /**
   * Verify a user's email manually.
   */
  verifyEmail: async (userId: string): Promise<AdminUser> => {
    const response = await api.post(`/admin/users/${userId}/verify-email`);
    return response.data;
  },

  /**
   * Resend verification email.
   */
  resendVerification: async (userId: string): Promise<{ message: string }> => {
    const response = await api.post(`/admin/users/${userId}/resend-verification`);
    return response.data;
  },

  /**
   * Send password reset email.
   */
  sendPasswordReset: async (userId: string): Promise<{ message: string }> => {
    const response = await api.post(`/admin/users/${userId}/reset-password`);
    return response.data;
  },

  /**
   * Force logout all sessions for a user.
   */
  forceLogout: async (userId: string): Promise<{ message: string; sessions_invalidated: number }> => {
    const response = await api.post(`/admin/users/${userId}/force-logout`);
    return response.data;
  },

  /**
   * Get user's login history.
   */
  getLoginHistory: async (
    userId: string,
    limit = 50
  ): Promise<LoginEvent[]> => {
    const response = await api.get(`/admin/users/${userId}/login-history`, {
      params: { limit },
    });
    return response.data;
  },

  /**
   * Bulk activate users.
   */
  bulkActivate: async (userIds: string[]): Promise<{ affected: number }> => {
    const response = await api.post('/admin/users/bulk/activate', { user_ids: userIds });
    return response.data;
  },

  /**
   * Bulk deactivate users.
   */
  bulkDeactivate: async (userIds: string[]): Promise<{ affected: number }> => {
    const response = await api.post('/admin/users/bulk/deactivate', { user_ids: userIds });
    return response.data;
  },

  /**
   * Bulk delete users.
   */
  bulkDelete: async (userIds: string[]): Promise<{ affected: number }> => {
    const response = await api.post('/admin/users/bulk/delete', { user_ids: userIds });
    return response.data;
  },

  /**
   * Export users to CSV.
   */
  export: async (params: UserListParams = {}): Promise<Blob> => {
    const response = await api.get('/admin/users/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};

// =============================================================================
// ADMIN ORGANIZATIONS API
// =============================================================================

export const adminOrganizationsApi = {
  /**
   * List all organizations.
   */
  list: async (params: {
    search?: string;
    filter?: 'all' | 'active' | 'trial' | 'expired';
    page?: number;
    limit?: number;
  } = {}): Promise<{
    organizations: AdminOrganization[];
    total: number;
    page: number;
    limit: number;
  }> => {
    const response = await api.get('/admin/organizations', { params });
    return response.data;
  },

  /**
   * Get a single organization by ID.
   */
  get: async (orgId: string): Promise<AdminOrganization> => {
    const response = await api.get(`/admin/organizations/${orgId}`);
    return response.data;
  },

  /**
   * Update an organization.
   */
  update: async (
    orgId: string,
    data: Partial<Organization>
  ): Promise<AdminOrganization> => {
    const response = await api.put(`/admin/organizations/${orgId}`, data);
    return response.data;
  },

  /**
   * Delete an organization.
   */
  delete: async (orgId: string): Promise<void> => {
    await api.delete(`/admin/organizations/${orgId}`);
  },

  /**
   * Get organization members.
   */
  getMembers: async (orgId: string): Promise<OrganizationMember[]> => {
    const response = await api.get(`/admin/organizations/${orgId}/members`);
    return response.data;
  },

  /**
   * Change organization tier.
   */
  changeTier: async (
    orgId: string,
    tier: 'free' | 'pro' | 'enterprise'
  ): Promise<AdminOrganization> => {
    const response = await api.post(`/admin/organizations/${orgId}/tier`, { tier });
    return response.data;
  },

  /**
   * Transfer organization ownership.
   */
  transferOwnership: async (
    orgId: string,
    newOwnerId: string
  ): Promise<AdminOrganization> => {
    const response = await api.post(`/admin/organizations/${orgId}/transfer`, {
      new_owner_id: newOwnerId,
    });
    return response.data;
  },
};

// =============================================================================
// ADMIN DASHBOARD API
// =============================================================================

export const adminDashboardApi = {
  /**
   * Get admin dashboard statistics.
   */
  getStats: async (): Promise<AdminStats> => {
    const response = await api.get('/admin/stats');
    return response.data;
  },

  /**
   * Get recent system activity.
   */
  getActivity: async (limit = 20): Promise<SystemActivity[]> => {
    const response = await api.get('/admin/activity', { params: { limit } });
    return response.data;
  },

  /**
   * Get user growth metrics.
   */
  getUserGrowth: async (
    period: '7d' | '30d' | '90d' | '1y' = '30d'
  ): Promise<{
    labels: string[];
    data: number[];
    total_growth: number;
    growth_rate: number;
  }> => {
    const response = await api.get('/admin/metrics/user-growth', { params: { period } });
    return response.data;
  },

  /**
   * Get organization metrics.
   */
  getOrganizationMetrics: async (): Promise<{
    by_tier: { tier: string; count: number }[];
    by_trial_status: { status: string; count: number }[];
    average_member_count: number;
  }> => {
    const response = await api.get('/admin/metrics/organizations');
    return response.data;
  },
};

// =============================================================================
// ADMIN SETTINGS API
// =============================================================================

export const adminSettingsApi = {
  /**
   * Get system settings.
   */
  get: async (): Promise<SystemSettings> => {
    const response = await api.get('/admin/settings');
    return response.data;
  },

  /**
   * Update system settings.
   */
  update: async (settings: Partial<SystemSettings>): Promise<SystemSettings> => {
    const response = await api.put('/admin/settings', settings);
    return response.data;
  },

  /**
   * Test SMTP configuration.
   */
  testSmtp: async (email: string): Promise<{ success: boolean; message: string }> => {
    const response = await api.post('/admin/settings/test-smtp', { email });
    return response.data;
  },

  /**
   * Enable maintenance mode.
   */
  enableMaintenanceMode: async (): Promise<{ message: string }> => {
    const response = await api.post('/admin/settings/maintenance/enable');
    return response.data;
  },

  /**
   * Disable maintenance mode.
   */
  disableMaintenanceMode: async (): Promise<{ message: string }> => {
    const response = await api.post('/admin/settings/maintenance/disable');
    return response.data;
  },
};

// =============================================================================
// ADMIN ROLES API
// =============================================================================

export const adminRolesApi = {
  /**
   * List all roles.
   */
  list: async (): Promise<Role[]> => {
    const response = await api.get('/admin/roles');
    return response.data;
  },

  /**
   * Get a single role.
   */
  get: async (roleId: string): Promise<Role> => {
    const response = await api.get(`/admin/roles/${roleId}`);
    return response.data;
  },

  /**
   * Create a new role.
   */
  create: async (data: {
    name: string;
    description?: string;
    permissions: string[];
  }): Promise<Role> => {
    const response = await api.post('/admin/roles', data);
    return response.data;
  },

  /**
   * Update a role.
   */
  update: async (
    roleId: string,
    data: { name?: string; description?: string; permissions?: string[] }
  ): Promise<Role> => {
    const response = await api.put(`/admin/roles/${roleId}`, data);
    return response.data;
  },

  /**
   * Delete a role.
   */
  delete: async (roleId: string): Promise<void> => {
    await api.delete(`/admin/roles/${roleId}`);
  },

  /**
   * Get all available permissions.
   */
  getPermissions: async (): Promise<{
    permissions: { key: string; name: string; description: string; category: string }[];
  }> => {
    const response = await api.get('/admin/permissions');
    return response.data;
  },
};

// =============================================================================
// ADMIN AUDIT LOG API
// =============================================================================

export interface AuditLogEntry {
  id: string;
  actor_id: string;
  actor_email: string;
  action: string;
  resource_type: string;
  resource_id: string;
  details: Record<string, unknown>;
  ip_address: string;
  user_agent: string;
  timestamp: string;
}

export const adminAuditApi = {
  /**
   * Get audit log entries.
   */
  list: async (params: {
    actor_id?: string;
    action?: string;
    resource_type?: string;
    from_date?: string;
    to_date?: string;
    page?: number;
    limit?: number;
  } = {}): Promise<{
    entries: AuditLogEntry[];
    total: number;
    page: number;
    limit: number;
  }> => {
    const response = await api.get('/admin/audit', { params });
    return response.data;
  },

  /**
   * Export audit log.
   */
  export: async (params: {
    from_date: string;
    to_date: string;
    format?: 'csv' | 'json';
  }): Promise<Blob> => {
    const response = await api.get('/admin/audit/export', {
      params,
      responseType: 'blob',
    });
    return response.data;
  },
};
