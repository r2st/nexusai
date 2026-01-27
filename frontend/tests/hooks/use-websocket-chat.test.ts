/**
 * WebSocket Chat Hook Tests
 *
 * Note: These tests focus on the hook's public interface and state management.
 * Due to React Strict Mode and the hook's mount protection, some WebSocket
 * lifecycle tests require careful timing.
 */

import { describe, it, expect, beforeEach, vi, afterEach, afterAll } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';
import { useWebSocketChat } from '@/hooks/use-websocket-chat';

// Mock WebSocket
class MockWebSocket {
  static CONNECTING = 0;
  static OPEN = 1;
  static CLOSING = 2;
  static CLOSED = 3;

  readyState = MockWebSocket.CONNECTING;
  url: string;
  onopen: ((event: Event) => void) | null = null;
  onclose: ((event: CloseEvent) => void) | null = null;
  onerror: ((event: Event) => void) | null = null;
  onmessage: ((event: MessageEvent) => void) | null = null;

  constructor(url: string) {
    this.url = url;
    mockWebSocketInstances.push(this);
  }

  send = vi.fn((data: string) => {
    if (this.readyState !== MockWebSocket.OPEN) {
      throw new Error('WebSocket is not open');
    }
  });

  close = vi.fn((code?: number, reason?: string) => {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({
      code: code ?? 1000,
      reason: reason ?? '',
      wasClean: true,
    } as CloseEvent);
  });

  // Helper to simulate receiving a message
  simulateMessage(data: unknown) {
    this.onmessage?.({
      data: JSON.stringify(data),
    } as MessageEvent);
  }

  // Helper to simulate connection open
  simulateOpen() {
    this.readyState = MockWebSocket.OPEN;
    this.onopen?.(new Event('open'));
  }

  // Helper to simulate error
  simulateError() {
    this.onerror?.(new Event('error'));
  }

  // Helper to simulate close
  simulateClose(code = 1000, reason = '') {
    this.readyState = MockWebSocket.CLOSED;
    this.onclose?.({
      code,
      reason,
      wasClean: code === 1000,
    } as CloseEvent);
  }
}

// Track created WebSocket instances
let mockWebSocketInstances: MockWebSocket[] = [];

// Replace global WebSocket with mock
const originalWebSocket = global.WebSocket;

