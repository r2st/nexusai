/**
 * NexusAI VS Code Extension
 * 
 * Main extension entry point that registers commands, views, and providers.
 */

import * as vscode from 'vscode';
import { NexusAIService } from './services/nexusai-service';
import { ChatViewProvider } from './providers/chat-view-provider';
import { AnalysisViewProvider } from './providers/analysis-view-provider';
import { HistoryViewProvider } from './providers/history-view-provider';
import { CodeActionProvider } from './providers/code-action-provider';
import { InlineHintProvider } from './providers/inline-hint-provider';
import { registerCommands } from './commands';
import { StatusBarManager } from './ui/status-bar';
import { DiagnosticsManager } from './diagnostics/diagnostics-manager';

let nexusService: NexusAIService;
let statusBar: StatusBarManager;
let diagnosticsManager: DiagnosticsManager;

export async function activate(context: vscode.ExtensionContext) {
    console.log('NexusAI extension is activating...');

    // Initialize the NexusAI service
    nexusService = new NexusAIService(context);
    
    // Initialize status bar
    statusBar = new StatusBarManager(context);
    
    // Initialize diagnostics manager
    diagnosticsManager = new DiagnosticsManager();

    // Register chat view provider
    const chatViewProvider = new ChatViewProvider(context.extensionUri, nexusService);
    context.subscriptions.push(
        vscode.window.registerWebviewViewProvider('nexusai.chatView', chatViewProvider)
    );

    // Register analysis view provider
    const analysisViewProvider = new AnalysisViewProvider(nexusService);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('nexusai.analysisView', analysisViewProvider)
    );

    // Register history view provider
    const historyViewProvider = new HistoryViewProvider(context, nexusService);
    context.subscriptions.push(
        vscode.window.registerTreeDataProvider('nexusai.historyView', historyViewProvider)
    );

    // Register code action provider for all languages
    context.subscriptions.push(
        vscode.languages.registerCodeActionsProvider(
            { scheme: 'file' },
            new CodeActionProvider(nexusService, diagnosticsManager),
            { providedCodeActionKinds: CodeActionProvider.providedCodeActionKinds }
        )
    );

    // Register inline hints provider if enabled
    const config = vscode.workspace.getConfiguration('nexusai');
    if (config.get('enableInlineHints')) {
        const inlineHintProvider = new InlineHintProvider(nexusService);
        context.subscriptions.push(
            vscode.languages.registerInlayHintsProvider(
                { scheme: 'file' },
                inlineHintProvider
            )
        );
    }

    // Register all commands
    registerCommands(context, nexusService, chatViewProvider, diagnosticsManager, statusBar);

    // Auto-analyze on save if enabled
    if (config.get('enableAutoAnalysis')) {
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(async (document) => {
                if (document.uri.scheme === 'file') {
                    await analyzeDocument(document);
                }
            })
        );
    }

    // Update status bar with connection status
    await updateConnectionStatus();

    // Listen for configuration changes
    context.subscriptions.push(
        vscode.workspace.onDidChangeConfiguration((e) => {
            if (e.affectsConfiguration('nexusai')) {
                nexusService.updateConfiguration();
                updateConnectionStatus();
            }
        })
    );

    console.log('NexusAI extension activated successfully');
}

async function analyzeDocument(document: vscode.TextDocument): Promise<void> {
    try {
        statusBar.setAnalyzing(true);
        const issues = await nexusService.analyzeCode(
            document.getText(),
            document.languageId,
            document.fileName
        );
        diagnosticsManager.updateDiagnostics(document.uri, issues);
    } catch (error) {
        console.error('Auto-analysis failed:', error);
    } finally {
        statusBar.setAnalyzing(false);
    }
}

async function updateConnectionStatus(): Promise<void> {
    try {
        const isConnected = await nexusService.testConnection();
        statusBar.setConnected(isConnected);
    } catch {
        statusBar.setConnected(false);
    }
}

export function deactivate() {
    if (diagnosticsManager) {
        diagnosticsManager.dispose();
    }
    console.log('NexusAI extension deactivated');
}

// Export for use by other modules
export { nexusService, statusBar, diagnosticsManager };
