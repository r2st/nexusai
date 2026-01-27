# NexusAI GitHub Action

Run AI-powered code analysis and quality gate checks on your pull requests.

## Features

- **Code Analysis**: Detect bugs, security vulnerabilities, and code smells
- **Quality Gates**: Configurable pass/fail criteria for PRs
- **PR Comments**: Automatic summary comments on pull requests
- **Badges**: Dynamic quality score badges for your README

## Usage

### Basic Usage

```yaml
name: Code Quality

on:
  pull_request:
    branches: [main, develop]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0  # Required for diff detection

      - name: NexusAI Quality Gate
        uses: nexusai/github-action@v1
        with:
          api-key: ${{ secrets.NEXUSAI_API_KEY }}
```

### Advanced Usage

```yaml
name: Code Quality

on:
  pull_request:
    branches: [main, develop]
  push:
    branches: [main]

jobs:
  quality-gate:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0

      - name: NexusAI Quality Gate
        id: quality
        uses: nexusai/github-action@v1
        with:
          api-key: ${{ secrets.NEXUSAI_API_KEY }}
          nexusai-server: 'https://api.nexusai.dev'
          config-name: 'strict'
          fail-on-quality-gate: 'true'
          post-pr-comment: 'true'
          include-patterns: '**/*.py,**/*.ts,**/*.tsx'
          exclude-patterns: '**/tests/**,**/node_modules/**'
          max-files: '50'

      - name: Use outputs
        run: |
          echo "Status: ${{ steps.quality.outputs.status }}"
          echo "Quality Score: ${{ steps.quality.outputs.quality-score }}"
          echo "Total Issues: ${{ steps.quality.outputs.total-issues }}"
```

## Inputs

| Input | Description | Required | Default |
|-------|-------------|----------|---------|
| `api-key` | NexusAI API key | Yes | - |
| `nexusai-server` | NexusAI server URL | No | `https://api.nexusai.dev` |
| `config-name` | Quality gate configuration name | No | `default` |
| `fail-on-quality-gate` | Fail workflow if quality gate fails | No | `true` |
| `post-pr-comment` | Post results as PR comment | No | `true` |
| `include-patterns` | File patterns to include (comma-separated) | No | `**/*.py,**/*.ts,...` |
| `exclude-patterns` | File patterns to exclude (comma-separated) | No | `**/node_modules/**,...` |
| `max-files` | Maximum files to analyze | No | `100` |

## Outputs

| Output | Description |
|--------|-------------|
| `status` | Quality gate status (`passed`, `failed`, `warning`) |
| `passed` | Whether quality gate passed (`true`/`false`) |
| `total-issues` | Total number of issues found |
| `critical-issues` | Number of critical issues |
| `security-issues` | Number of security issues |
| `quality-score` | Code quality score (0-10) |
| `badge-url` | URL for quality gate badge |
| `summary` | Quality gate summary message |

## Quality Gate Configurations

### Default Configuration

The default quality gate includes these conditions:

- **No Critical Issues**: Any critical severity issue fails the gate
- **No Security Vulnerabilities**: Any security issue fails the gate
- **Limited New Issues**: Warning if more than 10 new issues (doesn't fail)
- **Code Quality Score**: Warning if score below 7.0 (doesn't fail)

### Custom Configurations

Create custom configurations via the NexusAI API:

```bash
curl -X PUT https://api.nexusai.dev/api/v1/quality-gate/config \
  -H "Authorization: Bearer $NEXUSAI_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "strict",
    "conditions": [
      {
        "name": "Zero Issues",
        "thresholds": [
          {"metric": "total_issues", "operator": "eq", "value": 0, "level": "error"}
        ],
        "required": true
      }
    ]
  }'
```

## Badge

Add a quality badge to your README:

```markdown
![NexusAI Quality](https://api.nexusai.dev/badge/{owner}/{repo})
```

## Getting Started

1. Sign up at [nexusai.dev](https://nexusai.dev)
2. Create an API key in your dashboard
3. Add `NEXUSAI_API_KEY` to your repository secrets
4. Add the action to your workflow

## Examples

### Block merges on security issues

```yaml
- name: NexusAI Security Check
  uses: nexusai/github-action@v1
  with:
    api-key: ${{ secrets.NEXUSAI_API_KEY }}
    config-name: 'security-only'
    fail-on-quality-gate: 'true'
```

### Run on specific directories

```yaml
- name: NexusAI Quality Gate
  uses: nexusai/github-action@v1
  with:
    api-key: ${{ secrets.NEXUSAI_API_KEY }}
    include-patterns: 'src/**/*.ts,lib/**/*.ts'
    exclude-patterns: 'src/**/*.test.ts'
```

### Warning-only mode (no failures)

```yaml
- name: NexusAI Quality Gate
  uses: nexusai/github-action@v1
  with:
    api-key: ${{ secrets.NEXUSAI_API_KEY }}
    fail-on-quality-gate: 'false'
    post-pr-comment: 'true'
```

## Support

- Documentation: [docs.nexusai.dev](https://docs.nexusai.dev)
- Issues: [GitHub Issues](https://github.com/nexusai/github-action/issues)
- Email: support@nexusai.dev
