'use client';

import { useEffect, useState, type ReactNode } from 'react';
import { useRouter, usePathname } from 'next/navigation';
import { Loader2 } from 'lucide-react';
import { useAuthStore } from '@/store/auth';
import { type UserRole, hasPermission, isAdminRole } from '@/lib/security';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface RouteGuardProps {
  children: ReactNode;
  /** Required roles to access this route */
  allowedRoles?: UserRole[];
  /** Required permission (resource + action) */
  requiredPermission?: {
    resource: string;
    action: 'create' | 'read' | 'update' | 'delete';
  };
  /** Redirect path when unauthorized (default: /login) */
  redirectTo?: string;
  /** Show loading spinner while checking auth */
  showLoader?: boolean;
  /** Fallback component when unauthorized */
  fallback?: ReactNode;
  /** Require admin access */
  requireAdmin?: boolean;
  /** Require org admin access */
  requireOrgAdmin?: boolean;
}

// -----------------------------------------------------------------------------
// Route Guard Component
// -----------------------------------------------------------------------------

export function RouteGuard({
  children,
  allowedRoles,
  requiredPermission,
  redirectTo = '/login',
  showLoader = true,
  fallback,
  requireAdmin = false,
  requireOrgAdmin = false,
}: RouteGuardProps) {
  const router = useRouter();
  const pathname = usePathname();
  const [isChecking, setIsChecking] = useState(true);
  const [isAuthorized, setIsAuthorized] = useState(false);

  const {
    isAuthenticated,
    memberRole,
    isSessionExpired,
    can,
    isAdmin,
    isOrgOwner,
  } = useAuthStore();

  useEffect(() => {
    const checkAuth = async () => {
      setIsChecking(true);

      // Check if authenticated
      if (!isAuthenticated) {
        const redirectUrl = `${redirectTo}?redirect=${encodeURIComponent(pathname)}`;
        router.push(redirectUrl);
        return;
      }

      // Check session expiry
      if (isSessionExpired()) {
        // Session expired, redirect to login
        router.push(`${redirectTo}?expired=true&redirect=${encodeURIComponent(pathname)}`);
        return;
      }

      // Check admin requirement
      if (requireAdmin && !isAdmin()) {
        setIsAuthorized(false);
        setIsChecking(false);
        if (!fallback) {
          router.push('/unauthorized');
        }
        return;
      }

      // Check org admin requirement
      if (requireOrgAdmin && !isOrgOwner()) {
        setIsAuthorized(false);
        setIsChecking(false);
        if (!fallback) {
          router.push('/unauthorized');
        }
        return;
      }

      // Check role requirement
      if (allowedRoles && allowedRoles.length > 0) {
        if (!memberRole || !allowedRoles.includes(memberRole)) {
          setIsAuthorized(false);
          setIsChecking(false);
          if (!fallback) {
            router.push('/unauthorized');
          }
          return;
        }
      }

      // Check permission requirement
      if (requiredPermission) {
        if (!can(requiredPermission.resource, requiredPermission.action)) {
          setIsAuthorized(false);
          setIsChecking(false);
          if (!fallback) {
            router.push('/unauthorized');
          }
          return;
        }
      }

      // All checks passed
      setIsAuthorized(true);
      setIsChecking(false);
    };

    checkAuth();
  }, [
    isAuthenticated,
    memberRole,
    pathname,
    router,
    redirectTo,
    allowedRoles,
    requiredPermission,
    requireAdmin,
    requireOrgAdmin,
    isSessionExpired,
    can,
    isAdmin,
    isOrgOwner,
    fallback,
  ]);

  // Show loading state
  if (isChecking && showLoader) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Checking authorization...</p>
        </div>
      </div>
    );
  }

  // Show fallback when unauthorized
  if (!isAuthorized && fallback) {
    return <>{fallback}</>;
  }

  // Don't render children if not authorized (redirect will happen)
  if (!isAuthorized) {
    return null;
  }

  return <>{children}</>;
}

// -----------------------------------------------------------------------------
// Higher-Order Component for Route Protection
// -----------------------------------------------------------------------------

export function withRouteGuard<P extends object>(
  Component: React.ComponentType<P>,
  guardProps: Omit<RouteGuardProps, 'children'>
) {
  return function GuardedComponent(props: P) {
    return (
      <RouteGuard {...guardProps}>
        <Component {...props} />
      </RouteGuard>
    );
  };
}

// -----------------------------------------------------------------------------
// Permission-Based Rendering
// -----------------------------------------------------------------------------

export interface CanProps {
  resource: string;
  action: 'create' | 'read' | 'update' | 'delete';
  children: ReactNode;
  fallback?: ReactNode;
}

export function Can({ resource, action, children, fallback }: CanProps) {
  const can = useAuthStore((state) => state.can);

  if (can(resource, action)) {
    return <>{children}</>;
  }

  return fallback ? <>{fallback}</> : null;
}

// -----------------------------------------------------------------------------
// Role-Based Rendering
// -----------------------------------------------------------------------------

export interface RequireRoleProps {
  roles: UserRole[];
  children: ReactNode;
  fallback?: ReactNode;
}

export function RequireRole({ roles, children, fallback }: RequireRoleProps) {
  const memberRole = useAuthStore((state) => state.memberRole);

  if (memberRole && roles.includes(memberRole)) {
    return <>{children}</>;
  }

  return fallback ? <>{fallback}</> : null;
}

// -----------------------------------------------------------------------------
// Admin-Only Rendering
// -----------------------------------------------------------------------------

export interface AdminOnlyProps {
  children: ReactNode;
  fallback?: ReactNode;
  orgAdminOnly?: boolean;
}

export function AdminOnly({ children, fallback, orgAdminOnly = false }: AdminOnlyProps) {
  const isAdmin = useAuthStore((state) => state.isAdmin);
  const isOrgOwner = useAuthStore((state) => state.isOrgOwner);

  const hasAccess = orgAdminOnly ? isOrgOwner() : isAdmin();

  if (hasAccess) {
    return <>{children}</>;
  }

  return fallback ? <>{fallback}</> : null;
}

// -----------------------------------------------------------------------------
// Unauthorized Page Component
// -----------------------------------------------------------------------------

export function UnauthorizedPage() {
  const router = useRouter();

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="text-center space-y-4 max-w-md">
        <div className="text-6xl">🔒</div>
        <h1 className="text-2xl font-bold">Access Denied</h1>
        <p className="text-muted-foreground">
          You don&apos;t have permission to access this page.
          Please contact your administrator if you believe this is a mistake.
        </p>
        <div className="flex items-center justify-center gap-4 pt-4">
          <button
            onClick={() => router.back()}
            className="px-4 py-2 text-sm font-medium border rounded-md hover:bg-muted transition-colors"
          >
            Go Back
          </button>
          <button
            onClick={() => router.push('/')}
            className="px-4 py-2 text-sm font-medium bg-primary text-primary-foreground rounded-md hover:bg-primary/90 transition-colors"
          >
            Go Home
          </button>
        </div>
      </div>
    </div>
  );
}

export default RouteGuard;
