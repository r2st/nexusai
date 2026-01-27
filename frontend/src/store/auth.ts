import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { User, Organization, OrganizationMember } from '@/lib/api';
import { TenantContext, api } from '@/lib/api';
import { type UserRole, hasPermission, isAdminRole, isOrgAdmin } from '@/lib/security';

// Extended User type with role
export interface AuthUser extends User {
  role: UserRole;
  organization_id: string | null;
}

interface AuthState {
  // Hydration state
  _hasHydrated: boolean;
  setHasHydrated: (state: boolean) => void;

  // Core auth state
  user: AuthUser | null;
  isAuthenticated: boolean;

  // Organization context
  currentOrganization: Organization | null;
  organizations: Organization[];
  memberRole: UserRole | null;

  // Session management
  sessionExpiresAt: number | null;
  lastActivity: number;

  // Actions
  setUser: (user: AuthUser | null) => void;
  login: (user: AuthUser, accessToken: string, refreshToken: string, expiresIn?: number) => void;
  logout: () => void;

  // Organization actions
  setCurrentOrganization: (org: Organization | null) => void;
  setOrganizations: (orgs: Organization[]) => void;
  setMemberRole: (role: UserRole | null) => void;
  switchOrganization: (orgId: string) => void;

  // Permission helpers
  can: (resource: string, action: 'create' | 'read' | 'update' | 'delete') => boolean;
  isAdmin: () => boolean;
  isOrgOwner: () => boolean;

  // Session helpers
  updateLastActivity: () => void;
  isSessionExpired: () => boolean;
  getSessionTimeRemaining: () => number;
}

