'use client';

/**
 * Role-Based Access Control Component
 *
 * Wraps content that requires specific roles or permissions to access.
 */

import { useEffect, useState, createContext, useContext, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Shield, AlertTriangle } from 'lucide-react';
import { api, User } from '@/lib/api';

// =============================================================================
// AUTH CONTEXT
// =============================================================================

interface AuthContextType {
  user: User | null;
  isLoading: boolean;
  isAuthenticated: boolean;
  hasRole: (role: string | string[]) => boolean;
  hasPermission: (permission: string | string[]) => boolean;
  refreshUser: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType>({
  user: null,
  isLoading: true,
  isAuthenticated: false,
  hasRole: () => false,
  hasPermission: () => false,
  refreshUser: async () => {},
});

export const useAuth = () => useContext(AuthContext);

// =============================================================================
// AUTH PROVIDER
// =============================================================================

interface AuthProviderProps {
  children: ReactNode;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [user, setUser] = useState<User | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const fetchUser = async () => {
    try {
      const token = localStorage.getItem('access_token');
      if (!token) {
        setUser(null);
        return;
      }

      const response = await api.get('/auth/me');
      setUser(response.data);
    } catch (error) {
      console.error('Failed to fetch user:', error);
      setUser(null);
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchUser();
  }, []);

  const hasRole = (role: string | string[]): boolean => {
    if (!user) return false;
    const roles = Array.isArray(role) ? role : [role];
    return roles.includes(user.role);
  };

