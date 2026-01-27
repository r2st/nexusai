/**
 * ChatInput component tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ChatInput } from '@/components/chat/input';

describe('ChatInput Component', () => {
  describe('rendering', () => {
    it('renders with default placeholder', () => {
      render(<ChatInput onSend={vi.fn()} />);
      const input = screen.getByLabelText('Message input');
      expect(input.getAttribute('placeholder')).toContain('Send a message');
    });

    it('renders with custom placeholder', () => {
      render(<ChatInput onSend={vi.fn()} placeholder="Ask a question..." />);
      expect(screen.getByLabelText('Message input')).toHaveAttribute(
        'placeholder',
        'Ask a question...'
      );
    });

    it('renders send button', () => {
      render(<ChatInput onSend={vi.fn()} />);
      expect(screen.getByLabelText('Send message')).toBeInTheDocument();
    });

    it('renders attach file button', () => {
      render(<ChatInput onSend={vi.fn()} />);
      expect(screen.getByLabelText('Attach file')).toBeInTheDocument();
    });

    it('renders disclaimer text', () => {
      render(<ChatInput onSend={vi.fn()} />);
      expect(
        screen.getByText(/NexusAI can make mistakes/i)
      ).toBeInTheDocument();
    });
  });

  describe('input behavior', () => {
    it('updates value when typing', async () => {
      render(<ChatInput onSend={vi.fn()} />);
      const textarea = screen.getByLabelText('Message input');
      
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      
      expect(textarea).toHaveValue('Hello');
    });

    it('clears input after sending', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      const textarea = screen.getByLabelText('Message input');
      
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      fireEvent.click(screen.getByLabelText('Send message'));
      
      expect(textarea).toHaveValue('');
    });
  });

  describe('sending messages', () => {
    it('calls onSend with trimmed message when send button clicked', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: '  Hello world  ' } });
      fireEvent.click(screen.getByLabelText('Send message'));
      
      expect(onSend).toHaveBeenCalledWith('Hello world');
    });

    it('calls onSend when Enter is pressed without Shift', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
      
      expect(onSend).toHaveBeenCalledWith('Hello');
    });

    it('does not call onSend when Shift+Enter is pressed', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: true });
      
      expect(onSend).not.toHaveBeenCalled();
    });

    it('does not call onSend with empty message', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      
      fireEvent.click(screen.getByLabelText('Send message'));
      
      expect(onSend).not.toHaveBeenCalled();
    });

    it('does not call onSend with whitespace-only message', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: '   ' } });
      fireEvent.click(screen.getByLabelText('Send message'));
      
      expect(onSend).not.toHaveBeenCalled();
    });
  });

  describe('disabled state', () => {
    it('disables textarea when disabled prop is true', () => {
      render(<ChatInput onSend={vi.fn()} disabled />);
      expect(screen.getByLabelText('Message input')).toBeDisabled();
    });

    it('disables send button when disabled', () => {
      render(<ChatInput onSend={vi.fn()} disabled />);
      expect(screen.getByLabelText('Send message')).toBeDisabled();
    });

    it('disables attach button when disabled', () => {
      render(<ChatInput onSend={vi.fn()} disabled />);
      expect(screen.getByLabelText('Attach file')).toBeDisabled();
    });

    it('does not call onSend when disabled', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} disabled />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      fireEvent.click(screen.getByLabelText('Send message'));
      
      expect(onSend).not.toHaveBeenCalled();
    });
  });

  describe('loading state', () => {
    it('disables textarea when loading', () => {
      render(<ChatInput onSend={vi.fn()} isLoading />);
      expect(screen.getByLabelText('Message input')).toBeDisabled();
    });

    it('disables send button when loading', () => {
      render(<ChatInput onSend={vi.fn()} isLoading />);
      expect(screen.getByLabelText('Send message')).toBeDisabled();
    });

    it('does not call onSend when loading', () => {
      const onSend = vi.fn();
      render(<ChatInput onSend={onSend} isLoading />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      fireEvent.keyDown(textarea, { key: 'Enter', shiftKey: false });
      
      expect(onSend).not.toHaveBeenCalled();
    });
  });

  describe('send button state', () => {
    it('disables send button when input is empty', () => {
      render(<ChatInput onSend={vi.fn()} />);
      expect(screen.getByLabelText('Send message')).toBeDisabled();
    });

    it('enables send button when input has content', () => {
      render(<ChatInput onSend={vi.fn()} />);
      
      const textarea = screen.getByLabelText('Message input');
      fireEvent.change(textarea, { target: { value: 'Hello' } });
      
      expect(screen.getByLabelText('Send message')).not.toBeDisabled();
    });
  });
});
