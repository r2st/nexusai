'use client';

import { useEffect, useCallback, useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { toast } from 'sonner';
import { ChatSidebar } from '@/components/chat/sidebar';
import { ChatUI } from '@/components/chat/assistant-ui';
import { useWebSocketRuntime } from '@/components/chat/assistant-ui/websocket-runtime';
import { chatApi } from '@/lib/api';
import { useAuthStore, useAuthHydrated } from '@/store/auth';
import { useChatStore } from '@/store/chat';

export default function EnhancedChatPage() {
  const router = useRouter();
  const queryClient = useQueryClient();
  const { isAuthenticated } = useAuthStore();
  const hasHydrated = useAuthHydrated();
  const [useMcpTools, setUseMcpTools] = useState(true);

  const {
    conversations,
    setConversations,
    currentConversation,
    setCurrentConversation,
    messages,
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
    conversationId: currentConversation?.id || null,
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
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['conversations'] });
      if (currentConversation) {
        setCurrentConversation(null);
        setMessages([]);
        setRuntimeMessages([]);
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
        currentId={currentConversation?.id}
        onNewChat={handleNewChat}
        onDelete={handleDeleteConversation}
      />

      {/* Main Chat Area */}
      <main className="flex flex-1 flex-col relative" role="main" aria-label="Chat area">
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
      </main>
    </div>
  );
}
