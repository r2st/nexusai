/**
 * NexusAI Desktop - Main Process
 * 
 * Electron main process that creates and manages the application window.
 */

import { app, BrowserWindow, ipcMain, shell, nativeTheme, Menu, Tray, globalShortcut } from 'electron';
import { autoUpdater } from 'electron-updater';
import Store from 'electron-store';
import * as path from 'path';
import { createMenu } from './menu';
import { registerIpcHandlers } from './ipc-handlers';

// =============================================================================
// Configuration
// =============================================================================

const store = new Store({
    defaults: {
        windowBounds: { width: 1200, height: 800 },
        theme: 'system',
        startMinimized: false,
        minimizeToTray: true,
        autoUpdate: true,
        apiEndpoint: 'https://api.nexusai.dev',
    }
});

const isDev = process.env.NODE_ENV === 'development';
const isMac = process.platform === 'darwin';

// =============================================================================
// Window Management
// =============================================================================

let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;

function createWindow(): void {
    const bounds = store.get('windowBounds') as { width: number; height: number; x?: number; y?: number };

    mainWindow = new BrowserWindow({
        width: bounds.width,
        height: bounds.height,
        x: bounds.x,
        y: bounds.y,
        minWidth: 800,
        minHeight: 600,
        title: 'NexusAI',
        icon: path.join(__dirname, '../../assets/icon.png'),
        backgroundColor: nativeTheme.shouldUseDarkColors ? '#1a1a1a' : '#ffffff',
        titleBarStyle: isMac ? 'hiddenInset' : 'default',
        trafficLightPosition: { x: 15, y: 15 },
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            spellcheck: true,
        },
        show: false, // Show when ready
    });

    // Load the app
    if (isDev) {
        mainWindow.loadURL('http://localhost:3000');
        mainWindow.webContents.openDevTools();
    } else {
        mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
    }

    // Show when ready
    mainWindow.once('ready-to-show', () => {
        if (!store.get('startMinimized')) {
            mainWindow?.show();
        }
    });

    // Save window bounds on close
    mainWindow.on('close', (event) => {
        if (store.get('minimizeToTray') && !app.isQuitting) {
            event.preventDefault();
            mainWindow?.hide();
            return;
        }

        if (mainWindow) {
            store.set('windowBounds', mainWindow.getBounds());
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });

    // Open external links in browser
    mainWindow.webContents.setWindowOpenHandler(({ url }) => {
        shell.openExternal(url);
        return { action: 'deny' };
    });

    // Handle navigation
    mainWindow.webContents.on('will-navigate', (event, url) => {
        if (!url.startsWith('http://localhost') && !url.startsWith('file://')) {
            event.preventDefault();
            shell.openExternal(url);
        }
    });
}

// =============================================================================
// Tray
// =============================================================================

function createTray(): void {
    const iconPath = path.join(__dirname, '../../assets/tray-icon.png');
    tray = new Tray(iconPath);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: 'Open NexusAI',
            click: () => {
                mainWindow?.show();
            }
        },
        {
            label: 'New Chat',
            accelerator: 'CmdOrCtrl+N',
            click: () => {
                mainWindow?.show();
                mainWindow?.webContents.send('new-chat');
            }
        },
        { type: 'separator' },
        {
            label: 'Quick Ask',
            accelerator: 'CmdOrCtrl+Shift+Space',
            click: () => {
                showQuickAsk();
            }
        },
        { type: 'separator' },
        {
            label: 'Preferences',
            accelerator: 'CmdOrCtrl+,',
            click: () => {
                mainWindow?.show();
                mainWindow?.webContents.send('open-settings');
            }
        },
        { type: 'separator' },
        {
            label: 'Quit',
            accelerator: isMac ? 'Cmd+Q' : 'Ctrl+Q',
            click: () => {
                (app as any).isQuitting = true;
                app.quit();
            }
        }
    ]);

    tray.setToolTip('NexusAI');
    tray.setContextMenu(contextMenu);

    tray.on('click', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow?.show();
        }
    });
}

