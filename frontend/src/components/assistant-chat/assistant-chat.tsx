'use client';

/**
 * Assistant Chat Component
 *
 * Main chat interface built with assistant-ui (MIT License)
 * Provides a complete conversational UI for GSTIndia setup assistant
 */

import { useState, useCallback } from 'react';
import { ArrowLeft, X, Sparkles, RotateCcw, Settings } from 'lucide-react';
import { cn } from '@/lib/utils';
import { AssistantProvider } from './assistant-provider';
import { AssistantThread } from './assistant-thread';
import { QuickReplyBar } from './quick-reply-bar';
import { useNexusRuntimeState, useResetAssistant } from '@/lib/assistant-runtime';
import type { NexusAssistantConfig } from '@/lib/assistant-runtime';

// =============================================================================
// TYPES
// =============================================================================

type FlowType = 'connection' | 'project' | 'pipeline' | 'onboarding';

interface AssistantChatProps {
  /** Initial flow type to start */
  flowType?: FlowType;
  /** Plugin to configure (for connection flow) */
  plugin?: string;
  /** Callback when close button is clicked */
  onClose?: () => void;
  /** Callback when flow completes */
  onComplete?: (data: Record<string, unknown>) => void;
  /** Additional CSS classes */
  className?: string;
  /** Whether to show the header */
  showHeader?: boolean;
  /** Whether to show quick replies bar */
  showQuickReplies?: boolean;
}

// =============================================================================
// HEADER COMPONENT
// =============================================================================

interface ChatHeaderProps {
  onClose?: () => void;
  onReset?: () => void;
  currentStep?: string | null;
  canGoBack?: boolean;
}