describe('useWebSocketChat', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    mockWebSocketInstances = [];
    localStorage.clear();

    // Install WebSocket mock
    global.WebSocket = MockWebSocket as unknown as typeof WebSocket;
  });

  afterEach(() => {
    vi.clearAllMocks();
    mockWebSocketInstances = [];
  });

  afterAll(() => {
    global.WebSocket = originalWebSocket;
  });

  describe('Initial State', () => {
    it('should return initial disconnected state', () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      expect(result.current.isConnected).toBe(false);
      expect(result.current.isConnecting).toBe(false);
      expect(result.current.isStreaming).toBe(false);
      expect(result.current.streamingContent).toBe('');
      expect(result.current.error).toBeNull();
    });

    it('should provide connect and disconnect functions', () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      expect(typeof result.current.connect).toBe('function');
      expect(typeof result.current.disconnect).toBe('function');
    });

    it('should provide sendMessage and createConversation functions', () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      expect(typeof result.current.sendMessage).toBe('function');
      expect(typeof result.current.createConversation).toBe('function');
    });
  });

  describe('Connection', () => {
    it('should close if connect timeout elapses', () => {
      vi.useFakeTimers();
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      const ws = mockWebSocketInstances[0];

      act(() => {
        vi.advanceTimersByTime(8000);
      });

      expect(ws.close).toHaveBeenCalledWith(4000, 'Connect timeout');
      vi.useRealTimers();
    });
    it('should set error when no access token', async () => {
      localStorage.removeItem('access_token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(result.current.error).toBe('No access token available');
      });
    });

    it('should create WebSocket connection with token', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      expect(mockWebSocketInstances[0].url).toContain('token=test-token');
    });

    it('should set isConnecting to true while connecting', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(result.current.isConnecting).toBe(true);
      });
    });

    it('should become connected when receiving connected message', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onConnected = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onConnected })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });
      expect(result.current.isConnecting).toBe(false);
      expect(onConnected).toHaveBeenCalledWith('user-123');
    });
  });

  describe('Disconnection', () => {
    it('should close WebSocket on disconnect', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        result.current.disconnect();
      });

      expect(mockWebSocketInstances[0].close).toHaveBeenCalled();
      await waitFor(() => {
        expect(result.current.isConnected).toBe(false);
      });
    });
  });

  describe('Message Handling', () => {
    it('should handle token streaming', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      // Simulate message start
      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_start',
          conversation_id: 'conv-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isStreaming).toBe(true);
      });
      expect(result.current.streamingConversationId).toBe('conv-123');

      // Simulate token
      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'token',
          content: 'Hello',
        });
      });

      await waitFor(() => {
        expect(result.current.streamingContent).toBe('Hello');
      });

      // Simulate another token
      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'token',
          content: ' world!',
        });
      });

      await waitFor(() => {
        expect(result.current.streamingContent).toBe('Hello world!');
      });
    });

    it('should close when pong timeout elapses', async () => {
      vi.useFakeTimers();
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      const ws = mockWebSocketInstances[0];

      act(() => {
        ws.simulateOpen();
      });

      act(() => {
        vi.advanceTimersByTime(60000);
      });

      expect(ws.close).toHaveBeenCalledWith(4001, 'Pong timeout');
      vi.useRealTimers();
    });

    it('should handle message complete', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onMessageComplete = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onMessageComplete })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_start',
          conversation_id: 'conv-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'token',
          content: 'Hello',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_complete',
          conversation_id: 'conv-123',
          message: {
            id: 'msg-123',
            role: 'assistant',
            content: '',
            created_at: '2024-01-01T00:00:00Z',
          },
        });
      });

      await waitFor(() => {
        expect(result.current.isStreaming).toBe(false);
      });
      expect(result.current.streamingContent).toBe('');
      expect(onMessageComplete).toHaveBeenCalledWith(
        'conv-123',
        expect.objectContaining({
          id: 'msg-123',
          content: 'Hello',
        })
      );
    });

    it('should prefer completed message content over streamed tokens', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onMessageComplete = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onMessageComplete })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_start',
          conversation_id: 'conv-456',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'token',
          content: 'Hello',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'token',
          content: ' world',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_complete',
          conversation_id: 'conv-456',
          message: {
            id: 'msg-456',
            role: 'assistant',
            content: 'Hello world',
            created_at: '2024-01-01T00:00:00Z',
          },
        });
      });

      await waitFor(() => {
        expect(result.current.isStreaming).toBe(false);
      });

      expect(onMessageComplete).toHaveBeenCalledWith(
        'conv-456',
        expect.objectContaining({
          id: 'msg-456',
          content: 'Hello world',
        })
      );
    });

    it('should handle conversation created', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onConversationCreated = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onConversationCreated })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      const mockConversation = {
        id: 'conv-123',
        title: 'New Conversation',
        model_provider: 'anthropic',
        model_name: 'claude-3-5-sonnet',
      };

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'conversation_created',
          conversation: mockConversation,
        });
      });

      await waitFor(() => {
        expect(onConversationCreated).toHaveBeenCalledWith(mockConversation);
      });
    });

    it('should handle tool calls', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_start',
          conversation_id: 'conv-123',
        });
      });

      const toolCall = {
        name: 'search_web',
        args: { query: 'test' },
        status: 'running',
        id: 'tool-123',
      };

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'tool_call',
          tool_call: toolCall,
        });
      });

      await waitFor(() => {
        expect(result.current.streamingToolCalls).toContainEqual(toolCall);
      });
    });

    it('should handle tool results', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'message_start',
          conversation_id: 'conv-123',
        });
      });

      const toolResult = {
        name: 'search_web',
        output: 'Search results...',
        success: true,
        id: 'tool-123',
      };

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'tool_result',
          tool_result: toolResult,
        });
      });

      await waitFor(() => {
        expect(result.current.streamingToolResults).toContainEqual(toolResult);
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle error messages from server', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onError = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onError })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'error',
          error: 'Something went wrong',
        });
      });

      await waitFor(() => {
        expect(result.current.error).toBe('Something went wrong');
      });
      expect(onError).toHaveBeenCalledWith('Something went wrong');
    });

    it('should ignore empty error payloads from server', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onError = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onError })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'error',
          error: {},
        });
      });

      expect(result.current.error).toBeNull();
      expect(onError).not.toHaveBeenCalled();
    });

    it('should ignore empty error strings from server', async () => {
      localStorage.setItem('access_token', 'test-token');
      const onError = vi.fn();

      const { result } = renderHook(() =>
        useWebSocketChat({ onError })
      );

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      act(() => {
        mockWebSocketInstances[0].simulateMessage({
          type: 'error',
          error: '{}',
        });
      });

      expect(result.current.error).toBeNull();
      expect(onError).not.toHaveBeenCalled();
    });

    it('should set error when sending message without connection', () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.sendMessage('conv-123', 'Hello');
      });

      expect(result.current.error).toBe('WebSocket not connected');
    });
  });

  describe('Send Message', () => {
    it('should send chat message through WebSocket', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.sendMessage('conv-123', 'Hello world');
      });

      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"chat"')
      );
      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"conversation_id":"conv-123"')
      );
      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"message":"Hello world"')
      );
    });

    it('should send message with MCP options', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.sendMessage('conv-123', 'Hello', {
          use_mcp: true,
          temperature: 0.5,
          max_tokens: 2048,
        });
      });

      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"use_mcp":true')
      );
      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"temperature":0.5')
      );
    });
  });

  describe('Create Conversation', () => {
    it('should send create conversation message', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.createConversation('Test Chat', 'anthropic', 'claude-3-5-sonnet');
      });

      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"type":"new_conversation"')
      );
      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"title":"Test Chat"')
      );
    });

    it('should use default title if not provided', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
        mockWebSocketInstances[0].simulateMessage({
          type: 'connected',
          user_id: 'user-123',
        });
      });

      await waitFor(() => {
        expect(result.current.isConnected).toBe(true);
      });

      act(() => {
        result.current.createConversation();
      });

      expect(mockWebSocketInstances[0].send).toHaveBeenCalledWith(
        expect.stringContaining('"title":"New Conversation"')
      );
    });
  });

  describe('Cleanup', () => {
    it('should cleanup on unmount', async () => {
      localStorage.setItem('access_token', 'test-token');

      const { result, unmount } = renderHook(() => useWebSocketChat());

      act(() => {
        result.current.connect();
      });

      await waitFor(() => {
        expect(mockWebSocketInstances.length).toBeGreaterThan(0);
      });

      act(() => {
        mockWebSocketInstances[0].simulateOpen();
      });

      unmount();

      // WebSocket should be closed on unmount
      expect(mockWebSocketInstances[0].readyState).toBe(MockWebSocket.CLOSED);
    });
  });
});
