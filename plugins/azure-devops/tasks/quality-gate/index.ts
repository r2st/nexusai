import * as tl from 'azure-pipelines-task-lib/task';
import * as axios from 'axios';

interface QualityGateResult {
    passed: boolean;
    status: string;
    score: number;
    issues: Issue[];
}

interface Issue {
    type: string;
    severity: string;
    message: string;
    file?: string;
    line?: number;
}

async function run(): Promise<void> {
    try {
        // Get inputs
        const serviceConnection = tl.getInput('serviceConnection', true)!;
        const threshold = tl.getInput('threshold', true)!;
        const failOnIssues = tl.getBoolInput('failOnIssues', false);
        const categoriesInput = tl.getInput('categories', false);
        const categories = categoriesInput
            ? categoriesInput.split(',').map((c) => c.trim())
            : undefined;

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

        console.log('[NexusAI] Running quality gate check...');
        console.log(`  Threshold: ${threshold}`);
        console.log(`  Fail on issues: ${failOnIssues}`);
        if (categories) {
            console.log(`  Categories: ${categories.join(', ')}`);
        }

        // Call NexusAI API
        const response = await axios.default.post<QualityGateResult>(
            `${endpoint}/api/v2/ci/quality-gate`,
            {
                threshold,
                fail_on_issues: failOnIssues,
                categories,
                pipeline_name: tl.getVariable('Build.DefinitionName'),
                build_number: tl.getVariable('Build.BuildNumber'),
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
        console.log('[NexusAI] Quality Gate Result:');
        console.log(`  Status: ${result.status}`);
        console.log(`  Passed: ${result.passed}`);
        console.log(`  Score: ${result.score}`);

        if (result.issues && result.issues.length > 0) {
            console.log(`  Issues found: ${result.issues.length}`);
            result.issues.forEach((issue) => {
                const location = issue.file ? ` at ${issue.file}:${issue.line}` : '';
                console.log(`    [${issue.severity}] ${issue.message}${location}`);
            });
        }

        // Set output variables
        tl.setVariable('NexusAI.QualityGatePassed', String(result.passed));
        tl.setVariable('NexusAI.QualityScore', String(result.score));
        tl.setVariable('NexusAI.IssueCount', String(result.issues?.length || 0));

        // Determine result
        if (!result.passed && failOnIssues) {
            tl.setResult(
                tl.TaskResult.Failed,
                `Quality gate failed: ${result.status}`
            );
        } else {
            tl.setResult(
                tl.TaskResult.Succeeded,
                `Quality gate ${result.passed ? 'passed' : 'completed with warnings'}`
            );
        }
    } catch (err: unknown) {
        const error = err as Error;
        tl.setResult(tl.TaskResult.Failed, error.message);
    }
}

run();
