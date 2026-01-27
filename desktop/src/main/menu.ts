/**
 * NexusAI Desktop - Application Menu
 * 
 * Defines the native application menu for all platforms.
 */

import { app, BrowserWindow, Menu, MenuItemConstructorOptions, shell } from 'electron';
import Store from 'electron-store';

const isMac = process.platform === 'darwin';

export function createMenu(mainWindow: BrowserWindow, store: Store): Menu {
    const template: MenuItemConstructorOptions[] = [
        // App Menu (macOS only)
        ...(isMac ? [{
            label: app.name,
            submenu: [
                { role: 'about' as const },
                { type: 'separator' as const },
                {
                    label: 'Preferences...',
                    accelerator: 'Cmd+,',
                    click: () => mainWindow.webContents.send('open-settings')
                },
                { type: 'separator' as const },
                { role: 'services' as const },
                { type: 'separator' as const },
                { role: 'hide' as const },
                { role: 'hideOthers' as const },
                { role: 'unhide' as const },
                { type: 'separator' as const },
                { role: 'quit' as const }
            ]
        }] : []),

        // File Menu
        {
            label: 'File',
            submenu: [
                {
                    label: 'New Chat',
                    accelerator: 'CmdOrCtrl+N',
                    click: () => mainWindow.webContents.send('new-chat')
                },
                { type: 'separator' },
                {
                    label: 'Open Workspace...',
                    accelerator: 'CmdOrCtrl+O',
                    click: () => mainWindow.webContents.send('open-workspace')
                },
                { type: 'separator' },
                {
                    label: 'Export Conversation...',
                    accelerator: 'CmdOrCtrl+Shift+E',
                    click: () => mainWindow.webContents.send('export-conversation')
                },
                { type: 'separator' },
                ...(isMac ? [] : [
                    {
                        label: 'Settings',
                        accelerator: 'Ctrl+,',
                        click: () => mainWindow.webContents.send('open-settings')
                    },
                    { type: 'separator' as const },
                ]),
                isMac ? { role: 'close' as const } : { role: 'quit' as const }
            ]
        },

        // Edit Menu
        {
            label: 'Edit',
            submenu: [
                { role: 'undo' },
                { role: 'redo' },
                { type: 'separator' },
                { role: 'cut' },
                { role: 'copy' },
                { role: 'paste' },
                ...(isMac ? [
                    { role: 'pasteAndMatchStyle' as const },
                    { role: 'delete' as const },
                    { role: 'selectAll' as const },
                    { type: 'separator' as const },
                    {
                        label: 'Speech',
                        submenu: [
                            { role: 'startSpeaking' as const },
                            { role: 'stopSpeaking' as const }
                        ]
                    }
                ] : [
                    { role: 'delete' as const },
                    { type: 'separator' as const },
                    { role: 'selectAll' as const }
                ])
            ]
        },

        // View Menu
        {
            label: 'View',
            submenu: [
                {
                    label: 'Toggle Sidebar',
                    accelerator: 'CmdOrCtrl+B',
                    click: () => mainWindow.webContents.send('toggle-sidebar')
                },
                { type: 'separator' },
                { role: 'reload' },
                { role: 'forceReload' },
                { role: 'toggleDevTools' },
                { type: 'separator' },
                { role: 'resetZoom' },
                { role: 'zoomIn' },
                { role: 'zoomOut' },
                { type: 'separator' },
                { role: 'togglefullscreen' }
            ]
        },

        // Chat Menu
        {
            label: 'Chat',
            submenu: [
                {
                    label: 'Focus Input',
                    accelerator: 'CmdOrCtrl+L',
                    click: () => mainWindow.webContents.send('focus-input')
                },
                {
                    label: 'Stop Generation',
                    accelerator: 'Escape',
                    click: () => mainWindow.webContents.send('stop-generation')
                },
                { type: 'separator' },
                {
                    label: 'Previous Conversation',
                    accelerator: 'CmdOrCtrl+[',
                    click: () => mainWindow.webContents.send('previous-conversation')
                },
                {
                    label: 'Next Conversation',
                    accelerator: 'CmdOrCtrl+]',
                    click: () => mainWindow.webContents.send('next-conversation')
                },
                { type: 'separator' },
                {
                    label: 'Search Conversations',
                    accelerator: 'CmdOrCtrl+Shift+F',
                    click: () => mainWindow.webContents.send('open-search')
                },
                { type: 'separator' },
                {
                    label: 'Share Conversation',
                    accelerator: 'CmdOrCtrl+Shift+S',
                    click: () => mainWindow.webContents.send('share-conversation')
                }
            ]
        },

        // Window Menu
        {
            label: 'Window',
            submenu: [
                { role: 'minimize' },
                { role: 'zoom' },
                ...(isMac ? [
                    { type: 'separator' as const },
                    { role: 'front' as const },
                    { type: 'separator' as const },
                    { role: 'window' as const }
                ] : [
                    { role: 'close' as const }
                ])
            ]
        },

        // Help Menu
        {
            role: 'help',
            submenu: [
                {
                    label: 'Documentation',
                    click: () => shell.openExternal('https://docs.nexusai.dev')
                },
                {
                    label: 'Release Notes',
                    click: () => shell.openExternal('https://nexusai.dev/changelog')
                },
                { type: 'separator' },
                {
                    label: 'Report Issue',
                    click: () => shell.openExternal('https://github.com/nexusai/desktop/issues')
                },
                {
                    label: 'Community',
                    click: () => shell.openExternal('https://discord.gg/nexusai')
                },
                { type: 'separator' },
                {
                    label: 'Check for Updates...',
                    click: () => mainWindow.webContents.send('check-for-updates')
                },
                ...(isMac ? [] : [
                    { type: 'separator' as const },
                    {
                        label: 'About NexusAI',
                        click: () => mainWindow.webContents.send('show-about')
                    }
                ])
            ]
        }
    ];

    return Menu.buildFromTemplate(template);
}
