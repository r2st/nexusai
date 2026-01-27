/**
 * RouteGuard component tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { RouteGuard, Can, RequireRole, AdminOnly } from '@/components/auth/route-guard';

// Mock next/navigation
const mockPush = vi.fn();
const mockPathname = '/protected';

vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
  }),
  usePathname: () => mockPathname,
}));

// Mock auth store
const mockAuthStore: {
  isAuthenticated: boolean;
  memberRole: string;
  isSessionExpired: ReturnType<typeof vi.fn>;
  can: ReturnType<typeof vi.fn>;
  isAdmin: ReturnType<typeof vi.fn>;
  isOrgOwner: ReturnType<typeof vi.fn>;
} = {
  isAuthenticated: true,
  memberRole: 'staff_engineer',
  isSessionExpired: vi.fn(() => false),
  can: vi.fn((resource: string, action: string) => true),
  isAdmin: vi.fn(() => false),
  isOrgOwner: vi.fn(() => false),
};

vi.mock('@/store/auth', () => ({
  useAuthStore: (selector?: (state: typeof mockAuthStore) => unknown) =>
    selector ? selector(mockAuthStore) : mockAuthStore,
}));

describe('RouteGuard Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockAuthStore.isAuthenticated = true;
    mockAuthStore.memberRole = 'staff_engineer';
    mockAuthStore.isSessionExpired.mockReturnValue(false);
    mockAuthStore.can.mockReturnValue(true);
    mockAuthStore.isAdmin.mockReturnValue(false);
    mockAuthStore.isOrgOwner.mockReturnValue(false);
  });

  describe('authentication check', () => {
    it('renders children when authenticated', async () => {
      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });
    });

    it('redirects to login when not authenticated', async () => {
      mockAuthStore.isAuthenticated = false;

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining('/login')
        );
      });
    });

    it('includes redirect path in login URL', async () => {
      mockAuthStore.isAuthenticated = false;

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining(`redirect=${encodeURIComponent(mockPathname)}`)
        );
      });
    });

    it('uses custom redirectTo path', async () => {
      mockAuthStore.isAuthenticated = false;

      render(
        <RouteGuard redirectTo="/custom-login">
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining('/custom-login')
        );
      });
    });
  });

  describe('session expiry', () => {
    it('redirects when session is expired', async () => {
      mockAuthStore.isSessionExpired.mockReturnValue(true);

      render(
        <RouteGuard>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith(
          expect.stringContaining('expired=true')
        );
      });
    });
  });

  describe('role-based access', () => {
    it('allows access for allowed roles', async () => {
      mockAuthStore.memberRole = 'staff_admin';

      render(
        <RouteGuard allowedRoles={['staff_admin', 'org_admin']}>
          <div>Admin Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Admin Content')).toBeInTheDocument();
      });
    });

    it('denies access for non-allowed roles', async () => {
      mockAuthStore.memberRole = 'staff_viewer';

      render(
        <RouteGuard allowedRoles={['staff_admin', 'org_admin']}>
          <div>Admin Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });
    });

    it('shows fallback for unauthorized roles', async () => {
      mockAuthStore.memberRole = 'staff_viewer';

      render(
        <RouteGuard
          allowedRoles={['staff_admin']}
          fallback={<div>Access Denied</div>}
        >
          <div>Admin Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Access Denied')).toBeInTheDocument();
        expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
      });
    });
  });

  describe('permission-based access', () => {
    it('allows access when permission is granted', async () => {
      mockAuthStore.can.mockReturnValue(true);

      render(
        <RouteGuard requiredPermission={{ resource: 'users', action: 'read' }}>
          <div>Has Permission</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Has Permission')).toBeInTheDocument();
      });
    });

    it('denies access when permission is denied', async () => {
      mockAuthStore.can.mockReturnValue(false);

      render(
        <RouteGuard requiredPermission={{ resource: 'users', action: 'delete' }}>
          <div>Has Permission</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });
    });
  });

  describe('admin requirements', () => {
    it('allows admin access when requireAdmin is true and user is admin', async () => {
      mockAuthStore.isAdmin.mockReturnValue(true);

      render(
        <RouteGuard requireAdmin>
          <div>Admin Area</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Admin Area')).toBeInTheDocument();
      });
    });

    it('denies non-admin access when requireAdmin is true', async () => {
      mockAuthStore.isAdmin.mockReturnValue(false);

      render(
        <RouteGuard requireAdmin>
          <div>Admin Area</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/unauthorized');
      });
    });

    it('allows org admin access when requireOrgAdmin is true', async () => {
      mockAuthStore.isOrgOwner.mockReturnValue(true);

      render(
        <RouteGuard requireOrgAdmin>
          <div>Org Admin Area</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.getByText('Org Admin Area')).toBeInTheDocument();
      });
    });
  });

  describe('loading state', () => {
    it('eventually shows content after authorization check', async () => {
      render(
        <RouteGuard showLoader>
          <div>Protected Content</div>
        </RouteGuard>
      );

      // With synchronous mocks, authorization check completes immediately
      // so we should see the protected content
      await waitFor(() => {
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });
    });

    it('hides loading state when showLoader is false', async () => {
      render(
        <RouteGuard showLoader={false}>
          <div>Protected Content</div>
        </RouteGuard>
      );

      await waitFor(() => {
        expect(screen.queryByText('Checking authorization...')).not.toBeInTheDocument();
        expect(screen.getByText('Protected Content')).toBeInTheDocument();
      });
    });
  });
});

describe('Can Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when permission is granted', () => {
    mockAuthStore.can.mockReturnValue(true);

    render(
      <Can resource="documents" action="create">
        <div>Create Document</div>
      </Can>
    );

    expect(screen.getByText('Create Document')).toBeInTheDocument();
  });

  it('renders nothing when permission is denied', () => {
    mockAuthStore.can.mockReturnValue(false);

    render(
      <Can resource="documents" action="delete">
        <div>Delete Document</div>
      </Can>
    );

    expect(screen.queryByText('Delete Document')).not.toBeInTheDocument();
  });

  it('renders fallback when permission is denied', () => {
    mockAuthStore.can.mockReturnValue(false);

    render(
      <Can
        resource="documents"
        action="delete"
        fallback={<div>No Permission</div>}
      >
        <div>Delete Document</div>
      </Can>
    );

    expect(screen.getByText('No Permission')).toBeInTheDocument();
    expect(screen.queryByText('Delete Document')).not.toBeInTheDocument();
  });
});

describe('RequireRole Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children for matching role', () => {
    mockAuthStore.memberRole = 'staff_admin';

    render(
      <RequireRole roles={['staff_admin', 'org_admin']}>
        <div>Admin Panel</div>
      </RequireRole>
    );

    expect(screen.getByText('Admin Panel')).toBeInTheDocument();
  });

  it('renders nothing for non-matching role', () => {
    mockAuthStore.memberRole = 'staff_viewer';

    render(
      <RequireRole roles={['staff_admin']}>
        <div>Admin Panel</div>
      </RequireRole>
    );

    expect(screen.queryByText('Admin Panel')).not.toBeInTheDocument();
  });

  it('renders fallback for non-matching role', () => {
    mockAuthStore.memberRole = 'staff_viewer';

    render(
      <RequireRole
        roles={['staff_admin']}
        fallback={<div>Viewer Content</div>}
      >
        <div>Admin Panel</div>
      </RequireRole>
    );

    expect(screen.getByText('Viewer Content')).toBeInTheDocument();
  });
});

describe('AdminOnly Component', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children for admin users', () => {
    mockAuthStore.isAdmin.mockReturnValue(true);

    render(
      <AdminOnly>
        <div>Admin Content</div>
      </AdminOnly>
    );

    expect(screen.getByText('Admin Content')).toBeInTheDocument();
  });

  it('renders nothing for non-admin users', () => {
    mockAuthStore.isAdmin.mockReturnValue(false);

    render(
      <AdminOnly>
        <div>Admin Content</div>
      </AdminOnly>
    );

    expect(screen.queryByText('Admin Content')).not.toBeInTheDocument();
  });

  it('checks org admin when orgAdminOnly is true', () => {
    mockAuthStore.isOrgOwner.mockReturnValue(true);
    mockAuthStore.isAdmin.mockReturnValue(false);

    render(
      <AdminOnly orgAdminOnly>
        <div>Org Admin Content</div>
      </AdminOnly>
    );

    expect(screen.getByText('Org Admin Content')).toBeInTheDocument();
    expect(mockAuthStore.isOrgOwner).toHaveBeenCalled();
  });

  it('renders fallback for non-admin users', () => {
    mockAuthStore.isAdmin.mockReturnValue(false);

    render(
      <AdminOnly fallback={<div>Regular User View</div>}>
        <div>Admin Content</div>
      </AdminOnly>
    );

    expect(screen.getByText('Regular User View')).toBeInTheDocument();
  });
});
