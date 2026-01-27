/**
 * useElectron Hook Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook, act } from '@testing-library/react';

// Mock Electron API
interface ElectronAPI {
  isElectron: boolean;
  platform: string;
  appVersion: string;
  minimize: () => void;
  maximize: () => void;
  close: () => void;
  openExternal: (url: string) => Promise<void>;
  showNotification: (title: string, body: string) => void;
  onMenuAction: (callback: (action: string) => void) => () => void;
}

// Mock useElectron hook
const useElectron = () => {
  const isElectron = typeof window !== 'undefined' && !!(window as any).electronAPI;
  const api = (window as any).electronAPI as ElectronAPI | undefined;

  const minimize = () => api?.minimize();
  const maximize = () => api?.maximize();
  const close = () => api?.close();
  
  const openExternal = async (url: string) => {
    if (api?.openExternal) {
      await api.openExternal(url);
    } else {
      window.open(url, '_blank');
    }
  };

  const showNotification = (title: string, body: string) => {
    if (api?.showNotification) {
      api.showNotification(title, body);
    } else if ('Notification' in window) {
      new Notification(title, { body });
    }
  };

  const useMenuAction = (callback: (action: string) => void) => {
    if (api?.onMenuAction) {
      return api.onMenuAction(callback);
    }
    return () => {};
  };

  return {
    isElectron,
    platform: api?.platform || 'web',
    appVersion: api?.appVersion || '0.0.0',
    minimize,
    maximize,
    close,
    openExternal,
    showNotification,
    useMenuAction,
  };
};

describe('useElectron', () => {
  const mockElectronAPI: ElectronAPI = {
    isElectron: true,
    platform: 'darwin',
    appVersion: '1.0.0',
    minimize: vi.fn(),
    maximize: vi.fn(),
    close: vi.fn(),
    openExternal: vi.fn().mockResolvedValue(undefined),
    showNotification: vi.fn(),
    onMenuAction: vi.fn((callback) => {
      return () => {};
    }),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    delete (window as any).electronAPI;
  });

  describe('when in Electron environment', () => {
    beforeEach(() => {
      (window as any).electronAPI = mockElectronAPI;
    });

    it('detects Electron environment', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.isElectron).toBe(true);
    });

    it('returns platform', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.platform).toBe('darwin');
    });

    it('returns app version', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.appVersion).toBe('1.0.0');
    });

    it('calls minimize', () => {
      const { result } = renderHook(() => useElectron());
      result.current.minimize();
      expect(mockElectronAPI.minimize).toHaveBeenCalled();
    });

    it('calls maximize', () => {
      const { result } = renderHook(() => useElectron());
      result.current.maximize();
      expect(mockElectronAPI.maximize).toHaveBeenCalled();
    });

    it('calls close', () => {
      const { result } = renderHook(() => useElectron());
      result.current.close();
      expect(mockElectronAPI.close).toHaveBeenCalled();
    });

    it('opens external URL', async () => {
      const { result } = renderHook(() => useElectron());
      await result.current.openExternal('https://example.com');
      expect(mockElectronAPI.openExternal).toHaveBeenCalledWith('https://example.com');
    });

    it('shows notification', () => {
      const { result } = renderHook(() => useElectron());
      result.current.showNotification('Title', 'Body');
      expect(mockElectronAPI.showNotification).toHaveBeenCalledWith('Title', 'Body');
    });

    it('registers menu action handler', () => {
      const callback = vi.fn();
      const { result } = renderHook(() => useElectron());
      result.current.useMenuAction(callback);
      expect(mockElectronAPI.onMenuAction).toHaveBeenCalledWith(callback);
    });
  });

  describe('when in web environment', () => {
    let originalOpen: typeof window.open;

    beforeEach(() => {
      originalOpen = window.open;
      window.open = vi.fn();
      delete (window as any).electronAPI;
    });

    afterEach(() => {
      window.open = originalOpen;
    });

    it('detects web environment', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.isElectron).toBe(false);
    });

    it('returns web platform', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.platform).toBe('web');
    });

    it('returns default app version', () => {
      const { result } = renderHook(() => useElectron());
      expect(result.current.appVersion).toBe('0.0.0');
    });

    it('opens external URL in new tab', async () => {
      const { result } = renderHook(() => useElectron());
      await result.current.openExternal('https://example.com');
      expect(window.open).toHaveBeenCalledWith('https://example.com', '_blank');
    });

    it('window controls do nothing in web', () => {
      const { result } = renderHook(() => useElectron());
      expect(() => result.current.minimize()).not.toThrow();
      expect(() => result.current.maximize()).not.toThrow();
      expect(() => result.current.close()).not.toThrow();
    });

    it('useMenuAction returns noop', () => {
      const callback = vi.fn();
      const { result } = renderHook(() => useElectron());
      const cleanup = result.current.useMenuAction(callback);
      expect(typeof cleanup).toBe('function');
    });
  });
});