  const hasPermission = (permission: string | string[]): boolean => {
    if (!user) return false;
    // In a real implementation, this would check against user's permissions
    // For now, admins have all permissions
    if (user.role === 'admin' || user.role === 'superadmin') return true;
    // TODO: Implement permission checking from user metadata or API
    return false;
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        isAuthenticated: !!user,
        hasRole,
        hasPermission,
        refreshUser: fetchUser,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

// =============================================================================
// REQUIRE ROLE COMPONENT
// =============================================================================

interface RequireRoleProps {
  children: ReactNode;
  roles: string | string[];
  fallback?: ReactNode;
  redirectTo?: string;
}

/**
 * Wraps content that requires specific roles to view.
 * Shows fallback or redirects if user doesn't have the required role.
 */
export function RequireRole({
  children,
  roles,
  fallback,
  redirectTo,
}: RequireRoleProps) {
  const router = useRouter();
  const { user, isLoading, hasRole } = useAuth();

  useEffect(() => {
    if (!isLoading && !hasRole(roles) && redirectTo) {
      router.push(redirectTo);
    }
  }, [isLoading, hasRole, roles, redirectTo, router]);

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  if (!hasRole(roles)) {
    if (fallback) return <>{fallback}</>;

    return (
      <div className="flex flex-col items-center justify-center p-8 text-center">
        <div className="h-16 w-16 rounded-full bg-destructive/10 flex items-center justify-center mb-4">
          <Shield className="h-8 w-8 text-destructive" />
        </div>
        <h2 className="text-xl font-semibold mb-2">Access Denied</h2>
        <p className="text-muted-foreground max-w-md">
          You don't have permission to access this content.
          Please contact an administrator if you believe this is an error.
        </p>
      </div>
    );
  }

  return <>{children}</>;
}

// =============================================================================
// REQUIRE PERMISSION COMPONENT
// =============================================================================

interface RequirePermissionProps {
  children: ReactNode;
  permissions: string | string[];
  requireAll?: boolean;
  fallback?: ReactNode;
}

/**
 * Wraps content that requires specific permissions to view.
 */
export function RequirePermission({
  children,
  permissions,
  requireAll = false,
  fallback,
}: RequirePermissionProps) {
  const { isLoading, hasPermission } = useAuth();

  if (isLoading) {
    return (
      <div className="flex items-center justify-center p-8">
        <div className="h-8 w-8 rounded-full border-2 border-primary border-t-transparent animate-spin" />
      </div>
    );
  }

  const permArray = Array.isArray(permissions) ? permissions : [permissions];
  const hasAccess = requireAll
    ? permArray.every((p) => hasPermission(p))
    : permArray.some((p) => hasPermission(p));

  if (!hasAccess) {
    return fallback ? <>{fallback}</> : null;
  }

  return <>{children}</>;
}

// =============================================================================
// ROLE BADGE COMPONENT
// =============================================================================

interface RoleBadgeProps {
  role: string;
  size?: 'sm' | 'md' | 'lg';
}

const roleStyles: Record<string, string> = {
  superadmin: 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400',
  admin: 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400',
  user: 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400',
  member: 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400',
  owner: 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
};

const sizeStyles: Record<string, string> = {
  sm: 'px-1.5 py-0.5 text-xs',
  md: 'px-2 py-1 text-xs',
  lg: 'px-3 py-1.5 text-sm',
};

export function RoleBadge({ role, size = 'md' }: RoleBadgeProps) {
  const style = roleStyles[role.toLowerCase()] || roleStyles.user;
  const sizeStyle = sizeStyles[size];

  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full font-medium ${style} ${sizeStyle}`}
    >
      {(role === 'admin' || role === 'superadmin') && (
        <Shield className={size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'} />
      )}
      {role}
    </span>
  );
}

// =============================================================================
// PROTECTED ROUTE COMPONENT
// =============================================================================

interface ProtectedRouteProps {
  children: ReactNode;
  requiredRoles?: string[];
  requiredPermissions?: string[];
  requireAllPermissions?: boolean;
  loginPath?: string;
  unauthorizedPath?: string;
}

/**
 * Higher-level component for protecting entire routes.
 */
export function ProtectedRoute({
  children,
  requiredRoles,
  requiredPermissions,
  requireAllPermissions = false,
  loginPath = '/login',
  unauthorizedPath,
}: ProtectedRouteProps) {
  const router = useRouter();
  const { user, isLoading, hasRole, hasPermission } = useAuth();
  const [isAuthorized, setIsAuthorized] = useState(false);

  useEffect(() => {
    if (isLoading) return;

    // Not authenticated
    if (!user) {
      router.push(`${loginPath}?redirect=${encodeURIComponent(window.location.pathname)}`);
      return;
    }

    // Check roles
    if (requiredRoles && requiredRoles.length > 0) {
      if (!hasRole(requiredRoles)) {
        if (unauthorizedPath) {
          router.push(unauthorizedPath);
        }
        return;
      }
    }

    // Check permissions
    if (requiredPermissions && requiredPermissions.length > 0) {
      const hasAccess = requireAllPermissions
        ? requiredPermissions.every((p) => hasPermission(p))
        : requiredPermissions.some((p) => hasPermission(p));

      if (!hasAccess) {
        if (unauthorizedPath) {
          router.push(unauthorizedPath);
        }
        return;
      }
    }

    setIsAuthorized(true);
  }, [
    user,
    isLoading,
    requiredRoles,
    requiredPermissions,
    requireAllPermissions,
    hasRole,
    hasPermission,
    router,
    loginPath,
    unauthorizedPath,
  ]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4">
          <div className="h-12 w-12 rounded-full bg-primary/10 flex items-center justify-center animate-pulse">
            <Shield className="h-6 w-6 text-primary" />
          </div>
          <p className="text-sm text-muted-foreground">Verifying access...</p>
        </div>
      </div>
    );
  }

  if (!isAuthorized) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-background">
        <div className="flex flex-col items-center gap-4 text-center p-8">
          <div className="h-16 w-16 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
            <AlertTriangle className="h-8 w-8 text-yellow-600" />
          </div>
          <h1 className="text-2xl font-bold">Unauthorized</h1>
          <p className="text-muted-foreground max-w-md">
            You don't have permission to access this page.
            Please contact an administrator if you believe this is an error.
          </p>
          <button
            onClick={() => router.back()}
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
          >
            Go Back
          </button>
        </div>
      </div>
    );
  }

  return <>{children}</>;
}

// =============================================================================
// HOOK: useRequireRole
// =============================================================================

/**
 * Hook version for checking roles in components.
 */
export function useRequireRole(roles: string | string[]) {
  const { user, isLoading, hasRole } = useAuth();
  const router = useRouter();

  const canAccess = hasRole(roles);

  return {
    user,
    isLoading,
    canAccess,
    redirect: (path: string) => {
      if (!isLoading && !canAccess) {
        router.push(path);
      }
    },
  };
}

// =============================================================================
// HOOK: useRequirePermission
// =============================================================================

/**
 * Hook version for checking permissions in components.
 */
export function useRequirePermission(
  permissions: string | string[],
  requireAll = false
) {
  const { user, isLoading, hasPermission } = useAuth();

  const permArray = Array.isArray(permissions) ? permissions : [permissions];
  const canAccess = requireAll
    ? permArray.every((p) => hasPermission(p))
    : permArray.some((p) => hasPermission(p));

  return {
    user,
    isLoading,
    canAccess,
  };
}
