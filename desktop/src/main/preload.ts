/**
 * NexusAI Desktop - Preload Script
 * 
 * Exposes safe APIs to the renderer process via contextBridge.
 */

import { contextBridge, ipcRenderer } from 'electron';

// =============================================================================
// API Definition
// =============================================================================

const electronAPI = {
    // App Info
    getAppInfo: () => ipcRenderer.invoke('get-app-info'),
    getPlatform: () => process.platform,
    
    // Configuration
    getConfig: (key: string) => ipcRenderer.invoke('get-config', key),
    setConfig: (key: string, value: unknown) => ipcRenderer.invoke('set-config', key, value),
    
    // Window Controls
    minimize: () => ipcRenderer.send('window-minimize'),
    maximize: () => ipcRenderer.send('window-maximize'),
    close: () => ipcRenderer.send('window-close'),
    isMaximized: () => ipcRenderer.invoke('window-is-maximized'),
    
    // Theme
    getTheme: () => ipcRenderer.invoke('get-theme'),
    setTheme: (theme: 'light' | 'dark' | 'system') => ipcRenderer.invoke('set-theme', theme),
    onThemeChange: (callback: (theme: string) => void) => {
        const handler = (_event: any, theme: string) => callback(theme);
        ipcRenderer.on('theme-changed', handler);
        return () => ipcRenderer.removeListener('theme-changed', handler);
    },
    
    // Notifications
    showNotification: (options: { title: string; body: string }) => 
        ipcRenderer.invoke('show-notification', options),
    setBadgeCount: (count: number) => ipcRenderer.invoke('set-badge-count', count),
    
    // External Links
    openExternal: (url: string) => ipcRenderer.invoke('open-external', url),
    
    // File Operations
    showOpenDialog: (options: any) => ipcRenderer.invoke('show-open-dialog', options),
    showSaveDialog: (options: any) => ipcRenderer.invoke('show-save-dialog', options),
    readFile: (path: string) => ipcRenderer.invoke('read-file', path),
    writeFile: (path: string, content: string) => ipcRenderer.invoke('write-file', path, content),
    
    // Updates
    checkForUpdates: () => ipcRenderer.invoke('check-for-updates'),
    downloadUpdate: () => ipcRenderer.invoke('download-update'),
    installUpdate: () => ipcRenderer.invoke('install-update'),
    onUpdateAvailable: (callback: (info: any) => void) => {
        const handler = (_event: any, info: any) => callback(info);
        ipcRenderer.on('update-available', handler);
        return () => ipcRenderer.removeListener('update-available', handler);
    },
    onUpdateDownloaded: (callback: (info: any) => void) => {
        const handler = (_event: any, info: any) => callback(info);
        ipcRenderer.on('update-downloaded', handler);
        return () => ipcRenderer.removeListener('update-downloaded', handler);
    },
    
    // Menu Events
    onNewChat: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('new-chat', handler);
        return () => ipcRenderer.removeListener('new-chat', handler);
    },
    onFocusInput: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('focus-input', handler);
        return () => ipcRenderer.removeListener('focus-input', handler);
    },
    onOpenSettings: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('open-settings', handler);
        return () => ipcRenderer.removeListener('open-settings', handler);
    },
    onOpenSearch: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('open-search', handler);
        return () => ipcRenderer.removeListener('open-search', handler);
    },
    onToggleSidebar: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('toggle-sidebar', handler);
        return () => ipcRenderer.removeListener('toggle-sidebar', handler);
    },
    onStopGeneration: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('stop-generation', handler);
        return () => ipcRenderer.removeListener('stop-generation', handler);
    },
    onPreviousConversation: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('previous-conversation', handler);
        return () => ipcRenderer.removeListener('previous-conversation', handler);
    },
    onNextConversation: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('next-conversation', handler);
        return () => ipcRenderer.removeListener('next-conversation', handler);
    },
    onShareConversation: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('share-conversation', handler);
        return () => ipcRenderer.removeListener('share-conversation', handler);
    },
    onExportConversation: (callback: () => void) => {
        const handler = () => callback();
        ipcRenderer.on('export-conversation', handler);
        return () => ipcRenderer.removeListener('export-conversation', handler);
    },
    onDeepLink: (callback: (url: string) => void) => {
        const handler = (_event: any, url: string) => callback(url);
        ipcRenderer.on('deep-link', handler);
        return () => ipcRenderer.removeListener('deep-link', handler);
    },
    
    // Quick Ask
    submitQuickAsk: (query: string) => ipcRenderer.invoke('submit-quick-ask', query),
    closeQuickAsk: () => ipcRenderer.send('close-quick-ask'),
    
    // Helpers
    isElectron: true,
    platform: process.platform,
};

// =============================================================================
// Expose API
// =============================================================================

contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Type declaration for renderer
export type ElectronAPI = typeof electronAPI;
