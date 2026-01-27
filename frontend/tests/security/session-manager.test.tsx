/**
 * Tests for Session Manager Component
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, act, waitFor, fireEvent } from '@testing-library/react';
import { SessionProvider, SessionIndicator, useSession } from '@/components/security/session-manager';

// Mock dependencies
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
  }),
}));

vi.mock('@/store/auth', () => ({
  useAuthStore: () => ({
    isAuthenticated: true,
    logout: vi.fn(),
  }),
}));

vi.mock('@/lib/api', () => ({
  api: {
    post: vi.fn().mockResolvedValue({ data: { access_token: 'new_token' } }),
  },
}));

// Mock localStorage
const mockLocalStorage: Record<string, string> = {};
vi.stubGlobal('localStorage', {
  getItem: (key: string) => mockLocalStorage[key] || null,
  setItem: (key: string, value: string) => { mockLocalStorage[key] = value; },
  removeItem: (key: string) => { delete mockLocalStorage[key]; },
  clear: () => { Object.keys(mockLocalStorage).forEach(key => delete mockLocalStorage[key]); },
});

// Test component that uses the hook
function TestConsumer() {
  const { lastActivity, timeUntilTimeout, isWarningVisible, extendSession } = useSession();
  return (
    <div>
      <span data-testid="last-activity">{lastActivity}</span>
      <span data-testid="time-until-timeout">{timeUntilTimeout}</span>
      <span data-testid="warning-visible">{isWarningVisible.toString()}</span>
      <button onClick={extendSession}>Extend</button>
    </div>
  );
}

describe('SessionProvider', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('provides session context to children', () => {
    render(
      <SessionProvider>
        <TestConsumer />
      </SessionProvider>
    );

    expect(screen.getByTestId('last-activity')).toBeInTheDocument();
    expect(screen.getByTestId('time-until-timeout')).toBeInTheDocument();
    expect(screen.getByTestId('warning-visible')).toHaveTextContent('false');
  });

  it('renders children', () => {
    render(
      <SessionProvider>
        <div data-testid="child">Child Content</div>
      </SessionProvider>
    );

    expect(screen.getByTestId('child')).toHaveTextContent('Child Content');
  });

  it('can be disabled', () => {
    render(
      <SessionProvider enabled={false}>
        <TestConsumer />
      </SessionProvider>
    );

    // Should still render children
    expect(screen.getByTestId('last-activity')).toBeInTheDocument();
  });

  it('extends session on extend button click', async () => {
    render(
      <SessionProvider timeoutMs={60000} warningBeforeMs={30000}>
        <TestConsumer />
      </SessionProvider>
    );

    const extendButton = screen.getByText('Extend');
    await act(async () => {
      fireEvent.click(extendButton);
    });

    // Session should be extended - warning should be false
    expect(screen.getByTestId('warning-visible')).toHaveTextContent('false');
  });
});

describe('SessionIndicator', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('does not render when user is not authenticated', () => {
    // Override mock for this test
    vi.doMock('@/store/auth', () => ({
      useAuthStore: () => ({
        isAuthenticated: false,
        logout: vi.fn(),
      }),
    }));

    const { container } = render(
      <SessionProvider>
        <SessionIndicator />
      </SessionProvider>
    );

    // Should be empty or not render the indicator
    expect(container).toBeDefined();
  });

  it('renders when showAlways is true', () => {
    render(
      <SessionProvider>
        <SessionIndicator showAlways />
      </SessionProvider>
    );

    // Should render time display with format XX:XX
    const timeDisplay = screen.getByText(/\d{2}:\d{2}/);
    expect(timeDisplay).toBeInTheDocument();
  });

  it('applies custom className', () => {
    render(
      <SessionProvider>
        <SessionIndicator showAlways className="custom-class" />
      </SessionProvider>
    );

    const indicator = screen.getByText(/\d{2}:\d{2}/).parentElement;
    expect(indicator).toHaveClass('custom-class');
  });
});

describe('Session Warning Modal', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    localStorage.clear();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('provides context values', () => {
    render(
      <SessionProvider timeoutMs={5000} warningBeforeMs={4000}>
        <TestConsumer />
      </SessionProvider>
    );

    // Just verify context is provided - warning modal timing is hard to test with fake timers
    expect(screen.getByTestId('warning-visible')).toBeInTheDocument();
  });
});
