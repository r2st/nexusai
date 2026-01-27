'use client';

import { useEffect, useCallback, useState, useRef } from 'react';
import { useRouter, useParams } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChatSidebar } from '@/components/chat/sidebar';
import { ChatUI } from '@/components/chat/assistant-ui';
import { useWebSocketRuntime, type Message } from '@/components/chat/assistant-ui/websocket-runtime';
import { chatApi } from '@/lib/api';
import { useAuthStore, useAuthHydrated } from '@/store/auth';
import { useChatStore } from '@/store/chat';

export default function EnhancedChatConversationPage() {
  const router = useRouter();
  const params = useParams();
  const conversationId = params.id as string;
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const hasHydrated = useAuthHydrated();
  const [useMcpTools, setUseMcpTools] = useState(true);

  // Track streaming state to avoid refetch conflicts
  const wasStreamingRef = useRef(false);
  const streamingEndTimeRef = useRef<number>(0);

  const {
    conversations,
    setConversations,
    currentConversation,
    setCurrentConversation,
    setMessages,
    isLoading,
  } = useChatStore();

  // WebSocket runtime
  const {
    isConnected,
    isConnecting,
    isStreaming,
    streamingContent,
    streamingToolCalls,
    streamingToolResults,
    error: wsError,
    messages: runtimeMessages,
    setMessages: setRuntimeMessages,
    sendMessage,
    createConversation: wsCreateConversation,
  } = useWebSocketRuntime({
    conversationId,
    onConversationCreated: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setCurrentConversation(conversation);
      setMessages([]);
      router.push(`/chat/enhanced/${conversation.id}`);
    },
  });

  // Redirect if not authenticated
  useEffect(() => {
    if (hasHydrated && !isAuthenticated) {
      router.push('/login');
    }
  }, [hasHydrated, isAuthenticated, router]);

  // Show WebSocket errors
  useEffect(() => {
    if (wsError) {
      const normalizedError = String(wsError).trim();
      if (normalizedError && normalizedError !== '{}') {
        toast.error(`Connection error: ${normalizedError}`);
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

  // Fetch messages - disabled during streaming to prevent race conditions
  const { data: messagesData } = useQuery({
    queryKey: ['messages', conversationId],
    queryFn: () => chatApi.getMessages(conversationId),
    enabled: isAuthenticated && !!conversationId && !isStreaming,
    // Don't refetch while streaming
    refetchOnWindowFocus: !isStreaming,
  });

  // Track when streaming ends to prevent immediate refetch overwrite
  useEffect(() => {
    if (isStreaming) {
      wasStreamingRef.current = true;
    } else if (wasStreamingRef.current) {
      // Streaming just ended - mark the time
      wasStreamingRef.current = false;
      streamingEndTimeRef.current = Date.now();
    }
  }, [isStreaming]);

  // Sync fetched messages to runtime (only when not streaming and not just after streaming)
  useEffect(() => {
    // Skip sync during streaming to avoid conflicts with optimistic updates
    if (!messagesData || isStreaming) {
      return;
    }

    // Skip sync if streaming just ended (within 2 seconds)
    // This prevents the refetch from overwriting the WebSocket-delivered messages
    const timeSinceStreamEnd = Date.now() - streamingEndTimeRef.current;
    if (streamingEndTimeRef.current > 0 && timeSinceStreamEnd < 2000) {
      return;
    }

    setMessages(messagesData);
    // Convert to the format expected by the runtime
    const converted: Message[] = messagesData.map((msg) => ({
      id: msg.id,
      role: msg.role as 'user' | 'assistant' | 'system',
      content: msg.content,
      created_at: msg.created_at,
      model_name: msg.model_name ?? undefined,
      tool_calls: msg.tool_calls,
      tool_results: msg.tool_results,
    }));
    setRuntimeMessages(converted);
  }, [messagesData, setMessages, setRuntimeMessages, isStreaming]);

  // Create conversation mutation
  const createMutation = useMutation({
    mutationFn: chatApi.createConversation,
    onSuccess: (conversation) => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      setCurrentConversation(conversation);
      setMessages([]);
      setRuntimeMessages([]);
      router.push(`/chat/enhanced/${conversation.id}`);
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
        router.push('/chat/enhanced');
      }
      toast.success('Conversation deleted');
    },
    onError: () => {
      toast.error('Failed to delete conversation');
    },
  });

  const handleNewChat = useCallback(() => {
    if (isConnected) {
      wsCreateConversation('New Conversation');
    } else {
      createMutation.mutate({});
    }
  }, [isConnected, wsCreateConversation, createMutation]);

  const handleDeleteConversation = useCallback(
    (id: string) => {
      deleteMutation.mutate(id);
    },
    [deleteMutation]
  );

  const handleSendMessage = useCallback(
    (message: string) => {
      sendMessage(message, { use_mcp: useMcpTools });
    },
    [sendMessage, useMcpTools]
  );

  if (!isAuthenticated) {
    return null;
  }

  return (
    <div className="flex h-screen bg-background">
      {/* Sidebar */}
      <ChatSidebar
        conversations={conversations}
        currentId={conversationId}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col relative" role="main" aria-label="Chat area">
        {/* Conversation Header */}
        {currentConversation && (
          <div className="flex h-14 items-center border-b px-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 absolute top-0 left-0 right-0 z-10">
            <h1 className="font-medium truncate">
              {currentConversation.title}
            </h1>
            <span className="ml-2 text-xs text-muted-foreground">
              {currentConversation.model_name}
            </span>
          </div>
        )}

        <div className={currentConversation ? 'pt-14 h-full' : 'h-full'}>
          <ChatUI
            messages={runtimeMessages}
            isStreaming={isStreaming}
            streamingContent={streamingContent}
            streamingToolCalls={streamingToolCalls}
            streamingToolResults={streamingToolResults}
            isConnected={isConnected}
            isConnecting={isConnecting}
            isLoading={isLoading}
            toolsEnabled={useMcpTools}
            onSend={handleSendMessage}
            onToggleTools={setUseMcpTools}
            className="h-full"
          />
        </div>
      </main>
    </div>
  );
}
