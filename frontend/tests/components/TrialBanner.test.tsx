import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
import type { ReactNode } from 'react';

import type { TrialStatus } from '@/lib/api';
import { TrialBanner, TrialBannerCompact } from '@/components/trial/trial-banner';
import { trialsApi, TenantContext } from '@/lib/api';

vi.mock('next/link', () => ({
  default: ({ href, children }: { href: string; children: ReactNode }) => (
    <a href={href}>{children}</a>
  ),
}));

vi.mock('@/lib/api', async () => {
  const actual = await vi.importActual<typeof import('@/lib/api')>('@/lib/api');
  return {
    ...actual,
    trialsApi: {
      getStatus: vi.fn(),
    },
    TenantContext: {
      getCurrentTenantId: vi.fn(),
    },
  };
});

const mockStatus = (overrides: Partial<TrialStatus> = {}): TrialStatus => ({
  trial_status: 'active',
  is_trial_active: true,
  trial_started_at: '2024-01-01T00:00:00Z',
  trial_ends_at: '2024-01-14T00:00:00Z',
  trial_days_remaining: 7,
  can_access_features: true,
  current_tier: 'starter',
  max_members: 5,
  max_projects: 3,
  was_extended: false,
  ...overrides,
});

const mockTrialsApi = trialsApi as unknown as { getStatus: ReturnType<typeof vi.fn> };
const mockTenantContext = TenantContext as unknown as { getCurrentTenantId: ReturnType<typeof vi.fn> };

describe('TrialBanner', () => {
  beforeEach(() => {
    sessionStorage.clear();
    mockTrialsApi.getStatus.mockReset();
    mockTenantContext.getCurrentTenantId.mockReset();
  });

  afterEach(() => {
    sessionStorage.clear();
  });

  it('renders nothing when no org id is available', async () => {
    mockTenantContext.getCurrentTenantId.mockReturnValue(null);
    const { container } = render(<TrialBanner />);

    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
    expect(mockTrialsApi.getStatus).not.toHaveBeenCalled();
  });

  it('renders urgent messaging when trial is expiring soon', async () => {
    mockTrialsApi.getStatus.mockResolvedValue(
      mockStatus({ trial_days_remaining: 2 })
    );

    render(<TrialBanner orgId="org-123" />);

    expect(await screen.findByText('Your trial expires in 2 days!')).toBeInTheDocument();
    expect(screen.getByText('(starter tier)')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upgrade Now' })).toBeInTheDocument();
    expect(mockTrialsApi.getStatus).toHaveBeenCalledWith('org-123');
  });

  it('dismisses banner and persists dismissal per org', async () => {
    mockTrialsApi.getStatus.mockResolvedValue(
      mockStatus({ trial_days_remaining: 5 })
    );

    render(<TrialBanner orgId="org-456" />);

    expect(await screen.findByText('5 days left in your trial')).toBeInTheDocument();

    fireEvent.click(screen.getByLabelText('Dismiss trial banner'));

    await waitFor(() => {
      expect(screen.queryByText('5 days left in your trial')).not.toBeInTheDocument();
    });

    expect(sessionStorage.getItem('trial_banner_dismissed_org-456')).toBe('true');
  });
});

describe('TrialBannerCompact', () => {
  beforeEach(() => {
    mockTrialsApi.getStatus.mockReset();
    mockTenantContext.getCurrentTenantId.mockReset();
  });

  it('renders compact banner with remaining days', async () => {
    mockTrialsApi.getStatus.mockResolvedValue(
      mockStatus({ trial_days_remaining: 1 })
    );

    render(<TrialBannerCompact orgId="org-compact" />);

    expect(await screen.findByText('1 day left')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Upgrade' })).toBeInTheDocument();
    expect(mockTrialsApi.getStatus).toHaveBeenCalledWith('org-compact');
  });

  it('hides compact banner when trial is inactive', async () => {
    mockTrialsApi.getStatus.mockResolvedValue(
      mockStatus({ is_trial_active: false })
    );

    const { container } = render(<TrialBannerCompact orgId="org-off" />);

    await waitFor(() => {
      expect(container).toBeEmptyDOMElement();
    });
  });
});
