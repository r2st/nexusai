# NexusAI Mobile

React Native mobile application for NexusAI - AI-powered software intelligence platform.

## Features

- **Chat Interface**: Natural language conversations with AI assistant
- **Project Analysis**: View code metrics and quality reports
- **Conversation History**: Access and continue past conversations
- **Push Notifications**: Stay updated on analysis results
- **Offline Support**: View cached conversations offline
- **Dark Mode**: Automatic theme switching based on system settings

## Requirements

- Node.js 18+
- Expo CLI
- iOS Simulator (macOS) or Android Emulator

## Installation

```bash
# Install dependencies
npm install

# Start development server
npm start

# Run on iOS
npm run ios

# Run on Android
npm run android
```

## Project Structure

```
mobile/
├── App.tsx                 # App entry point
├── app.json               # Expo configuration
├── src/
│   ├── components/        # Reusable UI components
│   │   ├── MessageBubble.tsx
│   │   ├── QuickActions.tsx
│   │   └── TypingIndicator.tsx
│   ├── contexts/          # React contexts
│   │   ├── AuthContext.tsx
│   │   └── ThemeContext.tsx
│   ├── navigation/        # Navigation configuration
│   │   └── index.tsx
│   ├── screens/           # Screen components
│   │   ├── ChatScreen.tsx
│   │   ├── HistoryScreen.tsx
│   │   ├── AnalysisScreen.tsx
│   │   ├── SettingsScreen.tsx
│   │   ├── LoginScreen.tsx
│   │   └── OnboardingScreen.tsx
│   └── services/          # API and utilities
│       └── api.ts
└── assets/                # Images and fonts
```

## Screens

### Chat Screen
Main interface for interacting with NexusAI. Features:
- Real-time message streaming
- Code syntax highlighting
- Quick action buttons
- Copy/paste support

### History Screen
Browse and search conversation history:
- Search by title or content
- Delete conversations
- Continue previous chats

### Analysis Screen
View project metrics and code health:
- Overall code health score
- Complexity metrics
- Test coverage
- Issue tracking

### Settings Screen
Configure app preferences:
- Theme (light/dark/system)
- AI model selection
- Notification settings
- Account management

## Building for Production

### iOS

```bash
# Build for App Store
eas build --platform ios --profile production

# Submit to App Store
eas submit --platform ios
```

### Android

```bash
# Build for Play Store
eas build --platform android --profile production

# Submit to Play Store
eas submit --platform android
```

## Configuration

Create an `eas.json` file for build profiles:

```json
{
  "cli": {
    "version": ">= 5.0.0"
  },
  "build": {
    "development": {
      "developmentClient": true,
      "distribution": "internal"
    },
    "preview": {
      "distribution": "internal"
    },
    "production": {}
  },
  "submit": {
    "production": {}
  }
}
```

## Environment Variables

Set in `app.json` under `extra`:

```json
{
  "extra": {
    "apiUrl": "https://api.nexusai.dev"
  }
}
```

## Testing

```bash
# Run unit tests
npm test

# Run with coverage
npm test -- --coverage
```

## License

MIT License - see [LICENSE](LICENSE) for details.
