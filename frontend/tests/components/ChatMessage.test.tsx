/**
 * ChatMessage component tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { ChatMessage } from '@/components/chat/message';

describe('ChatMessage Component', () => {
  describe('user messages', () => {
    it('renders user message content', () => {
      render(<ChatMessage role="user" content="Hello, world!" />);
      expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    });

    it('displays "You" label for user messages', () => {
      render(<ChatMessage role="user" content="Test message" />);
      expect(screen.getByText('You')).toBeInTheDocument();
    });

    it('has user role data attribute', () => {
      render(<ChatMessage role="user" content="Test" />);
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('data-role', 'user');
    });

    it('has correct aria-label for user', () => {
      render(<ChatMessage role="user" content="Test" />);
      expect(screen.getByLabelText('Message from you')).toBeInTheDocument();
    });
  });

  describe('assistant messages', () => {
    it('renders assistant message content', () => {
      render(<ChatMessage role="assistant" content="Hi there!" />);
      expect(screen.getByText('Hi there!')).toBeInTheDocument();
    });

    it('displays "Assistant" label for assistant messages', () => {
      render(<ChatMessage role="assistant" content="Test message" />);
      expect(screen.getByText('Assistant')).toBeInTheDocument();
    });

    it('has assistant role data attribute', () => {
      render(<ChatMessage role="assistant" content="Test" />);
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('data-role', 'assistant');
    });

    it('has correct aria-label for assistant', () => {
      render(<ChatMessage role="assistant" content="Test" />);
      expect(screen.getByLabelText('Message from assistant')).toBeInTheDocument();
    });
  });

  describe('markdown rendering', () => {
    it('renders bold text', () => {
      render(<ChatMessage role="assistant" content="This is **bold** text" />);
      // Check that the word bold appears in the document
      expect(screen.getByText(/bold/)).toBeInTheDocument();
    });

    it('renders code content', () => {
      render(<ChatMessage role="assistant" content="```js\nconst x = 1;\n```" />);
      // The code content should be in a code element
      const codeElement = document.querySelector('code');
      expect(codeElement).toBeInTheDocument();
      expect(codeElement?.textContent).toContain('const x = 1');
    });

    it('renders inline code', () => {
      render(<ChatMessage role="assistant" content="Use `console.log()` to debug" />);
      // Check that code element exists with the expected content
      const codeElement = document.querySelector('code');
      expect(codeElement).toBeInTheDocument();
      expect(codeElement?.textContent).toContain('console.log()');
    });

    it('renders lists', () => {
      render(<ChatMessage role="assistant" content="- Item 1\n- Item 2" />);
      // Check that list elements exist
      const listElement = document.querySelector('ul');
      expect(listElement).toBeInTheDocument();
      // The list content should be somewhere in the document
      expect(screen.getByText(/Item 1/)).toBeInTheDocument();
    });
  });

  describe('streaming state', () => {
    it('sets streaming data attribute when streaming', () => {
      render(<ChatMessage role="assistant" content="Loading..." isStreaming />);
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('data-streaming', 'true');
    });

    it('does not have streaming attribute when not streaming', () => {
      render(<ChatMessage role="assistant" content="Done" isStreaming={false} />);
      const article = screen.getByRole('article');
      expect(article).not.toHaveAttribute('data-streaming');
    });
  });

  describe('system messages', () => {
    it('renders system message content', () => {
      render(<ChatMessage role="system" content="System message" />);
      expect(screen.getByText('System message')).toBeInTheDocument();
    });

    it('has system role data attribute', () => {
      render(<ChatMessage role="system" content="System" />);
      const article = screen.getByRole('article');
      expect(article).toHaveAttribute('data-role', 'system');
    });
  });
});
