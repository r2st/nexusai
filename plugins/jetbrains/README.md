# NexusAI JetBrains Plugin

IntelliJ IDEA / WebStorm / PyCharm plugin for NexusAI integration.

## Features

- **AI-Powered Code Assistant**: Get contextual code suggestions and explanations
- **Code Review**: AI-assisted pull request review within the IDE
- **Documentation Generation**: Auto-generate docs for functions and classes
- **Bug Detection**: Real-time code analysis for potential issues
- **Team Collaboration**: Share insights and collaborate in real-time

## Installation

### From JetBrains Marketplace
1. Open IDE Settings → Plugins
2. Search for "NexusAI"
3. Click Install

### Manual Installation
1. Download the latest `.zip` from releases
2. Open IDE Settings → Plugins → ⚙️ → Install Plugin from Disk
3. Select the downloaded file

## Configuration

1. Open Settings → Tools → NexusAI
2. Enter your NexusAI API endpoint and token
3. Configure team settings if needed

## Usage

### Code Assistant
- **Alt+Enter** on any code selection → "Ask NexusAI"
- Right-click context menu → NexusAI submenu

### Review
- Open VCS → Pull Requests
- Click "AI Review" on any PR

### Documentation
- Select code → Right-click → "Generate Documentation"

## Development

### Prerequisites
- IntelliJ IDEA 2023.1+
- JDK 17+
- Gradle 8+

### Build
```bash
./gradlew build
```

### Run IDE with Plugin
```bash
./gradlew runIde
```

### Test
```bash
./gradlew test
```

## Project Structure

```
jetbrains/
├── src/
│   └── main/
│       ├── kotlin/
│       │   └── com/nexusai/plugin/
│       │       ├── NexusAIPlugin.kt
│       │       ├── actions/
│       │       ├── services/
│       │       ├── ui/
│       │       └── settings/
│       └── resources/
│           └── META-INF/
│               └── plugin.xml
├── build.gradle.kts
└── gradle.properties
```
