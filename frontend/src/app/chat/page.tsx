'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChatSidebar } from '@/components/chat/sidebar';
import { ChatMessage } from '@/components/chat/message';
import { StatusRail } from '@/components/chat/status-rail';
import { ChatInput } from '@/components/chat/input';
import { ModelSelector, type AIModel, models as MODEL_CATALOG } from '@/components/chat/model-selector';
import { chatApi, type Conversation } from '@/lib/api';
import { useAuthStore, useAuthHydrated } from '@/store/auth';
import { useChatStore } from '@/store/chat';

// Helper to get provider from model name
function getProviderForModel(modelName: string): string {
  const model = MODEL_CATALOG.find(m => m.id === modelName || m.name === modelName);
  return model?.provider || 'google';
}
import { useWebSocketChat } from '@/hooks/use-websocket-chat';

export default function ChatPage() {
  const router = useRouter();
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
    setIsLoading,
    setIsStreaming,
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
    streamingToolCalls,
    streamingToolResults,
    connect,
    sendMessage: wsSendMessage,
    createConversation: wsCreateConversation,
  } = useWebSocketChat({
    onConnected: (userId) => {
      console.log('WebSocket connected for user:', userId);
    },
    onError: (error) => {
      toast.error(`Chat error: ${error}`);
    },
    onConversationCreated: (conversation) => {
      // Navigate to the new conversation
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setCurrentConversation(conversation);
      setMessages([]);
      router.push(`/chat/${conversation.id}`);
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

  // Redirect if not authenticated (wait for hydration first)
  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Connect WebSocket when authenticated
  // Use a ref to track if this is the "stable" mount (survived Strict Mode's unmount)
  const mountTimeRef = useRef<number>(0);
  const hasStabilizedRef = useRef(false);

  useEffect(() => {
    mountTimeRef.current = Date.now();
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

  // Create conversation mutation (fallback for non-WebSocket)
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (currentConversation) {
        setCurrentConversation(null);
        setMessages([]);
      }
      toast.success('Conversation deleted');
    },
    onError: () => {
      toast.error('Failed to delete conversation');
    },
  });

  const handleNewChat = useCallback(() => {
    const provider = getProviderForModel(selectedModel);
    if (isConnected) {
      wsCreateConversation('New Conversation', provider, selectedModel);
    } else {
      createMutation.mutate({ model_provider: provider, model_name: selectedModel });
    }
  }, [isConnected, wsCreateConversation, createMutation, selectedModel]);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      deleteMutation.mutate(id);
    },
    [deleteMutation]
  );

  const handleSendMessage = useCallback(
    async (message: string) => {
      if (!currentConversation) {
        // Create new conversation first via WebSocket or HTTP
        const provider = getProviderForModel(selectedModel);
        if (isConnected) {
          wsCreateConversation(message.slice(0, 50), provider, selectedModel);
          // The conversation will be created and we'll navigate to it
          // Then we need to send the message - this is handled by the user re-sending
          // For better UX, we could queue the message, but for now keep it simple
        } else {
          const conversation = await chatApi.createConversation({
            title: message.slice(0, 50),
            model_provider: provider,
            model_name: selectedModel,
          });
          setCurrentConversation(conversation);
          queryClient.invalidateQueries({ queryKey: ['conversations'] });
          router.push(`/chat/${conversation.id}`);
          // Message will need to be sent from the conversation page
        }
        return;
      }

      // Add user message immediately for feedback
      addMessage({
        id: `temp-${Date.now()}`,
        role: 'user',
        content: message,
        model_name: null,
        created_at: new Date().toISOString(),
      });

      setIsLoading(true);
      clearStreamingContent();

      if (isConnected) {
        wsSendMessage(currentConversation.id, message, { use_mcp: useMcpTools, model_name: selectedModel });
      } else {
        // Fallback to HTTP
        await sendMessageViaHttp(currentConversation, message, useMcpTools);
      }
    },
    [
      currentConversation,
      isConnected,
      useMcpTools,
      selectedModel,
      wsCreateConversation,
      wsSendMessage,
      addMessage,
      setIsLoading,
      clearStreamingContent,
      setCurrentConversation,
      queryClient,
      router,
    ]
  );

  const sendMessageViaHttp = async (
    conversation: Conversation,
    message: string,
    useMcp: boolean
  ) => {
    setIsStreaming(true);
    try {
      const response = await chatApi.sendMessage(conversation.id, message, {
        stream: true,
        use_mcp: useMcp,
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
          model_name: conversation.model_name,
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
    }
  };

  if (!isAuthenticated) {
    return null;
  }

  const { isStreaming, streamingContent } = useChatStore.getState();
  const displayStreaming = wsIsStreaming || isStreaming;
  const displayContent = wsIsStreaming ? wsStreamingContent : streamingContent;

  return (
    <div className="flex h-screen">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentId={currentConversation?.id}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col" role="main" aria-label="Chat area">
        {/* Header with model selector and connection status */}
        <div className="flex h-14 items-center justify-between border-b px-4">
          {/* Model Selector */}
          <div className="flex items-center gap-3">
            <ModelSelector
              selectedModel={selectedModel}
              onSelectModel={handleModelSelect}
              compact
            />
          </div>

          {/* Connection Status */}
          <div className="flex items-center gap-2" role="status" aria-live="polite">
            <div
              className={`h-2 w-2 rounded-full ${
                isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
              }`}
              aria-hidden="true"
            />
            <span className="text-xs text-muted-foreground">
              {isConnected ? 'Live' : isConnecting ? 'Connecting...' : 'Offline'}
            </span>
          </div>
        </div>

        {/* Messages */}
        <div ref={messagesContainerRef} className="flex-1 overflow-y-auto" aria-live="polite" aria-atomic="false">
          <StatusRail status={displayStreaming ? 'responding' : 'idle'} />
          {messages.length === 0 && !displayStreaming ? (
            <div className="flex h-full items-center justify-center">
              <div className="text-center">
                <h2 className="text-2xl font-semibold">How can I help you today?</h2>
                <p className="mt-2 text-muted-foreground">
                  Start a conversation with AI
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
              {displayStreaming && displayContent && !messages.some(
                (m) => m.role === 'assistant' && m.content === displayContent
              ) && (
                <ChatMessage
                  role="assistant"
                  content={displayContent}
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
        {useChatStore.getState().isLoading && (
          <div className="sr-only" aria-live="assertive" aria-busy="true">
            Loading response...
          </div>
        )}

        {/* Input */}
        <ChatInput
          onSend={handleSendMessage}
          isLoading={useChatStore.getState().isLoading}
          toolsEnabled={useMcpTools}
          onToggleTools={setUseMcpTools}
        />
      </main>
    </div>
  );
}
