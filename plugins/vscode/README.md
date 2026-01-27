# NexusAI for Visual Studio Code

AI-powered software intelligence assistant for code analysis, documentation, and review.

## Features

### 💬 Chat Assistant
- Natural language interface for code questions
- Context-aware responses based on your codebase
- Code explanations and suggestions
- Streaming responses

### 🔍 Code Analysis
- Real-time bug detection
- Security vulnerability scanning
- Code smell detection
- Complexity analysis

### 📝 Documentation Generation
- Auto-generate docstrings and comments
- JSDoc, Python docstrings, and more
- Keep documentation in sync with code

### 🔧 Refactoring Suggestions
- AI-powered refactoring recommendations
- One-click code improvements
- Maintainability enhancements

### 🧪 Test Generation
- Generate unit tests for selected code
- Support for popular testing frameworks
- Coverage-focused test suggestions

### 📊 Code Metrics
- Cyclomatic complexity
- Maintainability index
- Lines of code analysis

## Installation

1. Install from the VS Code Marketplace
2. Configure your API key in settings
3. Start chatting with NexusAI!

## Configuration

Open Settings (Ctrl+,) and search for "NexusAI":

| Setting | Description | Default |
|---------|-------------|---------|
| `nexusai.apiEndpoint` | NexusAI API URL | `https://api.nexusai.dev` |
| `nexusai.apiKey` | Your API key | - |
| `nexusai.model` | Preferred AI model | `auto` |
| `nexusai.enableInlineHints` | Show inline hints | `true` |
| `nexusai.enableAutoAnalysis` | Auto-analyze on save | `false` |
| `nexusai.maxContextLines` | Max context lines | `100` |

## Commands

| Command | Description | Shortcut |
|---------|-------------|----------|
| `NexusAI: Open Chat` | Open the chat panel | `Ctrl+Shift+N` |
| `NexusAI: Explain Code` | Explain selected code | `Ctrl+Shift+E` |
| `NexusAI: Ask Question` | Ask about selection | `Ctrl+Shift+A` |
| `NexusAI: Review Code` | Analyze for issues | - |
| `NexusAI: Generate Docs` | Generate documentation | - |
| `NexusAI: Find Bugs` | Find potential bugs | - |
| `NexusAI: Suggest Refactoring` | Get refactoring ideas | - |
| `NexusAI: Generate Tests` | Generate unit tests | - |
| `NexusAI: Analyze File` | Analyze current file | - |
| `NexusAI: Show Metrics` | Show code metrics | - |
| `NexusAI: Review PR` | Review Git changes | - |

## Context Menu

Right-click on selected code to access NexusAI commands:

- Explain Code
- Review Code
- Generate Documentation
- Find Bugs
- Suggest Refactoring
- Generate Tests
- Ask Question

## Quick Fixes

When NexusAI detects issues, you can:
- Click the lightbulb icon
- Press `Ctrl+.` on the issue
- Select "Fix with NexusAI" or "Explain Issue"

## Requirements

- VS Code 1.85.0 or higher
- NexusAI account (free tier available)
- Internet connection

## Privacy

- Code is sent to NexusAI servers for analysis
- No code is stored permanently
- Enterprise customers can use self-hosted models
- See our [Privacy Policy](https://nexusai.dev/privacy)

## Support

- [Documentation](https://docs.nexusai.dev/vscode)
- [GitHub Issues](https://github.com/nexusai/vscode-extension/issues)
- [Discord Community](https://discord.gg/nexusai)

## License

MIT License - see [LICENSE](LICENSE) for details.