function ChatHeader({ onClose, onReset, currentStep, canGoBack }: ChatHeaderProps) {
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
      <div className="flex items-center gap-3">
        {canGoBack && (
          <button
            onClick={() => {/* Go back logic */}}
            className="p-1 hover:bg-muted rounded-md transition-colors"
            title="Go back"
          >
            <ArrowLeft className="h-5 w-5" />
          </button>
        )}
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <h2 className="font-semibold text-sm">GSTIndia Assistant</h2>
            {currentStep && (
              <p className="text-xs text-muted-foreground capitalize">
                {currentStep.replace(/_/g, ' ')}
              </p>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-1">
        {onReset && (
          <button
            onClick={onReset}
            className="p-1.5 hover:bg-muted rounded-md transition-colors"
            title="Start over"
          >
            <RotateCcw className="h-4 w-4" />
          </button>
        )}
        {onClose && (
          <button
            onClick={onClose}
            className="p-1.5 hover:bg-muted rounded-md transition-colors"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>
    </div>
  );
}

// =============================================================================
// PROGRESS BAR
// =============================================================================

interface ProgressBarProps {
  stepNumber?: number;
  totalSteps?: number;
  percent?: number;
}

function ProgressBar({ stepNumber, totalSteps, percent }: ProgressBarProps) {
  if (percent === undefined) return null;

  return (
    <div className="px-4 py-2 border-b">
      <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
        {stepNumber && totalSteps && (
          <span>Step {stepNumber} of {totalSteps}</span>
        )}
        <span>{Math.round(percent)}%</span>
      </div>
      <div className="h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className="h-full bg-primary transition-all duration-300 ease-out rounded-full"
          style={{ width: `${percent}%` }}
        />
      </div>
    </div>
  );
}

// =============================================================================
// COMPLETION STATE
// =============================================================================

interface CompletionStateProps {
  onClose?: () => void;
  onReset?: () => void;
}

function CompletionState({ onClose, onReset }: CompletionStateProps) {
  return (
    <div className="p-4 border-t bg-muted/30">
      <div className="text-center space-y-3">
        <div className="h-12 w-12 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center mx-auto">
          <span className="text-2xl">✅</span>
        </div>
        <p className="text-sm text-muted-foreground">
          Setup complete! You can close this assistant or start a new setup.
        </p>
        <div className="flex gap-2 justify-center">
          {onClose && (
            <button
              onClick={onClose}
              className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors text-sm"
            >
              Close
            </button>
          )}
          {onReset && (
            <button
              onClick={onReset}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm"
            >
              New Setup
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// INNER CHAT COMPONENT (uses runtime context)
// =============================================================================

interface InnerChatProps {
  onClose?: () => void;
  showHeader?: boolean;
  showQuickReplies?: boolean;
  className?: string;
}

function InnerChat({ onClose, showHeader = true, showQuickReplies = true, className }: InnerChatProps) {
  const state = useNexusRuntimeState();
  const resetAssistant = useResetAssistant();

  const handleReset = useCallback(async () => {
    await resetAssistant();
    // Optionally reload the page or reinitialize
    window.location.reload();
  }, [resetAssistant]);

  return (
    <div className={cn('flex flex-col h-full bg-background', className)}>
      {/* Header */}
      {showHeader && (
        <ChatHeader
          onClose={onClose}
          onReset={handleReset}
          currentStep={state.currentStep}
          canGoBack={state.canGoBack}
        />
      )}

      {/* Thread */}
      <div className="flex-1 overflow-hidden">
        <AssistantThread showComposer={!state.isComplete} />
      </div>

      {/* Quick Replies */}
      {showQuickReplies && !state.isComplete && state.quickReplies.length > 0 && (
        <QuickReplyBar />
      )}

      {/* Completion State */}
      {state.isComplete && (
        <CompletionState onClose={onClose} onReset={handleReset} />
      )}
    </div>
  );
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export function AssistantChat({
  flowType,
  plugin,
  onClose,
  onComplete,
  className,
  showHeader = true,
  showQuickReplies = true,
}: AssistantChatProps) {
  const [error, setError] = useState<string | null>(null);

  const handleError = useCallback((err: Error) => {
    console.error('Assistant error:', err);
    setError(err.message);
  }, []);

  const handleComplete = useCallback((data: Record<string, unknown>) => {
    console.log('Flow completed:', data);
    onComplete?.(data);
  }, [onComplete]);

  return (
    <AssistantProvider
      flowType={flowType}
      plugin={plugin}
      onComplete={handleComplete}
      onError={handleError}
    >
      {error && (
        <div className="p-4 bg-destructive/10 border-b border-destructive/20">
          <p className="text-sm text-destructive">{error}</p>
          <button
            onClick={() => setError(null)}
            className="text-xs text-destructive/80 hover:text-destructive underline mt-1"
          >
            Dismiss
          </button>
        </div>
      )}
      <InnerChat
        onClose={onClose}
        showHeader={showHeader}
        showQuickReplies={showQuickReplies}
        className={className}
      />
    </AssistantProvider>
  );
}

// =============================================================================
// FLOATING VARIANT
// =============================================================================

interface FloatingAssistantChatProps extends Omit<AssistantChatProps, 'className'> {
  isOpen: boolean;
  isMinimized?: boolean;
  onMinimize?: () => void;
}

export function FloatingAssistantChat({
  isOpen,
  isMinimized = false,
  onMinimize,
  onClose,
  ...props
}: FloatingAssistantChatProps) {
  if (!isOpen) return null;

  if (isMinimized) {
    return (
      <div className="fixed bottom-6 right-6 z-50">
        <button
          onClick={onMinimize}
          className="flex items-center gap-3 px-4 py-3 bg-background rounded-2xl shadow-2xl border hover:bg-muted/50 transition-colors"
        >
          <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
            <Sparkles className="h-4 w-4 text-primary-foreground" />
          </div>
          <span className="font-medium text-sm">GSTIndia Assistant</span>
        </button>
      </div>
    );
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[400px] h-[600px] max-h-[80vh]">
      <div className="w-full h-full bg-background rounded-2xl shadow-2xl border overflow-hidden">
        <AssistantChat
          {...props}
          onClose={onClose}
          className="h-full"
        />
      </div>
    </div>
  );
}
