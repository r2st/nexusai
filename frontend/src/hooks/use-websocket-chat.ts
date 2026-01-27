'use client';

import { useCallback, useEffect, useRef, useState } from 'react';

// Types
export interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  model_name?: string;
  created_at: string;
  widgets?: Array<{
    type: 'dora' | 'space' | 'insights' | 'pipeline_progress';
    [key: string]: unknown;
  }>;
  tool_calls?: Array<{
    name: string;
    args?: Record<string, unknown>;
    status?: 'queued' | 'running' | 'completed' | 'failed';
    id?: string;
  }>;
  tool_results?: Array<{
    name?: string;
    output?: string;
    success?: boolean;
    id?: string;
  }>;
}

export interface Conversation {
  id: string;
  title: string;
  model_provider: string;
  model_name: string;
  message_count: number;
  total_tokens: number;
  created_at: string;
  updated_at: string;
}

interface WebSocketMessage {
  type: string;
  [key: string]: unknown;
}

interface UseWebSocketChatOptions {
  onConnected?: (userId: string) => void;
  onDisconnected?: () => void;
  onError?: (error: string) => void;
  onConversationCreated?: (conversation: Conversation) => void;
  onMessageComplete?: (conversationId: string, message: Message) => void;
  reconnectAttempts?: number;
  reconnectDelay?: number;
}

interface UseWebSocketChatReturn {
  isConnected: boolean;
  isConnecting: boolean;
  isStreaming: boolean;
  streamingContent: string;
  streamingConversationId: string | null;
  streamingToolCalls: Message['tool_calls'];
  streamingToolResults: Message['tool_results'];
  error: string | null;
  connect: () => void;
  disconnect: () => void;
  sendMessage: (conversationId: string, message: string, options?: ChatOptions) => void;
  createConversation: (title?: string, modelProvider?: string, modelName?: string) => void;
}

interface ChatOptions {
  temperature?: number;
  max_tokens?: number;
  use_mcp?: boolean;
  model_name?: string;
  mcp_servers?: Array<{
    name?: string;
    transport?: string;
    url?: string;
    command?: string;
    args?: string[];
    env?: Record<string, string>;
    headers?: Record<string, string>;
    timeout_seconds?: number;
  }>;
}

// Get WebSocket URL based on environment
function getWebSocketUrl(): string {
  if (typeof window === 'undefined') return '';
  
  // Check for explicit WebSocket URL
  const wsUrl = process.env.NEXT_PUBLIC_WS_URL;
  if (wsUrl) return wsUrl;
  
  // Check for API URL and convert to WebSocket
  const apiUrl = process.env.NEXT_PUBLIC_API_URL;
  if (apiUrl && apiUrl.startsWith('http')) {
    const url = new URL(apiUrl);
    const wsProtocol = url.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${wsProtocol}//${url.host}/api/v1/ws/chat`;
  }
  
  // Default to same host with ws protocol
  const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
  
  // In development, connect directly to backend
  if (process.env.NODE_ENV === 'development') {
    return 'ws://localhost:8000/api/v1/ws/chat';
  }
  
  return `${protocol}//${window.location.host}/api/v1/ws/chat`;
}

