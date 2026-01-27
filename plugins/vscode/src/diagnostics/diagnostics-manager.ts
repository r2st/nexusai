/**
 * Diagnostics Manager
 * 
 * Manages VS Code diagnostics for code issues.
 */

import * as vscode from 'vscode';
import { CodeIssue } from '../services/nexusai-service';

export class DiagnosticsManager {
    private diagnosticCollection: vscode.DiagnosticCollection;
    private issueMap: Map<string, Map<string, CodeIssue>> = new Map();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('NexusAI');
    }

    updateDiagnostics(uri: vscode.Uri, issues: CodeIssue[]): void {
        const diagnostics: vscode.Diagnostic[] = [];
        const issueMapForUri = new Map<string, CodeIssue>();

        for (const issue of issues) {
            const range = new vscode.Range(
                issue.line - 1,
                issue.column - 1,
                (issue.endLine || issue.line) - 1,
                (issue.endColumn || issue.column + 10) - 1
            );

            const diagnostic = new vscode.Diagnostic(
                range,
                issue.message,
                this.getSeverity(issue.severity)
            );

            diagnostic.source = 'NexusAI';
            diagnostic.code = issue.code;

            // Create unique key for this diagnostic
            const key = `${issue.line}:${issue.column}:${issue.message}`;
            issueMapForUri.set(key, issue);

            diagnostics.push(diagnostic);
        }

        this.diagnosticCollection.set(uri, diagnostics);
        this.issueMap.set(uri.toString(), issueMapForUri);
    }

    getIssueForDiagnostic(uri: vscode.Uri, diagnostic: vscode.Diagnostic): CodeIssue | undefined {
        const issueMapForUri = this.issueMap.get(uri.toString());
        if (!issueMapForUri) return undefined;

        const key = `${diagnostic.range.start.line + 1}:${diagnostic.range.start.character + 1}:${diagnostic.message}`;
        return issueMapForUri.get(key);
    }

    clearDiagnostics(uri?: vscode.Uri): void {
        if (uri) {
            this.diagnosticCollection.delete(uri);
            this.issueMap.delete(uri.toString());
        } else {
            this.diagnosticCollection.clear();
            this.issueMap.clear();
        }
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
    }

    private getSeverity(severity: string): vscode.DiagnosticSeverity {
        switch (severity) {
            case 'error':
                return vscode.DiagnosticSeverity.Error;
            case 'warning':
                return vscode.DiagnosticSeverity.Warning;
            case 'info':
                return vscode.DiagnosticSeverity.Information;
            default:
                return vscode.DiagnosticSeverity.Hint;
        }
    }
}
