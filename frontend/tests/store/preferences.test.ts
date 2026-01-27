/**
 * Preferences Store Tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { act } from '@testing-library/react';

// Mock localStorage
const mockLocalStorage = (() => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => store[key] || null,
    setItem: (key: string, value: string) => { store[key] = value; },
    removeItem: (key: string) => { delete store[key]; },
    clear: () => { store = {}; },
  };
})();

Object.defineProperty(window, 'localStorage', { value: mockLocalStorage });

// Mock types
interface Preferences {
  theme: 'light' | 'dark' | 'system';
  language: string;
  fontSize: number;
  codeFont: string;
  lineNumbers: boolean;
  wordWrap: boolean;
  autoSave: boolean;
  notifications: {
    email: boolean;
    push: boolean;
    desktop: boolean;
  };
  sidebar: {
    collapsed: boolean;
    width: number;
  };
  chat: {
    streamingEnabled: boolean;
    showTimestamps: boolean;
    sendOnEnter: boolean;
  };
}

type PreferencesStore = {
  preferences: Preferences;
  setTheme: (theme: Preferences['theme']) => void;
  setLanguage: (language: string) => void;
  setFontSize: (size: number) => void;
  setCodeFont: (font: string) => void;
  setLineNumbers: (enabled: boolean) => void;
  setWordWrap: (enabled: boolean) => void;
  setAutoSave: (enabled: boolean) => void;
  setNotifications: (notifications: Partial<Preferences['notifications']>) => void;
  setSidebar: (sidebar: Partial<Preferences['sidebar']>) => void;
  setChat: (chat: Partial<Preferences['chat']>) => void;
  resetToDefaults: () => void;
};

const defaultPreferences: Preferences = {
  theme: 'system',
  language: 'en',
  fontSize: 14,
  codeFont: 'JetBrains Mono',
  lineNumbers: true,
  wordWrap: false,
  autoSave: true,
  notifications: {
    email: true,
    push: true,
    desktop: true,
  },
  sidebar: {
    collapsed: false,
    width: 280,
  },
  chat: {
    streamingEnabled: true,
    showTimestamps: true,
    sendOnEnter: true,
  },
};

// Simple mock store for testing
const createPreferencesStore = (): PreferencesStore => {
  let state = { ...defaultPreferences };
  
  const persist = () => {
    localStorage.setItem('preferences', JSON.stringify(state));
  };

  const load = () => {
    const saved = localStorage.getItem('preferences');
    if (saved) {
      state = { ...defaultPreferences, ...JSON.parse(saved) };
    }
  };

  load();

  return {
    get preferences() { return state; },
    setTheme: (theme) => { state = { ...state, theme }; persist(); },
    setLanguage: (language) => { state = { ...state, language }; persist(); },
    setFontSize: (fontSize) => { state = { ...state, fontSize }; persist(); },
    setCodeFont: (codeFont) => { state = { ...state, codeFont }; persist(); },
    setLineNumbers: (lineNumbers) => { state = { ...state, lineNumbers }; persist(); },
    setWordWrap: (wordWrap) => { state = { ...state, wordWrap }; persist(); },
    setAutoSave: (autoSave) => { state = { ...state, autoSave }; persist(); },
    setNotifications: (notifications) => {
      state = { ...state, notifications: { ...state.notifications, ...notifications } };
      persist();
    },
    setSidebar: (sidebar) => {
      state = { ...state, sidebar: { ...state.sidebar, ...sidebar } };
      persist();
    },
    setChat: (chat) => {
      state = { ...state, chat: { ...state.chat, ...chat } };
      persist();
    },
    resetToDefaults: () => {
      state = { ...defaultPreferences };
      persist();
    },
  };
};

describe('Preferences Store', () => {
  let store: PreferencesStore;

  beforeEach(() => {
    mockLocalStorage.clear();
    store = createPreferencesStore();
  });

  describe('initial state', () => {
    it('has default theme', () => {
      expect(store.preferences.theme).toBe('system');
    });

    it('has default language', () => {
      expect(store.preferences.language).toBe('en');
    });

    it('has default font size', () => {
      expect(store.preferences.fontSize).toBe(14);
    });

    it('has default notification settings', () => {
      expect(store.preferences.notifications).toEqual({
        email: true,
        push: true,
        desktop: true,
      });
    });

    it('has default sidebar settings', () => {
      expect(store.preferences.sidebar).toEqual({
        collapsed: false,
        width: 280,
      });
    });

    it('has default chat settings', () => {
      expect(store.preferences.chat).toEqual({
        streamingEnabled: true,
        showTimestamps: true,
        sendOnEnter: true,
      });
    });
  });

  describe('setTheme', () => {
    it('sets light theme', () => {
      store.setTheme('light');
      expect(store.preferences.theme).toBe('light');
    });

    it('sets dark theme', () => {
      store.setTheme('dark');
      expect(store.preferences.theme).toBe('dark');
    });

    it('sets system theme', () => {
      store.setTheme('dark');
      store.setTheme('system');
      expect(store.preferences.theme).toBe('system');
    });

    it('persists to localStorage', () => {
      store.setTheme('dark');
      const saved = JSON.parse(localStorage.getItem('preferences')!);
      expect(saved.theme).toBe('dark');
    });
  });

  describe('setLanguage', () => {
    it('sets language', () => {
      store.setLanguage('es');
      expect(store.preferences.language).toBe('es');
    });
  });

  describe('setFontSize', () => {
    it('sets font size', () => {
      store.setFontSize(16);
      expect(store.preferences.fontSize).toBe(16);
    });
  });

  describe('setCodeFont', () => {
    it('sets code font', () => {
      store.setCodeFont('Fira Code');
      expect(store.preferences.codeFont).toBe('Fira Code');
    });
  });

  describe('setLineNumbers', () => {
    it('enables line numbers', () => {
      store.setLineNumbers(true);
      expect(store.preferences.lineNumbers).toBe(true);
    });

    it('disables line numbers', () => {
      store.setLineNumbers(false);
      expect(store.preferences.lineNumbers).toBe(false);
    });
  });

  describe('setWordWrap', () => {
    it('enables word wrap', () => {
      store.setWordWrap(true);
      expect(store.preferences.wordWrap).toBe(true);
    });
  });

  describe('setAutoSave', () => {
    it('disables auto save', () => {
      store.setAutoSave(false);
      expect(store.preferences.autoSave).toBe(false);
    });
  });

  describe('setNotifications', () => {
    it('updates email notification setting', () => {
      store.setNotifications({ email: false });
      expect(store.preferences.notifications.email).toBe(false);
      expect(store.preferences.notifications.push).toBe(true);
    });

    it('updates multiple notification settings', () => {
      store.setNotifications({ email: false, push: false });
      expect(store.preferences.notifications.email).toBe(false);
      expect(store.preferences.notifications.push).toBe(false);
    });
  });

  describe('setSidebar', () => {
    it('sets sidebar collapsed', () => {
      store.setSidebar({ collapsed: true });
      expect(store.preferences.sidebar.collapsed).toBe(true);
    });

    it('sets sidebar width', () => {
      store.setSidebar({ width: 320 });
      expect(store.preferences.sidebar.width).toBe(320);
    });
  });

  describe('setChat', () => {
    it('disables streaming', () => {
      store.setChat({ streamingEnabled: false });
      expect(store.preferences.chat.streamingEnabled).toBe(false);
    });

    it('hides timestamps', () => {
      store.setChat({ showTimestamps: false });
      expect(store.preferences.chat.showTimestamps).toBe(false);
    });

    it('changes send on enter', () => {
      store.setChat({ sendOnEnter: false });
      expect(store.preferences.chat.sendOnEnter).toBe(false);
    });
  });

  describe('resetToDefaults', () => {
    it('resets all preferences to defaults', () => {
      store.setTheme('dark');
      store.setFontSize(20);
      store.setNotifications({ email: false });
      store.setSidebar({ collapsed: true });

      store.resetToDefaults();

      expect(store.preferences.theme).toBe('system');
      expect(store.preferences.fontSize).toBe(14);
      expect(store.preferences.notifications.email).toBe(true);
      expect(store.preferences.sidebar.collapsed).toBe(false);
    });
  });

  describe('persistence', () => {
    it('loads saved preferences on init', () => {
      store.setTheme('dark');
      store.setFontSize(18);
      
      const newStore = createPreferencesStore();
      
      expect(newStore.preferences.theme).toBe('dark');
      expect(newStore.preferences.fontSize).toBe(18);
    });
  });
});
