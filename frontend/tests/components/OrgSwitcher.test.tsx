import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { OrgSwitcher } from '@/components/organization/org-switcher';

// Mock next/navigation
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
  }),
}));

// Mock next/link
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Mock auth store
const mockIsAuthenticated = vi.fn(() => true);
vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: mockIsAuthenticated(),
  }),
}));

// Mock organizations API
const mockOrganizations = [
  {
    id: 'org-1',
    name: 'Acme Corp',
    slug: 'acme',
    tier: 'pro',
    description: 'Test organization',
    logo_url: null,
    settings: {},
    max_members: 25,
    max_projects: 100,
    is_active: true,
    owner_id: 'user-1',
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  },
  {
    id: 'org-2',
    name: 'Beta Inc',
    slug: 'beta',
    tier: 'free',
    description: null,
    logo_url: null,
    settings: {},
    max_members: 5,
    max_projects: 3,
    is_active: true,
    owner_id: 'user-1',
    created_at: '2024-01-02T00:00:00Z',
    updated_at: '2024-01-02T00:00:00Z',
  },
];

let mockCurrentTenantId: string | null = 'org-1';

vi.mock('@/lib/api', () => ({
  organizationsApi: {
    list: vi.fn(() => Promise.resolve(mockOrganizations)),
    getCurrentId: vi.fn(() => mockCurrentTenantId),
    switchTo: vi.fn((id: string) => {
      mockCurrentTenantId = id;
    }),
  },
  TenantContext: {
    getCurrentTenantId: vi.fn(() => mockCurrentTenantId),
    setCurrentTenantId: vi.fn((id: string | null) => {
      mockCurrentTenantId = id;
    }),
    subscribe: vi.fn(() => () => {}),
  },
}));

describe('OrgSwitcher', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockCurrentTenantId = 'org-1';
    mockIsAuthenticated.mockReturnValue(true);
  });

  it('renders nothing when not authenticated', async () => {
    mockIsAuthenticated.mockReturnValue(false);
    const { container } = render(<OrgSwitcher />);
    expect(container.firstChild).toBeNull();
  });

  it('renders current organization name', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });
  });

  it('opens dropdown when clicked', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Organizations')).toBeInTheDocument();
      expect(screen.getByText('Beta Inc')).toBeInTheDocument();
    });
  });

  it('shows plan tier for each organization', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('pro plan')).toBeInTheDocument();
      expect(screen.getByText('free plan')).toBeInTheDocument();
    });
  });

  it('shows checkmark for selected organization', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getAllByText('Acme Corp').length).toBeGreaterThan(0);
    });

    fireEvent.click(screen.getAllByText('Acme Corp')[0]);

    await waitFor(() => {
      // The selected org in dropdown should have the highlight class
      const orgButtons = document.querySelectorAll('button.bg-primary\\/10');
      expect(orgButtons.length).toBeGreaterThan(0);
    });
  });

  it('shows management links in dropdown', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Manage Team')).toBeInTheDocument();
      expect(screen.getByText('Organization Settings')).toBeInTheDocument();
      expect(screen.getByText('Create New Organization')).toBeInTheDocument();
    });
  });

  it('closes dropdown when clicking outside', async () => {
    render(<OrgSwitcher />);
    
    await waitFor(() => {
      expect(screen.getByText('Acme Corp')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('Acme Corp'));

    await waitFor(() => {
      expect(screen.getByText('Organizations')).toBeInTheDocument();
    });

    // Click the backdrop
    const backdrop = document.querySelector('.fixed.inset-0.z-40');
    if (backdrop) {
      fireEvent.click(backdrop);
    }

    await waitFor(() => {
      expect(screen.queryByText('Organizations')).not.toBeInTheDocument();
    });
  });
});
