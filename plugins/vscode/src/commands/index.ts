/**
 * Command Registration
 * 
 * Registers all VS Code commands for the NexusAI extension.
 */

import * as vscode from 'vscode';
import { NexusAIService, CodeIssue } from '../services/nexusai-service';
import { ChatViewProvider } from '../providers/chat-view-provider';
import { DiagnosticsManager } from '../diagnostics/diagnostics-manager';
import { StatusBarManager } from '../ui/status-bar';

export function registerCommands(
    context: vscode.ExtensionContext,
    service: NexusAIService,
    chatProvider: ChatViewProvider,
    diagnostics: DiagnosticsManager,
    statusBar: StatusBarManager
): void {
    // Open Chat
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.openChat', () => {
            vscode.commands.executeCommand('nexusai.chatView.focus');
        })
    );

    // Clear Chat
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.clearChat', () => {
            chatProvider.clearChat();
        })
    );

    // Explain Code
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.explainCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            if (selection.isEmpty) {
                vscode.window.showWarningMessage('Please select code to explain');
                return;
            }

            const code = editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Explaining code...',
                cancellable: false
            }, async () => {
                try {
                    const result = await service.explainCode(code, language);
                    
                    // Show in chat
                    chatProvider.addCodeContext(code, language, 'Selected code');
                    chatProvider.sendMessage(`Explain this code:\n\`\`\`${language}\n${code}\n\`\`\``);
                    
                    // Focus chat view
                    vscode.commands.executeCommand('nexusai.chatView.focus');
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to explain code: ${error}`);
                }
            });
        })
    );

    // Review Code
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.reviewCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            const code = selection.isEmpty 
                ? editor.document.getText() 
                : editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Reviewing code...',
                cancellable: false
            }, async () => {
                try {
                    const issues = await service.analyzeCode(code, language, editor.document.fileName);
                    diagnostics.updateDiagnostics(editor.document.uri, issues);
                    
                    const message = issues.length === 0 
                        ? 'No issues found!'
                        : `Found ${issues.length} issue(s). Check the Problems panel.`;
                    
                    vscode.window.showInformationMessage(message);
                    statusBar.showMessage(`${issues.length} issues`);
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to review code: ${error}`);
                }
            });
        })
    );

    // Generate Documentation
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.generateDocs', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            if (selection.isEmpty) {
                vscode.window.showWarningMessage('Please select code to document');
                return;
            }

            const code = editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Generating documentation...',
                cancellable: false
            }, async () => {
                try {
                    const result = await service.generateDocumentation(code, language);
                    
                    // Insert documentation above the selection
                    await editor.edit(editBuilder => {
                        const position = new vscode.Position(selection.start.line, 0);
                        editBuilder.insert(position, result.documentation + '\n');
                    });
                    
                    vscode.window.showInformationMessage('Documentation generated!');
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to generate documentation: ${error}`);
                }
            });
        })
    );

    // Find Bugs
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.findBugs', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            const code = selection.isEmpty 
                ? editor.document.getText() 
                : editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Finding bugs...',
                cancellable: false
            }, async () => {
                try {
                    const issues = await service.analyzeCode(code, language, editor.document.fileName);
                    const bugs = issues.filter(i => i.severity === 'error' || i.source.includes('bug'));
                    
                    diagnostics.updateDiagnostics(editor.document.uri, bugs);
                    
                    const message = bugs.length === 0 
                        ? 'No bugs found!'
                        : `Found ${bugs.length} potential bug(s). Check the Problems panel.`;
                    
                    vscode.window.showInformationMessage(message);
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to find bugs: ${error}`);
                }
            });
        })
    );

    // Refactor Code
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.refactorCode', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            if (selection.isEmpty) {
                vscode.window.showWarningMessage('Please select code to refactor');
                return;
            }

            const code = editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Suggesting refactoring...',
                cancellable: false
            }, async () => {
                try {
                    const result = await service.suggestRefactoring(code, language);
                    
                    if (result.suggestions.length === 0) {
                        vscode.window.showInformationMessage('No refactoring suggestions');
                        return;
                    }

                    // Show suggestions in quick pick
                    const items = result.suggestions.map(s => ({
                        label: s.title,
                        description: s.impact,
                        detail: s.description,
                        code: s.code
                    }));

                    const selected = await vscode.window.showQuickPick(items, {
                        placeHolder: 'Select a refactoring suggestion'
                    });

                    if (selected) {
                        await editor.edit(editBuilder => {
                            editBuilder.replace(selection, selected.code);
                        });
                    }
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to suggest refactoring: ${error}`);
                }
            });
        })
    );

    // Generate Tests
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.generateTests', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            const selection = editor.selection;
            if (selection.isEmpty) {
                vscode.window.showWarningMessage('Please select code to generate tests for');
                return;
            }

            const code = editor.document.getText(selection);
            const language = editor.document.languageId;

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Generating tests...',
                cancellable: false
            }, async () => {
                try {
                    const result = await service.generateTests(code, language);
                    
                    // Open new document with tests
                    const doc = await vscode.workspace.openTextDocument({
                        content: result.tests,
                        language: language
                    });
                    
                    await vscode.window.showTextDocument(doc, { preview: true });
                    vscode.window.showInformationMessage(`Tests generated using ${result.framework}`);
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to generate tests: ${error}`);
                }
            });
        })
    );

    // Ask Question
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.askQuestion', async () => {
            const editor = vscode.window.activeTextEditor;
            
            const question = await vscode.window.showInputBox({
                prompt: 'Ask a question about the selected code (or codebase)',
                placeHolder: 'What does this code do?'
            });

            if (!question) return;

            let context: any = undefined;
            if (editor && !editor.selection.isEmpty) {
                context = {
                    code: editor.document.getText(editor.selection),
                    language: editor.document.languageId,
                    file: editor.document.fileName
                };
            }

            chatProvider.sendMessage(question, context);
            vscode.commands.executeCommand('nexusai.chatView.focus');
        })
    );

    // Analyze File
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.analyzeFile', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            statusBar.setAnalyzing(true);
            
            try {
                const issues = await service.analyzeCode(
                    editor.document.getText(),
                    editor.document.languageId,
                    editor.document.fileName
                );
                
                diagnostics.updateDiagnostics(editor.document.uri, issues);
                statusBar.showMessage(`${issues.length} issues found`);
            } catch (error) {
                vscode.window.showErrorMessage(`Analysis failed: ${error}`);
            } finally {
                statusBar.setAnalyzing(false);
            }
        })
    );

    // Analyze Workspace
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.analyzeWorkspace', async () => {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Analyzing workspace...',
                cancellable: true
            }, async (progress, token) => {
                try {
                    const files = await vscode.workspace.findFiles(
                        '**/*.{ts,js,tsx,jsx,py,java,go,rs,cpp,c}',
                        '**/node_modules/**',
                        100
                    );

                    const fileContents = await Promise.all(
                        files.slice(0, 50).map(async (uri) => {
                            const doc = await vscode.workspace.openTextDocument(uri);
                            return {
                                path: uri.fsPath,
                                content: doc.getText(),
                                language: doc.languageId
                            };
                        })
                    );

                    const result = await service.analyzeWorkspace(fileContents);
                    
                    vscode.window.showInformationMessage(
                        `Workspace analysis complete. Found ${result.issues.length} issues.`
                    );
                } catch (error) {
                    vscode.window.showErrorMessage(`Workspace analysis failed: ${error}`);
                }
            });
        })
    );

    // Show Metrics
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.showMetrics', async () => {
            const editor = vscode.window.activeTextEditor;
            if (!editor) {
                vscode.window.showWarningMessage('No active editor');
                return;
            }

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Calculating metrics...',
                cancellable: false
            }, async () => {
                try {
                    const metrics = await service.getCodeMetrics(
                        editor.document.getText(),
                        editor.document.languageId
                    );

                    const message = [
                        `Complexity: ${metrics.complexity}`,
                        `Maintainability: ${metrics.maintainability}%`,
                        `Lines of Code: ${metrics.linesOfCode}`,
                        `Functions: ${metrics.functions}`,
                        `Classes: ${metrics.classes}`
                    ].join('\n');

                    vscode.window.showInformationMessage(
                        `Code Metrics:\n${message}`,
                        { modal: true }
                    );
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to get metrics: ${error}`);
                }
            });
        })
    );

    // Fix Issue
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.fixIssue', async () => {
            vscode.window.showInformationMessage(
                'Click on an issue in the Problems panel and use the Quick Fix (Ctrl+.)'
            );
        })
    );

    // Fix Issue Inline (called from code action)
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.fixIssueInline', async (
            document: vscode.TextDocument,
            issue: CodeIssue
        ) => {
            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Generating fix...',
                cancellable: false
            }, async () => {
                try {
                    const fixedCode = await service.fixIssue(
                        document.getText(),
                        issue,
                        document.languageId
                    );

                    // Show diff and let user accept
                    const action = await vscode.window.showInformationMessage(
                        'Fix generated. Apply changes?',
                        'Apply',
                        'Preview',
                        'Cancel'
                    );

                    if (action === 'Apply') {
                        const edit = new vscode.WorkspaceEdit();
                        edit.replace(
                            document.uri,
                            new vscode.Range(0, 0, document.lineCount, 0),
                            fixedCode
                        );
                        await vscode.workspace.applyEdit(edit);
                    } else if (action === 'Preview') {
                        // Show diff in new tab
                        const newDoc = await vscode.workspace.openTextDocument({
                            content: fixedCode,
                            language: document.languageId
                        });
                        await vscode.commands.executeCommand(
                            'vscode.diff',
                            document.uri,
                            newDoc.uri,
                            'Original ↔ Fixed'
                        );
                    }
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to generate fix: ${error}`);
                }
            });
        })
    );

    // Review PR
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.reviewPR', async () => {
            // Try to get diff from Git extension
            const gitExtension = vscode.extensions.getExtension('vscode.git')?.exports;
            if (!gitExtension) {
                vscode.window.showWarningMessage('Git extension not available');
                return;
            }

            const api = gitExtension.getAPI(1);
            const repo = api.repositories[0];
            if (!repo) {
                vscode.window.showWarningMessage('No Git repository found');
                return;
            }

            await vscode.window.withProgress({
                location: vscode.ProgressLocation.Notification,
                title: 'NexusAI: Reviewing changes...',
                cancellable: false
            }, async () => {
                try {
                    const diff = await repo.diff();
                    if (!diff) {
                        vscode.window.showInformationMessage('No changes to review');
                        return;
                    }

                    const result = await service.reviewPullRequest(diff);
                    
                    // Show review in chat
                    chatProvider.sendMessage(
                        `Review the following changes and provide feedback:\n\`\`\`diff\n${diff.slice(0, 2000)}\n\`\`\``
                    );
                    vscode.commands.executeCommand('nexusai.chatView.focus');
                } catch (error) {
                    vscode.window.showErrorMessage(`Failed to review: ${error}`);
                }
            });
        })
    );

    // Sign In
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.signIn', async () => {
            const email = await vscode.window.showInputBox({
                prompt: 'Enter your email',
                placeHolder: 'user@example.com'
            });
            if (!email) return;

            const password = await vscode.window.showInputBox({
                prompt: 'Enter your password',
                password: true
            });
            if (!password) return;

            try {
                const result = await service.signIn({ email, password });
                vscode.window.showInformationMessage(`Signed in as ${result.user.name}`);
                statusBar.setConnected(true);
            } catch (error) {
                vscode.window.showErrorMessage(`Sign in failed: ${error}`);
            }
        })
    );

    // Sign Out
    context.subscriptions.push(
        vscode.commands.registerCommand('nexusai.signOut', async () => {
            await service.signOut();
            vscode.window.showInformationMessage('Signed out');
            statusBar.setConnected(false);
        })
    );
}
