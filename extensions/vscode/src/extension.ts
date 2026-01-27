import * as vscode from 'vscode';
import { NexusAIClient } from './client';
import { DiagnosticsProvider } from './diagnostics';
import { ChatViewProvider } from './chat';
import { IssuesViewProvider } from './issues';
import { MetricsViewProvider } from './metrics';
import { CodeActionsProvider } from './codeActions';
import { CompletionProvider } from './completion';

let client: NexusAIClient;
let diagnosticsProvider: DiagnosticsProvider;

export async function activate(context: vscode.ExtensionContext) {
    console.log('NexusAI extension is activating...');

    // Get configuration
    const config = vscode.workspace.getConfiguration('nexusai');
    const serverUrl = config.get<string>('serverUrl', 'http://localhost:8000');
    const apiKey = config.get<string>('apiKey', '');
    const enabled = config.get<boolean>('enabled', true);

    if (!enabled) {
        console.log('NexusAI extension is disabled');
        return;
    }

    // Initialize client
    client = new NexusAIClient(serverUrl, apiKey);

    // Check connection
    try {
        const capabilities = await client.getCapabilities();
        console.log('Connected to NexusAI server', capabilities);
    } catch (error) {
        vscode.window.showWarningMessage(
            'Could not connect to NexusAI server. Please check your settings.'
        );
        console.error('Connection error:', error);
    }

    // Initialize diagnostics provider
    diagnosticsProvider = new DiagnosticsProvider(client, context);

    // Register providers
    const codeActionsProvider = new CodeActionsProvider(client);
    const completionProvider = new CompletionProvider(client);

    // Register views
    const chatViewProvider = new ChatViewProvider(context.extensionUri, client);
    const issuesViewProvider = new IssuesViewProvider(diagnosticsProvider);
    const metricsViewProvider = new MetricsViewProvider(client);

    // Register all disposables
    context.subscriptions.push(
        // Diagnostics
        diagnosticsProvider,

        // Code actions
        vscode.languages.registerCodeActionsProvider(
            { scheme: 'file' },
            codeActionsProvider,
            { providedCodeActionKinds: CodeActionsProvider.providedCodeActionKinds }
        ),

        // Completions (if enabled)
        vscode.languages.registerCompletionItemProvider(
            { scheme: 'file' },
            completionProvider,
            '.'  // Trigger on dot
        ),

        // Views
        vscode.window.registerWebviewViewProvider('nexusai.chat', chatViewProvider),
        vscode.window.registerTreeDataProvider('nexusai.issues', issuesViewProvider),
        vscode.window.registerTreeDataProvider('nexusai.metrics', metricsViewProvider),

        // Commands
        vscode.commands.registerCommand('nexusai.analyzeFile', () => analyzeCurrentFile()),
        vscode.commands.registerCommand('nexusai.analyzeWorkspace', () => analyzeWorkspace()),
        vscode.commands.registerCommand('nexusai.explainCode', () => chatWithCode('explain')),
        vscode.commands.registerCommand('nexusai.fixCode', () => chatWithCode('fix')),
        vscode.commands.registerCommand('nexusai.refactorCode', () => chatWithCode('refactor')),
        vscode.commands.registerCommand('nexusai.documentCode', () => chatWithCode('document')),
        vscode.commands.registerCommand('nexusai.generateTests', () => chatWithCode('test')),
        vscode.commands.registerCommand('nexusai.openChat', () => openChat()),
        vscode.commands.registerCommand('nexusai.showSecurityDocs', (code: string) => showSecurityDocs(code)),
        vscode.commands.registerCommand('nexusai.applySuggestion', (suggestion: string) => applySuggestion(suggestion)),
        vscode.commands.registerCommand('nexusai.toggleAutoAnalysis', () => toggleAutoAnalysis()),

        // Configuration change listener
        vscode.workspace.onDidChangeConfiguration(onConfigurationChanged)
    );

    // Auto-analyze on save if enabled
    if (config.get<boolean>('autoAnalyze', true)) {
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(document => {
                diagnosticsProvider.analyzeDocument(document);
            })
        );
    }

    // Status bar item
    const statusBarItem = vscode.window.createStatusBarItem(
        vscode.StatusBarAlignment.Right,
        100
    );
    statusBarItem.text = '$(check) NexusAI';
    statusBarItem.tooltip = 'NexusAI Code Intelligence';
    statusBarItem.command = 'nexusai.openChat';
    statusBarItem.show();
    context.subscriptions.push(statusBarItem);

    console.log('NexusAI extension activated');
}

export function deactivate() {
    console.log('NexusAI extension deactivated');
}

