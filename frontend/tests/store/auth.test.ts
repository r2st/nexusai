/**
 * Auth store tests
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { useAuthStore, type AuthUser } from '@/store/auth';

// Mock the API module
vi.mock('@/lib/api', () => ({
  TenantContext: {
    setCurrentTenantId: vi.fn(),
    clear: vi.fn(),
  },
  api: {
    post: vi.fn(),
  },
}));

const mockUser: AuthUser = {
  id: 'user-123',
  email: 'test@example.com',
  full_name: 'Test User',
  role: 'staff_admin',
  organization_id: 'org-123',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

const mockOrg = {
  id: 'org-123',
  name: 'Test Org',
  slug: 'test-org',
  is_active: true,
  created_at: '2024-01-01T00:00:00Z',
  updated_at: '2024-01-01T00:00:00Z',
};

describe('useAuthStore', () => {
  beforeEach(() => {
    // Reset store state
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      currentOrganization: null,
      organizations: [],
      memberRole: null,
      sessionExpiresAt: null,
      lastActivity: Date.now(),
      _hasHydrated: false,
    });
    localStorage.clear();
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('initial state', () => {
    it('starts with null user', () => {
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
    });

    it('starts as not authenticated', () => {
      const state = useAuthStore.getState();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('setUser', () => {
    it('sets the user', () => {
      useAuthStore.getState().setUser(mockUser);
      
      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
    });

    it('sets isAuthenticated to false when user is null', () => {
      useAuthStore.getState().setUser(mockUser);
      useAuthStore.getState().setUser(null);
      
      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
    });
  });

  describe('login', () => {
    it('sets user and stores tokens', () => {
      const accessToken = 'access-token-123';
      const refreshToken = 'refresh-token-456';

      useAuthStore.getState().login(mockUser, accessToken, refreshToken);

      const state = useAuthStore.getState();
      expect(state.user).toEqual(mockUser);
      expect(state.isAuthenticated).toBe(true);
      expect(localStorage.getItem('access_token')).toBe(accessToken);
      expect(localStorage.getItem('refresh_token')).toBe(refreshToken);
    });
  });

  describe('logout', () => {
    it('clears user and removes tokens', () => {
      // First login
      useAuthStore.getState().login(mockUser, 'access', 'refresh');

      // Then logout
      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.user).toBeNull();
      expect(state.isAuthenticated).toBe(false);
      expect(localStorage.getItem('access_token')).toBeNull();
      expect(localStorage.getItem('refresh_token')).toBeNull();
    });

    it('clears organization state on logout', () => {
      useAuthStore.getState().login(mockUser, 'access', 'refresh');
      useAuthStore.getState().setOrganizations([mockOrg]);
      useAuthStore.getState().setCurrentOrganization(mockOrg);

      useAuthStore.getState().logout();

      const state = useAuthStore.getState();
      expect(state.currentOrganization).toBeNull();
      expect(state.organizations).toEqual([]);
    });
  });

  describe('Organization Management', () => {
    it('should set current organization', () => {
      useAuthStore.getState().setCurrentOrganization(mockOrg);

      const state = useAuthStore.getState();
      expect(state.currentOrganization).toEqual(mockOrg);
    });

    it('should set organizations list', () => {
      useAuthStore.getState().setOrganizations([mockOrg]);

      const state = useAuthStore.getState();
      expect(state.organizations).toEqual([mockOrg]);
    });

    it('should switch organization', () => {
      useAuthStore.getState().setOrganizations([mockOrg]);
      useAuthStore.getState().switchOrganization('org-123');

      const state = useAuthStore.getState();
      expect(state.currentOrganization).toEqual(mockOrg);
    });

    it('should not switch to non-existent organization', () => {
      useAuthStore.getState().setOrganizations([mockOrg]);
      useAuthStore.getState().switchOrganization('non-existent');

      const state = useAuthStore.getState();
      expect(state.currentOrganization).toBeNull();
    });
  });

  describe('Permission Helpers', () => {
    it('should return false for permissions when no role', () => {
      expect(useAuthStore.getState().can('users', 'read')).toBe(false);
    });

    it('should check admin status', () => {
      useAuthStore.getState().setUser(mockUser);
      expect(useAuthStore.getState().isAdmin()).toBe(true);
    });

    it('should return false for admin when not admin role', () => {
      useAuthStore.getState().setUser({ ...mockUser, role: 'staff_viewer' });
      expect(useAuthStore.getState().isAdmin()).toBe(false);
    });

    it('should check org admin status', () => {
      useAuthStore.setState({ memberRole: 'org_admin' });
      expect(useAuthStore.getState().isOrgOwner()).toBe(true);
    });

    it('should return false for org admin when not admin', () => {
      useAuthStore.setState({ memberRole: 'staff_viewer' });
      expect(useAuthStore.getState().isOrgOwner()).toBe(false);
    });
  });

  describe('Session Management', () => {
    beforeEach(() => {
      useAuthStore.getState().login(mockUser, 'token', 'refresh', 3600);
    });

    it('should update last activity', () => {
      const initialActivity = useAuthStore.getState().lastActivity;

      // Small delay to ensure time difference
      useAuthStore.getState().updateLastActivity();

      const state = useAuthStore.getState();
      expect(state.lastActivity).toBeGreaterThanOrEqual(initialActivity);
      // Session should be set (sliding window extends to 30 min from now)
      expect(state.sessionExpiresAt).not.toBeNull();
    });

    it('should get session time remaining', () => {
      const remaining = useAuthStore.getState().getSessionTimeRemaining();
      expect(remaining).toBeGreaterThan(0);
      expect(remaining).toBeLessThanOrEqual(3600 * 1000);
    });

    it('should return 0 for expired session', () => {
      useAuthStore.setState({ sessionExpiresAt: Date.now() - 1000 });
      expect(useAuthStore.getState().getSessionTimeRemaining()).toBe(0);
    });

    it('should return 0 when no session expiry', () => {
      useAuthStore.setState({ sessionExpiresAt: null });
      expect(useAuthStore.getState().getSessionTimeRemaining()).toBe(0);
    });

    it('should detect expired session by token expiry', () => {
      useAuthStore.setState({
        sessionExpiresAt: Date.now() - 1000,
        lastActivity: Date.now(),
      });

      expect(useAuthStore.getState().isSessionExpired()).toBe(true);
    });

    it('should detect expired session by inactivity', () => {
      useAuthStore.setState({
        sessionExpiresAt: Date.now() + 3600 * 1000,
        lastActivity: Date.now() - 31 * 60 * 1000, // 31 minutes ago
      });

      expect(useAuthStore.getState().isSessionExpired()).toBe(true);
    });

    it('should detect active session', () => {
      useAuthStore.setState({
        sessionExpiresAt: Date.now() + 3600 * 1000,
        lastActivity: Date.now(),
      });

      expect(useAuthStore.getState().isSessionExpired()).toBe(false);
    });

    it('should detect expired when no session expiry set', () => {
      useAuthStore.setState({ sessionExpiresAt: null });
      expect(useAuthStore.getState().isSessionExpired()).toBe(true);
    });
  });

  describe('Hydration', () => {
    it('should track hydration state', () => {
      expect(useAuthStore.getState()._hasHydrated).toBe(false);

      useAuthStore.getState().setHasHydrated(true);

      expect(useAuthStore.getState()._hasHydrated).toBe(true);
    });
  });
});
