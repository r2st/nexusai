/**
 * Assistant Runtime tests
 * Tests for NexusAI assistant runtime adapter, hooks, and state management
 *
 * Note: @ts-nocheck is used because @assistant-ui/react types are complex
 * and frequently changing. The tests verify runtime behavior correctly.
 */
// @ts-nocheck

import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { renderHook, act, waitFor } from '@testing-library/react';

// Mock the API module
const mockStartSession = vi.fn();
const mockSendMessage = vi.fn();
const mockStartOnboarding = vi.fn();
const mockQuickSetup = vi.fn();

vi.mock('@/lib/api', () => ({
  setupAssistantApi: {
    startSession: () => mockStartSession(),
    sendMessage: (sessionId: string, message: string, isQuickReply: boolean) =>
      mockSendMessage(sessionId, message, isQuickReply),
    startOnboarding: () => mockStartOnboarding(),
    quickSetup: (plugin: string) => mockQuickSetup(plugin),
    getSession: vi.fn(),
    getMessages: vi.fn(),
    cancelSession: vi.fn(),
    deleteSession: vi.fn(),
    listPlugins: vi.fn(),
  },
}));

// Mock @assistant-ui/react
vi.mock('@assistant-ui/react', () => ({
  useLocalRuntime: vi.fn((adapter) => ({
    adapter,
    messages: [],
    send: vi.fn(),
  })),
  AssistantRuntimeProvider: ({ children }: { children: React.ReactNode }) => children,
}));

// Import after mocking
import {
  createNexusChatAdapter,
  subscribeToState,
  getRuntimeState,
  useNexusRuntimeState,
  useQuickReplies,
  useResetAssistant,
  type NexusRuntimeState,
} from '@/lib/assistant-runtime';
import type { ChatModelRunOptions } from '@assistant-ui/react';

// Helper type for mock messages
type MockMessage = {
  role: 'user' | 'assistant';
  content: { type: 'text'; text: string }[];
};

// Helper to create mock run options
function createMockRunOptions(
  messages: MockMessage[],
  abortSignal?: AbortSignal
): ChatModelRunOptions {
  return {
    messages: messages as unknown as ChatModelRunOptions['messages'],
    abortSignal: abortSignal || new AbortController().signal,
  };
}

// Shorthand for single user message
function userMessage(text: string): ChatModelRunOptions {
  return createMockRunOptions([{ role: 'user', content: [{ type: 'text', text }] }]);
}

// Shorthand for conversation with final user message
function conversationWithMessages(...texts: string[]): ChatModelRunOptions {
  const messages: MockMessage[] = [];
  for (let i = 0; i < texts.length; i++) {
    messages.push({
      role: i % 2 === 0 ? 'user' : 'assistant',
      content: [{ type: 'text', text: texts[i] }],
    });
  }
  return createMockRunOptions(messages);
}

describe('Runtime State Management', () => {
  beforeEach(() => {
    vi.clearAllMocks();
    // Reset state by creating a fresh adapter with new config
  });

  describe('getRuntimeState', () => {
    it('returns initial state', () => {
      const state = getRuntimeState();
      expect(state).toHaveProperty('sessionId');
      expect(state).toHaveProperty('currentStep');
      expect(state).toHaveProperty('flowType');
      expect(state).toHaveProperty('isComplete');
      expect(state).toHaveProperty('collectedData');
      expect(state).toHaveProperty('quickReplies');
      expect(state).toHaveProperty('canGoBack');
    });

    it('returns state with correct shape', () => {
      const state = getRuntimeState();
      expect(typeof state.isComplete).toBe('boolean');
      expect(Array.isArray(state.quickReplies)).toBe(true);
      expect(typeof state.collectedData).toBe('object');
    });
  });

  describe('subscribeToState', () => {
    it('calls listener immediately with current state', () => {
      const listener = vi.fn();
      subscribeToState(listener);
      
      expect(listener).toHaveBeenCalledTimes(1);
      expect(listener).toHaveBeenCalledWith(expect.objectContaining({
        quickReplies: expect.any(Array),
      }));
    });

    it('returns unsubscribe function', () => {
      const listener = vi.fn();
      const unsubscribe = subscribeToState(listener);
      
      expect(typeof unsubscribe).toBe('function');
      unsubscribe();
    });
  });
});

