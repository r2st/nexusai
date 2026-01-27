'use client';

/**
 * WebSocket Runtime for Chat
 *
 * This module provides a WebSocket-based chat runtime that can be used
 * with the enhanced chat UI components.
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { useWebSocketChat } from '@/hooks/use-websocket-chat';
import type { Message, Conversation } from '@/hooks/use-websocket-chat';

export interface WebSocketRuntimeOptions {
  conversationId: string | null;
  onConversationCreated?: (conversation: Conversation) => void;
  onMessageComplete?: (conversationId: string, message: Message) => void;
}

export interface WebSocketRuntimeReturn {
  // Connection state
  isConnected: boolean;
  isConnecting: boolean;
  isStreaming: boolean;
  error: string | null;

  // Streaming state
  streamingContent: string;
  streamingToolCalls: Message['tool_calls'];
  streamingToolResults: Message['tool_results'];
  streamingConversationId: string | null;

  // Messages
  messages: Message[];
  setMessages: (messages: Message[]) => void;

  // Actions
  connect: () => void;
  disconnect: () => void;
  sendMessage: (message: string, options?: { use_mcp?: boolean }) => void;
  createConversation: (title?: string, modelProvider?: string, modelName?: string) => void;
}

export function useWebSocketRuntime(options: WebSocketRuntimeOptions): WebSocketRuntimeReturn {
  const { conversationId, onConversationCreated, onMessageComplete } = options;
  const [messages, setMessagesState] = useState<Message[]>([]);
  const messagesRef = useRef<Message[]>([]);

  const {
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
    sendMessage: wsSendMessage,
    createConversation: wsCreateConversation,
  } = useWebSocketChat({
    onConnected: (userId) => {
      console.log('WebSocket Runtime: Connected for user:', userId);
    },
    onConversationCreated,
    onMessageComplete: (convId, message) => {
      if (convId === conversationId) {
        // Check if this is a user message that we added optimistically
        // If so, replace the optimistic message with the real one
        const optimisticIndex = messagesRef.current.findIndex((m) => {
          // Match optimistic messages by: temp ID pattern + same role + same content
          const isTempId = m.id.startsWith('user-') && m.role === 'user';
          const isSameContent = m.role === message.role && m.content === message.content;
          return isTempId && isSameContent;
        });

        if (optimisticIndex !== -1) {
          // Replace optimistic message with real message from server
          const newMessages = [...messagesRef.current];
          newMessages[optimisticIndex] = message;
          messagesRef.current = newMessages;
          setMessagesState(newMessages);
        } else {
          // Check for exact duplicate (by ID or content+role)
          const isDuplicate = messagesRef.current.some((m) => {
            if (m.id === message.id) return true;
            if (m.role === message.role && m.content === message.content) return true;
            return false;
          });

          if (!isDuplicate) {
            const newMessages = [...messagesRef.current, message];
            messagesRef.current = newMessages;
            setMessagesState(newMessages);
          }
        }
      }
      onMessageComplete?.(convId, message);
    },
    onError: (err) => {
      console.error('WebSocket Runtime: Error:', err);
    },
  });

  // Connect on mount with stabilization for React Strict Mode
  useEffect(() => {
    let mounted = true;
    const timeout = setTimeout(() => {
      if (mounted && !isConnected && !isConnecting) {
        connect();
      }
    }, 100);

    return () => {
      mounted = false;
      clearTimeout(timeout);
    };
  }, [isConnected, isConnecting, connect]);

  const setMessages = useCallback((msgs: Message[]) => {
    messagesRef.current = msgs;
    setMessagesState(msgs);
  }, []);

  const sendMessage = useCallback((message: string, chatOptions?: { use_mcp?: boolean }) => {
    console.log('[WebSocket Runtime] sendMessage called:', {
      conversationId,
      messageLength: message.length,
      isConnected,
      chatOptions,
    });

    if (!conversationId) {
      console.error('[WebSocket Runtime] No conversation ID');
      return;
    }

    // Add user message optimistically
    const userMessage: Message = {
      id: `user-${Date.now()}`,
      role: 'user',
      content: message,
      created_at: new Date().toISOString(),
    };

    const newMessages = [...messagesRef.current, userMessage];
    messagesRef.current = newMessages;
    setMessagesState(newMessages);

    // Send via WebSocket
    if (isConnected) {
      console.log('[WebSocket Runtime] Sending via WebSocket to conversation:', conversationId);
      wsSendMessage(conversationId, message, chatOptions);
    } else {
      console.error('[WebSocket Runtime] WebSocket not connected, message not sent');
    }
  }, [conversationId, isConnected, wsSendMessage]);

  return {
    isConnected,
    isConnecting,
    isStreaming,
    error,
    streamingContent,
    streamingToolCalls,
    streamingToolResults,
    streamingConversationId,
    messages,
    setMessages,
    connect,
    disconnect,
    sendMessage,
    createConversation: wsCreateConversation,
  };
}

export type { Message, Conversation };
