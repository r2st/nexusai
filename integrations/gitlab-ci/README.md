# NexusAI GitLab CI Integration

Integrate NexusAI quality gates, code review, and DORA metrics into your GitLab CI/CD pipelines.

## Features

- **Quality Gate Analysis**: Automated code quality checks on merge requests and pushes
- **Code Review**: AI-powered code review comments on merge requests
- **DORA Metrics**: Automatic deployment tracking for DORA metrics calculation
- **MR Comments**: Automated feedback posted directly to merge requests

## Quick Start

### 1. Set Up CI/CD Variables

Add the following variables to your GitLab project (Settings → CI/CD → Variables):

| Variable | Description | Required |
|----------|-------------|----------|
| `NEXUSAI_API_URL` | Your NexusAI API URL (e.g., `https://api.nexusai.dev`) | Yes |
| `NEXUSAI_API_KEY` | Your NexusAI API key | Yes |
| `GITLAB_TOKEN` | GitLab personal access token for MR comments | Optional |

### 2. Include the Template

Add to your `.gitlab-ci.yml`:

```yaml
include:
  - remote: 'https://raw.githubusercontent.com/nexusai/integrations/main/gitlab-ci/.gitlab-ci.yml'

variables:
  NEXUSAI_API_URL: ${NEXUSAI_API_URL}
  NEXUSAI_API_KEY: ${NEXUSAI_API_KEY}
```

Or copy the jobs directly into your pipeline configuration.

## Jobs

### nexusai-quality-gate

Runs quality analysis on code changes and enforces quality gates.

**Triggers:**
- Merge request events
- Pushes to default branch

**Behavior:**
- Analyzes changed files
- Reports issues (bugs, security, style)
- Fails pipeline if quality gate fails
- Posts summary comment on MR

**Configuration:**

```yaml
variables:
  NEXUSAI_FAIL_ON_CRITICAL: "true"   # Fail on critical issues
  NEXUSAI_FAIL_ON_SECURITY: "true"   # Fail on security issues
```

### nexusai-dora-metrics

Reports deployment events for DORA metrics tracking.

**Triggers:**
- Successful deployments to default branch

**Tracked Metrics:**
- Deployment Frequency
- Lead Time for Changes
- Mean Time to Recovery
- Change Failure Rate

### nexusai-code-review

Requests AI-powered code review for merge requests.

**Triggers:**
- Merge request events

**Behavior:**
- Analyzes code diff
- Provides suggestions and feedback
- Posts review as MR comment

## Configuration Options

### Quality Gate Thresholds

Configure in your NexusAI dashboard or via API:

```json
{
  "max_critical_issues": 0,
  "max_security_issues": 0,
  "min_code_coverage": 80,
  "max_complexity": 15
}
```

### Custom Rules

Add a `.nexusai.yml` to your repository root:

```yaml
quality_gate:
  enabled: true
  fail_on_critical: true
  fail_on_security: true

  thresholds:
    critical_issues: 0
    high_issues: 5
    code_coverage: 80
    complexity: 15

  exclude:
    - "*.test.ts"
    - "**/__mocks__/**"
    - "vendor/**"

code_review:
  enabled: true
  auto_comment: true
  focus_areas:
    - security
    - performance
    - maintainability

dora_metrics:
  enabled: true
  environments:
    - production
    - staging
```

## Environment-Specific Configuration

### Production Pipeline

```yaml
nexusai-quality-gate:
  rules:
    - if: $CI_COMMIT_BRANCH == "main"
      variables:
        NEXUSAI_FAIL_ON_CRITICAL: "true"
        NEXUSAI_FAIL_ON_SECURITY: "true"
```

### Development Pipeline

```yaml
nexusai-quality-gate:
  rules:
    - if: $CI_COMMIT_BRANCH != "main"
      variables:
        NEXUSAI_FAIL_ON_CRITICAL: "false"
      allow_failure: true
```

## Artifacts

The quality gate job produces artifacts:

- `nexusai-report.json`: Full analysis report
- `nexusai.env`: Key metrics as environment variables

Access in subsequent jobs:

```yaml
deploy:
  needs:
    - nexusai-quality-gate
  script:
    - source nexusai.env
    - echo "Quality Score: $NEXUSAI_QUALITY_SCORE"
```

## Troubleshooting

### API Connection Issues

1. Verify `NEXUSAI_API_URL` is correct
2. Check `NEXUSAI_API_KEY` has proper permissions
3. Ensure network access to NexusAI API

### MR Comments Not Appearing

1. Verify `GITLAB_TOKEN` is set
2. Token needs `api` scope
3. Check token has access to the project

### Quality Gate Always Failing

1. Check thresholds in NexusAI dashboard
2. Review excluded paths configuration
3. Verify project is properly configured

## Support

- Documentation: https://docs.nexusai.dev/integrations/gitlab
- Issues: https://github.com/nexusai/nexusai/issues
- Support: support@nexusai.dev
