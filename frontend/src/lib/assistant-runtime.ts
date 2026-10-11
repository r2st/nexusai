/**
 * GSTIndia Assistant Runtime Adapter
 *
 * This module creates a custom runtime for assistant-ui that connects
 * to the GSTIndia FastAPI backend's setup chatbot service.
 *
 * MIT License - Compatible with GSTIndia open source license
 */

import {
  type AppendMessage,
  type ThreadMessage,
  type ThreadAssistantMessage,
  type ThreadUserMessage,
  AssistantRuntimeProvider,
  useLocalRuntime,
  type ChatModelAdapter,
  type ChatModelRunOptions,
  type ChatModelRunResult,
} from '@assistant-ui/react';
import { setupAssistantApi, type SetupMessage, type QuickReply } from './api';

// =============================================================================
// TYPES
// =============================================================================

export interface NexusAssistantConfig {
  /** Initial flow type to start */
  flowType?: 'connection' | 'project' | 'pipeline' | 'onboarding';
  /** Plugin to configure (for connection flow) */
  plugin?: string;
  /** Callback when session is created */
  onSessionCreated?: (sessionId: string) => void;
  /** Callback when flow completes */
  onFlowComplete?: (data: Record<string, unknown>) => void;
  /** Callback for errors */
  onError?: (error: Error) => void;
}

export interface NexusRuntimeState {
  sessionId: string | null;
  currentStep: string | null;
  flowType: string | null;
  isComplete: boolean;
  collectedData: Record<string, unknown>;
  quickReplies: QuickReply[];
  canGoBack: boolean;
}

// =============================================================================
// RUNTIME STATE MANAGEMENT
// =============================================================================

let runtimeState: NexusRuntimeState = {
  sessionId: null,
  currentStep: null,
  flowType: null,
  isComplete: false,
  collectedData: {},
  quickReplies: [],
  canGoBack: false,
};

const stateListeners: Set<(state: NexusRuntimeState) => void> = new Set();

function updateState(updates: Partial<NexusRuntimeState>) {
  runtimeState = { ...runtimeState, ...updates };
  stateListeners.forEach(listener => listener(runtimeState));
}

export function subscribeToState(listener: (state: NexusRuntimeState) => void) {
  stateListeners.add(listener);
  listener(runtimeState); // Immediately call with current state
  return () => stateListeners.delete(listener);
}

export function getRuntimeState(): NexusRuntimeState {
  return runtimeState;
}

// =============================================================================
// HELPER FUNCTIONS
// =============================================================================

/**
 * Convert SetupMessage to ThreadMessage format for assistant-ui
 */
function convertToThreadMessage(msg: SetupMessage, index: number): ThreadMessage {
  const baseMessage = {
    id: msg.id || `msg-${index}`,
    createdAt: new Date(msg.timestamp),
  };

  if (msg.role === 'user') {
    return {
      ...baseMessage,
      role: 'user' as const,
      content: [{ type: 'text' as const, text: msg.content }],
      attachments: [],
      metadata: { custom: msg.metadata || {} },
    } as unknown as ThreadUserMessage;
  }

  return {
    ...baseMessage,
    role: 'assistant' as const,
    content: [{ type: 'text' as const, text: msg.content }],
    status: { type: 'complete' as const, reason: 'stop' as const },
    metadata: {
      unstable_annotations: [],
      unstable_data: [],
      steps: [],
      custom: msg.metadata || {},
    },
  } as unknown as ThreadAssistantMessage;
}

/**
 * Format quick replies as suggestions in the message
 */
function formatQuickRepliesText(quickReplies: QuickReply[]): string {
  if (quickReplies.length === 0) return '';

  const suggestions = quickReplies
    .map(qr => `${qr.icon || ''} ${qr.label}`.trim())
    .join(' • ');

  return `\n\n💡 **Quick options:** ${suggestions}`;
}

// =============================================================================
// NEXUS CHAT MODEL ADAPTER
// =============================================================================

/**
 * Creates a ChatModelAdapter for the GSTIndia setup assistant
 */
