/**
 * NexusAI Desktop App - Electron Main Process
 * 
 * Wraps the Next.js web app in a native desktop shell with:
 * - System tray integration
 * - Native menus
 * - Offline support
 * - Deep linking
 * - Auto-updates
 */

import {
  app,
  BrowserWindow,
  Menu,
  Tray,
  ipcMain,
  shell,
  nativeTheme,
  Notification,
  dialog,
  globalShortcut,
} from 'electron';
import * as path from 'path';
import * as fs from 'fs';
import { autoUpdater } from 'electron-updater';

// Configuration
const isDev = process.env.NODE_ENV === 'development';
const APP_URL = isDev ? 'http://localhost:3000' : 'https://app.nexusai.dev';
const PRELOAD_PATH = path.join(__dirname, 'preload.js');

// Global references
let mainWindow: BrowserWindow | null = null;
let tray: Tray | null = null;
let isQuitting = false;

// =============================================================================
// Window Management
// =============================================================================

function createMainWindow(): BrowserWindow {
  const win = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    title: 'NexusAI',
    icon: getIconPath(),
    backgroundColor: nativeTheme.shouldUseDarkColors ? '#0a0a0a' : '#ffffff',
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    trafficLightPosition: { x: 16, y: 16 },
    webPreferences: {
      preload: PRELOAD_PATH,
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: true,
    },
    show: false, // Show when ready
  });

  // Load the app
  win.loadURL(APP_URL);

  // Show when ready
  win.once('ready-to-show', () => {
    win.show();
    if (isDev) {
      win.webContents.openDevTools();
    }
  });

  // Handle external links
  win.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: 'deny' };
  });

  // Handle close to tray
  win.on('close', (event) => {
    if (!isQuitting) {
      event.preventDefault();
      win.hide();
      
      // Show notification on first minimize
      const hasShownTrayNotification = getConfig('hasShownTrayNotification');
      if (!hasShownTrayNotification) {
        new Notification({
          title: 'NexusAI',
          body: 'NexusAI is still running in the system tray.',
          icon: getIconPath(),
        }).show();
        setConfig('hasShownTrayNotification', true);
      }
    }
  });

  win.on('closed', () => {
    mainWindow = null;
  });

  return win;
}

function showMainWindow(): void {
  if (mainWindow) {
    if (mainWindow.isMinimized()) {
      mainWindow.restore();
    }
    mainWindow.show();
    mainWindow.focus();
  } else {
    mainWindow = createMainWindow();
  }
}

// =============================================================================
// System Tray
// =============================================================================

function createTray(): Tray {
  const trayIcon = getTrayIconPath();
  const newTray = new Tray(trayIcon);

  const contextMenu = Menu.buildFromTemplate([
    {
      label: 'Open NexusAI',
      click: showMainWindow,
    },
    {
      label: 'New Chat',
      accelerator: 'CmdOrCtrl+N',
      click: () => {
        showMainWindow();
        mainWindow?.webContents.send('new-chat');
      },
    },
    { type: 'separator' },
    {
      label: 'Quick Ask...',
      accelerator: 'CmdOrCtrl+Shift+Space',
      click: () => {
        showMainWindow();
        mainWindow?.webContents.send('focus-input');
      },
    },
    { type: 'separator' },
    {
      label: 'Preferences',
      accelerator: 'CmdOrCtrl+,',
      click: () => {
        showMainWindow();
        mainWindow?.webContents.send('open-settings');
      },
    },
    { type: 'separator' },
    {
      label: 'Check for Updates',
      click: () => autoUpdater.checkForUpdates(),
    },
    { type: 'separator' },
    {
      label: 'Quit NexusAI',
      accelerator: 'CmdOrCtrl+Q',
      click: () => {
        isQuitting = true;
        app.quit();
      },
    },
  ]);

  newTray.setContextMenu(contextMenu);
  newTray.setToolTip('NexusAI');

  newTray.on('click', () => {
    showMainWindow();
  });

  newTray.on('double-click', () => {
    showMainWindow();
  });

  return newTray;
}

// =============================================================================
// Application Menu
// =============================================================================

