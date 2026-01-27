import * as tl from 'azure-pipelines-task-lib/task';
import * as axios from 'axios';

interface BuildContext {
    pipelineName: string;
    buildNumber: string;
    status: string;
    sourceVersion: string;
    sourceBranch: string;
    logs?: string;
}

interface AnalysisResult {
    summary: string;
    rootCause?: string;
    suggestions?: string[];
    severity?: string;
    metrics?: Record<string, unknown>;
}

async function run(): Promise<void> {
    try {
        // Get inputs
        const serviceConnection = tl.getInput('serviceConnection', true)!;
        const includeTests = tl.getBoolInput('includeTests', false);
        const includeLogs = tl.getBoolInput('includeLogs', false);
        const depth = tl.getInput('depth', false) || 'standard';

        // Get service connection details
        const endpoint = tl.getEndpointUrl(serviceConnection, false);
        const token = tl.getEndpointAuthorizationParameter(
            serviceConnection,
            'apitoken',
            false
        );

        if (!endpoint || !token) {
            throw new Error('Invalid service connection configuration');
        }

        console.log('[NexusAI] Starting build analysis...');
        console.log(`  Analysis depth: ${depth}`);

        // Build context from environment
        const context: BuildContext = {
            pipelineName: tl.getVariable('Build.DefinitionName') || '',
            buildNumber: tl.getVariable('Build.BuildNumber') || '',
            status: tl.getVariable('Agent.JobStatus') || 'Unknown',
            sourceVersion: tl.getVariable('Build.SourceVersion') || '',
            sourceBranch: tl.getVariable('Build.SourceBranch') || '',
        };

        // Include logs if requested
        if (includeLogs) {
            // In real implementation, would fetch actual logs
            context.logs = 'Build log content...';
        }

        // Call NexusAI API
        const response = await axios.default.post<AnalysisResult>(
            `${endpoint}/api/v2/ci/analyze`,
            {
                pipeline_name: context.pipelineName,
                build_number: context.buildNumber,
                status: context.status,
                source_version: context.sourceVersion,
                source_branch: context.sourceBranch,
                include_tests: includeTests,
                depth: depth,
                logs: context.logs,
            },
            {
                headers: {
                    'Authorization': `Bearer ${token}`,
                    'Content-Type': 'application/json',
                    'X-Client': 'azure-devops-extension',
                },
            }
        );

        const result = response.data;

        // Output results
        console.log('[NexusAI] Analysis complete:');
        console.log(`  Summary: ${result.summary}`);

        if (result.rootCause) {
            console.log(`  Root Cause: ${result.rootCause}`);
        }

        if (result.suggestions && result.suggestions.length > 0) {
            console.log('  Suggestions:');
            result.suggestions.forEach((suggestion) => {
                console.log(`    - ${suggestion}`);
            });
        }

        // Set output variables
        tl.setVariable('NexusAI.AnalysisSummary', result.summary);
        if (result.rootCause) {
            tl.setVariable('NexusAI.RootCause', result.rootCause);
        }
        if (result.severity) {
            tl.setVariable('NexusAI.Severity', result.severity);
        }

        tl.setResult(tl.TaskResult.Succeeded, 'Analysis completed successfully');
    } catch (err: unknown) {
        const error = err as Error;
        tl.setResult(tl.TaskResult.Failed, error.message);
    }
}

run();
