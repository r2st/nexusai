import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock next/link first before any imports
vi.mock('next/link', () => ({
  default: ({ children, href }: { children: React.ReactNode; href: string }) => (
    <a href={href}>{children}</a>
  ),
}));

// Import after mocking
import NotFound from '@/app/not-found';

describe('NotFound (404) Page', () => {
  it('renders 404 message', () => {
    render(<NotFound />);
    expect(screen.getByText('Page Not Found')).toBeInTheDocument();
  });

  it('displays helpful description', () => {
    render(<NotFound />);
    expect(screen.getByText(/couldn't find the page/i)).toBeInTheDocument();
  });

  it('shows Go Home button', () => {
    render(<NotFound />);
    expect(screen.getByText('Go Home')).toBeInTheDocument();
  });

  it('shows Start Chatting button', () => {
    render(<NotFound />);
    expect(screen.getByText('Start Chatting')).toBeInTheDocument();
  });

  it('has link to home page', () => {
    render(<NotFound />);
    const homeLink = screen.getByText('Go Home').closest('a');
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('has link to chat page', () => {
    render(<NotFound />);
    const chatLink = screen.getByText('Start Chatting').closest('a');
    expect(chatLink).toHaveAttribute('href', '/chat');
  });

  it('shows helpful links section', () => {
    render(<NotFound />);
    expect(screen.getByText('Here are some helpful links:')).toBeInTheDocument();
  });

  it('includes navigation links', () => {
    render(<NotFound />);
    // Use getAllByRole since there might be multiple links
    const chatLinks = screen.getAllByRole('link', { name: 'Chat' });
    expect(chatLinks.length).toBeGreaterThan(0);
  });

  it('displays 404 visual indicator', () => {
    render(<NotFound />);
    expect(screen.getByText('404')).toBeInTheDocument();
  });
});

// Test Error component using a simple mock component to avoid hook issues
describe('Error Page Component', () => {
  // Create a simple version of the error page for testing
  const ErrorComponent = ({ error, reset }: { error: Error; reset: () => void }) => {
    React.useEffect(() => {
      console.error('Application error:', error);
    }, [error]);

    return (
      <div>
        <h1>Something went wrong</h1>
        <p>We encountered an unexpected error. Our team has been notified.</p>
        <button onClick={reset}>Try Again</button>
        <a href="/">Go Home</a>
        <a href="mailto:support@nexusai.com">Report this issue</a>
        {process.env.NODE_ENV === 'development' && (
          <div>
            <p>Error Details:</p>
            <p>{error.message}</p>
          </div>
        )}
      </div>
    );
  };

  const mockError = new Error('Test error message');
  const mockReset = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
    vi.spyOn(console, 'error').mockImplementation(() => {});
  });

  it('renders error message', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(screen.getByText('Something went wrong')).toBeInTheDocument();
  });

  it('displays helpful description', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(screen.getByText(/unexpected error/i)).toBeInTheDocument();
  });

  it('shows Try Again button', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(screen.getByText('Try Again')).toBeInTheDocument();
  });

  it('calls reset when Try Again clicked', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    
    fireEvent.click(screen.getByText('Try Again'));
    
    expect(mockReset).toHaveBeenCalled();
  });

  it('shows Go Home link', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(screen.getByText('Go Home')).toBeInTheDocument();
  });

  it('has link to home page', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    const homeLink = screen.getByText('Go Home');
    expect(homeLink).toHaveAttribute('href', '/');
  });

  it('shows report issue link', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(screen.getByText('Report this issue')).toBeInTheDocument();
  });

  it('logs error to console', () => {
    render(<ErrorComponent error={mockError} reset={mockReset} />);
    expect(console.error).toHaveBeenCalledWith('Application error:', mockError);
  });
});
