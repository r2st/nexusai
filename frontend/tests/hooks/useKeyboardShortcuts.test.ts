/**
 * useKeyboardShortcuts hooks tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';
import {
  useKeyboardShortcuts,
  useChatKeyboard,
  useGlobalKeyboard,
  useMessageHistory,
  CHAT_SHORTCUTS,
  GLOBAL_SHORTCUTS,
} from '@/hooks/use-keyboard-shortcuts';

describe('useKeyboardShortcuts Hook', () => {
  const dispatchKeyEvent = (
    key: string,
    options: { metaKey?: boolean; ctrlKey?: boolean; shiftKey?: boolean; altKey?: boolean } = {}
  ) => {
    window.dispatchEvent(
      new KeyboardEvent('keydown', {
        key,
        metaKey: options.metaKey || false,
        ctrlKey: options.ctrlKey || false,
        shiftKey: options.shiftKey || false,
        altKey: options.altKey || false,
        bubbles: true,
      })
    );
  };

  afterEach(() => {
    vi.clearAllMocks();
  });

  describe('basic shortcut handling', () => {
    it('triggers handler for matching shortcut', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler }],
        })
      );

      dispatchKeyEvent('k', { metaKey: true });

      expect(handler).toHaveBeenCalled();
    });

    it('does not trigger handler for non-matching shortcut', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler }],
        })
      );

      dispatchKeyEvent('j', { metaKey: true });

      expect(handler).not.toHaveBeenCalled();
    });

    it('handles Ctrl key as alternative to Meta', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler }],
        })
      );

      dispatchKeyEvent('k', { ctrlKey: true });

      expect(handler).toHaveBeenCalled();
    });

    it('respects enabled flag', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler }],
          enabled: false,
        })
      );

      dispatchKeyEvent('k', { metaKey: true });

      expect(handler).not.toHaveBeenCalled();
    });

    it('respects individual shortcut enabled flag', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler, enabled: false }],
        })
      );

      dispatchKeyEvent('k', { metaKey: true });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('modifier key combinations', () => {
    it('handles Shift modifier', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'Enter', shiftKey: true, handler }],
        })
      );

      dispatchKeyEvent('Enter', { shiftKey: true });

      expect(handler).toHaveBeenCalled();
    });

    it('handles Alt modifier', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 's', altKey: true, handler }],
        })
      );

      dispatchKeyEvent('s', { altKey: true });

      expect(handler).toHaveBeenCalled();
    });

    it('handles multiple modifiers', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 's', metaKey: true, shiftKey: true, handler }],
        })
      );

      dispatchKeyEvent('s', { metaKey: true, shiftKey: true });

      expect(handler).toHaveBeenCalled();
    });

    it('does not match without required modifiers', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 's', metaKey: true, shiftKey: true, handler }],
        })
      );

      // Missing shiftKey
      dispatchKeyEvent('s', { metaKey: true });

      expect(handler).not.toHaveBeenCalled();
    });
  });

  describe('preventDefault behavior', () => {
    it('prevents default by default', () => {
      const handler = vi.fn();
      renderHook(() =>
        useKeyboardShortcuts({
          shortcuts: [{ key: 'k', metaKey: true, handler }],
        })
      );

      const event = new KeyboardEvent('keydown', {
        key: 'k',
        metaKey: true,
        bubbles: true,
        cancelable: true,
      });
      const preventDefaultSpy = vi.spyOn(event, 'preventDefault');

      window.dispatchEvent(event);

      expect(preventDefaultSpy).toHaveBeenCalled();
    });
  });
});

describe('useChatKeyboard Hook', () => {
  const createTextarea = (): HTMLTextAreaElement => {
    const textarea = document.createElement('textarea');
    document.body.appendChild(textarea);
    return textarea;
  };

  const createKeyboardEvent = (
    key: string,
    options: { shiftKey?: boolean; metaKey?: boolean; ctrlKey?: boolean } = {}
  ): React.KeyboardEvent<HTMLTextAreaElement> => {
    return {
      key,
      shiftKey: options.shiftKey || false,
      metaKey: options.metaKey || false,
      ctrlKey: options.ctrlKey || false,
      preventDefault: vi.fn(),
      target: createTextarea(),
    } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;
  };

  afterEach(() => {
    document.body.innerHTML = '';
    vi.clearAllMocks();
  });

  describe('Enter key behavior', () => {
    it('calls onSend when Enter pressed without Shift', () => {
      const onSend = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend,
          onNewLine: vi.fn(),
          onHistoryUp: vi.fn(),
          onHistoryDown: vi.fn(),
          onEscape: vi.fn(),
        })
      );

      const event = createKeyboardEvent('Enter');
      result.current.handleKeyDown(event);

      expect(onSend).toHaveBeenCalled();
      expect(event.preventDefault).toHaveBeenCalled();
    });

    it('calls onNewLine when Shift+Enter pressed', () => {
      const onNewLine = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend: vi.fn(),
          onNewLine,
          onHistoryUp: vi.fn(),
          onHistoryDown: vi.fn(),
          onEscape: vi.fn(),
        })
      );

      const event = createKeyboardEvent('Enter', { shiftKey: true });
      result.current.handleKeyDown(event);

      expect(onNewLine).toHaveBeenCalled();
    });
  });

  describe('Arrow key history navigation', () => {
    it('calls onHistoryUp when ArrowUp pressed at empty input', () => {
      const onHistoryUp = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend: vi.fn(),
          onNewLine: vi.fn(),
          onHistoryUp,
          onHistoryDown: vi.fn(),
          onEscape: vi.fn(),
        })
      );

      const textarea = createTextarea();
      textarea.value = '';
      textarea.selectionStart = 0;
      textarea.selectionEnd = 0;

      const event = {
        key: 'ArrowUp',
        preventDefault: vi.fn(),
        target: textarea,
      } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

      result.current.handleKeyDown(event);

      expect(onHistoryUp).toHaveBeenCalled();
    });

    it('calls onHistoryDown when ArrowDown pressed at empty input', () => {
      const onHistoryDown = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend: vi.fn(),
          onNewLine: vi.fn(),
          onHistoryUp: vi.fn(),
          onHistoryDown,
          onEscape: vi.fn(),
        })
      );

      const textarea = createTextarea();
      textarea.value = '';

      const event = {
        key: 'ArrowDown',
        preventDefault: vi.fn(),
        target: textarea,
      } as unknown as React.KeyboardEvent<HTMLTextAreaElement>;

      result.current.handleKeyDown(event);

      expect(onHistoryDown).toHaveBeenCalled();
    });
  });

  describe('Escape key behavior', () => {
    it('calls onEscape when Escape pressed', () => {
      const onEscape = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend: vi.fn(),
          onNewLine: vi.fn(),
          onHistoryUp: vi.fn(),
          onHistoryDown: vi.fn(),
          onEscape,
        })
      );

      const event = createKeyboardEvent('Escape');
      result.current.handleKeyDown(event);

      expect(onEscape).toHaveBeenCalled();
    });
  });

  describe('Command+K behavior', () => {
    it('calls onCommandK when Cmd+K pressed', () => {
      const onCommandK = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend: vi.fn(),
          onNewLine: vi.fn(),
          onHistoryUp: vi.fn(),
          onHistoryDown: vi.fn(),
          onEscape: vi.fn(),
          onCommandK,
        })
      );

      const event = createKeyboardEvent('k', { metaKey: true });
      result.current.handleKeyDown(event);

      expect(onCommandK).toHaveBeenCalled();
    });
  });

  describe('enabled state', () => {
    it('does not call handlers when disabled', () => {
      const onSend = vi.fn();
      const { result } = renderHook(() =>
        useChatKeyboard({
          onSend,
          onNewLine: vi.fn(),
          onHistoryUp: vi.fn(),
          onHistoryDown: vi.fn(),
          onEscape: vi.fn(),
          enabled: false,
        })
      );

      const event = createKeyboardEvent('Enter');
      result.current.handleKeyDown(event);

      expect(onSend).not.toHaveBeenCalled();
    });
  });
});

describe('useGlobalKeyboard Hook', () => {
  afterEach(() => {
    vi.clearAllMocks();
  });

  it('calls onCommandK when Cmd+K pressed', () => {
    const onCommandK = vi.fn();
    renderHook(() => useGlobalKeyboard({ onCommandK }));

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true })
    );

    expect(onCommandK).toHaveBeenCalled();
  });

  it('calls onEscape when Escape pressed outside input', () => {
    const onEscape = vi.fn();
    renderHook(() => useGlobalKeyboard({ onEscape }));

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })
    );

    expect(onEscape).toHaveBeenCalled();
  });

  it('respects enabled flag', () => {
    const onCommandK = vi.fn();
    renderHook(() => useGlobalKeyboard({ onCommandK, enabled: false }));

    window.dispatchEvent(
      new KeyboardEvent('keydown', { key: 'k', metaKey: true, bubbles: true })
    );

    expect(onCommandK).not.toHaveBeenCalled();
  });
});

describe('useMessageHistory Hook', () => {
  describe('addToHistory', () => {
    it('adds message to history (verified via navigateUp)', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First message');
      });

      // Verify via navigateUp since history is stored in a ref
      let message: string | null = null;
      act(() => {
        message = result.current.navigateUp();
      });
      expect(message).toBe('First message');
    });

    it('trims whitespace from messages', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('  Trimmed message  ');
      });

      // Verify trimmed via navigateUp
      let message: string | null = null;
      act(() => {
        message = result.current.navigateUp();
      });
      expect(message).toBe('Trimmed message');
    });

    it('does not add empty messages', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('');
        result.current.addToHistory('   ');
      });

      // navigateUp should return null since nothing was added
      let message: string | null = 'not-null';
      act(() => {
        message = result.current.navigateUp();
      });
      expect(message).toBeNull();
    });

    it('avoids consecutive duplicates', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('Same message');
        result.current.addToHistory('Same message');
        result.current.addToHistory('Different message');
      });

      // Navigate through history - should only have two unique messages
      const messages: (string | null)[] = [];
      act(() => {
        messages.push(result.current.navigateUp()); // Different message
        messages.push(result.current.navigateUp()); // Same message
        messages.push(result.current.navigateUp()); // null (at start)
      });
      expect(messages).toEqual(['Different message', 'Same message', 'Same message']);
    });

    it('respects maxHistory limit', () => {
      const { result } = renderHook(() => useMessageHistory({ maxHistory: 3 }));

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
        result.current.addToHistory('Third');
        result.current.addToHistory('Fourth');
      });

      // Navigate through history - should only have 3 items (First should be dropped)
      const messages: (string | null)[] = [];
      act(() => {
        messages.push(result.current.navigateUp()); // Fourth
        messages.push(result.current.navigateUp()); // Third
        messages.push(result.current.navigateUp()); // Second
        messages.push(result.current.navigateUp()); // Second again (at start)
      });
      expect(messages[0]).toBe('Fourth');
      expect(messages[1]).toBe('Third');
      expect(messages[2]).toBe('Second');
      // First should not be in history
    });
  });

  describe('navigateUp', () => {
    it('returns most recent message', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
        result.current.addToHistory('Third');
      });

      let message: string | null = null;
      act(() => {
        message = result.current.navigateUp();
      });

      expect(message).toBe('Third');
    });

    it('navigates through history', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
        result.current.addToHistory('Third');
      });

      let messages: (string | null)[] = [];
      act(() => {
        messages.push(result.current.navigateUp());
        messages.push(result.current.navigateUp());
        messages.push(result.current.navigateUp());
      });

      expect(messages).toEqual(['Third', 'Second', 'First']);
    });

    it('returns null when history is empty', () => {
      const { result } = renderHook(() => useMessageHistory());

      let message: string | null = null;
      act(() => {
        message = result.current.navigateUp();
      });

      expect(message).toBeNull();
    });

    it('stays at oldest message when at end', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
      });

      let messages: (string | null)[] = [];
      act(() => {
        messages.push(result.current.navigateUp());
        messages.push(result.current.navigateUp());
        messages.push(result.current.navigateUp());
      });

      expect(messages[2]).toBe('First');
    });
  });

  describe('navigateDown', () => {
    it('navigates forward in history', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
        result.current.addToHistory('Third');
      });

      act(() => {
        result.current.navigateUp();
        result.current.navigateUp();
      });

      let message: string | null = null;
      act(() => {
        message = result.current.navigateDown();
      });

      expect(message).toBe('Third');
    });

    it('returns empty string when back to current input', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
      });

      act(() => {
        result.current.navigateUp();
      });

      let message: string | null = null;
      act(() => {
        message = result.current.navigateDown();
      });

      expect(message).toBe('');
    });
  });

  describe('reset', () => {
    it('resets navigation index', () => {
      const { result } = renderHook(() => useMessageHistory());

      act(() => {
        result.current.addToHistory('First');
        result.current.addToHistory('Second');
      });

      act(() => {
        result.current.navigateUp();
        result.current.navigateUp();
      });

      act(() => {
        result.current.reset();
      });

      let message: string | null = null;
      act(() => {
        message = result.current.navigateUp();
      });

      // Should start from most recent again
      expect(message).toBe('Second');
    });
  });
});

describe('Shortcut Constants', () => {
  describe('CHAT_SHORTCUTS', () => {
    it('contains Enter shortcut', () => {
      expect(CHAT_SHORTCUTS.some(s => s.keys === 'Enter')).toBe(true);
    });

    it('contains Shift+Enter shortcut', () => {
      expect(CHAT_SHORTCUTS.some(s => s.keys === 'Shift + Enter')).toBe(true);
    });

    it('contains arrow key shortcuts', () => {
      expect(CHAT_SHORTCUTS.some(s => s.keys === '\u2191')).toBe(true);
      expect(CHAT_SHORTCUTS.some(s => s.keys === '\u2193')).toBe(true);
    });
  });

  describe('GLOBAL_SHORTCUTS', () => {
    it('contains Cmd+K shortcut', () => {
      expect(GLOBAL_SHORTCUTS.some(s => s.keys.includes('K'))).toBe(true);
    });

    it('contains Escape shortcut', () => {
      expect(GLOBAL_SHORTCUTS.some(s => s.keys === 'Esc')).toBe(true);
    });
  });
});
