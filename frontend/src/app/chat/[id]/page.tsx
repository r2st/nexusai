'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChatSidebar } from '@/components/chat/sidebar';
import { ChatMessage } from '@/components/chat/message';
import { StatusRail } from '@/components/chat/status-rail';
import { ChatInput } from '@/components/chat/input';
import { ModelSelector, type AIModel, models as MODEL_CATALOG } from '@/components/chat/model-selector';
import { chatApi } from '@/lib/api';
import { useAuthStore, useAuthHydrated } from '@/store/auth';
import { useChatStore } from '@/store/chat';
import { useWebSocketChat } from '@/hooks/use-websocket-chat';

// Helper to get provider from model name
function getProviderForModel(modelName: string): string {
  const model = MODEL_CATALOG.find(m => m.id === modelName || m.name === modelName);
  return model?.provider || 'google';
}

export default function ChatConversationPage() {
  const router = useRouter();
  const params = useParams();
  const conversationId = params.id as string;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const hasHydrated = useAuthHydrated();
  const [useMcpTools, setUseMcpTools] = useState(true);
  const messagesContainerRef = useRef<HTMLDivElement>(null);

  const {
    conversations,
    setConversations,
    currentConversation,
    setCurrentConversation,
    messages,
    setMessages,
    addMessage,
    isLoading,
    isStreaming,
    streamingContent,
    setIsLoading,
    setIsStreaming,
    setStreamingContent,
    clearStreamingContent,
    selectedModel,
    setSelectedModel,
  } = useChatStore();

  // Handle model selection
  const handleModelSelect = useCallback((model: AIModel) => {
    setSelectedModel(model.id);
  }, [setSelectedModel]);

  // WebSocket chat hook
  const {
    isConnected,
    isConnecting,
    isStreaming: wsIsStreaming,
    streamingContent: wsStreamingContent,
    streamingConversationId,
    streamingToolCalls,
    streamingToolResults,
    error: wsError,
    connect,
    disconnect,
    sendMessage: wsSendMessage,
  } = useWebSocketChat({
    onConnected: (userId) => {
      console.log('WebSocket connected for user:', userId);
    },
    onDisconnected: () => {
      console.log('WebSocket disconnected');
    },
    onError: (error) => {
      const normalizedError = String(error).trim();
      if (!normalizedError || normalizedError === '{}' || normalizedError === '[object Object]') {
        return;
      }
      toast.error(`Chat error: ${normalizedError}`);
    },
    onMessageComplete: (convId, message) => {
      // Don't add the message here - the query invalidation below will fetch it from the server
      // This prevents duplicate messages when WebSocket and DB generate different IDs
      setIsLoading(false);
      setIsStreaming(false);
      clearStreamingContent();
      // Refresh messages to sync with server - this will add the message with the correct DB ID
      queryClient.invalidateQueries({ queryKey: ['messages', convId] });
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
    },
  });

  // Sync WebSocket streaming state to store
  useEffect(() => {
    if (wsIsStreaming && streamingConversationId === conversationId) {
      setIsStreaming(true);
      setStreamingContent(wsStreamingContent);
    }
  }, [wsIsStreaming, wsStreamingContent, streamingConversationId, conversationId, setIsStreaming, setStreamingContent]);

  // Redirect if not authenticated (wait for hydration first)
  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Connect WebSocket when authenticated
  // Use a ref to track if this is the "stable" mount (survived Strict Mode's unmount)
  const hasStabilizedRef = useRef(false);

  useEffect(() => {
    hasStabilizedRef.current = false;

    // In development, wait for Strict Mode cycle to complete before allowing connections
    // Strict Mode unmount/remount happens synchronously, so a small delay ensures stability
    const stabilizeTimeout = setTimeout(() => {
      hasStabilizedRef.current = true;
    }, 50);

    return () => {
      clearTimeout(stabilizeTimeout);
      hasStabilizedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!isAuthenticated || isConnected || isConnecting) {
      return;
    }

    // Wait for component to stabilize (survive Strict Mode) before connecting
    const connectTimeout = setTimeout(() => {
      if (hasStabilizedRef.current) {
        connect();
      }
    }, 100);

    return () => {
      clearTimeout(connectTimeout);
    };
  }, [isAuthenticated, isConnected, isConnecting, connect]);

  // Show WebSocket errors
  useEffect(() => {
    if (wsError) {
      const normalizedError = String(wsError).trim();
      if (!normalizedError) {
        return;
      }

      if (normalizedError === '{}' || normalizedError === '[object Object]') {
        return;
      }

      const isTransient =
        normalizedError.includes('WebSocket is closed before the connection is established') ||
        normalizedError.includes('Component unmount');

      if (isTransient && process.env.NODE_ENV === 'development') {
        return;
      }

      if (process.env.NODE_ENV === 'development') {
        console.warn('WebSocket error:', wsError);
      } else {
        console.error('WebSocket error:', wsError);
      }
    }
  }, [wsError]);

  // Fetch conversations
  const { data: conversationsData } = useQuery({
    queryKey: ['conversations'],
    queryFn: () => chatApi.listConversations(),
    enabled: isAuthenticated,
  });

  useEffect(() => {
    if (conversationsData) {
      setConversations(conversationsData);
    }
  }, [conversationsData, setConversations]);

  // Fetch current conversation
  const { data: conversationData } = useQuery({
    queryKey: ['conversation', conversationId],
    queryFn: () => chatApi.getConversation(conversationId),
    enabled: isAuthenticated && !!conversationId,
  });

  useEffect(() => {
    if (conversationData) {
      setCurrentConversation(conversationData);
    }
  }, [conversationData, setCurrentConversation]);

  // Fetch messages
  const { data: messagesData } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => chatApi.getMessages(conversationId),
    enabled: isAuthenticated && !!conversationId,
  });

  useEffect(() => {
    if (messagesData) {
      setMessages(messagesData);
    }
  }, [messagesData, setMessages]);

  // Scroll to bottom when messages change or on initial load
  const scrollToBottom = useCallback((smooth = true) => {
    const container = messagesContainerRef.current;
    if (container) {
      if (smooth) {
        container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
      } else {
        container.scrollTop = container.scrollHeight;
      }
    }
  }, []);

  // Scroll to bottom when messages load - use instant scroll on initial load
  useEffect(() => {
    if (messages.length > 0) {
      // Use requestAnimationFrame to ensure DOM has updated
      requestAnimationFrame(() => {
        scrollToBottom(false); // Instant scroll on load
      });
    }
  }, [messages.length, scrollToBottom]);

  // Create conversation mutation
  const createMutation = useMutation({
    mutationFn: chatApi.createConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setCurrentConversation(conversation);
      setMessages([]);
      router.push(`/chat/${conversation.id}`);
    },
    onError: () => {
      toast.error('Failed to create conversation');
    },
  });

  // Delete conversation mutation
  const deleteMutation = useMutation({
    mutationFn: chatApi.deleteConversation,
    onSuccess: (_, deletedId) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (conversationId === deletedId) {
        router.push('/chat');
      }
      toast.success('Conversation deleted');
    },
    onError: () => {
      toast.error('Failed to delete conversation');
    },
  });

  const handleNewChat = useCallback(() => {
    const provider = getProviderForModel(selectedModel);
    createMutation.mutate({ model_provider: provider, model_name: selectedModel });
  }, [createMutation, selectedModel]);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      deleteMutation.mutate(id);
    },
    [deleteMutation]
  );

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!currentConversation) return;

      // Add user message immediately for instant feedback
      addMessage({
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message,
        model_name: null,
        created_at: new Date().toISOString(),
      });

      setIsLoading(true);
      clearStreamingContent();

      // Use WebSocket if connected, otherwise fall back to HTTP
      if (isConnected) {
        wsSendMessage(currentConversation.id, message, { use_mcp: useMcpTools, model_name: selectedModel });
      } else {
        // Fallback to HTTP streaming
        try {
          setIsStreaming(true);
          const response = await chatApi.sendMessage(currentConversation.id, message, {
            stream: true,
            use_mcp: useMcpTools,
          });

          if (response instanceof Response) {
            const reader = response.body?.getReader();
            const decoder = new TextDecoder();
            let fullContent = '';

            if (reader) {
              while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n');

                for (const line of lines) {
                  if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                      break;
                    }
                    fullContent += data;
                    useChatStore.getState().appendStreamingContent(data);
                  }
                }
              }
            }

            // Add the complete assistant message
            addMessage({
              id: `assistant-${Date.now()}`,
              role: 'assistant',
              content: fullContent,
              model_name: currentConversation.model_name,
              created_at: new Date().toISOString(),
            });
          }
        } catch (error) {
          toast.error('Failed to send message');
          console.error(error);
        } finally {
          setIsLoading(false);
          setIsStreaming(false);
          clearStreamingContent();
          queryClient.invalidateQueries({ queryKey: ['messages', conversationId] });
        }
      }
    },
    [
      currentConversation,
      conversationId,
      addMessage,
      setIsLoading,
      setIsStreaming,
      setStreamingContent,
      clearStreamingContent,
      isConnected,
      useMcpTools,
      selectedModel,
      wsSendMessage,
      queryClient,
    ]
  );

  if (!isAuthenticated) {
    return null;
  }

  // Get current streaming content
  const displayStreamingContent = wsIsStreaming && streamingConversationId === conversationId
    ? wsStreamingContent
    : streamingContent;

  const isCurrentlyStreaming = (wsIsStreaming && streamingConversationId === conversationId) || isStreaming;

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentId={conversationId}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col" role="main" aria-label="Chat area">
        {/* Header with model selector */}
        <div className="flex h-14 items-center justify-between border-b px-4">
          {/* Left side: Model Selector */}
          <div className="flex items-center gap-3">
            <ModelSelector
              selectedModel={selectedModel}
              onSelectModel={handleModelSelect}
              compact
            />
            {currentConversation && (
              <span className="text-sm text-muted-foreground truncate max-w-[200px]">
                {currentConversation.title}
              </span>
            )}
          </div>

          {/* Right side: Connection Status */}
          <div className="flex items-center gap-2">
            <div
              className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500' : 'bg-red-500'
              }`}
              title={isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
            />
            <span className="text-xs text-muted-foreground">
              {isConnected ? 'Live' : isConnecting ? 'Connecting...' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto" aria-live="polite" aria-atomic="false">
          <StatusRail status={isCurrentlyStreaming ? 'responding' : 'idle'} />
          {messages.length === 0 && !isCurrentlyStreaming ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <h2 className="text-2xl font-semibold">Start the conversation</h2>
                <p className="mt-2 text-muted-foreground">
                  Send a message to begin
                </p>
              </div>
            </div>
          ) : (
            <div className="mx-auto max-w-3xl" data-message-list>
              {messages.map((msg) => (
                <ChatMessage
                  key={msg.id}
                  role={msg.role}
                  content={msg.content}
                  tools={[
                    ...(msg.tool_calls?.map((tool) => ({
                      type: 'tool_call' as const,
                      name: tool.name,
                      args: tool.args,
                      status: tool.status,
                      id: tool.id,
                    })) ?? []),
                    ...(msg.tool_results?.map((tool) => ({
                      type: 'tool_result' as const,
                      name: tool.name,
                      output: tool.output,
                      success: tool.success,
                      id: tool.id,
                    })) ?? []),
                  ]}
                />
              ))}
              {/* Only show streaming message if content is not already in messages list
                  This prevents duplicates during the race condition when message_complete
                  triggers query invalidation while streaming state is still clearing */}
              {isCurrentlyStreaming && displayStreamingContent && !messages.some(
                (m) => m.role === 'assistant' && m.content === displayStreamingContent
              ) && (
                <ChatMessage
                  role="assistant"
                  content={displayStreamingContent}
                  isStreaming
                  tools={[
                    ...(streamingToolCalls?.map((tool) => ({
                      type: 'tool_call' as const,
                      name: tool.name,
                      args: tool.args,
                      status: tool.status,
                      id: tool.id,
                    })) ?? []),
                    ...(streamingToolResults?.map((tool) => ({
                      type: 'tool_result' as const,
                      name: tool.name,
                      output: tool.output,
                      success: tool.success,
                      id: tool.id,
                    })) ?? []),
                  ]}
                />
              )}
            </div>
          )}
        </div>

        {/* Loading indicator for screen readers */}
        {isLoading && (
          <div className="sr-only" aria-live="assertive" aria-busy="true">
            Loading response...
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSendMessage}
          isLoading={isLoading}
          toolsEnabled={useMcpTools}
          onToggleTools={setUseMcpTools}
        />
      </main>
    </div>
  );
}
