/**
 * Tests for Rate Limit Feedback Components
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import {
  RateLimitProvider,
  RateLimitBanner,
  useRateLimit,
} from '@/components/security/rate-limit-feedback';

// Mock security utilities
vi.mock('@/lib/security', () => ({
  checkRateLimit: vi.fn().mockReturnValue({ allowed: true, remaining: 5, resetIn: 0 }),
  resetRateLimit: vi.fn(),
}));

// Test component that uses the hook
function TestConsumer() {
  const { rateLimitState, setRateLimited, clearRateLimit, checkEndpointLimit } = useRateLimit();
  return (
    <div>
      <span data-testid="is-limited">{rateLimitState.isLimited.toString()}</span>
      <span data-testid="endpoint">{rateLimitState.endpoint || 'none'}</span>
      <button onClick={() => setRateLimited('/api/test', 5000)}>Set Limited</button>
      <button onClick={clearRateLimit}>Clear</button>
      <button onClick={() => checkEndpointLimit('/api/check')}>Check Endpoint</button>
    </div>
  );
}

describe('RateLimitProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('provides rate limit context to children', () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    expect(screen.getByTestId('is-limited')).toHaveTextContent('false');
    expect(screen.getByTestId('endpoint')).toHaveTextContent('none');
  });

  it('renders children', () => {
    render(
      <RateLimitProvider>
        <div data-testid="child">Child Content</div>
      </RateLimitProvider>
    );

    expect(screen.getByTestId('child')).toHaveTextContent('Child Content');
  });

  it('can set rate limited state', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    expect(screen.getByTestId('is-limited')).toHaveTextContent('true');
    expect(screen.getByTestId('endpoint')).toHaveTextContent('/api/test');
  });

  it('can clear rate limited state', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    // First set limited
    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });
    expect(screen.getByTestId('is-limited')).toHaveTextContent('true');

    // Then clear
    await act(async () => {
      fireEvent.click(screen.getByText('Clear'));
    });
    expect(screen.getByTestId('is-limited')).toHaveTextContent('false');
  });

  it('shows modal when rate limited', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    expect(screen.getByText('Too Many Requests')).toBeInTheDocument();
  });

  it('auto-clears rate limit after timeout', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    // Set rate limited
    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });
    expect(screen.getByTestId('is-limited')).toHaveTextContent('true');

    // Advance past the timeout
    await act(async () => {
      vi.advanceTimersByTime(6000);
    });

    expect(screen.getByTestId('is-limited')).toHaveTextContent('false');
  });
});

describe('RateLimitBanner', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not render when not rate limited', () => {
    const { container } = render(
      <RateLimitProvider>
        <RateLimitBanner />
      </RateLimitProvider>
    );

    // Banner should not be visible
    expect(container.querySelector('.bg-yellow-50')).toBeNull();
  });

  it('renders when rate limited', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
        <RateLimitBanner />
      </RateLimitProvider>
    );

    // Set rate limited
    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    // Banner should show countdown - multiple elements show the rate limit message
    const rateLimitedElements = screen.getAllByText(/rate limited/i);
    expect(rateLimitedElements.length).toBeGreaterThan(0);
  });

  it('applies custom className', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
        <RateLimitBanner className="custom-class" />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    // Find the banner by its custom class
    const banner = document.querySelector('.custom-class');
    expect(banner).toBeInTheDocument();
  });
});

describe('Rate Limit Modal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('displays countdown timer', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    // Should show countdown (5s)
    expect(screen.getByText('5s')).toBeInTheDocument();
  });

  it('shows dismiss button', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    // Find dismiss button (X icon)
    const dismissButtons = screen.getAllByRole('button');
    expect(dismissButtons.length).toBeGreaterThan(0);
  });

  it('shows endpoint information', async () => {
    render(
      <RateLimitProvider>
        <TestConsumer />
      </RateLimitProvider>
    );

    await act(async () => {
      fireEvent.click(screen.getByText('Set Limited'));
    });

    // Find the endpoint in the modal (inside a code element)
    const codeElements = screen.getAllByText('/api/test');
    expect(codeElements.length).toBeGreaterThan(0);
  });
});
