import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import type { Conversation, Message } from '@/lib/api';

// Default model - will be overridden by API response
// This is just a fallback if API is unavailable
export const DEFAULT_MODEL = 'gemini-2.0-flash-exp';

interface ChatState {
  conversations: Conversation[];
  currentConversation: Conversation | null;
  messages: Message[];
  isLoading: boolean;
  isStreaming: boolean;
  streamingContent: string;
  selectedModel: string;

  setConversations: (conversations: Conversation[]) => void;
  addConversation: (conversation: Conversation) => void;
  removeConversation: (id: string) => void;
  setCurrentConversation: (conversation: Conversation | null) => void;
  setMessages: (messages: Message[]) => void;
  addMessage: (message: Message) => void;
  setIsLoading: (isLoading: boolean) => void;
  setIsStreaming: (isStreaming: boolean) => void;
  setStreamingContent: (content: string) => void;
  appendStreamingContent: (chunk: string) => void;
  clearStreamingContent: () => void;
  setSelectedModel: (model: string) => void;
}

export const useChatStore = create<ChatState>()(
  persist(
    (set) => ({
  conversations: [],
  currentConversation: null,
  messages: [],
  isLoading: false,
  isStreaming: false,
  streamingContent: '',
  selectedModel: DEFAULT_MODEL,

  setConversations: (conversations) => set({ conversations }),

  addConversation: (conversation) =>
    set((state) => ({
      conversations: [conversation, ...state.conversations],
    })),

  removeConversation: (id) =>
    set((state) => ({
      conversations: state.conversations.filter((c) => c.id !== id),
      currentConversation:
        state.currentConversation?.id === id ? null : state.currentConversation,
    })),

  setCurrentConversation: (conversation) =>
    set({ currentConversation: conversation }),

  setMessages: (messages) =>
    set((state) => {
      // Deduplicate incoming messages by ID and content
      const seenIds = new Set<string>();
      const seenContent = new Map<string, string>(); // "role:content" -> first message id

      const deduplicatedMessages = messages.filter((m) => {
        // Exact ID match - skip duplicate
        if (seenIds.has(m.id)) return false;
        seenIds.add(m.id);

        // For non-empty messages, deduplicate by role+content
        // This handles cases where same message has different IDs
        if (m.content && m.content.length > 0) {
          const contentKey = `${m.role}:${m.content}`;
          if (seenContent.has(contentKey)) {
            return false; // Skip duplicate content
          }
          seenContent.set(contentKey, m.id);
        }

        return true;
      });

      // When setting messages from server, we need to be careful not to lose
      // any optimistically added messages that haven't synced yet
      // Filter out temp messages that have a matching real message
      const tempMessages = state.messages.filter((m) => m.id.startsWith('temp-'));
      const unmatchedTempMessages = tempMessages.filter((temp) =>
        !deduplicatedMessages.some((m) => m.role === temp.role && m.content === temp.content)
      );

      // If there are unmatched temp messages, append them to the end
      if (unmatchedTempMessages.length > 0) {
        return { messages: [...deduplicatedMessages, ...unmatchedTempMessages] };
      }

      return { messages: deduplicatedMessages };
    }),

  addMessage: (message) =>
    set((state) => {
      // Check for duplicates by ID or by role+content
      const isDuplicate = state.messages.some((m) => {
        // Exact ID match
        if (m.id === message.id) return true;
        // Same role and content means duplicate (handles ID mismatches)
        if (m.role === message.role && m.content === message.content && m.content.length > 0) {
          return true;
        }
        return false;
      });

      if (isDuplicate) {
        // If it's a real ID replacing a temp ID, update the temp message
        const tempIndex = state.messages.findIndex(
          (m) => m.id.startsWith('temp-') && m.role === message.role && m.content === message.content
        );
        if (tempIndex !== -1 && !message.id.startsWith('temp-')) {
          const newMessages = [...state.messages];
          newMessages[tempIndex] = message;
          return { messages: newMessages };
        }
        return state; // No change needed - skip duplicate
      }

      return { messages: [...state.messages, message] };
    }),

  setIsLoading: (isLoading) => set({ isLoading }),

  setIsStreaming: (isStreaming) => set({ isStreaming }),

  setStreamingContent: (content) => set({ streamingContent: content }),

  appendStreamingContent: (chunk) =>
    set((state) => ({
      streamingContent: state.streamingContent + chunk,
    })),

  clearStreamingContent: () => set({ streamingContent: '' }),

  setSelectedModel: (model) => set({ selectedModel: model }),
    }),
    {
      name: 'nexusai-chat-storage',
      partialize: (state) => ({ selectedModel: state.selectedModel }),
    }
  )
);