describe('createNexusChatAdapter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('creates adapter with run method', () => {
    const adapter = createNexusChatAdapter();
    expect(adapter).toHaveProperty('run');
    expect(typeof adapter.run).toBe('function');
  });

  it('accepts config options', () => {
    const config = {
      flowType: 'connection' as const,
      plugin: 'github',
      onSessionCreated: vi.fn(),
      onFlowComplete: vi.fn(),
      onError: vi.fn(),
    };
    
    const adapter = createNexusChatAdapter(config);
    expect(adapter).toBeDefined();
  });

  describe('adapter.run', () => {
    it('initializes session for first message', async () => {
      mockStartSession.mockResolvedValue({
        session_id: 'session-123',
        current_step: 'welcome',
        message: {
          id: 'msg-1',
          content: 'Welcome to setup!',
          quick_replies: [],
          metadata: {},
        },
      });

      const adapter = createNexusChatAdapter();
      const result = await adapter.run(userMessage('Hello'));

      expect(mockStartSession).toHaveBeenCalled();
      expect(result).toHaveProperty('content');
      expect((result as { content: { type: string }[] }).content[0]).toHaveProperty('type', 'text');
    });

    it('throws error for non-user message', async () => {
      const adapter = createNexusChatAdapter();

      await expect(
        adapter.run(createMockRunOptions([{ role: 'assistant', content: [{ type: 'text', text: 'Response' }] }]))
      ).rejects.toThrow('Expected user message');
    });

    it('handles API errors gracefully', async () => {
      mockStartSession.mockRejectedValue(new Error('Network error'));

      const onError = vi.fn();
      const adapter = createNexusChatAdapter({ onError });

      const result = await adapter.run(userMessage('Hello'));

      expect(onError).toHaveBeenCalledWith(expect.any(Error));
      expect(result.content[0].text).toContain('Error');
    });

    it('creates adapter that can be called', async () => {
      mockStartSession.mockResolvedValue({
        session_id: 'session-456',
        message: {
          id: 'msg-1',
          content: 'Welcome!',
          quick_replies: [],
          metadata: {},
        },
      });

      const adapter = createNexusChatAdapter();
      expect(adapter).toBeDefined();
      expect(adapter.run).toBeDefined();
    });

    it('adapter config accepts flowType', () => {
      const adapter = createNexusChatAdapter({ flowType: 'onboarding' });
      expect(adapter).toBeDefined();
    });

    it('adapter config accepts plugin', () => {
      const adapter = createNexusChatAdapter({ plugin: 'github' });
      expect(adapter).toBeDefined();
    });

    it('adapter config accepts callbacks', () => {
      const config = {
        onSessionCreated: vi.fn(),
        onFlowComplete: vi.fn(),
        onError: vi.fn(),
      };
      const adapter = createNexusChatAdapter(config);
      expect(adapter).toBeDefined();
    });
  });
});

describe('useNexusRuntimeState hook', () => {
  it('returns current runtime state', () => {
    const { result } = renderHook(() => useNexusRuntimeState());
    
    expect(result.current).toHaveProperty('sessionId');
    expect(result.current).toHaveProperty('currentStep');
    expect(result.current).toHaveProperty('flowType');
    expect(result.current).toHaveProperty('isComplete');
    expect(result.current).toHaveProperty('quickReplies');
  });

  it('has correct initial state shape', () => {
    const { result } = renderHook(() => useNexusRuntimeState());
    
    expect(result.current.isComplete).toBe(false);
    expect(result.current.quickReplies).toEqual([]);
    expect(result.current.collectedData).toEqual({});
    expect(result.current.canGoBack).toBe(false);
  });
});

describe('useQuickReplies hook', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('returns quickReplies array', () => {
    const { result } = renderHook(() => useQuickReplies());
    
    expect(result.current).toHaveProperty('quickReplies');
    expect(Array.isArray(result.current.quickReplies)).toBe(true);
  });

  it('returns sendQuickReply function', () => {
    const { result } = renderHook(() => useQuickReplies());
    
    expect(result.current).toHaveProperty('sendQuickReply');
    expect(typeof result.current.sendQuickReply).toBe('function');
  });

  it('returns canGoBack boolean', () => {
    const { result } = renderHook(() => useQuickReplies());
    
    expect(result.current).toHaveProperty('canGoBack');
    expect(typeof result.current.canGoBack).toBe('boolean');
  });
});

describe('useResetAssistant hook', () => {
  it('returns reset function', () => {
    const { result } = renderHook(() => useResetAssistant());
    
    expect(typeof result.current).toBe('function');
  });

  it('reset function clears state', async () => {
    const { result: resetResult } = renderHook(() => useResetAssistant());
    const { result: stateResult } = renderHook(() => useNexusRuntimeState());
    
    await act(async () => {
      await resetResult.current();
    });

    // After reset, state should be cleared
    expect(stateResult.current.sessionId).toBeNull();
    expect(stateResult.current.currentStep).toBeNull();
    expect(stateResult.current.flowType).toBeNull();
    expect(stateResult.current.isComplete).toBe(false);
    expect(stateResult.current.quickReplies).toEqual([]);
  });
});

