/**
 * Electron Integration Hook
 * 
 * Provides access to Electron APIs when running in the desktop app.
 * Falls back gracefully when running in a browser.
 */

import { useEffect, useState, useCallback } from 'react';

// =============================================================================
// Types
// =============================================================================

interface ElectronAPI {
  getAppInfo: () => Promise<{ version: string; platform: string; isDev: boolean }>;
  getConfig: (key: string) => Promise<unknown>;
  setConfig: (key: string, value: unknown) => Promise<void>;
  showNotification: (options: { title: string; body: string }) => Promise<void>;
  openExternal: (url: string) => Promise<void>;
  getTheme: () => Promise<'light' | 'dark'>;
  setBadgeCount: (count: number) => Promise<void>;
  onNewChat: (callback: () => void) => () => void;
  onFocusInput: (callback: () => void) => () => void;
  onOpenSettings: (callback: () => void) => () => void;
  onOpenSearch: (callback: () => void) => () => void;
  onToggleSidebar: (callback: () => void) => () => void;
  onStopGeneration: (callback: () => void) => () => void;
  onPreviousConversation: (callback: () => void) => () => void;
  onNextConversation: (callback: () => void) => () => void;
  onShareConversation: (callback: () => void) => () => void;
  onExportConversation: (callback: () => void) => () => void;
  platform: string;
  isElectron: boolean;
}

declare global {
  interface Window {
    electronAPI?: ElectronAPI;
  }
}

// =============================================================================
// Hook
// =============================================================================

interface UseElectronReturn {
  isElectron: boolean;
  platform: string | null;
  appVersion: string | null;
  isDev: boolean;
  systemTheme: 'light' | 'dark' | null;
  showNotification: (title: string, body: string) => Promise<void>;
  openExternal: (url: string) => Promise<void>;
  setBadgeCount: (count: number) => Promise<void>;
  getConfig: <T>(key: string) => Promise<T | null>;
  setConfig: (key: string, value: unknown) => Promise<void>;
}

export function useElectron(): UseElectronReturn {
  const [isElectron, setIsElectron] = useState(false);
  const [platform, setPlatform] = useState<string | null>(null);
  const [appVersion, setAppVersion] = useState<string | null>(null);
  const [isDev, setIsDev] = useState(false);
  const [systemTheme, setSystemTheme] = useState<'light' | 'dark' | null>(null);

  useEffect(() => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      setIsElectron(true);
      setPlatform(api.platform);

      // Get app info
      api.getAppInfo().then((info) => {
        setAppVersion(info.version);
        setIsDev(info.isDev);
      });

      // Get system theme
      api.getTheme().then(setSystemTheme);
    }
  }, []);

  const showNotification = useCallback(async (title: string, body: string) => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      await api.showNotification({ title, body });
    } else if ('Notification' in window && Notification.permission === 'granted') {
      new Notification(title, { body });
    }
  }, []);

  const openExternal = useCallback(async (url: string) => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      await api.openExternal(url);
    } else {
      window.open(url, '_blank', 'noopener,noreferrer');
    }
  }, []);

  const setBadgeCount = useCallback(async (count: number) => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      await api.setBadgeCount(count);
    }
  }, []);

  const getConfig = useCallback(async <T,>(key: string): Promise<T | null> => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      return (await api.getConfig(key)) as T | null;
    }
    // Fallback to localStorage
    const stored = localStorage.getItem(`electron-config-${key}`);
    return stored ? JSON.parse(stored) : null;
  }, []);

  const setConfig = useCallback(async (key: string, value: unknown) => {
    const api = window.electronAPI;
    if (api?.isElectron) {
      await api.setConfig(key, value);
    } else {
      // Fallback to localStorage
      localStorage.setItem(`electron-config-${key}`, JSON.stringify(value));
    }
  }, []);

  return {
    isElectron,
    platform,
    appVersion,
    isDev,
    systemTheme,
    showNotification,
    openExternal,
    setBadgeCount,
    getConfig,
    setConfig,
  };
}

// =============================================================================
// Event Hooks
// =============================================================================

/**
 * Hook to listen for Electron menu events
 */
export function useElectronEvents(handlers: {
  onNewChat?: () => void;
  onFocusInput?: () => void;
  onOpenSettings?: () => void;
  onOpenSearch?: () => void;
  onToggleSidebar?: () => void;
  onStopGeneration?: () => void;
  onPreviousConversation?: () => void;
  onNextConversation?: () => void;
  onShareConversation?: () => void;
  onExportConversation?: () => void;
}): void {
  useEffect(() => {
    const api = window.electronAPI;
    if (!api?.isElectron) return;

    const cleanups: (() => void)[] = [];

    if (handlers.onNewChat) {
      cleanups.push(api.onNewChat(handlers.onNewChat));
    }
    if (handlers.onFocusInput) {
      cleanups.push(api.onFocusInput(handlers.onFocusInput));
    }
    if (handlers.onOpenSettings) {
      cleanups.push(api.onOpenSettings(handlers.onOpenSettings));
    }
    if (handlers.onOpenSearch) {
      cleanups.push(api.onOpenSearch(handlers.onOpenSearch));
    }
    if (handlers.onToggleSidebar) {
      cleanups.push(api.onToggleSidebar(handlers.onToggleSidebar));
    }
    if (handlers.onStopGeneration) {
      cleanups.push(api.onStopGeneration(handlers.onStopGeneration));
    }
    if (handlers.onPreviousConversation) {
      cleanups.push(api.onPreviousConversation(handlers.onPreviousConversation));
    }
    if (handlers.onNextConversation) {
      cleanups.push(api.onNextConversation(handlers.onNextConversation));
    }
    if (handlers.onShareConversation) {
      cleanups.push(api.onShareConversation(handlers.onShareConversation));
    }
    if (handlers.onExportConversation) {
      cleanups.push(api.onExportConversation(handlers.onExportConversation));
    }

    return () => {
      cleanups.forEach((cleanup) => cleanup());
    };
  }, [handlers]);
}

// =============================================================================
// Utility
// =============================================================================

/**
 * Check if running in Electron
 */
export function isRunningInElectron(): boolean {
  return typeof window !== 'undefined' && !!window.electronAPI?.isElectron;
}

/**
 * Get current platform
 */
export function getPlatform(): string {
  if (typeof window !== 'undefined' && window.electronAPI?.platform) {
    return window.electronAPI.platform;
  }
  return 'web';
}

export default useElectron;
