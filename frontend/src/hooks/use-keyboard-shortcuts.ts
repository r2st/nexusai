'use client';

import { useEffect, useCallback, useRef } from 'react';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export interface KeyboardShortcut {
  key: string;
  ctrlKey?: boolean;
  metaKey?: boolean;
  shiftKey?: boolean;
  altKey?: boolean;
  handler: (event: KeyboardEvent) => void;
  description?: string;
  enabled?: boolean;
}

export interface UseKeyboardShortcutsOptions {
  shortcuts: KeyboardShortcut[];
  enabled?: boolean;
  preventDefault?: boolean;
}

export interface UseChatKeyboardOptions {
  onSend: () => void;
  onNewLine: () => void;
  onHistoryUp: () => void;
  onHistoryDown: () => void;
  onEscape: () => void;
  onCommandK?: () => void;
  onSlash?: () => void;
  enabled?: boolean;
}

export interface UseGlobalKeyboardOptions {
  onCommandK?: () => void;
  onCommandSlash?: () => void;
  onEscape?: () => void;
  enabled?: boolean;
}

// -----------------------------------------------------------------------------
// General Keyboard Shortcuts Hook
// -----------------------------------------------------------------------------

export function useKeyboardShortcuts({
  shortcuts,
  enabled = true,
  preventDefault = true,
}: UseKeyboardShortcutsOptions): void {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      for (const shortcut of shortcuts) {
        if (shortcut.enabled === false) continue;

        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrlKey ? event.ctrlKey : !event.ctrlKey;
        const metaMatch = shortcut.metaKey ? event.metaKey : !event.metaKey;
        const shiftMatch = shortcut.shiftKey ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.altKey ? event.altKey : !event.altKey;

        // Handle Cmd+Key on Mac, Ctrl+Key on Windows/Linux
        const cmdOrCtrlMatch = (shortcut.metaKey || shortcut.ctrlKey)
          ? (event.metaKey || event.ctrlKey)
          : (!event.metaKey && !event.ctrlKey);

        if (keyMatch && (shortcut.metaKey || shortcut.ctrlKey ? cmdOrCtrlMatch : (ctrlMatch && metaMatch)) && shiftMatch && altMatch) {
          if (preventDefault) {
            event.preventDefault();
          }
          shortcut.handler(event);
          break;
        }
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [shortcuts, enabled, preventDefault]);
}

// -----------------------------------------------------------------------------
// Chat Input Keyboard Shortcuts Hook
// -----------------------------------------------------------------------------

export function useChatKeyboard({
  onSend,
  onNewLine,
  onHistoryUp,
  onHistoryDown,
  onEscape,
  onCommandK,
  onSlash,
  enabled = true,
}: UseChatKeyboardOptions) {
  const handleKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
      if (!enabled) return;

      const target = event.target as HTMLTextAreaElement;
      const isAtStart = target.selectionStart === 0 && target.selectionEnd === 0;
      const isEmpty = target.value.trim() === '';

      // Enter to send (without Shift)
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        onSend();
        return;
      }

      // Shift+Enter for new line
      if (event.key === 'Enter' && event.shiftKey) {
        // Let the default behavior happen (new line)
        onNewLine();
        return;
      }

      // Arrow Up for history (when at start of input and input is empty or cursor at beginning)
      if (event.key === 'ArrowUp' && (isEmpty || isAtStart)) {
        event.preventDefault();
        onHistoryUp();
        return;
      }

      // Arrow Down for history forward
      if (event.key === 'ArrowDown' && isEmpty) {
        event.preventDefault();
        onHistoryDown();
        return;
      }

      // Escape to cancel/blur
      if (event.key === 'Escape') {
        event.preventDefault();
        onEscape();
        return;
      }

      // Cmd/Ctrl+K for command palette
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onCommandK?.();
        return;
      }

      // / at start for slash commands
      if (event.key === '/' && isEmpty) {
        onSlash?.();
        return;
      }
    },
    [enabled, onSend, onNewLine, onHistoryUp, onHistoryDown, onEscape, onCommandK, onSlash]
  );

  return { handleKeyDown };
}

// -----------------------------------------------------------------------------
// Global Keyboard Shortcuts Hook
// -----------------------------------------------------------------------------

