/**
 * NexusAI Desktop App - Preload Script
 * 
 * Exposes safe APIs to the renderer process via contextBridge.
 * This is the only way to communicate between the web app and Electron.
 */

import { contextBridge, ipcRenderer } from 'electron';

// Define the API exposed to the renderer
const electronAPI = {
  // App info
  getAppInfo: () => ipcRenderer.invoke('get-app-info'),

  // Configuration
  getConfig: (key: string) => ipcRenderer.invoke('get-config', key),
  setConfig: (key: string, value: unknown) => ipcRenderer.invoke('set-config', key, value),

  // Notifications
  showNotification: (options: { title: string; body: string }) =>
    ipcRenderer.invoke('show-notification', options),

  // External links
  openExternal: (url: string) => ipcRenderer.invoke('open-external', url),

  // Theme
  getTheme: () => ipcRenderer.invoke('get-theme'),

  // Badge
  setBadgeCount: (count: number) => ipcRenderer.invoke('set-badge-count', count),

  // Event listeners from main process
  onNewChat: (callback: () => void) => {
    ipcRenderer.on('new-chat', callback);
    return () => ipcRenderer.removeListener('new-chat', callback);
  },

  onFocusInput: (callback: () => void) => {
    ipcRenderer.on('focus-input', callback);
    return () => ipcRenderer.removeListener('focus-input', callback);
  },

  onOpenSettings: (callback: () => void) => {
    ipcRenderer.on('open-settings', callback);
    return () => ipcRenderer.removeListener('open-settings', callback);
  },

  onOpenSearch: (callback: () => void) => {
    ipcRenderer.on('open-search', callback);
    return () => ipcRenderer.removeListener('open-search', callback);
  },

  onToggleSidebar: (callback: () => void) => {
    ipcRenderer.on('toggle-sidebar', callback);
    return () => ipcRenderer.removeListener('toggle-sidebar', callback);
  },

  onStopGeneration: (callback: () => void) => {
    ipcRenderer.on('stop-generation', callback);
    return () => ipcRenderer.removeListener('stop-generation', callback);
  },

  onPreviousConversation: (callback: () => void) => {
    ipcRenderer.on('previous-conversation', callback);
    return () => ipcRenderer.removeListener('previous-conversation', callback);
  },

  onNextConversation: (callback: () => void) => {
    ipcRenderer.on('next-conversation', callback);
    return () => ipcRenderer.removeListener('next-conversation', callback);
  },

  onShareConversation: (callback: () => void) => {
    ipcRenderer.on('share-conversation', callback);
    return () => ipcRenderer.removeListener('share-conversation', callback);
  },

  onExportConversation: (callback: () => void) => {
    ipcRenderer.on('export-conversation', callback);
    return () => ipcRenderer.removeListener('export-conversation', callback);
  },

  // Platform info
  platform: process.platform,
  isElectron: true,
};

// Expose to renderer
contextBridge.exposeInMainWorld('electronAPI', electronAPI);

// Type declaration for the renderer
export type ElectronAPI = typeof electronAPI;