// Command implementations
async function analyzeCurrentFile() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        vscode.window.showWarningMessage('No file is currently open');
        return;
    }

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'NexusAI: Analyzing file...',
            cancellable: false
        },
        async () => {
            await diagnosticsProvider.analyzeDocument(editor.document);
        }
    );
}

async function analyzeWorkspace() {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) {
        vscode.window.showWarningMessage('No workspace is open');
        return;
    }

    await vscode.window.withProgress(
        {
            location: vscode.ProgressLocation.Notification,
            title: 'NexusAI: Analyzing workspace...',
            cancellable: true
        },
        async (progress, token) => {
            const config = vscode.workspace.getConfiguration('nexusai');
            const enabledLanguages = config.get<string[]>('enabledLanguages', []);
            const maxFileSize = config.get<number>('maxFileSize', 500) * 1024;

            // Find all files
            const files = await vscode.workspace.findFiles(
                '**/*.{py,ts,tsx,js,jsx,go,rs,java}',
                '**/node_modules/**'
            );

            let analyzed = 0;
            for (const file of files) {
                if (token.isCancellationRequested) {
                    break;
                }

                try {
                    const stat = await vscode.workspace.fs.stat(file);
                    if (stat.size > maxFileSize) {
                        continue;
                    }

                    const document = await vscode.workspace.openTextDocument(file);
                    if (enabledLanguages.includes(document.languageId)) {
                        await diagnosticsProvider.analyzeDocument(document);
                        analyzed++;
                        progress.report({
                            increment: 100 / files.length,
                            message: `${analyzed}/${files.length} files`
                        });
                    }
                } catch (error) {
                    console.error(`Error analyzing ${file.path}:`, error);
                }
            }

            vscode.window.showInformationMessage(
                `NexusAI: Analyzed ${analyzed} files`
            );
        }
    );
}

async function chatWithCode(command: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor || !editor.selection || editor.selection.isEmpty) {
        vscode.window.showWarningMessage('Please select some code first');
        return;
    }

    const selection = editor.document.getText(editor.selection);

    // Focus the chat view and send message
    await vscode.commands.executeCommand('nexusai.chat.focus');

    // The chat view provider will handle the actual message
    vscode.commands.executeCommand('nexusai.chat.sendMessage', {
        command,
        selection,
        fileUri: editor.document.uri.toString(),
        languageId: editor.document.languageId
    });
}

async function openChat() {
    await vscode.commands.executeCommand('nexusai.chat.focus');
}

async function showSecurityDocs(code: string) {
    const securityDocs: Record<string, string> = {
        'hardcoded_secret': 'https://owasp.org/www-community/vulnerabilities/Use_of_hard-coded_password',
        'sql_injection': 'https://owasp.org/www-community/attacks/SQL_Injection',
        'xss_vulnerability': 'https://owasp.org/www-community/attacks/xss/',
        'dangerous_eval': 'https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/eval#never_use_eval!',
        'insecure_deserialization': 'https://owasp.org/www-project-web-security-testing-guide/latest/4-Web_Application_Security_Testing/07-Input_Validation_Testing/18-Testing_for_Insecure_Deserialization',
    };

    const url = securityDocs[code] || 'https://owasp.org/www-project-top-ten/';
    await vscode.env.openExternal(vscode.Uri.parse(url));
}

async function applySuggestion(suggestion: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
        return;
    }

    // Show suggestion in info message with apply option
    const action = await vscode.window.showInformationMessage(
        `NexusAI Suggestion: ${suggestion}`,
        'Apply',
        'Dismiss'
    );

    if (action === 'Apply') {
        // This would need more context to actually apply
        // For now, show in chat
        await vscode.commands.executeCommand('nexusai.chat.focus');
    }
}

function toggleAutoAnalysis() {
    const config = vscode.workspace.getConfiguration('nexusai');
    const current = config.get<boolean>('autoAnalyze', true);
    config.update('autoAnalyze', !current, vscode.ConfigurationTarget.Workspace);

    vscode.window.showInformationMessage(
        `NexusAI: Auto-analysis ${!current ? 'enabled' : 'disabled'}`
    );
}

function onConfigurationChanged(e: vscode.ConfigurationChangeEvent) {
    if (e.affectsConfiguration('nexusai')) {
        const config = vscode.workspace.getConfiguration('nexusai');

        // Update client settings
        const serverUrl = config.get<string>('serverUrl', 'http://localhost:8000');
        const apiKey = config.get<string>('apiKey', '');
        client.updateConfig(serverUrl, apiKey);

        // Update diagnostics settings
        diagnosticsProvider.updateConfig(config);
    }
}
