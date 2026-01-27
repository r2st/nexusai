/**
 * Login Page Tests
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { useRouter, useSearchParams } from 'next/navigation';
import LoginPage from '@/app/(auth)/login/page';
import { useAuthStore } from '@/store/auth';

// Mock the API
const mockLogin = vi.fn();
const mockListOrganizations = vi.fn();
const mockSwitchTo = vi.fn();

vi.mock('@/lib/api', () => ({
  authApi: {
    login: (...args: unknown[]) => mockLogin(...args),
  },
  organizationsApi: {
    list: () => mockListOrganizations(),
    switchTo: (...args: unknown[]) => mockSwitchTo(...args),
  },
  TenantContext: {
    setCurrentTenantId: vi.fn(),
    clear: vi.fn(),
  },
  api: {
    post: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Get mocked router
const mockPush = vi.fn();
const mockSearchParamsGet = vi.fn();

vi.mock('next/navigation', async () => {
  return {
    useRouter: vi.fn(() => ({
      push: mockPush,
      replace: vi.fn(),
      back: vi.fn(),
    })),
    useSearchParams: vi.fn(() => ({
      get: mockSearchParamsGet,
    })),
  };
});

describe('LoginPage', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    role: 'staff_admin',
    organization_id: 'org-123',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  const mockTokens = {
    access_token: 'test-access-token',
    refresh_token: 'test-refresh-token',
    expires_in: 3600,
  };

  const mockOrg = {
    id: 'org-123',
    name: 'Test Org',
    slug: 'test-org',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    // Reset mocks
    vi.clearAllMocks();

    // Reset auth store
    useAuthStore.setState({
      user: null,
      isAuthenticated: false,
      currentOrganization: null,
      organizations: [],
      memberRole: null,
      sessionExpiresAt: null,
      lastActivity: Date.now(),
      _hasHydrated: true,
    });

    // Default mock implementations
    mockSearchParamsGet.mockImplementation((key: string) => {
      if (key === 'redirect') return '/chat';
      if (key === 'expired') return null;
      if (key === 'invite') return null;
      return null;
    });

    mockLogin.mockResolvedValue({
      user: mockUser,
      tokens: mockTokens,
    });

    mockListOrganizations.mockResolvedValue([mockOrg]);
  });

  afterEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  describe('Rendering', () => {
    it('should render login form', () => {
      render(<LoginPage />);

      expect(screen.getByRole('heading', { name: /welcome back/i })).toBeInTheDocument();
      expect(screen.getByLabelText(/^email$/i)).toBeInTheDocument();
      expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
    });

    it('should render organization and staff login tabs', () => {
      render(<LoginPage />);

      expect(screen.getByRole('button', { name: /organization/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /staff/i })).toBeInTheDocument();
    });

    it('should show organization field when organization tab is selected', () => {
      render(<LoginPage />);

      // Organization tab should be selected by default
      expect(screen.getByLabelText(/organization/i)).toBeInTheDocument();
    });

    it('should hide organization field when staff tab is selected', () => {
      render(<LoginPage />);

      // Click staff tab
      const staffTab = screen.getByRole('button', { name: /staff/i });
      fireEvent.click(staffTab);

      // Organization field should not be visible
      expect(screen.queryByPlaceholderText(/your-org-slug/i)).not.toBeInTheDocument();
    });

    it('should render forgot password link', () => {
      render(<LoginPage />);

      expect(screen.getByRole('link', { name: /forgot password/i })).toBeInTheDocument();
    });

    it('should render sign up link', () => {
      render(<LoginPage />);

      expect(screen.getByRole('link', { name: /sign up/i })).toBeInTheDocument();
    });

    it('should render OAuth buttons', () => {
      render(<LoginPage />);

      expect(screen.getByRole('button', { name: /google/i })).toBeInTheDocument();
      expect(screen.getByRole('button', { name: /github/i })).toBeInTheDocument();
    });
  });

  describe('Form Interactions', () => {
    it('should update email input value', async () => {
      render(<LoginPage />);

      const emailInput = screen.getByLabelText(/^email$/i);
      await userEvent.type(emailInput, 'test@example.com');

      expect(emailInput).toHaveValue('test@example.com');
    });

    it('should update password input value', async () => {
      render(<LoginPage />);

      const passwordInput = screen.getByLabelText(/^password$/i);
      await userEvent.type(passwordInput, 'password123');

      expect(passwordInput).toHaveValue('password123');
    });

    it('should toggle password visibility', async () => {
      render(<LoginPage />);

      const passwordInput = screen.getByLabelText(/^password$/i);
      expect(passwordInput).toHaveAttribute('type', 'password');

      // Click show password button
      const toggleButton = screen.getByRole('button', { name: /show password/i });
      await userEvent.click(toggleButton);

      expect(passwordInput).toHaveAttribute('type', 'text');

      // Click hide password button
      const hideButton = screen.getByRole('button', { name: /hide password/i });
      await userEvent.click(hideButton);

      expect(passwordInput).toHaveAttribute('type', 'password');
    });
  });

  describe('Form Submission', () => {
    it('should call login API on form submit', async () => {
      render(<LoginPage />);

      // Fill form
      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      // Submit form
      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockLogin).toHaveBeenCalledWith('test@example.com', 'password123');
      });
    });

    it('should show loading state during submission', async () => {
      // Make login slow
      mockLogin.mockImplementation(() => new Promise((resolve) => setTimeout(resolve, 1000)));

      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      // Button should show loading state
      expect(screen.getByText(/signing in/i)).toBeInTheDocument();
    });

    it('should redirect to chat page after successful login', async () => {
      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/chat');
      });
    });

    it('should redirect to custom redirect URL after login', async () => {
      mockSearchParamsGet.mockImplementation((key: string) => {
        if (key === 'redirect') return '/dashboard';
        return null;
      });

      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/dashboard');
      });
    });

    it('should store auth state after successful login', async () => {
      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        const state = useAuthStore.getState();
        expect(state.isAuthenticated).toBe(true);
        expect(state.user?.email).toBe('test@example.com');
      });
    });
  });

  describe('Error Handling', () => {
    it('should show error message on login failure', async () => {
      const { toast } = await import('sonner');
      mockLogin.mockRejectedValue(new Error('Invalid email or password'));

      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'wrongpassword');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Invalid email or password');
      });
    });

    it('should not redirect on login failure', async () => {
      mockLogin.mockRejectedValue(new Error('Invalid credentials'));

      render(<LoginPage />);

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'wrongpassword');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockPush).not.toHaveBeenCalled();
      });
    });
  });

  describe('Session Expired Alert', () => {
    it('should show expired session alert when expired param is true', async () => {
      const { toast } = await import('sonner');
      mockSearchParamsGet.mockImplementation((key: string) => {
        if (key === 'expired') return 'true';
        if (key === 'redirect') return '/chat';
        return null;
      });

      render(<LoginPage />);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('Your session has expired. Please sign in again.');
      });
    });
  });

  describe('Invite Token', () => {
    it('should switch to staff tab when invite token is present', () => {
      mockSearchParamsGet.mockImplementation((key: string) => {
        if (key === 'invite') return 'invite-token-123';
        if (key === 'redirect') return '/chat';
        return null;
      });

      render(<LoginPage />);

      // Staff tab should be selected
      const staffTab = screen.getByRole('button', { name: /staff/i });
      expect(staffTab).toHaveClass('bg-background');
    });

    it('should show invite banner when invite token is present', () => {
      mockSearchParamsGet.mockImplementation((key: string) => {
        if (key === 'invite') return 'invite-token-123';
        if (key === 'redirect') return '/chat';
        return null;
      });

      render(<LoginPage />);

      expect(screen.getByText(/you've been invited/i)).toBeInTheDocument();
    });
  });

  describe('Organization Login', () => {
    it('should validate organization access on org login', async () => {
      mockListOrganizations.mockResolvedValue([mockOrg]);

      render(<LoginPage />);

      // Fill org slug
      const orgInput = screen.getByPlaceholderText(/your-org-slug/i);
      await userEvent.type(orgInput, 'test-org');

      // Fill credentials
      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      // Submit
      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(mockListOrganizations).toHaveBeenCalled();
      });
    });

    it('should show error when user has no access to organization', async () => {
      const { toast } = await import('sonner');
      mockListOrganizations.mockResolvedValue([{ ...mockOrg, slug: 'other-org' }]);

      render(<LoginPage />);

      const orgInput = screen.getByPlaceholderText(/your-org-slug/i);
      await userEvent.type(orgInput, 'test-org');

      await userEvent.type(screen.getByLabelText(/^email$/i), 'test@example.com');
      await userEvent.type(screen.getByLabelText(/^password$/i), 'password123');

      const submitButton = screen.getByRole('button', { name: /sign in/i });
      await userEvent.click(submitButton);

      await waitFor(() => {
        expect(toast.error).toHaveBeenCalledWith('You do not have access to this organization');
      });
    });
  });
});
