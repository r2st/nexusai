import * as vscode from 'vscode';
import { NexusAIClient, AnalysisIssue, QuickFix } from './client';

export class CodeActionsProvider implements vscode.CodeActionProvider {
    static readonly providedCodeActionKinds = [
        vscode.CodeActionKind.QuickFix,
        vscode.CodeActionKind.Refactor,
        vscode.CodeActionKind.Source
    ];

    private client: NexusAIClient;

    constructor(client: NexusAIClient) {
        this.client = client;
    }

    async provideCodeActions(
        document: vscode.TextDocument,
        range: vscode.Range | vscode.Selection,
        context: vscode.CodeActionContext,
        token: vscode.CancellationToken
    ): Promise<vscode.CodeAction[]> {
        const actions: vscode.CodeAction[] = [];

        // Get code actions for diagnostics
        for (const diagnostic of context.diagnostics) {
            if (diagnostic.source !== 'NexusAI') {
                continue;
            }

            const issue = (diagnostic as any).nexusaiIssue as AnalysisIssue | undefined;
            if (!issue) {
                continue;
            }

            // Add quick fixes from the issue
            for (const fix of issue.quick_fixes) {
                const action = this.createCodeAction(fix, diagnostic, document);
                if (action) {
                    actions.push(action);
                }
            }

            // Add AI fix option
            const aiFix = new vscode.CodeAction(
                `NexusAI: Fix "${issue.code || 'issue'}" with AI`,
                vscode.CodeActionKind.QuickFix
            );
            aiFix.command = {
                command: 'nexusai.fixWithAI',
                title: 'Fix with AI',
                arguments: [document.uri, issue]
            };
            aiFix.diagnostics = [diagnostic];
            actions.push(aiFix);

            // Add explain option
            const explain = new vscode.CodeAction(
                `NexusAI: Explain this issue`,
                vscode.CodeActionKind.QuickFix
            );
            explain.command = {
                command: 'nexusai.explainIssue',
                title: 'Explain Issue',
                arguments: [issue]
            };
            explain.diagnostics = [diagnostic];
            actions.push(explain);
        }

        // Add refactoring actions for selection
        if (!range.isEmpty) {
            actions.push(this.createRefactorAction('Extract function', document, range));
            actions.push(this.createRefactorAction('Extract variable', document, range));
            actions.push(this.createRefactorAction('Improve readability', document, range));
        }

        return actions;
    }

    private createCodeAction(
        fix: QuickFix,
        diagnostic: vscode.Diagnostic,
        document: vscode.TextDocument
    ): vscode.CodeAction | undefined {
        const action = new vscode.CodeAction(
            fix.title,
            fix.kind === 'refactor' ? vscode.CodeActionKind.Refactor : vscode.CodeActionKind.QuickFix
        );

        action.diagnostics = [diagnostic];
        action.isPreferred = fix.is_preferred;

        if (fix.edit) {
            const edit = new vscode.WorkspaceEdit();
            // Convert edit format to vscode format
            // This would need proper implementation based on edit format
            action.edit = edit;
        }

        if (fix.command) {
            action.command = {
                command: fix.command,
                title: fix.title,
                arguments: fix.arguments
            };
        }

        return action;
    }

    private createRefactorAction(
        title: string,
        document: vscode.TextDocument,
        range: vscode.Range
    ): vscode.CodeAction {
        const action = new vscode.CodeAction(
            `NexusAI: ${title}`,
            vscode.CodeActionKind.Refactor
        );

        action.command = {
            command: 'nexusai.refactorCode',
            title: title,
            arguments: [document.uri, range, title.toLowerCase().replace(' ', '_')]
        };

        return action;
    }
}
