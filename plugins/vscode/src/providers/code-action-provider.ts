/**
 * Code Action Provider
 * 
 * Provides quick fixes and code actions for detected issues.
 */

import * as vscode from 'vscode';
import { NexusAIService, CodeIssue } from '../services/nexusai-service';
import { DiagnosticsManager } from '../diagnostics/diagnostics-manager';

export class CodeActionProvider implements vscode.CodeActionProvider {
    public static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix,
        vscode.CodeActionKind.RefactorRewrite,
    ];

    constructor(
        private readonly service: NexusAIService,
        private readonly diagnostics: DiagnosticsManager
    ) {}

    provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        _token: vscode.CancellationToken
    ): vscode.CodeAction[] {
        const actions: vscode.CodeAction[] = [];

        // Add quick fixes for NexusAI diagnostics
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source === 'NexusAI') {
                const issue = this.diagnostics.getIssueForDiagnostic(document.uri, diagnostic);
                if (issue) {
                    // Add "Fix with AI" action
                    const fixAction = new vscode.CodeAction(
                        `Fix: ${diagnostic.message}`,
                        vscode.CodeActionKind.QuickFix
                    );
                    fixAction.command = {
                        command: 'nexusai.fixIssueInline',
                        title: 'Fix Issue',
                        arguments: [document, issue]
                    };
                    fixAction.diagnostics = [diagnostic];
                    fixAction.isPreferred = true;
                    actions.push(fixAction);

                    // Add "Explain Issue" action
                    const explainAction = new vscode.CodeAction(
                        `Explain: ${diagnostic.message}`,
                        vscode.CodeActionKind.QuickFix
                    );
                    explainAction.command = {
                        command: 'nexusai.explainIssue',
                        title: 'Explain Issue',
                        arguments: [document, issue]
                    };
                    explainAction.diagnostics = [diagnostic];
                    actions.push(explainAction);
                }
            }
        }

        // Add context-aware actions if there's a selection
        if (!range.isEmpty) {
            const selectedText = document.getText(range);
            
            if (selectedText.length > 10) {
                // Refactor action
                const refactorAction = new vscode.CodeAction(
                    'Refactor with NexusAI',
                    vscode.CodeActionKind.RefactorRewrite
                );
                refactorAction.command = {
                    command: 'nexusai.refactorCode',
                    title: 'Refactor Code'
                };
                actions.push(refactorAction);

                // Generate docs action
                const docsAction = new vscode.CodeAction(
                    'Generate Documentation',
                    vscode.CodeActionKind.RefactorRewrite
                );
                docsAction.command = {
                    command: 'nexusai.generateDocs',
                    title: 'Generate Documentation'
                };
                actions.push(docsAction);

                // Generate tests action
                const testsAction = new vscode.CodeAction(
                    'Generate Tests',
                    vscode.CodeActionKind.RefactorRewrite
                );
                testsAction.command = {
                    command: 'nexusai.generateTests',
                    title: 'Generate Tests'
                };
                actions.push(testsAction);
            }
        }

        return actions;
    }
}
