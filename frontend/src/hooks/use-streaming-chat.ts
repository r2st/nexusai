'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import { TenantContext } from '@/lib/api';
import { sanitizeChatContent, detectPromptInjection } from '@/lib/security';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface StreamingMessage {
  id: string;
  role: 'user' | 'assistant' | 'system' | 'tool';
  content: string;
  isStreaming: boolean;
  model_name?: string;
  created_at: string;
  metadata?: MessageMetadata;
  toolEvents?: ToolEvent[];
}

export interface MessageMetadata {
  model_provider?: string;
  tokens_used?: number;
  latency_ms?: number;
  time_to_first_token_ms?: number;
}

export interface ToolEvent {
  tool_name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  input?: Record<string, unknown>;
  output?: Record<string, unknown>;
  error?: string;
  started_at: string;
  completed_at?: string;
}

export interface UseStreamingChatOptions {
  conversationId?: string;
  apiBaseUrl?: string;
  onError?: (error: Error) => void;
  onComplete?: (message: StreamingMessage) => void;
  onToolEvent?: (event: ToolEvent) => void;
  maxRetries?: number;
}

export interface UseStreamingChatReturn {
  messages: StreamingMessage[];
  isStreaming: boolean;
  isLoading: boolean;
  streamingContent: string;
  timeToFirstToken: number | null;
  error: Error | null;
  sendMessage: (content: string, options?: SendMessageOptions) => Promise<void>;
  stopStreaming: () => void;
  clearMessages: () => void;
  addMessage: (message: StreamingMessage) => void;
  setMessages: (messages: StreamingMessage[]) => void;
}

export interface SendMessageOptions {
  temperature?: number;
  max_tokens?: number;
  system_prompt?: string;
  context?: Record<string, unknown>;
}

// -----------------------------------------------------------------------------
// Constants
// -----------------------------------------------------------------------------

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
const DEFAULT_MAX_RETRIES = 3;
const RETRY_DELAY_MS = 1000;

// -----------------------------------------------------------------------------
// Hook Implementation
// -----------------------------------------------------------------------------

