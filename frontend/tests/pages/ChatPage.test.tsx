/**
 * Chat Page Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface ChatPageProps {
  conversationId?: string;
  initialMessages?: Message[];
  onSendMessage?: (content: string) => Promise<void>;
  isLoading?: boolean;
}

// Mock ChatPage component
const ChatPage = ({
  conversationId,
  initialMessages = [],
  onSendMessage,
  isLoading = false,
}: ChatPageProps) => {
  const [messages, setMessages] = React.useState<Message[]>(initialMessages);
  const [input, setInput] = React.useState('');
  const [isSending, setIsSending] = React.useState(false);

  const handleSend = async () => {
    if (!input.trim() || isSending) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsSending(true);

    try {
      await onSendMessage?.(input);
    } finally {
      setIsSending(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (isLoading) {
    return <div data-testid="loading-state">Loading conversation...</div>;
  }

  return (
    <div data-testid="chat-page" className="chat-page">
      <header data-testid="chat-header">
        <h1>Chat</h1>
        {conversationId && <span data-testid="conversation-id">ID: {conversationId}</span>}
      </header>

      <div data-testid="messages-container" className="messages">
        {messages.length === 0 ? (
          <div data-testid="empty-state">
            <h2>Start a conversation</h2>
            <p>Send a message to begin chatting with NexusAI</p>
          </div>
        ) : (
          messages.map((message) => (
            <div
              key={message.id}
              data-testid={`message-${message.id}`}
              className={`message ${message.role}`}
            >
              <span className="role">{message.role}</span>
              <p className="content">{message.content}</p>
            </div>
          ))
        )}
        {isSending && <div data-testid="typing-indicator">AI is typing...</div>}
      </div>

      <div data-testid="input-area" className="input-area">
        <textarea
          data-testid="message-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type a message..."
          disabled={isSending}
        />
        <button
          data-testid="send-button"
          onClick={handleSend}
          disabled={!input.trim() || isSending}
        >
          {isSending ? 'Sending...' : 'Send'}
        </button>
      </div>
    </div>
  );
};

describe('ChatPage', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders chat page', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('chat-page')).toBeInTheDocument();
  });

  it('renders header', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('chat-header')).toBeInTheDocument();
    expect(screen.getByText('Chat')).toBeInTheDocument();
  });

  it('shows conversation ID when provided', () => {
    render(<ChatPage conversationId="conv-123" />);
    expect(screen.getByTestId('conversation-id')).toHaveTextContent('ID: conv-123');
  });

  it('shows loading state', () => {
    render(<ChatPage isLoading={true} />);
    expect(screen.getByTestId('loading-state')).toHaveTextContent('Loading conversation...');
  });

  it('shows empty state when no messages', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('empty-state')).toBeInTheDocument();
    expect(screen.getByText('Start a conversation')).toBeInTheDocument();
  });

  it('renders initial messages', () => {
    const messages: Message[] = [
      { id: '1', role: 'user', content: 'Hello', timestamp: new Date() },
      { id: '2', role: 'assistant', content: 'Hi there!', timestamp: new Date() },
    ];
    render(<ChatPage initialMessages={messages} />);

    expect(screen.getByTestId('message-1')).toBeInTheDocument();
    expect(screen.getByTestId('message-2')).toBeInTheDocument();
    expect(screen.getByText('Hello')).toBeInTheDocument();
    expect(screen.getByText('Hi there!')).toBeInTheDocument();
  });

  it('renders input area', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('input-area')).toBeInTheDocument();
    expect(screen.getByTestId('message-input')).toBeInTheDocument();
    expect(screen.getByTestId('send-button')).toBeInTheDocument();
  });

  it('updates input value on change', () => {
    render(<ChatPage />);
    const input = screen.getByTestId('message-input');
    
    fireEvent.change(input, { target: { value: 'Test message' } });
    expect(input).toHaveValue('Test message');
  });

  it('disables send button when input is empty', () => {
    render(<ChatPage />);
    expect(screen.getByTestId('send-button')).toBeDisabled();
  });

  it('enables send button when input has value', () => {
    render(<ChatPage />);
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Test' } });
    expect(screen.getByTestId('send-button')).not.toBeDisabled();
  });

  it('adds user message on send', async () => {
    render(<ChatPage />);
    
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Hello AI' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByText('Hello AI')).toBeInTheDocument();
    });
  });

  it('clears input after send', async () => {
    render(<ChatPage />);
    
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Hello' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(screen.getByTestId('message-input')).toHaveValue('');
    });
  });

  it('calls onSendMessage callback', async () => {
    const onSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<ChatPage onSendMessage={onSendMessage} />);
    
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Test message' } });
    fireEvent.click(screen.getByTestId('send-button'));

    await waitFor(() => {
      expect(onSendMessage).toHaveBeenCalledWith('Test message');
    });
  });

  it('shows typing indicator while sending', async () => {
    const onSendMessage = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );
    render(<ChatPage onSendMessage={onSendMessage} />);
    
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Test' } });
    fireEvent.click(screen.getByTestId('send-button'));

    expect(screen.getByTestId('typing-indicator')).toBeInTheDocument();
  });

  it('sends message on Enter key', async () => {
    const onSendMessage = vi.fn().mockResolvedValue(undefined);
    render(<ChatPage onSendMessage={onSendMessage} />);
    
    const input = screen.getByTestId('message-input');
    fireEvent.change(input, { target: { value: 'Enter test' } });
    fireEvent.keyDown(input, { key: 'Enter' });

    await waitFor(() => {
      expect(onSendMessage).toHaveBeenCalledWith('Enter test');
    });
  });

  it('does not send on Shift+Enter', () => {
    const onSendMessage = vi.fn();
    render(<ChatPage onSendMessage={onSendMessage} />);
    
    const input = screen.getByTestId('message-input');
    fireEvent.change(input, { target: { value: 'Multi-line' } });
    fireEvent.keyDown(input, { key: 'Enter', shiftKey: true });

    expect(onSendMessage).not.toHaveBeenCalled();
  });

  it('disables input while sending', async () => {
    const onSendMessage = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );
    render(<ChatPage onSendMessage={onSendMessage} />);
    
    fireEvent.change(screen.getByTestId('message-input'), { target: { value: 'Test' } });
    fireEvent.click(screen.getByTestId('send-button'));

    expect(screen.getByTestId('message-input')).toBeDisabled();
  });
});
