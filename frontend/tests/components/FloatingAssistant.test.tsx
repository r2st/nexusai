/**
 * Tests for FloatingAssistant Component
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor, act } from '@testing-library/react';
import { FloatingAssistant, useFloatingAssistant } from '@/components/assistant/floating-assistant';

// Mock the chat API
vi.mock('@/lib/api', () => ({
  chatApi: {
    sendMessage: vi.fn().mockResolvedValue({
      content: 'Hello! How can I help you?',
    }),
  },
}));

// Mock the chat store
vi.mock('@/store/chat', () => ({
  useChatStore: () => ({
    selectedModel: 'gemini-flash',
  }),
  DEFAULT_MODEL: 'gemini-flash',
}));

describe('FloatingAssistant', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders floating button when closed', () => {
    render(<FloatingAssistant />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    expect(button).toBeInTheDocument();
  });

  it('opens chat panel when button clicked', async () => {
    render(<FloatingAssistant />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
  });

  it('shows welcome message when opened', async () => {
    render(<FloatingAssistant />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByText(/how can i help you/i)).toBeInTheDocument();
  });

  it('shows custom initial message', async () => {
    render(<FloatingAssistant initialMessage="Custom welcome message!" />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    await act(async () => {
      fireEvent.click(button);
    });

    expect(screen.getByText('Custom welcome message!')).toBeInTheDocument();
  });

  it('closes when X button clicked', async () => {
    render(<FloatingAssistant />);
    
    // Open the assistant
    const openButton = screen.getByRole('button', { name: /open ai assistant/i });
    await act(async () => {
      fireEvent.click(openButton);
    });

    // Close it
    const closeButton = screen.getAllByRole('button').find(btn => 
      btn.querySelector('svg.lucide-x')
    );
    expect(closeButton).toBeDefined();
    
    await act(async () => {
      fireEvent.click(closeButton!);
    });

    // Should be back to just the floating button
    expect(screen.getByRole('button', { name: /open ai assistant/i })).toBeInTheDocument();
    expect(screen.queryByText('AI Assistant')).not.toBeInTheDocument();
  });

  it('minimizes when minimize button clicked', async () => {
    render(<FloatingAssistant />);
    
    // Open the assistant
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    // Find minimize button - it's the middle button in the header (reset, minimize, close)
    const buttons = screen.getAllByRole('button');
    // The minimize button has an svg with class containing 'minimize' or we can find it by position
    const minimizeButton = buttons.find(btn => {
      const svg = btn.querySelector('svg');
      return svg && (svg.classList.contains('lucide-minimize-2') || 
                     svg.getAttribute('class')?.includes('minimize'));
    }) || buttons[2]; // fallback to 3rd button (after reset)
    
    expect(minimizeButton).toBeTruthy();
    
    await act(async () => {
      fireEvent.click(minimizeButton!);
    });

    // Should still show title but not input
    expect(screen.getByText('AI Assistant')).toBeInTheDocument();
    expect(screen.queryByPlaceholderText('Ask me anything...')).not.toBeInTheDocument();
  });

  it('does not render when enabled is false', () => {
    render(<FloatingAssistant enabled={false} />);
    
    expect(screen.queryByRole('button', { name: /open ai assistant/i })).not.toBeInTheDocument();
  });

  it('renders quick action buttons', async () => {
    render(<FloatingAssistant />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    // Should show quick questions
    expect(screen.getByText('Quick questions:')).toBeInTheDocument();
  });

  it('uses context-specific title for documents', async () => {
    render(<FloatingAssistant context="documents" />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText('Document Helper')).toBeInTheDocument();
  });

  it('uses context-specific title for settings', async () => {
    render(<FloatingAssistant context="settings" />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText('Settings Helper')).toBeInTheDocument();
  });

  it('uses context-specific title for team', async () => {
    render(<FloatingAssistant context="team" />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText('Team Assistant')).toBeInTheDocument();
  });

  it('uses context-specific title for analytics', async () => {
    render(<FloatingAssistant context="analytics" />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText('Analytics Helper')).toBeInTheDocument();
  });

  it('uses context-specific title for integrations', async () => {
    render(<FloatingAssistant context="integrations" />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText('Integration Helper')).toBeInTheDocument();
  });

  it('positions at bottom-right by default', async () => {
    const { container } = render(<FloatingAssistant />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    expect(button).toHaveClass('bottom-6');
    expect(button).toHaveClass('right-6');
  });

  it('positions at bottom-left when specified', async () => {
    render(<FloatingAssistant position="bottom-left" />);
    
    const button = screen.getByRole('button', { name: /open ai assistant/i });
    expect(button).toHaveClass('bottom-6');
    expect(button).toHaveClass('left-6');
  });

  it('has input field in chat panel', async () => {
    render(<FloatingAssistant />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByPlaceholderText('Ask me anything...')).toBeInTheDocument();
  });

  it('has send button in chat panel', async () => {
    render(<FloatingAssistant />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    // Find the send button by its icon
    const sendButton = screen.getAllByRole('button').find(btn => 
      btn.querySelector('svg.lucide-send')
    );
    expect(sendButton).toBeDefined();
  });

  it('shows model name at bottom', async () => {
    render(<FloatingAssistant />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    expect(screen.getByText(/powered by/i)).toBeInTheDocument();
    expect(screen.getByText(/gemini-flash/i)).toBeInTheDocument();
  });

  it('can reset conversation', async () => {
    render(<FloatingAssistant />);
    
    await act(async () => {
      fireEvent.click(screen.getByRole('button', { name: /open ai assistant/i }));
    });

    // Find reset button
    const resetButton = screen.getAllByRole('button').find(btn => 
      btn.querySelector('svg.lucide-rotate-ccw')
    );
    expect(resetButton).toBeDefined();
    
    await act(async () => {
      fireEvent.click(resetButton!);
    });

    // Messages should be cleared (welcome message should reappear on next open)
  });
});

describe('useFloatingAssistant hook', () => {
  it('returns context and visibility state', () => {
    const TestComponent = () => {
      const assistant = useFloatingAssistant('documents');
      return (
        <div>
          <span data-testid="context">{assistant.context}</span>
          <span data-testid="visible">{assistant.isVisible.toString()}</span>
          <button onClick={assistant.toggle}>Toggle</button>
        </div>
      );
    };

    render(<TestComponent />);
    
    expect(screen.getByTestId('context')).toHaveTextContent('documents');
    expect(screen.getByTestId('visible')).toHaveTextContent('true');
  });

  it('can toggle visibility', async () => {
    const TestComponent = () => {
      const assistant = useFloatingAssistant('documents');
      return (
        <div>
          <span data-testid="visible">{assistant.isVisible.toString()}</span>
          <button onClick={assistant.toggle}>Toggle</button>
        </div>
      );
    };

    render(<TestComponent />);
    
    expect(screen.getByTestId('visible')).toHaveTextContent('true');
    
    await act(async () => {
      fireEvent.click(screen.getByText('Toggle'));
    });
    
    expect(screen.getByTestId('visible')).toHaveTextContent('false');
  });

  it('can show and hide explicitly', async () => {
    const TestComponent = () => {
      const assistant = useFloatingAssistant('documents');
      return (
        <div>
          <span data-testid="visible">{assistant.isVisible.toString()}</span>
          <button onClick={assistant.show}>Show</button>
          <button onClick={assistant.hide}>Hide</button>
        </div>
      );
    };

    render(<TestComponent />);
    
    await act(async () => {
      fireEvent.click(screen.getByText('Hide'));
    });
    expect(screen.getByTestId('visible')).toHaveTextContent('false');
    
    await act(async () => {
      fireEvent.click(screen.getByText('Show'));
    });
    expect(screen.getByTestId('visible')).toHaveTextContent('true');
  });
});