export function useGlobalKeyboard({
  onCommandK,
  onCommandSlash,
  onEscape,
  enabled = true,
}: UseGlobalKeyboardOptions): void {
  useEffect(() => {
    if (!enabled) return;

    const handleKeyDown = (event: KeyboardEvent) => {
      // Ignore if user is typing in an input
      const target = event.target as HTMLElement;
      const isTyping = target.tagName === 'INPUT' ||
        target.tagName === 'TEXTAREA' ||
        target.isContentEditable;

      // Cmd/Ctrl+K - Command palette (works even when typing)
      if (event.key === 'k' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onCommandK?.();
        return;
      }

      // Cmd/Ctrl+/ - Show shortcuts help
      if (event.key === '/' && (event.metaKey || event.ctrlKey)) {
        event.preventDefault();
        onCommandSlash?.();
        return;
      }

      // Don't handle other shortcuts if typing
      if (isTyping) return;

      // Escape - Close dialogs/panels
      if (event.key === 'Escape') {
        onEscape?.();
        return;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [enabled, onCommandK, onCommandSlash, onEscape]);
}

// -----------------------------------------------------------------------------
// Message History Hook
// -----------------------------------------------------------------------------

export interface UseMessageHistoryOptions {
  maxHistory?: number;
}

export interface UseMessageHistoryReturn {
  history: string[];
  currentIndex: number;
  addToHistory: (message: string) => void;
  navigateUp: () => string | null;
  navigateDown: () => string | null;
  reset: () => void;
}

export function useMessageHistory({
  maxHistory = 50,
}: UseMessageHistoryOptions = {}): UseMessageHistoryReturn {
  const historyRef = useRef<string[]>([]);
  const currentIndexRef = useRef(-1);
  const tempInputRef = useRef<string>('');

  const addToHistory = useCallback((message: string) => {
    const trimmed = message.trim();
    if (!trimmed) return;

    // Avoid duplicates at the end
    if (historyRef.current[historyRef.current.length - 1] === trimmed) {
      return;
    }

    historyRef.current = [...historyRef.current, trimmed].slice(-maxHistory);
    currentIndexRef.current = -1;
    tempInputRef.current = '';
  }, [maxHistory]);

  const navigateUp = useCallback(() => {
    if (historyRef.current.length === 0) return null;

    // Save current input when starting to navigate
    if (currentIndexRef.current === -1) {
      tempInputRef.current = '';
    }

    // Move up in history
    if (currentIndexRef.current < historyRef.current.length - 1) {
      currentIndexRef.current++;
      const index = historyRef.current.length - 1 - currentIndexRef.current;
      return historyRef.current[index];
    }

    // Already at oldest, return it
    return historyRef.current[0];
  }, []);

  const navigateDown = useCallback(() => {
    if (currentIndexRef.current <= 0) {
      currentIndexRef.current = -1;
      return tempInputRef.current;
    }

    currentIndexRef.current--;
    const index = historyRef.current.length - 1 - currentIndexRef.current;
    return historyRef.current[index];
  }, []);

  const reset = useCallback(() => {
    currentIndexRef.current = -1;
    tempInputRef.current = '';
  }, []);

  return {
    history: historyRef.current,
    currentIndex: currentIndexRef.current,
    addToHistory,
    navigateUp,
    navigateDown,
    reset,
  };
}

// -----------------------------------------------------------------------------
// Shortcuts Registry
// -----------------------------------------------------------------------------

export interface ShortcutInfo {
  keys: string;
  description: string;
  category: 'chat' | 'navigation' | 'editing' | 'general';
}

export const CHAT_SHORTCUTS: ShortcutInfo[] = [
  { keys: 'Enter', description: 'Send message', category: 'chat' },
  { keys: 'Shift + Enter', description: 'New line', category: 'chat' },
  { keys: '\u2191', description: 'Previous message in history', category: 'chat' },
  { keys: '\u2193', description: 'Next message in history', category: 'chat' },
  { keys: 'Esc', description: 'Cancel / Clear', category: 'chat' },
  { keys: '/', description: 'Slash commands', category: 'chat' },
];

export const GLOBAL_SHORTCUTS: ShortcutInfo[] = [
  { keys: '\u2318/Ctrl + K', description: 'Open command palette', category: 'general' },
  { keys: '\u2318/Ctrl + /', description: 'Show keyboard shortcuts', category: 'general' },
  { keys: 'Esc', description: 'Close dialogs', category: 'general' },
];

export const ALL_SHORTCUTS: ShortcutInfo[] = [...CHAT_SHORTCUTS, ...GLOBAL_SHORTCUTS];

export default useKeyboardShortcuts;