export function useWebSocketChat(options: UseWebSocketChatOptions = {}): UseWebSocketChatReturn {
  const {
    onConnected,
    onDisconnected,
    onError,
    onConversationCreated,
    onMessageComplete,
    reconnectAttempts = 5,
    reconnectDelay = 3000,
  } = options;

  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [isStreaming, setIsStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [streamingConversationId, setStreamingConversationId] = useState<string | null>(null);
  const [streamingToolCalls, setStreamingToolCalls] = useState<Message['tool_calls']>([]);
  const [streamingToolResults, setStreamingToolResults] = useState<Message['tool_results']>([]);
  const [error, setError] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const reconnectAttemptsRef = useRef(0);
  const reconnectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const connectTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  const pingIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const streamingContentRef = useRef('');
  const lastStreamLogAtRef = useRef(0);
  const lastPongAtRef = useRef(0);
  const isMountedRef = useRef(false);
  const isIntentionalCloseRef = useRef(false);
  const isCleaningUpRef = useRef(false);

  // Cleanup function
  const cleanup = useCallback(() => {
    if (reconnectTimeoutRef.current) {
      clearTimeout(reconnectTimeoutRef.current);
      reconnectTimeoutRef.current = null;
    }
    if (connectTimeoutRef.current) {
      clearTimeout(connectTimeoutRef.current);
      connectTimeoutRef.current = null;
    }
    if (pingIntervalRef.current) {
      clearInterval(pingIntervalRef.current);
      pingIntervalRef.current = null;
    }
  }, []);

  // Handle incoming messages
  const handleMessage = useCallback((event: MessageEvent) => {
    try {
      const data: WebSocketMessage = JSON.parse(event.data);

      switch (data.type) {
        case 'connected':
          setIsConnected(true);
          setIsConnecting(false);
          reconnectAttemptsRef.current = 0;
          onConnected?.(data.user_id as string);
          break;

        case 'conversation_created':
          onConversationCreated?.(data.conversation as Conversation);
          break;

        case 'message_start':
          setIsStreaming(true);
          setStreamingContent('');
          streamingContentRef.current = '';
          setStreamingToolCalls([]);
          setStreamingToolResults([]);
          setStreamingConversationId(data.conversation_id as string);
          break;

        case 'token':
          streamingContentRef.current += data.content as string;
          setStreamingContent(streamingContentRef.current);
          if (
            process.env.NODE_ENV === 'development' &&
            process.env.NEXT_PUBLIC_WS_DEBUG === 'true'
          ) {
            const now = Date.now();
            if (now - lastStreamLogAtRef.current > 1000) {
              lastStreamLogAtRef.current = now;
              console.debug('WebSocket stream length:', streamingContentRef.current.length);
            }
          }
          break;

        case 'message_complete':
          setIsStreaming(false);
          const messagePayload = data.message as Message;
          const messageContent = messagePayload.content ?? '';
          const finalContent = messageContent || streamingContentRef.current;
          setStreamingContent('');
          streamingContentRef.current = '';
          setStreamingToolCalls([]);
          setStreamingToolResults([]);
          setStreamingConversationId(null);
          onMessageComplete?.(
            data.conversation_id as string,
            { ...messagePayload, content: finalContent }
          );
          break;

        case 'tool_call':
          setStreamingToolCalls((prev) => [
            ...(prev ?? []),
            data.tool_call as NonNullable<Message['tool_calls']>[number],
          ]);
          break;

        case 'tool_result':
          setStreamingToolResults((prev) => [
            ...(prev ?? []),
            data.tool_result as NonNullable<Message['tool_results']>[number],
          ]);
          break;

        case 'error':
          {
            const rawError = data.error;
            if (
              rawError &&
              typeof rawError === 'object' &&
              !Array.isArray(rawError) &&
              Object.keys(rawError as Record<string, unknown>).length === 0
            ) {
              break;
            }
            const errorMessage = typeof rawError === 'string'
              ? rawError.trim()
              : rawError
                ? JSON.stringify(rawError)
                : '';
            if (!errorMessage || errorMessage === '{}' || errorMessage === '[object Object]') {
              break;
            }
            setError(errorMessage);
            onError?.(errorMessage);
          }
          setIsStreaming(false);
          break;

        case 'pong':
          // Keepalive response, no action needed
          lastPongAtRef.current = Date.now();
          break;

        default:
          console.log('Unknown WebSocket message type:', data.type);
      }
    } catch (e) {
      console.error('Failed to parse WebSocket message:', e);
    }
  }, [onConnected, onConversationCreated, onMessageComplete, onError]);

  // Connect to WebSocket
  const connect = useCallback(() => {
    // Don't connect if not mounted (React Strict Mode double-mount protection)
    if (!isMountedRef.current) {
      return;
    }

    if (wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Also check for CONNECTING state to prevent duplicate connections
    if (wsRef.current?.readyState === WebSocket.CONNECTING) {
      return;
    }

    const token = localStorage.getItem('access_token');
    if (!token) {
      setError('No access token available');
      return;
    }

    isIntentionalCloseRef.current = false;
    setIsConnecting(true);
    setError(null);

    const wsUrl = `${getWebSocketUrl()}?token=${encodeURIComponent(token)}`;

    try {
      const ws = new WebSocket(wsUrl);

      // IMPORTANT: Attach error handler IMMEDIATELY after construction
      // to prevent Next.js dev overlay from catching unhandled WebSocket errors
      ws.onerror = (event) => {
        // Suppress errors entirely during cleanup (Strict Mode unmount)
        // This prevents "WebSocket is closed before connection is established" errors
        if (isCleaningUpRef.current) {
          return;
        }

        // Only process errors if component is still mounted
        if (isMountedRef.current) {
          const isTransient =
            ws.readyState === WebSocket.CONNECTING ||
            ws.readyState === WebSocket.CLOSING;
          if (isTransient) {
            return;
          }
          if (ws.readyState !== WebSocket.OPEN) {
            return;
          }

          if (
            process.env.NODE_ENV === 'development' &&
            process.env.NEXT_PUBLIC_WS_DEBUG === 'true'
          ) {
            console.debug('WebSocket error event:', event);
          }

          // Use console.warn instead of console.error to avoid Next.js error overlay
          // in development for expected WebSocket lifecycle events
          if (process.env.NODE_ENV === 'development') {
            console.warn('WebSocket connection error (this may be expected during navigation)');
          } else {
            console.error('WebSocket connection error');
          }
          // Provide more helpful error message
          const errorMsg = 'WebSocket connection error';
          setError(errorMsg);
          onError?.(errorMsg);
        }
      };

      wsRef.current = ws;
      lastPongAtRef.current = Date.now();
      connectTimeoutRef.current = setTimeout(() => {
        if (ws.readyState !== WebSocket.OPEN) {
          try {
            ws.close(4000, 'Connect timeout');
          } catch {
            // Ignore close errors during timeout handling
          }
        }
      }, 8000);

      ws.onopen = () => {
        // Check if still mounted before updating state
        if (!isMountedRef.current) {
          ws.close(1000, 'Component unmounted');
          return;
        }
        console.log('WebSocket connected');
        if (connectTimeoutRef.current) {
          clearTimeout(connectTimeoutRef.current);
          connectTimeoutRef.current = null;
        }
        lastPongAtRef.current = Date.now();
        // Start ping interval to keep connection alive
        pingIntervalRef.current = setInterval(() => {
          const now = Date.now();
          if (now - lastPongAtRef.current > 45000) {
            try {
              ws.close(4001, 'Pong timeout');
            } catch {
              // Ignore close errors during pong timeout handling
            }
            return;
          }
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          }
        }, 30000);
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        // Skip all processing if we're cleaning up (Strict Mode unmount)
        if (isCleaningUpRef.current) {
          return;
        }

        // Only log if still mounted (Strict Mode can cause benign close events)
        if (isMountedRef.current) {
          console.log('WebSocket closed:', event.code, event.reason);
        }
        setIsConnected(false);
        setIsConnecting(false);
        cleanup();

        // Only call onDisconnected if still mounted
        if (isMountedRef.current) {
          onDisconnected?.();
        }

        // Don't attempt reconnection if intentionally closed or unmounted
        if (isIntentionalCloseRef.current || !isMountedRef.current) {
          return;
        }

        // Attempt reconnection if not intentionally closed
        if (event.code !== 1000 && reconnectAttemptsRef.current < reconnectAttempts) {
          reconnectAttemptsRef.current++;
          const baseDelay = reconnectDelay * (2 ** (reconnectAttemptsRef.current - 1));
          const jitter = Math.floor(Math.random() * reconnectDelay);
          const delay = Math.min(baseDelay + jitter, 30000);
          console.log(`Reconnecting... attempt ${reconnectAttemptsRef.current}/${reconnectAttempts} in ${delay}ms`);
          reconnectTimeoutRef.current = setTimeout(connect, delay);
        }
      };
    } catch (e) {
      console.error('Failed to create WebSocket:', e);
      if (isMountedRef.current) {
        setIsConnecting(false);
        setError('Failed to create WebSocket connection');
      }
    }
  }, [handleMessage, onDisconnected, reconnectAttempts, reconnectDelay, cleanup]);

  // Disconnect from WebSocket
  const disconnect = useCallback(() => {
    isIntentionalCloseRef.current = true;
    cleanup();
    reconnectAttemptsRef.current = reconnectAttempts; // Prevent auto-reconnect
    if (wsRef.current) {
      wsRef.current.close(1000, 'Client disconnect');
      wsRef.current = null;
    }
    setIsConnected(false);
  }, [cleanup, reconnectAttempts]);

  // Send a chat message
  const sendMessage = useCallback((
    conversationId: string,
    message: string,
    chatOptions: ChatOptions = {}
  ) => {
    console.log('[useWebSocketChat] sendMessage called:', {
      conversationId,
      messagePreview: message.substring(0, 100),
      wsReadyState: wsRef.current?.readyState,
      chatOptions,
    });

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      console.error('[useWebSocketChat] WebSocket not connected, readyState:', wsRef.current?.readyState);
      setError('WebSocket not connected');
      return;
    }

    const payload = {
      type: 'chat',
      conversation_id: conversationId,
      message,
      temperature: chatOptions.temperature ?? 0.7,
      max_tokens: chatOptions.max_tokens ?? 4096,
      use_mcp: chatOptions.use_mcp,
      model_name: chatOptions.model_name,
      mcp_servers: chatOptions.mcp_servers ?? [],
    };

    console.log('[useWebSocketChat] Sending payload:', payload);
    wsRef.current.send(JSON.stringify(payload));
    console.log('[useWebSocketChat] Message sent successfully');
  }, []);

  // Create a new conversation
  const createConversation = useCallback((
    title?: string,
    modelProvider?: string,
    modelName?: string
  ) => {
    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      setError('WebSocket not connected');
      return;
    }

    wsRef.current.send(JSON.stringify({
      type: 'new_conversation',
      title: title || 'New Conversation',
      model_provider: modelProvider,
      model_name: modelName,
    }));
  }, []);

  // Track mounted state for React Strict Mode
  useEffect(() => {
    isMountedRef.current = true;
    // Reset refs on mount (important for Strict Mode remount)
    isIntentionalCloseRef.current = false;
    isCleaningUpRef.current = false;
    reconnectAttemptsRef.current = 0;

    return () => {
      // Set cleaning up FIRST to suppress any in-flight error handlers
      // This MUST happen before any WebSocket operations
      isCleaningUpRef.current = true;
      isMountedRef.current = false;
      isIntentionalCloseRef.current = true;
      cleanup();

      if (wsRef.current) {
        const ws = wsRef.current;
        wsRef.current = null;

        // Replace all handlers with no-ops IMMEDIATELY to prevent any callbacks
        // This is crucial for React Strict Mode where unmount happens quickly
        const noOp = () => {};
        ws.onopen = noOp;
        ws.onclose = noOp;
        ws.onerror = noOp;
        ws.onmessage = noOp;

        // Now safely close based on state
        if (ws.readyState === WebSocket.OPEN) {
          ws.close(1000, 'Component unmount');
        } else if (ws.readyState === WebSocket.CONNECTING) {
          // For CONNECTING state, the close will happen when it transitions
          // to OPEN (handled by onopen no-op above) or errors out (handled by onerror no-op)
          // We can still call close() - it will close when ready
          try {
            ws.close(1000, 'Component unmount');
          } catch {
            // Ignore any errors during cleanup close
          }
        }
      }
    };
  }, [cleanup]);

  // Reset connecting state when wsRef becomes null (connection was closed)
  // This handles the case where Strict Mode closes the connection during unmount
  useEffect(() => {
    if (wsRef.current === null && isConnecting) {
      setIsConnecting(false);
    }
  });

  return {
    isConnected,
    isConnecting,
    isStreaming,
    streamingContent,
    streamingConversationId,
    streamingToolCalls,
    streamingToolResults,
    error,
    connect,
    disconnect,
    sendMessage,
    createConversation,
  };
}
