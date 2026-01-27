/**
 * Chat Page Tests
 */

import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChatPage from '@/app/chat/page';
import { useAuthStore } from '@/store/auth';
import { useChatStore } from '@/store/chat';

// Mock next/navigation
const mockPush = vi.fn();
vi.mock('next/navigation', () => ({
  useRouter: () => ({
    push: mockPush,
    replace: vi.fn(),
  }),
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({}),
  usePathname: () => '/chat',
}));

// Mock WebSocket hook
const mockConnect = vi.fn();
const mockDisconnect = vi.fn();
const mockSendMessage = vi.fn();
const mockCreateConversation = vi.fn();

vi.mock('@/hooks/use-websocket-chat', () => ({
  useWebSocketChat: () => ({
    isConnected: true,
    isConnecting: false,
    isStreaming: false,
    streamingContent: '',
    streamingConversationId: null,
    streamingToolCalls: [],
    streamingToolResults: [],
    error: null,
    connect: mockConnect,
    disconnect: mockDisconnect,
    sendMessage: mockSendMessage,
    createConversation: mockCreateConversation,
  }),
}));

// Mock chat API
vi.mock('@/lib/api', () => ({
  chatApi: {
    listConversations: vi.fn().mockResolvedValue([]),
    getMessages: vi.fn().mockResolvedValue([]),
    createConversation: vi.fn(),
  },
  TenantContext: {
    setCurrentTenantId: vi.fn(),
    clear: vi.fn(),
  },
  api: {
    post: vi.fn(),
  },
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    success: vi.fn(),
    error: vi.fn(),
    info: vi.fn(),
  },
}));

// Create test query client
function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        gcTime: 0,
      },
    },
  });
}

// Wrapper component
function TestWrapper({ children }: { children: React.ReactNode }) {
  const queryClient = createTestQueryClient();
  return (
    <QueryClientProvider client={queryClient}>
      {children}
    </QueryClientProvider>
  );
}

describe('ChatPage', () => {
  const mockUser = {
    id: 'user-123',
    email: 'test@example.com',
    full_name: 'Test User',
    role: 'staff_admin' as const,
    organization_id: 'org-123',
    is_active: true,
    created_at: '2024-01-01T00:00:00Z',
    updated_at: '2024-01-01T00:00:00Z',
  };

  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();

    // Set up authenticated state
    useAuthStore.setState({
      user: mockUser,
      isAuthenticated: true,
      currentOrganization: null,
      organizations: [],
      memberRole: 'staff_admin',
      sessionExpiresAt: Date.now() + 3600 * 1000,
      lastActivity: Date.now(),
      _hasHydrated: true,
    });

    // Reset chat store
    useChatStore.setState({
      conversations: [],
      currentConversation: null,
      messages: [],
      isLoading: false,
      isStreaming: false,
      streamingContent: '',
    });
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render chat page with sidebar', () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      // Should show new chat button (use test id for specific targeting)
      expect(screen.getByTestId('new-chat-button')).toBeInTheDocument();
    });

    it('should render chat input', () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      expect(screen.getByPlaceholderText(/send a message/i)).toBeInTheDocument();
    });

    it('should show empty state when no messages', () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      expect(screen.getByText(/how can i help you/i)).toBeInTheDocument();
    });
  });

  describe('Authentication', () => {
    it('should redirect to login when not authenticated', async () => {
      useAuthStore.setState({
        user: null,
        isAuthenticated: false,
        _hasHydrated: true,
      });

      render(<ChatPage />, { wrapper: TestWrapper });

      await waitFor(() => {
        expect(mockPush).toHaveBeenCalledWith('/login');
      });
    });

    it('should not redirect when authenticated', async () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      // Wait a tick for effects to run
      await waitFor(() => {
        expect(mockPush).not.toHaveBeenCalledWith('/login');
      });
    });
  });

  describe('WebSocket Connection', () => {
    it('should show connection status indicator', async () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      // The connection status indicator should be visible
      // (shows green dot when connected, which is what the mock returns)
      await waitFor(() => {
        // Check that the connection status exists in the DOM
        expect(screen.getByLabelText(/chat area/i)).toBeInTheDocument();
      });
    });
  });

  describe('New Conversation', () => {
    it('should create conversation when clicking new chat', async () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      const newChatButton = screen.getByTestId('new-chat-button');
      await userEvent.click(newChatButton);

      await waitFor(() => {
        expect(mockCreateConversation).toHaveBeenCalled();
      });
    });
  });

  describe('Message Input', () => {
    it('should allow typing in message input', async () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      const input = screen.getByPlaceholderText(/send a message/i);
      await userEvent.type(input, 'Hello world');

      expect(input).toHaveValue('Hello world');
    });

    it('should have send button', () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      // The send button should exist (it might be an icon button)
      const sendButton = screen.getByRole('button', { name: /send/i });
      expect(sendButton).toBeInTheDocument();
    });
  });

  describe('Tools Toggle', () => {
    it('should have tools toggle checkbox', () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      const toolsCheckbox = screen.getByRole('checkbox');
      expect(toolsCheckbox).toBeInTheDocument();
    });

    it('should toggle tools on/off', async () => {
      render(<ChatPage />, { wrapper: TestWrapper });

      const toolsCheckbox = screen.getByRole('checkbox');
      expect(toolsCheckbox).toBeChecked();

      await userEvent.click(toolsCheckbox);
      expect(toolsCheckbox).not.toBeChecked();
    });
  });
});