function createAppMenu(): void {
  const isMac = process.platform === 'darwin';

  const template: Electron.MenuItemConstructorOptions[] = [
    // App menu (macOS only)
    ...(isMac
      ? [
          {
            label: app.name,
            submenu: [
              { role: 'about' as const },
              { type: 'separator' as const },
              {
                label: 'Preferences',
                accelerator: 'CmdOrCtrl+,',
                click: () => mainWindow?.webContents.send('open-settings'),
              },
              { type: 'separator' as const },
              { role: 'services' as const },
              { type: 'separator' as const },
              { role: 'hide' as const },
              { role: 'hideOthers' as const },
              { role: 'unhide' as const },
              { type: 'separator' as const },
              { role: 'quit' as const },
            ],
          },
        ]
      : []),

    // File menu
    {
      label: 'File',
      submenu: [
        {
          label: 'New Chat',
          accelerator: 'CmdOrCtrl+N',
          click: () => mainWindow?.webContents.send('new-chat'),
        },
        {
          label: 'New Window',
          accelerator: 'CmdOrCtrl+Shift+N',
          click: () => createMainWindow(),
        },
        { type: 'separator' },
        {
          label: 'Export Conversation',
          accelerator: 'CmdOrCtrl+E',
          click: () => mainWindow?.webContents.send('export-conversation'),
        },
        { type: 'separator' },
        isMac ? { role: 'close' } : { role: 'quit' },
      ],
    },

    // Edit menu
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
        { role: 'selectAll' },
        { type: 'separator' },
        {
          label: 'Find',
          accelerator: 'CmdOrCtrl+F',
          click: () => mainWindow?.webContents.send('open-search'),
        },
      ],
    },

    // View menu
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
        { type: 'separator' },
        {
          label: 'Toggle Sidebar',
          accelerator: 'CmdOrCtrl+B',
          click: () => mainWindow?.webContents.send('toggle-sidebar'),
        },
      ],
    },

    // Chat menu
    {
      label: 'Chat',
      submenu: [
        {
          label: 'Focus Input',
          accelerator: 'CmdOrCtrl+L',
          click: () => mainWindow?.webContents.send('focus-input'),
        },
        {
          label: 'Stop Generation',
          accelerator: 'Escape',
          click: () => mainWindow?.webContents.send('stop-generation'),
        },
        { type: 'separator' },
        {
          label: 'Previous Conversation',
          accelerator: 'CmdOrCtrl+[',
          click: () => mainWindow?.webContents.send('previous-conversation'),
        },
        {
          label: 'Next Conversation',
          accelerator: 'CmdOrCtrl+]',
          click: () => mainWindow?.webContents.send('next-conversation'),
        },
        { type: 'separator' },
        {
          label: 'Share Conversation',
          accelerator: 'CmdOrCtrl+Shift+S',
          click: () => mainWindow?.webContents.send('share-conversation'),
        },
      ],
    },

    // Window menu
    {
      label: 'Window',
      submenu: [
        { role: 'minimize' },
        { role: 'zoom' },
        ...(isMac
          ? [
              { type: 'separator' as const },
              { role: 'front' as const },
              { type: 'separator' as const },
              { role: 'window' as const },
            ]
          : [{ role: 'close' as const }]),
      ],
    },

    // Help menu
    {
      role: 'help',
      submenu: [
        {
          label: 'Documentation',
          click: () => shell.openExternal('https://docs.nexusai.dev'),
        },
        {
          label: 'Release Notes',
          click: () => shell.openExternal('https://nexusai.dev/changelog'),
        },
        { type: 'separator' },
        {
          label: 'Report Issue',
          click: () => shell.openExternal('https://github.com/nexusai/nexusai/issues'),
        },
        { type: 'separator' },
        {
          label: 'Check for Updates',
          click: () => autoUpdater.checkForUpdates(),
        },
      ],
    },
  ];

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// =============================================================================
// Global Shortcuts
// =============================================================================

function registerGlobalShortcuts(): void {
  // Quick access shortcut
  globalShortcut.register('CommandOrControl+Shift+Space', () => {
    showMainWindow();
    mainWindow?.webContents.send('focus-input');
  });
}

// =============================================================================
// Auto Updater
// =============================================================================