export function useStreamingChat(options: UseStreamingChatOptions = {}): UseStreamingChatReturn {
  const {
    conversationId,
    apiBaseUrl = API_BASE_URL,
    onError,
    onComplete,
    onToolEvent,
    maxRetries = DEFAULT_MAX_RETRIES,
  } = options;

  // State
  const [messages, setMessages] = useState<StreamingMessage[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [timeToFirstToken, setTimeToFirstToken] = useState<number | null>(null);
  const [error, setError] = useState<Error | null>(null);

  // Refs for cleanup and streaming control
  const abortControllerRef = useRef<AbortController | null>(null);
  const streamingStartTimeRef = useRef<number | null>(null);
  const receivedFirstTokenRef = useRef(false);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      abortControllerRef.current?.abort();
    };
  }, []);

  // Add a message to the list
  const addMessage = useCallback((message: StreamingMessage) => {
    setMessages(prev => [...prev, message]);
  }, []);

  // Clear all messages
  const clearMessages = useCallback(() => {
    setMessages([]);
    setStreamingContent('');
    setError(null);
  }, []);

  // Stop active streaming
  const stopStreaming = useCallback(() => {
    abortControllerRef.current?.abort();
    setIsStreaming(false);
    setIsLoading(false);
  }, []);

  // Send a message and handle streaming response
  const sendMessage = useCallback(async (
    content: string,
    sendOptions: SendMessageOptions = {}
  ) => {
    if (!conversationId) {
      const err = new Error('No conversation ID provided');
      setError(err);
      onError?.(err);
      return;
    }

    // Sanitize and validate input
    const sanitizedContent = sanitizeChatContent(content);
    const injectionCheck = detectPromptInjection(sanitizedContent);

    if (injectionCheck.detected && injectionCheck.severity === 'high') {
      const err = new Error('Potentially unsafe content detected');
      setError(err);
      onError?.(err);
      return;
    }

    // Cancel any existing stream
    abortControllerRef.current?.abort();
    abortControllerRef.current = new AbortController();

    // Reset state
    setIsLoading(true);
    setIsStreaming(false);
    setStreamingContent('');
    setTimeToFirstToken(null);
    setError(null);
    receivedFirstTokenRef.current = false;
    streamingStartTimeRef.current = Date.now();

    // Add user message immediately
    const userMessage: StreamingMessage = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: sanitizedContent,
      isStreaming: false,
      created_at: new Date().toISOString(),
    };
    addMessage(userMessage);

    // Prepare request
    const token = typeof window !== 'undefined' ? localStorage.getItem('access_token') : null;
    const tenantId = TenantContext.getCurrentTenantId();

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
    };

    if (token) {
      headers['Authorization'] = `Bearer ${token}`;
    }

    if (tenantId) {
      headers['X-Tenant-ID'] = tenantId;
    }

    const body = JSON.stringify({
      message: sanitizedContent,
      temperature: sendOptions.temperature ?? 0.7,
      max_tokens: sendOptions.max_tokens ?? 4096,
      stream: true,
      ...(sendOptions.system_prompt && { system_prompt: sendOptions.system_prompt }),
      ...(sendOptions.context && { context: sendOptions.context }),
    });

    let retryCount = 0;
    let lastError: Error | null = null;

    while (retryCount <= maxRetries) {
      try {
        const response = await fetch(
          `${apiBaseUrl}/chat/conversations/${conversationId}/chat`,
          {
            method: 'POST',
            headers,
            body,
            signal: abortControllerRef.current.signal,
          }
        );

        if (!response.ok) {
          if (response.status === 401) {
            throw new Error('Authentication required');
          }
          if (response.status === 429) {
            throw new Error('Rate limit exceeded. Please try again later.');
          }
          if (response.status >= 500 && retryCount < maxRetries) {
            retryCount++;
            await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS * retryCount));
            continue;
          }
          throw new Error(`Server error: ${response.status}`);
        }

        const reader = response.body?.getReader();
        if (!reader) {
          throw new Error('No response body');
        }

        setIsLoading(false);
        setIsStreaming(true);

        const decoder = new TextDecoder();
        let accumulatedContent = '';
        let currentToolEvents: ToolEvent[] = [];

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }

          const chunk = decoder.decode(value, { stream: true });
          const lines = chunk.split('\n');

          for (const line of lines) {
            if (!line.trim()) continue;

            if (line.startsWith('data: ')) {
              const data = line.slice(6);

              if (data === '[DONE]') {
                break;
              }

              try {
                const parsed = JSON.parse(data);

                // Handle different event types
                if (parsed.type === 'token' || parsed.content) {
                  const tokenContent = parsed.content || parsed.token || data;

                  // Track time to first token
                  if (!receivedFirstTokenRef.current && streamingStartTimeRef.current) {
                    receivedFirstTokenRef.current = true;
                    const ttft = Date.now() - streamingStartTimeRef.current;
                    setTimeToFirstToken(ttft);
                  }

                  accumulatedContent += tokenContent;
                  setStreamingContent(accumulatedContent);
                } else if (parsed.type === 'tool_start' || parsed.type === 'tool_end') {
                  const toolEvent: ToolEvent = {
                    tool_name: parsed.tool_name,
                    status: parsed.type === 'tool_start' ? 'running' : (parsed.error ? 'failed' : 'completed'),
                    input: parsed.input,
                    output: parsed.output,
                    error: parsed.error,
                    started_at: parsed.started_at || new Date().toISOString(),
                    completed_at: parsed.type === 'tool_end' ? new Date().toISOString() : undefined,
                  };
                  currentToolEvents.push(toolEvent);
                  onToolEvent?.(toolEvent);
                } else if (parsed.type === 'error') {
                  throw new Error(parsed.message || 'Stream error');
                }
              } catch (parseError) {
                // If not JSON, treat as raw token
                if (!receivedFirstTokenRef.current && streamingStartTimeRef.current) {
                  receivedFirstTokenRef.current = true;
                  const ttft = Date.now() - streamingStartTimeRef.current;
                  setTimeToFirstToken(ttft);
                }

                accumulatedContent += data;
                setStreamingContent(accumulatedContent);
              }
            }
          }
        }

        // Create final assistant message
        const assistantMessage: StreamingMessage = {
          id: `assistant-${Date.now()}`,
          role: 'assistant',
          content: accumulatedContent,
          isStreaming: false,
          created_at: new Date().toISOString(),
          metadata: {
            time_to_first_token_ms: timeToFirstToken ?? undefined,
            latency_ms: streamingStartTimeRef.current
              ? Date.now() - streamingStartTimeRef.current
              : undefined,
          },
          toolEvents: currentToolEvents.length > 0 ? currentToolEvents : undefined,
        };

        addMessage(assistantMessage);
        setStreamingContent('');
        setIsStreaming(false);
        onComplete?.(assistantMessage);

        return; // Success, exit retry loop

      } catch (err) {
        lastError = err instanceof Error ? err : new Error(String(err));

        if (err instanceof Error && err.name === 'AbortError') {
          // User cancelled, don't retry
          setIsLoading(false);
          setIsStreaming(false);
          return;
        }

        // Network errors might be retryable
        if (retryCount < maxRetries) {
          retryCount++;
          await new Promise(resolve => setTimeout(resolve, RETRY_DELAY_MS * retryCount));
          continue;
        }
      }
    }

    // All retries exhausted
    setIsLoading(false);
    setIsStreaming(false);
    setError(lastError);
    onError?.(lastError || new Error('Unknown error'));
  }, [conversationId, apiBaseUrl, maxRetries, addMessage, onError, onComplete, onToolEvent, timeToFirstToken]);

  return {
    messages,
    isStreaming,
    isLoading,
    streamingContent,
    timeToFirstToken,
    error,
    sendMessage,
    stopStreaming,
    clearMessages,
    addMessage,
    setMessages,
  };
}

export default useStreamingChat;