const SESSION_TIMEOUT_MS = 30 * 60 * 1000; // 30 minutes default

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      // Hydration state
      _hasHydrated: false,
      setHasHydrated: (state) => set({ _hasHydrated: state }),

      // Initial state
      user: null,
      isAuthenticated: false,
      currentOrganization: null,
      organizations: [],
      memberRole: null,
      sessionExpiresAt: null,
      lastActivity: Date.now(),

      setUser: (user) => set({
        user,
        isAuthenticated: !!user,
        memberRole: user?.role || null,
      }),

      login: (user, accessToken, refreshToken, expiresIn = 3600) => {
        localStorage.setItem('access_token', accessToken);
        localStorage.setItem('refresh_token', refreshToken);

        const now = Date.now();
        const sessionExpiresAt = now + (expiresIn * 1000);

        // Set tenant context if user has an organization
        if (user.organization_id) {
          TenantContext.setCurrentTenantId(user.organization_id);
        }

        set({
          user,
          isAuthenticated: true,
          memberRole: user.role,
          sessionExpiresAt,
          lastActivity: now,
        });
      },

      logout: () => {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        TenantContext.clear();

        set({
          user: null,
          isAuthenticated: false,
          currentOrganization: null,
          organizations: [],
          memberRole: null,
          sessionExpiresAt: null,
        });
      },

      // Organization management
      setCurrentOrganization: (org) => {
        if (org) {
          TenantContext.setCurrentTenantId(org.id);
        } else {
          TenantContext.clear();
        }
        set({ currentOrganization: org });
      },

      setOrganizations: (orgs) => set({ organizations: orgs }),

      setMemberRole: (role) => set({ memberRole: role }),

      switchOrganization: (orgId) => {
        const { organizations } = get();
        const org = organizations.find(o => o.id === orgId);
        if (org) {
          TenantContext.setCurrentTenantId(orgId);
          set({ currentOrganization: org });
        }
      },

      // Permission helpers
      can: (resource, action) => {
        const { memberRole } = get();
        if (!memberRole) return false;
        return hasPermission(memberRole, resource, action);
      },

      isAdmin: () => {
        const { memberRole } = get();
        if (!memberRole) return false;
        return isAdminRole(memberRole);
      },

      isOrgOwner: () => {
        const { memberRole } = get();
        if (!memberRole) return false;
        return isOrgAdmin(memberRole);
      },

      // Session management
      updateLastActivity: () => {
        const now = Date.now();
        const { sessionExpiresAt } = get();

        // Extend session on activity (sliding window)
        if (sessionExpiresAt) {
          set({
            lastActivity: now,
            sessionExpiresAt: now + SESSION_TIMEOUT_MS,
          });
        }
      },

      isSessionExpired: () => {
        const { sessionExpiresAt, lastActivity } = get();
        if (!sessionExpiresAt) return true;

        const now = Date.now();
        // Check both token expiry and inactivity
        const inactivityExpired = now - lastActivity > SESSION_TIMEOUT_MS;
        const tokenExpired = now > sessionExpiresAt;

        return inactivityExpired || tokenExpired;
      },

      getSessionTimeRemaining: () => {
        const { sessionExpiresAt } = get();
        if (!sessionExpiresAt) return 0;
        return Math.max(0, sessionExpiresAt - Date.now());
      },
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
        currentOrganization: state.currentOrganization,
        organizations: state.organizations,
        memberRole: state.memberRole,
        sessionExpiresAt: state.sessionExpiresAt,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Validate session on rehydration
          const accessToken = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
          const refreshToken = typeof window !== 'undefined' ? localStorage.getItem('refresh_token') : null;

          if (state.isAuthenticated && !accessToken) {
            // State says authenticated but no token - clear auth state
            state.user = null;
            state.isAuthenticated = false;
            state.memberRole = null;
            state.sessionExpiresAt = null;
          } else if (state.isAuthenticated && accessToken) {
            // Restore tenant context if user has organization
            if (state.user?.organization_id) {
              TenantContext.setCurrentTenantId(state.user.organization_id);
            } else if (state.currentOrganization?.id) {
              TenantContext.setCurrentTenantId(state.currentOrganization.id);
            }

            // Update lastActivity on rehydration to prevent inactivity timeout
            // This effectively resets the inactivity timer on page refresh
            const now = Date.now();
            useAuthStore.setState({ lastActivity: now });

            // Check if session appears expired based on token expiry timestamp
            if (state.sessionExpiresAt && now > state.sessionExpiresAt) {
              // Session expired - attempt refresh in background
              if (refreshToken) {
                api.post('/auth/refresh', { refresh_token: refreshToken })
                  .then((response) => {
                    const { access_token, refresh_token: newRefreshToken } = response.data;
                    localStorage.setItem('access_token', access_token);
                    localStorage.setItem('refresh_token', newRefreshToken);
                    // Update session expiry (1 hour from now)
                    useAuthStore.setState({
                      sessionExpiresAt: Date.now() + 3600 * 1000,
                      lastActivity: Date.now(),
                    });
                  })
                  .catch(() => {
                    // Refresh failed - clear auth state
                    localStorage.removeItem('access_token');
                    localStorage.removeItem('refresh_token');
                    useAuthStore.setState({
                      user: null,
                      isAuthenticated: false,
                      memberRole: null,
                      sessionExpiresAt: null,
                      currentOrganization: null,
                      organizations: [],
                    });
                  });
              } else {
                // No refresh token - clear auth state
                state.user = null;
                state.isAuthenticated = false;
                state.memberRole = null;
                state.sessionExpiresAt = null;
              }
            }
          }
          state.setHasHydrated(true);
        }
      },
    }
  )
);

// Hook to wait for hydration
export function useAuthHydrated() {
  return useAuthStore((state) => state._hasHydrated);
}

// Hook for checking permissions in components
export function usePermission(resource: string, action: 'create' | 'read' | 'update' | 'delete'): boolean {
  const can = useAuthStore(state => state.can);
  return can(resource, action);
}

// Hook for checking admin status
export function useIsAdmin(): boolean {
  const isAdmin = useAuthStore(state => state.isAdmin);
  return isAdmin();
}
