# NexusAI Azure DevOps Extension

Azure DevOps extension for NexusAI integration.

## Features

- **Pipeline Tasks**: AI-powered build analysis and quality gates
- **PR Decoration**: Automatic AI review comments on pull requests
- **Work Item Integration**: Link insights to work items
- **Dashboard Widgets**: DORA metrics and code health visualization

## Installation

### From Marketplace
1. Go to Azure DevOps Marketplace
2. Search for "NexusAI"
3. Install to your organization

### Manual Installation
1. Download `.vsix` from releases
2. Go to Organization Settings → Extensions
3. Upload the extension

## Configuration

### Service Connection
1. Project Settings → Service Connections
2. New → NexusAI
3. Enter endpoint and API token

## Pipeline Tasks

### NexusAI Analyze
```yaml
- task: NexusAIAnalyze@1
  inputs:
    serviceConnection: 'nexusai-connection'
    includeTests: true
    includeLogs: true
```

### NexusAI Quality Gate
```yaml
- task: NexusAIQualityGate@1
  inputs:
    serviceConnection: 'nexusai-connection'
    threshold: 'high'
    failOnIssues: true
    categories: 'security,performance'
```

### NexusAI PR Review
```yaml
- task: NexusAIPRReview@1
  inputs:
    serviceConnection: 'nexusai-connection'
    postComments: true
  condition: eq(variables['Build.Reason'], 'PullRequest')
```

### NexusAI Notify
```yaml
- task: NexusAINotify@1
  inputs:
    serviceConnection: 'nexusai-connection'
    channel: '#builds'
    includeAnalysis: true
  condition: failed()
```

## Dashboard Widgets

### DORA Metrics
Display deployment frequency, lead time, MTTR, and change failure rate.

### Code Health
Show code quality trends and technical debt metrics.

### AI Insights
Recent AI analysis results and recommendations.

## Development

### Prerequisites
- Node.js 18+
- tfx-cli (`npm install -g tfx-cli`)

### Build
```bash
npm install
npm run build
```

### Package
```bash
tfx extension create --manifest-globs vss-extension.json
```

### Publish
```bash
tfx extension publish --token <PAT>
```
