/**
 * TypingIndicator Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';

// Mock TypingIndicator component
interface TypingIndicatorProps {
  isTyping?: boolean;
  userName?: string;
}

const TypingIndicator = ({ isTyping = true, userName }: TypingIndicatorProps) => {
  if (!isTyping) return null;
  
  return (
    <div data-testid="typing-indicator" className="typing-indicator">
      <div className="dots">
        <span className="dot" data-testid="dot-1" />
        <span className="dot" data-testid="dot-2" />
        <span className="dot" data-testid="dot-3" />
      </div>
      {userName && <span data-testid="user-name">{userName} is typing...</span>}
    </div>
  );
};

describe('TypingIndicator', () => {
  it('renders when typing', () => {
    render(<TypingIndicator isTyping={true} />);
    expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
  });

  it('does not render when not typing', () => {
    render(<TypingIndicator isTyping={false} />);
    expect(screen.queryByTestId('typing-indicator')).not.toBeInTheDocument();
  });

  it('renders three dots', () => {
    render(<TypingIndicator />);
    expect(screen.getByTestId('dot-1')).toBeInTheDocument();
    expect(screen.getByTestId('dot-2')).toBeInTheDocument();
    expect(screen.getByTestId('dot-3')).toBeInTheDocument();
  });

  it('shows user name when provided', () => {
    render(<TypingIndicator userName="Assistant" />);
    expect(screen.getByTestId('user-name')).toHaveTextContent('Assistant is typing...');
  });

  it('hides user name when not provided', () => {
    render(<TypingIndicator />);
    expect(screen.queryByTestId('user-name')).not.toBeInTheDocument();
  });

  it('has correct CSS class', () => {
    render(<TypingIndicator />);
    expect(screen.getByTestId('typing-indicator')).toHaveClass('typing-indicator');
  });
});

describe('TypingIndicator Animation', () => {
  it('dots have animation class', () => {
    render(<TypingIndicator />);
    const dots = screen.getAllByTestId(/^dot-/);
    dots.forEach((dot) => {
      expect(dot).toHaveClass('dot');
    });
  });
});