// =============================================================================
// Quick Ask Window
// =============================================================================

let quickAskWindow: BrowserWindow | null = null;

function showQuickAsk(): void {
    if (quickAskWindow) {
        quickAskWindow.focus();
        return;
    }

    quickAskWindow = new BrowserWindow({
        width: 600,
        height: 80,
        frame: false,
        resizable: false,
        alwaysOnTop: true,
        skipTaskbar: true,
        transparent: true,
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
        }
    });

    if (isDev) {
        quickAskWindow.loadURL('http://localhost:3000/quick-ask');
    } else {
        quickAskWindow.loadFile(path.join(__dirname, '../renderer/quick-ask.html'));
    }

    quickAskWindow.on('blur', () => {
        quickAskWindow?.close();
    });

    quickAskWindow.on('closed', () => {
        quickAskWindow = null;
    });
}

// =============================================================================
// Global Shortcuts
// =============================================================================

function registerGlobalShortcuts(): void {
    // Quick Ask shortcut
    globalShortcut.register('CommandOrControl+Shift+Space', () => {
        showQuickAsk();
    });

    // Show/Hide main window
    globalShortcut.register('CommandOrControl+Shift+N', () => {
        if (mainWindow?.isVisible()) {
            mainWindow.hide();
        } else {
            mainWindow?.show();
        }
    });
}

// =============================================================================
// Auto Updater
// =============================================================================

function setupAutoUpdater(): void {
    if (isDev) return;

    autoUpdater.autoDownload = false;
    autoUpdater.autoInstallOnAppQuit = true;

    autoUpdater.on('update-available', (info) => {
        mainWindow?.webContents.send('update-available', info);
    });

    autoUpdater.on('update-downloaded', (info) => {
        mainWindow?.webContents.send('update-downloaded', info);
    });

    autoUpdater.on('error', (error) => {
        console.error('Auto-updater error:', error);
    });

    // Check for updates periodically
    if (store.get('autoUpdate')) {
        autoUpdater.checkForUpdates();
        setInterval(() => {
            autoUpdater.checkForUpdates();
        }, 60 * 60 * 1000); // Every hour
    }
}

// =============================================================================
// App Lifecycle
// =============================================================================

// Prevent multiple instances
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
    app.quit();
} else {
    app.on('second-instance', () => {
        if (mainWindow) {
            if (mainWindow.isMinimized()) mainWindow.restore();
            mainWindow.focus();
        }
    });
}

app.whenReady().then(() => {
    // Create window
    createWindow();

    // Create tray
    createTray();

    // Set up menu
    const menu = createMenu(mainWindow!, store);
    Menu.setApplicationMenu(menu);

    // Register IPC handlers
    registerIpcHandlers(mainWindow!, store);

    // Register global shortcuts
    registerGlobalShortcuts();

    // Set up auto updater
    setupAutoUpdater();

    // macOS: Re-create window when dock icon is clicked
    app.on('activate', () => {
        if (BrowserWindow.getAllWindows().length === 0) {
            createWindow();
        } else {
            mainWindow?.show();
        }
    });
});

app.on('window-all-closed', () => {
    if (!isMac) {
        app.quit();
    }
});

app.on('before-quit', () => {
    (app as any).isQuitting = true;
});

app.on('will-quit', () => {
    globalShortcut.unregisterAll();
});

// Handle certificate errors (for development)
if (isDev) {
    app.on('certificate-error', (event, _webContents, _url, _error, _certificate, callback) => {
        event.preventDefault();
        callback(true);
    });
}

// =============================================================================
// Deep Links
// =============================================================================

app.setAsDefaultProtocolClient('nexusai');

app.on('open-url', (_event, url) => {
    // Handle nexusai:// URLs
    if (url.startsWith('nexusai://')) {
        mainWindow?.webContents.send('deep-link', url);
    }
});