describe('Quick Reply Detection', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('detects quick reply by exact value match', async () => {
    // First initialize a session with quick replies
    mockStartSession.mockResolvedValue({
      session_id: 'session-qr-detect',
      message: {
        id: 'msg-1',
        content: 'Choose:',
        quick_replies: [
          { id: 'qr-1', label: 'Yes', value: 'yes_confirm' },
          { id: 'qr-2', label: 'No', value: 'no_cancel' },
        ],
        metadata: {},
      },
    });

    mockSendMessage.mockResolvedValue({
      message: {
        id: 'msg-2',
        content: 'Great choice!',
        quick_replies: [],
        metadata: {},
      },
      is_complete: false,
      collected_data: {},
      errors: [],
      can_go_back: true,
    });

    const adapter = createNexusChatAdapter();

    // First call initializes session
    await adapter.run(userMessage('start'));

    // Second call should detect quick reply
    await adapter.run(conversationWithMessages('start', 'Choose:', 'yes_confirm'));

    // sendMessage should have been called with isQuickReply = true
    expect(mockSendMessage).toHaveBeenCalledWith(
      expect.any(String),
      'yes_confirm',
      true
    );
  });
});

describe('Error Handling', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('handles response errors from API', async () => {
    mockStartSession.mockResolvedValue({
      session_id: 'session-err',
      message: {
        id: 'msg-1',
        content: 'Welcome',
        quick_replies: [],
        metadata: {},
      },
    });

    mockSendMessage.mockResolvedValue({
      message: {
        id: 'msg-2',
        content: 'Please try again',
        quick_replies: [],
        metadata: {},
      },
      is_complete: false,
      collected_data: {},
      errors: ['Invalid token format', 'Please provide a valid GitHub token'],
      warnings: [],
      can_go_back: true,
    });

    const adapter = createNexusChatAdapter();

    // Initialize session
    await adapter.run(userMessage('start'));

    // Send invalid data
    const result = await adapter.run(conversationWithMessages('start', 'Welcome', 'invalid-token'));

    expect((result as { content: { text: string }[] }).content[0].text).toContain('Invalid token format');
  });

  it('handles aborted requests', async () => {
    mockStartSession.mockResolvedValue({
      session_id: 'session-abort',
      message: {
        id: 'msg-1',
        content: 'Welcome',
        quick_replies: [],
        metadata: {},
      },
    });

    const controller = new AbortController();
    controller.abort();

    const adapter = createNexusChatAdapter();
    
    // Initialize session first
    await adapter.run({
      messages: [
        { role: 'user', content: [{ type: 'text', text: 'start' }] },
      ],
      abortSignal: new AbortController().signal,
    });

    // Then try with aborted signal
    const result = await adapter.run({
      messages: [
        { role: 'user', content: [{ type: 'text', text: 'start' }] },
        { role: 'assistant', content: [{ type: 'text', text: 'Welcome' }] },
        { role: 'user', content: [{ type: 'text', text: 'continue' }] },
      ],
      abortSignal: controller.signal,
    });

    expect(result.content[0].text).toContain('Error');
  });

  it('handles non-Error exceptions', async () => {
    mockStartSession.mockRejectedValue('String error');
    
    const onError = vi.fn();
    const adapter = createNexusChatAdapter({ onError });
    
    const result = await adapter.run({
      messages: [
        { role: 'user', content: [{ type: 'text', text: 'start' }] },
      ],
      abortSignal: new AbortController().signal,
    });

    // Response should contain error indicator (could be 'Error' or error emoji)
    expect(result.content[0].text).toMatch(/Error|❌|⚠️/);
  });
});

describe('Flow Completion', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('calls onFlowComplete when flow is done', async () => {
    mockStartSession.mockResolvedValue({
      session_id: 'session-complete',
      message: {
        id: 'msg-1',
        content: 'Enter your token:',
        quick_replies: [],
        metadata: {},
      },
    });

    mockSendMessage.mockResolvedValue({
      message: {
        id: 'msg-2',
        content: 'Setup complete!',
        quick_replies: [],
        metadata: {},
      },
      is_complete: true,
      collected_data: {
        github_token: 'ghp_xxx',
        repository: 'owner/repo',
      },
      errors: [],
      can_go_back: false,
    });

    const onFlowComplete = vi.fn();
    const adapter = createNexusChatAdapter({ onFlowComplete });
    
    // Initialize
    await adapter.run({
      messages: [
        { role: 'user', content: [{ type: 'text', text: 'start' }] },
      ],
      abortSignal: new AbortController().signal,
    });

    // Complete the flow
    await adapter.run({
      messages: [
        { role: 'user', content: [{ type: 'text', text: 'start' }] },
        { role: 'assistant', content: [{ type: 'text', text: 'Enter token' }] },
        { role: 'user', content: [{ type: 'text', text: 'ghp_xxx' }] },
      ],
      abortSignal: new AbortController().signal,
    });

    expect(onFlowComplete).toHaveBeenCalledWith({
      github_token: 'ghp_xxx',
      repository: 'owner/repo',
    });
  });
});
