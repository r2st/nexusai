# NexusAI Desktop

Native desktop application for NexusAI - AI-powered software intelligence platform.

## Features

- **Native Experience**: Full desktop application with system integration
- **Offline Support**: Work with cached conversations offline
- **Global Shortcuts**: Quick access from anywhere (Ctrl+Shift+Space)
- **System Tray**: Always-accessible background operation
- **Auto Updates**: Automatic updates for new features and fixes
- **Deep Links**: Open `nexusai://` links directly in the app

## Installation

### Download

- **macOS**: [Download DMG](https://github.com/nexusai/desktop/releases)
- **Windows**: [Download Installer](https://github.com/nexusai/desktop/releases)
- **Linux**: [Download AppImage](https://github.com/nexusai/desktop/releases)

### Build from Source

```bash
# Install dependencies
npm install

# Development
npm run dev

# Build for current platform
npm run dist

# Build for specific platform
npm run dist:mac
npm run dist:win
npm run dist:linux
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+Space` | Quick Ask (global) |
| `Ctrl+Shift+N` | Show/Hide window (global) |
| `Ctrl+N` | New chat |
| `Ctrl+L` | Focus input |
| `Escape` | Stop generation |
| `Ctrl+B` | Toggle sidebar |
| `Ctrl+[` | Previous conversation |
| `Ctrl+]` | Next conversation |
| `Ctrl+Shift+F` | Search conversations |
| `Ctrl+Shift+E` | Export conversation |
| `Ctrl+,` | Settings |

## System Requirements

- **macOS**: 10.15 (Catalina) or later
- **Windows**: Windows 10 or later
- **Linux**: Ubuntu 18.04, Fedora 32, or equivalent

## Architecture

```
desktop/
├── src/
│   └── main/           # Electron main process
│       ├── main.ts     # Entry point
│       ├── preload.ts  # Preload script (IPC bridge)
│       ├── menu.ts     # Application menu
│       └── ipc-handlers.ts
├── assets/             # App icons
├── package.json
└── tsconfig.main.json
```

The renderer process uses the shared Next.js frontend from `../frontend/`.

## Configuration

Settings are stored in the user data directory:
- **macOS**: `~/Library/Application Support/NexusAI/`
- **Windows**: `%APPDATA%\NexusAI\`
- **Linux**: `~/.config/NexusAI/`

## Development

### Running in Development

```bash
# Start the development server
npm run dev
```

This runs:
1. TypeScript compiler in watch mode for main process
2. Next.js dev server for renderer

### Building

```bash
# Build for production
npm run build

# Package without publishing
npm run pack

# Create distributable
npm run dist
```

### Code Signing

For macOS, set up code signing:

```bash
# Set environment variables
export CSC_LINK=/path/to/certificate.p12
export CSC_KEY_PASSWORD=your-password
export APPLE_ID=your-apple-id
export APPLE_ID_PASSWORD=app-specific-password
```

For Windows, use a code signing certificate via SignTool.

## Auto Updates

The app uses `electron-updater` for automatic updates:

1. Updates are checked on startup and periodically
2. Users are notified when updates are available
3. Updates are downloaded in the background
4. Updates are installed on next app restart

Configure update server in `package.json`:

```json
{
  "build": {
    "publish": {
      "provider": "github",
      "owner": "nexusai",
      "repo": "nexusai-desktop"
    }
  }
}
```

## License

MIT License - see [LICENSE](LICENSE) for details.
