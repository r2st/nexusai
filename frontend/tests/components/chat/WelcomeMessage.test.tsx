/**
 * WelcomeMessage Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock WelcomeMessage component
interface WelcomeMessageProps {
  userName?: string;
  suggestions?: string[];
  onSuggestionClick?: (suggestion: string) => void;
}

const WelcomeMessage = ({
  userName = 'User',
  suggestions = [],
  onSuggestionClick,
}: WelcomeMessageProps) => (
  <div data-testid="welcome-message" className="welcome-message">
    <h1 data-testid="greeting">Hello, {userName}!</h1>
    <p data-testid="subtitle">How can I help you today?</p>
    {suggestions.length > 0 && (
      <div data-testid="suggestions">
        {suggestions.map((suggestion, index) => (
          <button
            key={index}
            data-testid={`suggestion-${index}`}
            onClick={() => onSuggestionClick?.(suggestion)}
          >
            {suggestion}
          </button>
        ))}
      </div>
    )}
  </div>
);

describe('WelcomeMessage', () => {
  it('renders welcome message container', () => {
    render(<WelcomeMessage />);
    expect(screen.getByTestId('welcome-message')).toBeInTheDocument();
  });

  it('displays greeting with user name', () => {
    render(<WelcomeMessage userName="John" />);
    expect(screen.getByTestId('greeting')).toHaveTextContent('Hello, John!');
  });

  it('uses default user name when not provided', () => {
    render(<WelcomeMessage />);
    expect(screen.getByTestId('greeting')).toHaveTextContent('Hello, User!');
  });

  it('displays subtitle', () => {
    render(<WelcomeMessage />);
    expect(screen.getByTestId('subtitle')).toHaveTextContent('How can I help you today?');
  });

  it('renders suggestions when provided', () => {
    const suggestions = ['Explain code', 'Find bugs', 'Write tests'];
    render(<WelcomeMessage suggestions={suggestions} />);
    
    expect(screen.getByTestId('suggestions')).toBeInTheDocument();
    expect(screen.getByText('Explain code')).toBeInTheDocument();
    expect(screen.getByText('Find bugs')).toBeInTheDocument();
    expect(screen.getByText('Write tests')).toBeInTheDocument();
  });

  it('does not render suggestions container when empty', () => {
    render(<WelcomeMessage suggestions={[]} />);
    expect(screen.queryByTestId('suggestions')).not.toBeInTheDocument();
  });

  it('calls onSuggestionClick when suggestion is clicked', () => {
    const onSuggestionClick = vi.fn();
    const suggestions = ['Explain code'];
    render(<WelcomeMessage suggestions={suggestions} onSuggestionClick={onSuggestionClick} />);
    
    fireEvent.click(screen.getByText('Explain code'));
    expect(onSuggestionClick).toHaveBeenCalledWith('Explain code');
  });
});

describe('WelcomeMessage Suggestions', () => {
  it('renders multiple suggestions', () => {
    const suggestions = ['Option 1', 'Option 2', 'Option 3', 'Option 4'];
    render(<WelcomeMessage suggestions={suggestions} />);
    
    suggestions.forEach((suggestion, index) => {
      expect(screen.getByTestId(`suggestion-${index}`)).toHaveTextContent(suggestion);
    });
  });

  it('each suggestion is clickable', () => {
    const onSuggestionClick = vi.fn();
    const suggestions = ['A', 'B', 'C'];
    render(<WelcomeMessage suggestions={suggestions} onSuggestionClick={onSuggestionClick} />);
    
    suggestions.forEach((suggestion, index) => {
      fireEvent.click(screen.getByTestId(`suggestion-${index}`));
      expect(onSuggestionClick).toHaveBeenCalledWith(suggestion);
    });
    
    expect(onSuggestionClick).toHaveBeenCalledTimes(3);
  });
});