function setupAutoUpdater(): void {
  autoUpdater.autoDownload = false;

  autoUpdater.on('update-available', (info) => {
    dialog
      .showMessageBox({
        type: 'info',
        title: 'Update Available',
        message: `A new version (${info.version}) is available. Would you like to download it?`,
        buttons: ['Download', 'Later'],
      })
      .then((result) => {
        if (result.response === 0) {
          autoUpdater.downloadUpdate();
        }
      });
  });

  autoUpdater.on('update-downloaded', () => {
    dialog
      .showMessageBox({
        type: 'info',
        title: 'Update Ready',
        message: 'Update downloaded. The app will restart to install.',
        buttons: ['Restart Now', 'Later'],
      })
      .then((result) => {
        if (result.response === 0) {
          isQuitting = true;
          autoUpdater.quitAndInstall();
        }
      });
  });

  autoUpdater.on('error', (error) => {
    console.error('Auto-updater error:', error);
  });

  // Check for updates on startup (production only)
  if (!isDev) {
    autoUpdater.checkForUpdates();
  }
}

// =============================================================================
// IPC Handlers
// =============================================================================

function setupIpcHandlers(): void {
  // Get app info
  ipcMain.handle('get-app-info', () => ({
    version: app.getVersion(),
    platform: process.platform,
    isDev,
  }));

  // Get/set config
  ipcMain.handle('get-config', (_event, key: string) => getConfig(key));
  ipcMain.handle('set-config', (_event, key: string, value: unknown) => setConfig(key, value));

  // Show notification
  ipcMain.handle('show-notification', (_event, options: Electron.NotificationConstructorOptions) => {
    new Notification(options).show();
  });

  // Open external URL
  ipcMain.handle('open-external', (_event, url: string) => {
    shell.openExternal(url);
  });

  // Get theme
  ipcMain.handle('get-theme', () => nativeTheme.shouldUseDarkColors ? 'dark' : 'light');

  // Badge count (macOS/Linux)
  ipcMain.handle('set-badge-count', (_event, count: number) => {
    if (process.platform === 'darwin' || process.platform === 'linux') {
      app.setBadgeCount(count);
    }
  });
}

// =============================================================================
// Configuration Storage
// =============================================================================

const CONFIG_PATH = path.join(app.getPath('userData'), 'config.json');

function getConfig(key: string): unknown {
  try {
    if (fs.existsSync(CONFIG_PATH)) {
      const data = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
      return data[key];
    }
  } catch (error) {
    console.error('Error reading config:', error);
  }
  return undefined;
}

function setConfig(key: string, value: unknown): void {
  try {
    let data: Record<string, unknown> = {};
    if (fs.existsSync(CONFIG_PATH)) {
      data = JSON.parse(fs.readFileSync(CONFIG_PATH, 'utf-8'));
    }
    data[key] = value;
    fs.writeFileSync(CONFIG_PATH, JSON.stringify(data, null, 2));
  } catch (error) {
    console.error('Error writing config:', error);
  }
}

// =============================================================================
// Utilities
// =============================================================================

function getIconPath(): string {
  const iconName = process.platform === 'win32' ? 'icon.ico' : 'icon.png';
  return path.join(__dirname, 'assets', iconName);
}

function getTrayIconPath(): string {
  const iconName = process.platform === 'darwin' ? 'tray-icon-template.png' : 'tray-icon.png';
  return path.join(__dirname, 'assets', iconName);
}

// =============================================================================
// App Lifecycle
// =============================================================================

// Single instance lock
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', () => {
    showMainWindow();
  });

  app.whenReady().then(() => {
    createAppMenu();
    mainWindow = createMainWindow();
    tray = createTray();
    registerGlobalShortcuts();
    setupIpcHandlers();
    setupAutoUpdater();
  });

  app.on('activate', () => {
    // macOS: Re-create window when dock icon is clicked
    if (BrowserWindow.getAllWindows().length === 0) {
      mainWindow = createMainWindow();
    } else {
      showMainWindow();
    }
  });

  app.on('window-all-closed', () => {
    // Keep app running in tray on macOS
    if (process.platform !== 'darwin') {
      // On Windows/Linux, keep running if tray is active
      if (!tray) {
        app.quit();
      }
    }
  });

  app.on('before-quit', () => {
    isQuitting = true;
    globalShortcut.unregisterAll();
  });
}