export function createNexusChatAdapter(config: NexusAssistantConfig = {}): ChatModelAdapter {
  return {
    async run({ messages, abortSignal }: ChatModelRunOptions): Promise<ChatModelRunResult> {
      // Get the last user message
      const lastMessage = messages[messages.length - 1];
      if (lastMessage.role !== 'user') {
        throw new Error('Expected user message');
      }

      const userContent = lastMessage.content
        .filter((c): c is { type: 'text'; text: string } => c.type === 'text')
        .map(c => c.text)
        .join('\n');

      try {
        // Initialize session if needed
        if (!runtimeState.sessionId) {
          let result;

          if (config.flowType === 'onboarding') {
            result = await setupAssistantApi.startOnboarding();
          } else if (config.plugin) {
            result = await setupAssistantApi.quickSetup(config.plugin);
          } else {
            result = await setupAssistantApi.startSession({
              flow_type: config.flowType,
              plugin: config.plugin,
            });
          }

          updateState({
            sessionId: result.session_id,
            currentStep: result.current_step || null,
            flowType: config.flowType || null,
            quickReplies: result.message.quick_replies || [],
          });

          config.onSessionCreated?.(result.session_id);

          // Return the welcome message
          const welcomeContent = result.message.content +
            formatQuickRepliesText(result.message.quick_replies || []);

          return {
            content: [{ type: 'text', text: welcomeContent }],
          };
        }

        // Check for abort signal
        if (abortSignal?.aborted) {
          throw new Error('Request aborted');
        }

        // Check for special commands
        const isQuickReply = runtimeState.quickReplies.some(
          qr => qr.value === userContent || qr.label.toLowerCase() === userContent.toLowerCase()
        );

        // Send message to backend
        const response = await setupAssistantApi.sendMessage(
          runtimeState.sessionId,
          userContent,
          isQuickReply
        );

        // Update state
        updateState({
          currentStep: response.current_step || null,
          isComplete: response.is_complete,
          collectedData: response.collected_data,
          quickReplies: response.message.quick_replies || [],
          canGoBack: response.can_go_back,
        });

        // Handle completion
        if (response.is_complete) {
          config.onFlowComplete?.(response.collected_data);
        }

        // Handle errors
        if (response.errors.length > 0) {
          const errorText = response.errors.join('\n');
          return {
            content: [{ type: 'text', text: `⚠️ ${errorText}\n\n${response.message.content}` }],
          };
        }

        // Format response with quick replies
        const responseContent = response.message.content +
          formatQuickRepliesText(response.message.quick_replies || []);

        return {
          content: [{ type: 'text', text: responseContent }],
        };
      } catch (error) {
        const err = error instanceof Error ? error : new Error(String(error));
        config.onError?.(err);

        return {
          content: [{
            type: 'text',
            text: `❌ **Error:** ${err.message}\n\nPlease try again or type "help" for assistance.`
          }],
        };
      }
    },
  };
}

// =============================================================================
// HOOKS
// =============================================================================

import { useState, useEffect, useCallback } from 'react';

/**
 * Hook to use the GSTIndia assistant runtime
 */
export function useNexusRuntime(config: NexusAssistantConfig = {}) {
  const adapter = createNexusChatAdapter(config);
  const runtime = useLocalRuntime(adapter);

  return runtime;
}

/**
 * Hook to get current runtime state
 */
export function useNexusRuntimeState() {
  const [state, setState] = useState<NexusRuntimeState>(runtimeState);

  useEffect(() => {
    const unsubscribe = subscribeToState(setState);
    return () => { unsubscribe(); };
  }, []);

  return state;
}

/**
 * Hook for quick reply actions
 */
export function useQuickReplies() {
  const state = useNexusRuntimeState();

  const sendQuickReply = useCallback(async (value: string) => {
    if (!state.sessionId) return;

    try {
      const response = await setupAssistantApi.sendMessage(
        state.sessionId,
        value,
        true
      );

      updateState({
        currentStep: response.current_step || null,
        isComplete: response.is_complete,
        collectedData: response.collected_data,
        quickReplies: response.message.quick_replies || [],
        canGoBack: response.can_go_back,
      });

      return response;
    } catch (error) {
      console.error('Failed to send quick reply:', error);
      throw error;
    }
  }, [state.sessionId]);

  return {
    quickReplies: state.quickReplies,
    sendQuickReply,
    canGoBack: state.canGoBack,
  };
}

/**
 * Hook to reset/restart the assistant
 */
export function useResetAssistant() {
  return useCallback(async () => {
    // Reset state
    updateState({
      sessionId: null,
      currentStep: null,
      flowType: null,
      isComplete: false,
      collectedData: {},
      quickReplies: [],
      canGoBack: false,
    });
  }, []);
}

// =============================================================================
// PROVIDER COMPONENT
// =============================================================================

export { AssistantRuntimeProvider };
