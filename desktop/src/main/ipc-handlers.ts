/**
 * NexusAI Desktop - IPC Handlers
 * 
 * Handles inter-process communication between main and renderer processes.
 */

import { ipcMain, BrowserWindow, nativeTheme, Notification, dialog, shell, app } from 'electron';
import { autoUpdater } from 'electron-updater';
import Store from 'electron-store';
import * as fs from 'fs/promises';
import * as path from 'path';

export function registerIpcHandlers(mainWindow: BrowserWindow, store: Store): void {
    // ==========================================================================
    // App Info
    // ==========================================================================
    
    ipcMain.handle('get-app-info', () => {
        return {
            version: app.getVersion(),
            platform: process.platform,
            arch: process.arch,
            isDev: process.env.NODE_ENV === 'development',
            userDataPath: app.getPath('userData'),
        };
    });

    // ==========================================================================
    // Configuration
    // ==========================================================================
    
    ipcMain.handle('get-config', (_event, key: string) => {
        return store.get(key);
    });

    ipcMain.handle('set-config', (_event, key: string, value: unknown) => {
        store.set(key, value);
    });

    // ==========================================================================
    // Window Controls
    // ==========================================================================
    
    ipcMain.on('window-minimize', () => {
        mainWindow.minimize();
    });

    ipcMain.on('window-maximize', () => {
        if (mainWindow.isMaximized()) {
            mainWindow.unmaximize();
        } else {
            mainWindow.maximize();
        }
    });

    ipcMain.on('window-close', () => {
        mainWindow.close();
    });

    ipcMain.handle('window-is-maximized', () => {
        return mainWindow.isMaximized();
    });

    // ==========================================================================
    // Theme
    // ==========================================================================
    
    ipcMain.handle('get-theme', () => {
        const theme = store.get('theme') as string;
        if (theme === 'system') {
            return nativeTheme.shouldUseDarkColors ? 'dark' : 'light';
        }
        return theme;
    });

    ipcMain.handle('set-theme', (_event, theme: 'light' | 'dark' | 'system') => {
        store.set('theme', theme);
        
        if (theme === 'system') {
            nativeTheme.themeSource = 'system';
        } else {
            nativeTheme.themeSource = theme;
        }
        
        mainWindow.webContents.send('theme-changed', 
            theme === 'system' 
                ? (nativeTheme.shouldUseDarkColors ? 'dark' : 'light')
                : theme
        );
    });

    nativeTheme.on('updated', () => {
        const theme = store.get('theme');
        if (theme === 'system') {
            mainWindow.webContents.send('theme-changed', 
                nativeTheme.shouldUseDarkColors ? 'dark' : 'light'
            );
        }
    });

    // ==========================================================================
    // Notifications
    // ==========================================================================
    
    ipcMain.handle('show-notification', (_event, options: { title: string; body: string }) => {
        if (Notification.isSupported()) {
            const notification = new Notification({
                title: options.title,
                body: options.body,
                icon: path.join(__dirname, '../../assets/icon.png'),
            });
            notification.show();
            notification.on('click', () => {
                mainWindow.show();
                mainWindow.focus();
            });
        }
    });

    ipcMain.handle('set-badge-count', (_event, count: number) => {
        if (process.platform === 'darwin' || process.platform === 'linux') {
            app.setBadgeCount(count);
        }
        // On Windows, we could use a tray icon overlay
    });

    // ==========================================================================
    // External Links
    // ==========================================================================
    
    ipcMain.handle('open-external', (_event, url: string) => {
        return shell.openExternal(url);
    });

    // ==========================================================================
    // File Operations
    // ==========================================================================
    
    ipcMain.handle('show-open-dialog', async (_event, options: any) => {
        const result = await dialog.showOpenDialog(mainWindow, options);
        return result;
    });

    ipcMain.handle('show-save-dialog', async (_event, options: any) => {
        const result = await dialog.showSaveDialog(mainWindow, options);
        return result;
    });

    ipcMain.handle('read-file', async (_event, filePath: string) => {
        try {
            const content = await fs.readFile(filePath, 'utf-8');
            return { success: true, content };
        } catch (error) {
            return { success: false, error: (error as Error).message };
        }
    });

    ipcMain.handle('write-file', async (_event, filePath: string, content: string) => {
        try {
            await fs.writeFile(filePath, content, 'utf-8');
            return { success: true };
        } catch (error) {
            return { success: false, error: (error as Error).message };
        }
    });

    // ==========================================================================
    // Updates
    // ==========================================================================
    
    ipcMain.handle('check-for-updates', async () => {
        try {
            const result = await autoUpdater.checkForUpdates();
            return { available: result !== null };
        } catch (error) {
            return { available: false, error: (error as Error).message };
        }
    });

    ipcMain.handle('download-update', async () => {
        try {
            await autoUpdater.downloadUpdate();
            return { success: true };
        } catch (error) {
            return { success: false, error: (error as Error).message };
        }
    });

    ipcMain.handle('install-update', () => {
        autoUpdater.quitAndInstall();
    });

    // ==========================================================================
    // Quick Ask
    // ==========================================================================
    
    ipcMain.handle('submit-quick-ask', async (_event, query: string) => {
        // Show main window and send query
        mainWindow.show();
        mainWindow.webContents.send('quick-ask-query', query);
        return { success: true };
    });

    ipcMain.on('close-quick-ask', (event) => {
        const win = BrowserWindow.fromWebContents(event.sender);
        win?.close();
    });
}
