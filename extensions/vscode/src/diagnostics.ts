import * as vscode from 'vscode';
import { NexusAIClient, AnalysisIssue, AnalysisResult } from './client';

export class DiagnosticsProvider implements vscode.Disposable {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private client: NexusAIClient;
    private analysisResults: Map<string, AnalysisResult> = new Map();
    private debounceTimers: Map<string, NodeJS.Timeout> = new Map();
    private config: vscode.WorkspaceConfiguration;

    constructor(client: NexusAIClient, context: vscode.ExtensionContext) {
        this.client = client;
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('nexusai');
        this.config = vscode.workspace.getConfiguration('nexusai');

        // Analyze on type if enabled
        if (this.config.get<boolean>('analyzeOnType', false)) {
            context.subscriptions.push(
                vscode.workspace.onDidChangeTextDocument(e => {
                    this.debounceAnalyze(e.document);
                })
            );
        }

        // Clear diagnostics when document is closed
        context.subscriptions.push(
            vscode.workspace.onDidCloseTextDocument(document => {
                this.diagnosticCollection.delete(document.uri);
                this.analysisResults.delete(document.uri.toString());
            })
        );
    }

    updateConfig(config: vscode.WorkspaceConfiguration) {
        this.config = config;
    }

    private debounceAnalyze(document: vscode.TextDocument) {
        const uri = document.uri.toString();
        const timer = this.debounceTimers.get(uri);

        if (timer) {
            clearTimeout(timer);
        }

        const delay = this.config.get<number>('analyzeDelay', 500);
        this.debounceTimers.set(uri, setTimeout(() => {
            this.analyzeDocument(document);
            this.debounceTimers.delete(uri);
        }, delay));
    }

    async analyzeDocument(document: vscode.TextDocument): Promise<void> {
        // Check if language is enabled
        const enabledLanguages = this.config.get<string[]>('enabledLanguages', []);
        if (!enabledLanguages.includes(document.languageId)) {
            return;
        }

        // Check file size
        const maxFileSize = this.config.get<number>('maxFileSize', 500) * 1024;
        if (document.getText().length > maxFileSize) {
            console.log(`File too large to analyze: ${document.uri.toString()}`);
            return;
        }

        try {
            const result = await this.client.analyze(
                document.uri.toString(),
                document.getText(),
                document.languageId,
                document.version
            );

            this.analysisResults.set(document.uri.toString(), result);
            this.updateDiagnostics(document.uri, result.issues);

        } catch (error) {
            console.error(`Analysis failed for ${document.uri.toString()}:`, error);
            // Clear diagnostics on error
            this.diagnosticCollection.delete(document.uri);
        }
    }

    private updateDiagnostics(uri: vscode.Uri, issues: AnalysisIssue[]): void {
        const severityThreshold = this.config.get<string>('severityThreshold', 'info');
        const severityOrder = ['error', 'warning', 'info', 'hint'];
        const thresholdIndex = severityOrder.indexOf(severityThreshold);

        const diagnostics: vscode.Diagnostic[] = issues
            .filter(issue => severityOrder.indexOf(issue.severity) <= thresholdIndex)
            .map(issue => this.issueToDiagnostic(issue));

        this.diagnosticCollection.set(uri, diagnostics);
    }

    private issueToDiagnostic(issue: AnalysisIssue): vscode.Diagnostic {
        const range = new vscode.Range(
            new vscode.Position(issue.range.start.line, issue.range.start.character),
            new vscode.Position(issue.range.end.line, issue.range.end.character)
        );

        const severity = this.mapSeverity(issue.severity);
        const diagnostic = new vscode.Diagnostic(range, issue.message, severity);

        diagnostic.source = 'NexusAI';
        diagnostic.code = issue.code ? {
            value: issue.code,
            target: issue.code_description
                ? vscode.Uri.parse(`https://nexusai.dev/docs/issues/${issue.code}`)
                : undefined
        } : undefined;

        // Add tags for deprecated or unnecessary code
        if (issue.category === 'deprecated') {
            diagnostic.tags = [vscode.DiagnosticTag.Deprecated];
        } else if (issue.tags?.includes('unnecessary')) {
            diagnostic.tags = [vscode.DiagnosticTag.Unnecessary];
        }

        // Store the full issue for code actions
        (diagnostic as any).nexusaiIssue = issue;

        return diagnostic;
    }

    private mapSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'info':
                return vscode.DiagnosticSeverity.Information;
            case 'hint':
            default:
                return vscode.DiagnosticSeverity.Hint;
        }
    }

    getIssuesForDocument(uri: vscode.Uri): AnalysisIssue[] {
        const result = this.analysisResults.get(uri.toString());
        return result?.issues || [];
    }

    getAnalysisResult(uri: vscode.Uri): AnalysisResult | undefined {
        return this.analysisResults.get(uri.toString());
    }

    getAllIssues(): { uri: vscode.Uri; issues: AnalysisIssue[] }[] {
        const result: { uri: vscode.Uri; issues: AnalysisIssue[] }[] = [];

        this.analysisResults.forEach((analysis, uriString) => {
            result.push({
                uri: vscode.Uri.parse(uriString),
                issues: analysis.issues
            });
        });

        return result;
    }

    getTotalIssueCount(): { errors: number; warnings: number; info: number; hint: number } {
        let errors = 0, warnings = 0, info = 0, hint = 0;

        this.analysisResults.forEach(result => {
            result.issues.forEach(issue => {
                switch (issue.severity) {
                    case 'error': errors++; break;
                    case 'warning': warnings++; break;
                    case 'info': info++; break;
                    case 'hint': hint++; break;
                }
            });
        });

        return { errors, warnings, info, hint };
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
    }
}
