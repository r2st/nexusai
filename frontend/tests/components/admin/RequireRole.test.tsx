/**
 * RequireRole Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import React from 'react';

// Mock types
type Role = 'admin' | 'manager' | 'user' | 'guest';

interface User {
  id: string;
  name: string;
  role: Role;
}

interface RequireRoleProps {
  allowedRoles: Role[];
  user?: User | null;
  children: React.ReactNode;
  fallback?: React.ReactNode;
  redirectTo?: string;
}

// Mock navigation
const mockNavigate = vi.fn();

// Mock RequireRole component
const RequireRole = ({
  allowedRoles,
  user,
  children,
  fallback,
  redirectTo,
}: RequireRoleProps) => {
  if (!user) {
    if (redirectTo) {
      mockNavigate(redirectTo);
      return null;
    }
    return <>{fallback || <div data-testid="access-denied">Please log in to access this page.</div>}</>;
  }

  if (!allowedRoles.includes(user.role)) {
    if (redirectTo) {
      mockNavigate(redirectTo);
      return null;
    }
    return <>{fallback || <div data-testid="access-denied">You don't have permission to access this page.</div>}</>;
  }

  return <>{children}</>;
};

describe('RequireRole', () => {
  const adminUser: User = { id: '1', name: 'Admin', role: 'admin' };
  const managerUser: User = { id: '2', name: 'Manager', role: 'manager' };
  const regularUser: User = { id: '3', name: 'User', role: 'user' };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders children when user has allowed role', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={adminUser}>
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders children when user role is in allowed list', () => {
    render(
      <RequireRole allowedRoles={['admin', 'manager']} user={managerUser}>
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('shows access denied when user role is not allowed', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={regularUser}>
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('access-denied')).toHaveTextContent("You don't have permission");
  });

  it('shows access denied when no user is provided', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={null}>
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.queryByTestId('protected-content')).not.toBeInTheDocument();
    expect(screen.getByTestId('access-denied')).toHaveTextContent('Please log in');
  });

  it('renders custom fallback when provided', () => {
    render(
      <RequireRole
        allowedRoles={['admin']}
        user={regularUser}
        fallback={<div data-testid="custom-fallback">Custom Access Denied</div>}
      >
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByTestId('custom-fallback')).toBeInTheDocument();
    expect(screen.queryByTestId('access-denied')).not.toBeInTheDocument();
  });

  it('navigates to redirectTo when user is unauthorized', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={regularUser} redirectTo="/unauthorized">
        <div>Protected</div>
      </RequireRole>
    );
    expect(mockNavigate).toHaveBeenCalledWith('/unauthorized');
  });

  it('navigates to login when no user and redirectTo is set', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={null} redirectTo="/login">
        <div>Protected</div>
      </RequireRole>
    );
    expect(mockNavigate).toHaveBeenCalledWith('/login');
  });

  it('allows multiple roles', () => {
    render(
      <RequireRole allowedRoles={['admin', 'manager', 'user']} user={regularUser}>
        <div data-testid="protected-content">Protected Content</div>
      </RequireRole>
    );
    expect(screen.getByTestId('protected-content')).toBeInTheDocument();
  });

  it('renders nested children correctly', () => {
    render(
      <RequireRole allowedRoles={['admin']} user={adminUser}>
        <div>
          <h1 data-testid="title">Admin Dashboard</h1>
          <p data-testid="description">Welcome, Admin!</p>
        </div>
      </RequireRole>
    );
    expect(screen.getByTestId('title')).toHaveTextContent('Admin Dashboard');
    expect(screen.getByTestId('description')).toHaveTextContent('Welcome, Admin!');
  });
});
