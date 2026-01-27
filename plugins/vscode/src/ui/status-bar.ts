/**
 * Status Bar Manager
 * 
 * Manages the VS Code status bar items for NexusAI.
 */

import * as vscode from 'vscode';

export class StatusBarManager {
    private statusItem: vscode.StatusBarItem;
    private isConnected: boolean = false;
    private isAnalyzing: boolean = false;

    constructor(context: vscode.ExtensionContext) {
        this.statusItem = vscode.window.createStatusBarItem(
            vscode.StatusBarAlignment.Right,
            100
        );
        
        this.statusItem.command = 'nexusai.openChat';
        this.updateDisplay();
        this.statusItem.show();
        
        context.subscriptions.push(this.statusItem);
    }

    setConnected(connected: boolean): void {
        this.isConnected = connected;
        this.updateDisplay();
    }

    setAnalyzing(analyzing: boolean): void {
        this.isAnalyzing = analyzing;
        this.updateDisplay();
    }

    private updateDisplay(): void {
        if (this.isAnalyzing) {
            this.statusItem.text = '$(sync~spin) NexusAI';
            this.statusItem.tooltip = 'NexusAI is analyzing...';
            this.statusItem.backgroundColor = undefined;
        } else if (this.isConnected) {
            this.statusItem.text = '$(hubot) NexusAI';
            this.statusItem.tooltip = 'NexusAI is connected. Click to open chat.';
            this.statusItem.backgroundColor = undefined;
        } else {
            this.statusItem.text = '$(hubot) NexusAI';
            this.statusItem.tooltip = 'NexusAI is disconnected. Click to configure.';
            this.statusItem.backgroundColor = new vscode.ThemeColor('statusBarItem.warningBackground');
        }
    }

    showMessage(message: string, timeout: number = 3000): void {
        const originalText = this.statusItem.text;
        const originalTooltip = this.statusItem.tooltip;
        
        this.statusItem.text = `$(hubot) ${message}`;
        this.statusItem.tooltip = message;
        
        setTimeout(() => {
            this.statusItem.text = originalText;
            this.statusItem.tooltip = originalTooltip;
        }, timeout);
    }
}
