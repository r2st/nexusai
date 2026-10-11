'use client';

import { useState, useRef, useEffect, useCallback, memo } from 'react';
import { Send, Paperclip, Loader2, StopCircle, Sparkles, Command, Keyboard } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useChatKeyboard, useMessageHistory, CHAT_SHORTCUTS } from '@/hooks/use-keyboard-shortcuts';
import { validateChatInput, detectPromptInjection } from '@/lib/security';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

interface ChatInputProps {
  onSend: (message: string) => void;
  onStop?: () => void;
  onCommandK?: () => void;
  isLoading?: boolean;
  isStreaming?: boolean;
  disabled?: boolean;
  placeholder?: string;
  showQuickActions?: boolean;
  onQuickAction?: () => void;
  maxLength?: number;
  className?: string;
  toolsEnabled?: boolean;
  onToggleTools?: (enabled: boolean) => void;
}

// -----------------------------------------------------------------------------
// Component
// -----------------------------------------------------------------------------

export const ChatInput = memo(function ChatInput({
  onSend,
  onStop,
  onCommandK,
  isLoading,
  isStreaming,
  disabled,
  placeholder = 'Send a message... (Enter to send, Shift+Enter for new line)',
  showQuickActions = true,
  onQuickAction,
  maxLength = 32000,
  className,
  toolsEnabled = true,
  onToggleTools,
}: ChatInputProps) {
  const [value, setValue] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [warning, setWarning] = useState<string | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Message history for arrow key navigation
  const { addToHistory, navigateUp, navigateDown, reset: resetHistory } = useMessageHistory();

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [value]);

  // Auto-focus on mount
  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  // Validate input on change
  useEffect(() => {
    if (value.length > 0) {
      const validation = validateChatInput(value);
      const injection = detectPromptInjection(value);

      if (injection.detected && injection.severity !== 'low') {
        setWarning('Your message contains patterns that may be filtered');
      } else if (validation.warnings.length > 0) {
        setWarning(validation.warnings[0]);
      } else {
        setWarning(null);
      }
    } else {
      setWarning(null);
    }
  }, [value]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !isLoading && !disabled) {
      addToHistory(trimmed);
      onSend(trimmed);
      setValue('');
      resetHistory();
    }
  }, [value, isLoading, disabled, addToHistory, onSend, resetHistory]);

  const handleHistoryUp = useCallback(() => {
    const previous = navigateUp();
    if (previous !== null) {
      setValue(previous);
      // Move cursor to end
      requestAnimationFrame(() => {
        if (textareaRef.current) {
          textareaRef.current.selectionStart = textareaRef.current.value.length;
          textareaRef.current.selectionEnd = textareaRef.current.value.length;
        }
      });
    }
  }, [navigateUp]);

  const handleHistoryDown = useCallback(() => {
    const next = navigateDown();
    if (next !== null) {
      setValue(next);
    }
  }, [navigateDown]);

  const handleEscape = useCallback(() => {
    if (isStreaming && onStop) {
      onStop();
    } else if (value) {
      setValue('');
      resetHistory();
    } else {
      textareaRef.current?.blur();
    }
  }, [isStreaming, onStop, value, resetHistory]);

  const handleNewLine = useCallback(() => {
    // Default behavior handles this
  }, []);

  // Keyboard shortcuts for chat input
  const { handleKeyDown } = useChatKeyboard({
    onSend: handleSubmit,
    onNewLine: handleNewLine,
    onHistoryUp: handleHistoryUp,
    onHistoryDown: handleHistoryDown,
    onEscape: handleEscape,
    onCommandK,
    enabled: !disabled,
  });

  const handleStop = useCallback(() => {
    onStop?.();
  }, [onStop]);

  const charactersRemaining = maxLength - value.length;
  const isNearLimit = charactersRemaining < 1000;
  const isAtLimit = charactersRemaining <= 0;

  return (
    <div className={cn('border-t bg-background p-4', className)}>
      <div className="mx-auto max-w-3xl">
        {/* Input container */}
        <div
          className={cn(
            'relative flex items-end gap-2 rounded-lg border bg-background p-2 shadow-sm transition-shadow',
            isFocused && 'ring-2 ring-ring ring-offset-1',
            disabled && 'opacity-50'
          )}
        >
          {/* Attachment button */}
          <Button
            variant="ghost"
            size="icon"
            className="shrink-0 h-9 w-9"
            disabled={disabled || isLoading}
            aria-label="Attach file"
            title="Attach file"
          >
            <Paperclip className="h-4 w-4" aria-hidden="true" />
          </Button>

          {/* Quick actions button */}
          {showQuickActions && onQuickAction && (
            <Button
              variant="ghost"
              size="icon"
              className="shrink-0 h-9 w-9"
              disabled={disabled || isLoading}
              onClick={onQuickAction}
              aria-label="Quick actions"
              title="Quick actions"
            >
              <Sparkles className="h-4 w-4" aria-hidden="true" />
            </Button>
          )}

          {/* Textarea */}
          <textarea
            ref={textareaRef}
            value={value}
            onChange={(e) => {
              if (e.target.value.length <= maxLength) {
                setValue(e.target.value);
              }
            }}
            onKeyDown={handleKeyDown}
            onFocus={() => setIsFocused(true)}
            onBlur={() => setIsFocused(false)}
            placeholder={placeholder}
            disabled={disabled || isLoading}
            rows={1}
            aria-label="Message input"
            aria-describedby={warning ? 'input-warning' : undefined}
            data-chat-input
            className={cn(
              'flex-1 resize-none bg-transparent py-2 text-sm outline-none',
              'placeholder:text-muted-foreground',
              'disabled:cursor-not-allowed disabled:opacity-50',
              'min-h-[40px]'
            )}
          />

          {/* Character count (when near limit) */}
          {isNearLimit && (
            <span
              className={cn(
                'absolute bottom-2 right-24 text-xs',
                isAtLimit ? 'text-destructive' : 'text-muted-foreground'
              )}
            >
              {charactersRemaining}
            </span>
          )}

          {/* Command palette shortcut hint */}
          {onCommandK && !value && (
            <Button
              variant="ghost"
              size="sm"
              className="shrink-0 h-7 px-2 text-xs text-muted-foreground gap-1"
              onClick={onCommandK}
              title="Open command palette (Cmd+K)"
            >
              <Command className="h-3 w-3" aria-hidden="true" />
              <span>K</span>
            </Button>
          )}

          {/* Send/Stop button */}
          {isStreaming ? (
            <Button
              size="icon"
              variant="destructive"
              onClick={handleStop}
              className="shrink-0 h-9 w-9"
              aria-label="Stop generating"
              title="Stop generating (Esc)"
            >
              <StopCircle className="h-4 w-4" aria-hidden="true" />
            </Button>
          ) : (
            <Button
              size="icon"
              onClick={handleSubmit}
              disabled={!value.trim() || isLoading || disabled || isAtLimit}
              className="shrink-0 h-9 w-9"
              aria-label="Send message"
              title="Send message (Enter)"
            >
              {isLoading ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Send className="h-4 w-4" aria-hidden="true" />
              )}
            </Button>
          )}
        </div>

        {/* Warning message */}
        {warning && (
          <p
            id="input-warning"
            className="mt-2 text-center text-xs text-yellow-600 dark:text-yellow-400"
            role="alert"
          >
            {warning}
          </p>
        )}

        {/* Footer with shortcuts hint */}
        <div className="mt-2 flex items-center justify-between text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <Keyboard className="h-3 w-3" aria-hidden="true" />
            <span>
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Enter</kbd> send
              <span className="mx-1">·</span>
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Shift+Enter</kbd> new line
              <span className="mx-1">·</span>
              <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">{'\u2191'}</kbd> history
            </span>
          </div>
          <div className="flex items-center gap-3">
            {onToggleTools ? (
              <label className="flex items-center gap-2">
                <input
                  type="checkbox"
                  className="h-3 w-3 rounded border-muted-foreground"
                  checked={toolsEnabled}
                  onChange={(event) => onToggleTools(event.target.checked)}
                />
                <span>Tools {toolsEnabled ? 'on' : 'off'}</span>
              </label>
            ) : null}
            <span>GSTIndia can make mistakes</span>
          </div>
        </div>
      </div>
    </div>
  );
});

export default ChatInput;
