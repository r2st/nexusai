/**
 * SmartSuggestions Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock SmartSuggestions component
interface Suggestion {
  id: string;
  text: string;
  category?: string;
  icon?: string;
}

interface SmartSuggestionsProps {
  suggestions: Suggestion[];
  onSelect?: (suggestion: Suggestion) => void;
  isLoading?: boolean;
  maxVisible?: number;
}

const SmartSuggestions = ({
  suggestions,
  onSelect,
  isLoading = false,
  maxVisible = 4,
}: SmartSuggestionsProps) => {
  if (isLoading) {
    return (
      <div data-testid="suggestions-loading">
        <span>Loading suggestions...</span>
      </div>
    );
  }

  if (suggestions.length === 0) {
    return null;
  }

  const visibleSuggestions = suggestions.slice(0, maxVisible);

  return (
    <div data-testid="smart-suggestions" className="smart-suggestions">
      {visibleSuggestions.map((suggestion) => (
        <button
          key={suggestion.id}
          data-testid={`suggestion-${suggestion.id}`}
          onClick={() => onSelect?.(suggestion)}
          className="suggestion-item"
        >
          {suggestion.icon && <span className="icon">{suggestion.icon}</span>}
          <span className="text">{suggestion.text}</span>
          {suggestion.category && (
            <span data-testid={`category-${suggestion.id}`} className="category">
              {suggestion.category}
            </span>
          )}
        </button>
      ))}
      {suggestions.length > maxVisible && (
        <span data-testid="more-count">+{suggestions.length - maxVisible} more</span>
      )}
    </div>
  );
};

describe('SmartSuggestions', () => {
  const mockSuggestions: Suggestion[] = [
    { id: '1', text: 'Explain this code', category: 'Code' },
    { id: '2', text: 'Find bugs', category: 'Analysis' },
    { id: '3', text: 'Write tests', category: 'Testing' },
    { id: '4', text: 'Refactor', category: 'Code' },
  ];

  it('renders suggestions container', () => {
    render(<SmartSuggestions suggestions={mockSuggestions} />);
    expect(screen.getByTestId('smart-suggestions')).toBeInTheDocument();
  });

  it('renders all suggestions within limit', () => {
    render(<SmartSuggestions suggestions={mockSuggestions} />);
    
    mockSuggestions.forEach((suggestion) => {
      expect(screen.getByTestId(`suggestion-${suggestion.id}`)).toBeInTheDocument();
    });
  });

  it('renders suggestion text', () => {
    render(<SmartSuggestions suggestions={mockSuggestions} />);
    expect(screen.getByText('Explain this code')).toBeInTheDocument();
    expect(screen.getByText('Find bugs')).toBeInTheDocument();
  });

  it('renders suggestion category', () => {
    render(<SmartSuggestions suggestions={mockSuggestions} />);
    expect(screen.getByTestId('category-1')).toHaveTextContent('Code');
    expect(screen.getByTestId('category-2')).toHaveTextContent('Analysis');
  });

  it('calls onSelect when suggestion is clicked', () => {
    const onSelect = vi.fn();
    render(<SmartSuggestions suggestions={mockSuggestions} onSelect={onSelect} />);
    
    fireEvent.click(screen.getByTestId('suggestion-1'));
    expect(onSelect).toHaveBeenCalledWith(mockSuggestions[0]);
  });

  it('returns null when no suggestions', () => {
    const { container } = render(<SmartSuggestions suggestions={[]} />);
    expect(container).toBeEmptyDOMElement();
  });

  it('shows loading state', () => {
    render(<SmartSuggestions suggestions={[]} isLoading={true} />);
    expect(screen.getByTestId('suggestions-loading')).toBeInTheDocument();
    expect(screen.getByText('Loading suggestions...')).toBeInTheDocument();
  });

  it('respects maxVisible limit', () => {
    const manySuggestions = [
      ...mockSuggestions,
      { id: '5', text: 'Extra 1' },
      { id: '6', text: 'Extra 2' },
    ];
    
    render(<SmartSuggestions suggestions={manySuggestions} maxVisible={4} />);
    
    expect(screen.getByTestId('suggestion-1')).toBeInTheDocument();
    expect(screen.getByTestId('suggestion-4')).toBeInTheDocument();
    expect(screen.queryByTestId('suggestion-5')).not.toBeInTheDocument();
  });

  it('shows more count when suggestions exceed limit', () => {
    const manySuggestions = [
      ...mockSuggestions,
      { id: '5', text: 'Extra 1' },
      { id: '6', text: 'Extra 2' },
    ];
    
    render(<SmartSuggestions suggestions={manySuggestions} maxVisible={4} />);
    expect(screen.getByTestId('more-count')).toHaveTextContent('+2 more');
  });

  it('does not show more count when within limit', () => {
    render(<SmartSuggestions suggestions={mockSuggestions} maxVisible={4} />);
    expect(screen.queryByTestId('more-count')).not.toBeInTheDocument();
  });
});

describe('SmartSuggestions with Icons', () => {
  it('renders suggestion icon when provided', () => {
    const suggestions = [
      { id: '1', text: 'Test', icon: '🔍' },
    ];
    
    render(<SmartSuggestions suggestions={suggestions} />);
    expect(screen.getByText('🔍')).toBeInTheDocument();
  });
});
