/**
 * Chat store tests
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { useChatStore } from '@/store/chat';
import type { Conversation, Message } from '@/lib/api';

const mockConversation: Conversation = {
  id: 'conv-123',
  title: 'Test Conversation',
  model_provider: 'openai',
  model_name: 'gpt-4',
  message_count: 0,
  total_tokens: 0,
  created_at: '2024-06-15T10:00:00Z',
  updated_at: '2024-06-15T10:00:00Z',
};

const mockMessage: Message = {
  id: 'msg-123',
  role: 'user',
  content: 'Hello, world!',
  model_name: null,
  created_at: '2024-06-15T10:00:00Z',
};

describe('useChatStore', () => {
  beforeEach(() => {
    // Reset store state
    useChatStore.setState({
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      isStreaming: false,
      streamingContent: '',
    });
  });

  describe('initial state', () => {
    it('starts with empty conversations', () => {
      const state = useChatStore.getState();
      expect(state.conversations).toEqual([]);
    });

    it('starts with no current conversation', () => {
      const state = useChatStore.getState();
      expect(state.currentConversation).toBeNull();
    });

    it('starts with empty messages', () => {
      const state = useChatStore.getState();
      expect(state.messages).toEqual([]);
    });

    it('starts with isLoading false', () => {
      const state = useChatStore.getState();
      expect(state.isLoading).toBe(false);
    });

    it('starts with isStreaming false', () => {
      const state = useChatStore.getState();
      expect(state.isStreaming).toBe(false);
    });

    it('starts with empty streamingContent', () => {
      const state = useChatStore.getState();
      expect(state.streamingContent).toBe('');
    });
  });

  describe('setConversations', () => {
    it('sets conversations', () => {
      const conversations = [mockConversation];
      useChatStore.getState().setConversations(conversations);
      
      const state = useChatStore.getState();
      expect(state.conversations).toEqual(conversations);
    });
  });

  describe('addConversation', () => {
    it('adds a conversation to the beginning', () => {
      const existing: Conversation = { ...mockConversation, id: 'conv-1' };
      useChatStore.getState().setConversations([existing]);
      
      const newConversation: Conversation = { ...mockConversation, id: 'conv-2' };
      useChatStore.getState().addConversation(newConversation);
      
      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(2);
      expect(state.conversations[0].id).toBe('conv-2');
      expect(state.conversations[1].id).toBe('conv-1');
    });
  });

  describe('removeConversation', () => {
    it('removes a conversation by id', () => {
      const conv1: Conversation = { ...mockConversation, id: 'conv-1' };
      const conv2: Conversation = { ...mockConversation, id: 'conv-2' };
      useChatStore.getState().setConversations([conv1, conv2]);
      
      useChatStore.getState().removeConversation('conv-1');
      
      const state = useChatStore.getState();
      expect(state.conversations).toHaveLength(1);
      expect(state.conversations[0].id).toBe('conv-2');
    });

    it('clears current conversation if it was removed', () => {
      const conv: Conversation = { ...mockConversation, id: 'conv-1' };
      useChatStore.getState().setConversations([conv]);
      useChatStore.getState().setCurrentConversation(conv);
      
      useChatStore.getState().removeConversation('conv-1');
      
      const state = useChatStore.getState();
      expect(state.currentConversation).toBeNull();
    });

    it('keeps current conversation if different one was removed', () => {
      const conv1: Conversation = { ...mockConversation, id: 'conv-1' };
      const conv2: Conversation = { ...mockConversation, id: 'conv-2' };
      useChatStore.getState().setConversations([conv1, conv2]);
      useChatStore.getState().setCurrentConversation(conv1);
      
      useChatStore.getState().removeConversation('conv-2');
      
      const state = useChatStore.getState();
      expect(state.currentConversation?.id).toBe('conv-1');
    });
  });

  describe('setCurrentConversation', () => {
    it('sets the current conversation', () => {
      useChatStore.getState().setCurrentConversation(mockConversation);
      
      const state = useChatStore.getState();
      expect(state.currentConversation).toEqual(mockConversation);
    });

    it('can set to null', () => {
      useChatStore.getState().setCurrentConversation(mockConversation);
      useChatStore.getState().setCurrentConversation(null);
      
      const state = useChatStore.getState();
      expect(state.currentConversation).toBeNull();
    });
  });

  describe('setMessages', () => {
    it('sets messages', () => {
      const messages = [mockMessage];
      useChatStore.getState().setMessages(messages);
      
      const state = useChatStore.getState();
      expect(state.messages).toEqual(messages);
    });
  });

  describe('addMessage', () => {
    it('adds a message to the end', () => {
      const existing: Message = { ...mockMessage, id: 'msg-1', content: 'First message' };
      useChatStore.getState().setMessages([existing]);

      const newMessage: Message = { ...mockMessage, id: 'msg-2', content: 'Second message' };
      useChatStore.getState().addMessage(newMessage);

      const state = useChatStore.getState();
      expect(state.messages).toHaveLength(2);
      expect(state.messages[0].id).toBe('msg-1');
      expect(state.messages[1].id).toBe('msg-2');
    });
  });

  describe('setIsLoading', () => {
    it('sets isLoading', () => {
      useChatStore.getState().setIsLoading(true);
      expect(useChatStore.getState().isLoading).toBe(true);
      
      useChatStore.getState().setIsLoading(false);
      expect(useChatStore.getState().isLoading).toBe(false);
    });
  });

  describe('setIsStreaming', () => {
    it('sets isStreaming', () => {
      useChatStore.getState().setIsStreaming(true);
      expect(useChatStore.getState().isStreaming).toBe(true);
      
      useChatStore.getState().setIsStreaming(false);
      expect(useChatStore.getState().isStreaming).toBe(false);
    });
  });

  describe('streaming content', () => {
    it('setStreamingContent sets content', () => {
      useChatStore.getState().setStreamingContent('Hello');
      expect(useChatStore.getState().streamingContent).toBe('Hello');
    });

    it('appendStreamingContent appends to content', () => {
      useChatStore.getState().setStreamingContent('Hello');
      useChatStore.getState().appendStreamingContent(' World');
      expect(useChatStore.getState().streamingContent).toBe('Hello World');
    });

    it('clearStreamingContent clears content', () => {
      useChatStore.getState().setStreamingContent('Hello World');
      useChatStore.getState().clearStreamingContent();
      expect(useChatStore.getState().streamingContent).toBe('');
    });
  });
});
