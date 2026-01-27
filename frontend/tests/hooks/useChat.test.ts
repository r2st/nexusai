/**
 * Extended tests for useChat hook
 * Tests streaming, error handling, and edge cases
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useChatStore } from '@/store/chat';
import type { Conversation, Message } from '@/lib/api';

// Mock the API
vi.mock('@/lib/api', () => ({
  chatApi: {
    createConversation: vi.fn(),
    listConversations: vi.fn(),
    getConversation: vi.fn(),
    getMessages: vi.fn(),
    sendMessage: vi.fn(),
    deleteConversation: vi.fn(),
  },
}));

import { chatApi } from '@/lib/api';

const mockConversation: Conversation = {
  id: 'conv-123',
  title: 'Test Conversation',
  model_provider: 'openai',
  model_name: 'gpt-4',
  message_count: 0,
  total_tokens: 0,
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
};

const mockMessages: Message[] = [
  {
    id: 'msg-1',
    role: 'user',
    content: 'Hello',
    model_name: null,
    created_at: '2024-01-15T10:00:00Z',
  },
  {
    id: 'msg-2',
    role: 'assistant',
    content: 'Hi there! How can I help you?',
    model_name: 'gpt-4',
    created_at: '2024-01-15T10:00:01Z',
  },
];

describe('useChatStore extended tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    useChatStore.setState({
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      isStreaming: false,
      streamingContent: '',
    });
  });

  describe('Conversation Management', () => {
    it('sets conversations list', () => {
      useChatStore.getState().setConversations([mockConversation]);

      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(1);
      expect(state.conversations[0].title).toBe('Test Conversation');
    });

    it('adds conversation to the list', () => {
      useChatStore.getState().addConversation(mockConversation);

      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(1);
    });

    it('removes conversation by id and clears if current', () => {
      useChatStore.getState().setConversations([mockConversation]);
      useChatStore.getState().setCurrentConversation(mockConversation);

      useChatStore.getState().removeConversation('conv-123');

      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(0);
      expect(state.currentConversation).toBeNull();
    });

    it('preserves other conversations when removing one', () => {
      const conversations = [
        mockConversation,
        { ...mockConversation, id: 'conv-456', title: 'Second' },
        { ...mockConversation, id: 'conv-789', title: 'Third' },
      ];
      useChatStore.getState().setConversations(conversations);

      useChatStore.getState().removeConversation('conv-456');

      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(2);
      expect(state.conversations.map(c => c.id)).toEqual(['conv-123', 'conv-789']);
    });
  });

  describe('Message Management', () => {
    it('adds message to the end of messages array', () => {
      useChatStore.getState().setMessages(mockMessages);
      
      const newMessage: Message = {
        id: 'msg-3',
        role: 'user',
        content: 'New message',
        model_name: null,
        created_at: '2024-01-15T10:01:00Z',
      };

      useChatStore.getState().addMessage(newMessage);

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(3);
      expect(state.messages[2].content).toBe('New message');
    });

    it('clears messages array', () => {
      useChatStore.getState().setMessages(mockMessages);
      useChatStore.getState().setMessages([]);

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(0);
    });

    it('replaces entire messages array', () => {
      useChatStore.getState().setMessages(mockMessages);
      
      const newMessages: Message[] = [
        {
          id: 'new-1',
          role: 'system',
          content: 'You are a helpful assistant.',
          model_name: null,
          created_at: '2024-01-15T11:00:00Z',
        },
      ];

      useChatStore.getState().setMessages(newMessages);

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].id).toBe('new-1');
    });
  });

  describe('Streaming State Management', () => {
    it('tracks streaming state correctly', () => {
      const state1 = useChatStore.getState();
      expect(state1.isStreaming).toBe(false);
      expect(state1.streamingContent).toBe('');

      useChatStore.getState().setIsStreaming(true);
      useChatStore.getState().setStreamingContent('Starting...');

      const state2 = useChatStore.getState();
      expect(state2.isStreaming).toBe(true);
      expect(state2.streamingContent).toBe('Starting...');
    });

    it('appends to streaming content', () => {
      useChatStore.getState().setStreamingContent('Hello');
      useChatStore.getState().appendStreamingContent(' world');
      useChatStore.getState().appendStreamingContent('!');

      const state = useChatStore.getState();
      expect(state.streamingContent).toBe('Hello world!');
    });

    it('clears streaming content', () => {
      useChatStore.getState().setStreamingContent('Some content');
      useChatStore.getState().clearStreamingContent();

      const state = useChatStore.getState();
      expect(state.streamingContent).toBe('');
    });

    it('handles empty append', () => {
      useChatStore.getState().setStreamingContent('Base');
      useChatStore.getState().appendStreamingContent('');

      const state = useChatStore.getState();
      expect(state.streamingContent).toBe('Base');
    });

    it('handles streaming with special characters', () => {
      useChatStore.getState().setStreamingContent('Code: ```python\n');
      useChatStore.getState().appendStreamingContent('def hello():\n');
      useChatStore.getState().appendStreamingContent('    print("world")\n');
      useChatStore.getState().appendStreamingContent('```');

      const state = useChatStore.getState();
      expect(state.streamingContent).toContain('```python');
      expect(state.streamingContent).toContain('print("world")');
    });
  });

  describe('Loading State', () => {
    it('tracks loading state independently from streaming', () => {
      useChatStore.getState().setIsLoading(true);
      useChatStore.getState().setIsStreaming(false);

      const state = useChatStore.getState();
      expect(state.isLoading).toBe(true);
      expect(state.isStreaming).toBe(false);
    });

    it('allows both loading and streaming simultaneously', () => {
      useChatStore.getState().setIsLoading(true);
      useChatStore.getState().setIsStreaming(true);

      const state = useChatStore.getState();
      expect(state.isLoading).toBe(true);
      expect(state.isStreaming).toBe(true);
    });
  });

  describe('Model Selection', () => {
    it('stores selected model', () => {
      useChatStore.getState().setSelectedModel('claude-3-opus');

      const state = useChatStore.getState();
      expect(state.selectedModel).toBe('claude-3-opus');
    });

    it('can set any model name', () => {
      useChatStore.getState().setSelectedModel('gpt-4-turbo');
      const state = useChatStore.getState();
      expect(state.selectedModel).toBe('gpt-4-turbo');
    });
  });

  describe('State Reset via setState', () => {
    it('resets state by setting defaults', () => {
      // Set up some state
      useChatStore.getState().setConversations([mockConversation]);
      useChatStore.getState().setCurrentConversation(mockConversation);
      useChatStore.getState().setMessages(mockMessages);
      useChatStore.getState().setIsLoading(true);
      useChatStore.getState().setIsStreaming(true);
      useChatStore.getState().setStreamingContent('Some content');

      // Reset by setting defaults
      useChatStore.setState({
        conversations: [],
        currentConversation: null,
        messages: [],
        isLoading: false,
        isStreaming: false,
        streamingContent: '',
      });

      const state = useChatStore.getState();
      expect(state.conversations).toEqual([]);
      expect(state.currentConversation).toBeNull();
      expect(state.messages).toEqual([]);
      expect(state.isLoading).toBe(false);
      expect(state.isStreaming).toBe(false);
      expect(state.streamingContent).toBe('');
    });
  });

  describe('Concurrent State Updates', () => {
    it('handles rapid state updates correctly', () => {
      // Simulate rapid message additions
      for (let i = 0; i < 100; i++) {
        useChatStore.getState().addMessage({
          id: `msg-${i}`,
          role: i % 2 === 0 ? 'user' : 'assistant',
          content: `Message ${i}`,
          model_name: null,
          created_at: new Date().toISOString(),
        });
      }

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(100);
      expect(state.messages[0].id).toBe('msg-0');
      expect(state.messages[99].id).toBe('msg-99');
    });

    it('handles interleaved streaming updates', () => {
      // Simulate character-by-character streaming
      const content = 'Hello, world!';
      
      useChatStore.getState().setStreamingContent('');
      useChatStore.getState().setIsStreaming(true);

      for (const char of content) {
        useChatStore.getState().appendStreamingContent(char);
      }

      useChatStore.getState().setIsStreaming(false);

      const state = useChatStore.getState();
      expect(state.streamingContent).toBe('Hello, world!');
      expect(state.isStreaming).toBe(false);
    });
  });

  describe('Edge Cases', () => {
    it('handles message with empty content', () => {
      useChatStore.getState().addMessage({
        id: 'empty-msg',
        role: 'assistant',
        content: '',
        model_name: 'gpt-4',
        created_at: new Date().toISOString(),
      });

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(1);
      expect(state.messages[0].content).toBe('');
    });

    it('handles very long message content', () => {
      const longContent = 'x'.repeat(100000);
      
      useChatStore.getState().addMessage({
        id: 'long-msg',
        role: 'user',
        content: longContent,
        model_name: null,
        created_at: new Date().toISOString(),
      });

      const state = useChatStore.getState();
      expect(state.messages[0].content.length).toBe(100000);
    });

    it('handles unicode in messages', () => {
      useChatStore.getState().addMessage({
        id: 'unicode-msg',
        role: 'user',
        content: '你好世界 🌍 مرحبا',
        model_name: null,
        created_at: new Date().toISOString(),
      });

      const state = useChatStore.getState();
      expect(state.messages[0].content).toBe('你好世界 🌍 مرحبا');
    });

    it('handles special markdown in content', () => {
      const markdownContent = `
# Heading
- List item
\`\`\`javascript
const x = 1;
\`\`\`
> Quote
| Table | Header |
| ----- | ------ |
| Cell  | Cell   |
      `;

      useChatStore.getState().addMessage({
        id: 'markdown-msg',
        role: 'assistant',
        content: markdownContent,
        model_name: 'gpt-4',
        created_at: new Date().toISOString(),
      });

      const state = useChatStore.getState();
      expect(state.messages[0].content).toContain('# Heading');
      expect(state.messages[0].content).toContain('```javascript');
    });
  });
});
