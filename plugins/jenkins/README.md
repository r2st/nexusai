# NexusAI Jenkins Plugin

Jenkins plugin for NexusAI CI/CD integration.

## Features

- **Build Analysis**: AI-powered analysis of build failures
- **Quality Gates**: Automated code quality checks
- **PR Integration**: Automatic PR review on builds
- **Metrics Collection**: DORA metrics and build insights
- **Notifications**: Smart alerts and summaries

## Installation

### From Jenkins Update Center
1. Manage Jenkins → Plugin Manager
2. Search for "NexusAI"
3. Install and restart Jenkins

### Manual Installation
1. Download `nexusai.hpi` from releases
2. Manage Jenkins → Plugin Manager → Advanced
3. Upload the plugin file
4. Restart Jenkins

## Configuration

### Global Configuration
1. Manage Jenkins → Configure System
2. Find "NexusAI" section
3. Enter API endpoint and credentials

### Pipeline Usage

```groovy
pipeline {
    agent any
    
    stages {
        stage('Build') {
            steps {
                // Your build steps
            }
        }
        
        stage('NexusAI Analysis') {
            steps {
                nexusaiAnalyze()
            }
        }
        
        stage('Quality Gate') {
            steps {
                nexusaiQualityGate(
                    threshold: 'high',
                    failOnIssues: true
                )
            }
        }
    }
    
    post {
        failure {
            nexusaiNotify(
                channel: '#builds',
                includeAnalysis: true
            )
        }
    }
}
```

## Available Steps

### nexusaiAnalyze
Analyze build results and code changes.

```groovy
nexusaiAnalyze(
    includeTests: true,
    includeLogs: true,
    depth: 'full'
)
```

### nexusaiQualityGate
Enforce quality standards.

```groovy
nexusaiQualityGate(
    threshold: 'medium',  // low, medium, high, critical
    failOnIssues: true,
    categories: ['security', 'performance']
)
```

### nexusaiReviewPR
Review pull request changes.

```groovy
nexusaiReviewPR(
    postComments: true,
    requireApproval: false
)
```

### nexusaiNotify
Send notifications with AI insights.

```groovy
nexusaiNotify(
    channel: '#engineering',
    includeAnalysis: true,
    mentionOnFailure: '@oncall'
)
```

## Development

### Prerequisites
- Java 11+
- Maven 3.8+

### Build
```bash
mvn clean package
```

### Test
```bash
mvn test
```

### Run Local Jenkins
```bash
mvn hpi:run
```
