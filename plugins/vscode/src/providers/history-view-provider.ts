/**
 * History View Provider
 * 
 * Tree view for showing conversation history.
 */

import * as vscode from 'vscode';
import { NexusAIService } from '../services/nexusai-service';

interface ConversationSummary {
    id: string;
    title: string;
    timestamp: number;
    messageCount: number;
}

export class HistoryViewProvider implements vscode.TreeDataProvider<HistoryItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<HistoryItem | undefined | null | void> = 
        new vscode.EventEmitter<HistoryItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<HistoryItem | undefined | null | void> = 
        this._onDidChangeTreeData.event;

    private conversations: ConversationSummary[] = [];

    constructor(
        private readonly context: vscode.ExtensionContext,
        private readonly service: NexusAIService
    ) {
        this.loadHistory();
    }

    refresh(): void {
        this.loadHistory();
        this._onDidChangeTreeData.fire();
    }

    private loadHistory(): void {
        const history = this.context.globalState.get<ConversationSummary[]>('nexusai.conversationHistory', []);
        this.conversations = history.sort((a, b) => b.timestamp - a.timestamp);
    }

    saveConversation(id: string, title: string, messageCount: number): void {
        const existing = this.conversations.findIndex(c => c.id === id);
        const summary: ConversationSummary = {
            id,
            title,
            timestamp: Date.now(),
            messageCount
        };

        if (existing >= 0) {
            this.conversations[existing] = summary;
        } else {
            this.conversations.unshift(summary);
        }

        // Keep only last 50 conversations
        this.conversations = this.conversations.slice(0, 50);
        
        this.context.globalState.update('nexusai.conversationHistory', this.conversations);
        this.refresh();
    }

    deleteConversation(id: string): void {
        this.conversations = this.conversations.filter(c => c.id !== id);
        this.context.globalState.update('nexusai.conversationHistory', this.conversations);
        this.refresh();
    }

    clearHistory(): void {
        this.conversations = [];
        this.context.globalState.update('nexusai.conversationHistory', []);
        this.refresh();
    }

    getTreeItem(element: HistoryItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: HistoryItem): Thenable<HistoryItem[]> {
        if (element) {
            return Promise.resolve([]);
        }

        if (this.conversations.length === 0) {
            const emptyItem = new HistoryItem(
                'No conversations yet',
                vscode.TreeItemCollapsibleState.None,
                'empty'
            );
            emptyItem.iconPath = new vscode.ThemeIcon('comment-discussion');
            return Promise.resolve([emptyItem]);
        }

        const items = this.conversations.map(conv => {
            const item = new HistoryItem(
                conv.title,
                vscode.TreeItemCollapsibleState.None,
                'conversation'
            );
            item.id = conv.id;
            item.description = this.formatTimestamp(conv.timestamp);
            item.tooltip = `${conv.messageCount} messages\n${new Date(conv.timestamp).toLocaleString()}`;
            item.iconPath = new vscode.ThemeIcon('comment-discussion');
            item.command = {
                command: 'nexusai.loadConversation',
                title: 'Load Conversation',
                arguments: [conv.id]
            };
            item.contextValue = 'conversation';
            return item;
        });

        return Promise.resolve(items);
    }

    private formatTimestamp(timestamp: number): string {
        const now = Date.now();
        const diff = now - timestamp;
        
        const minutes = Math.floor(diff / 60000);
        const hours = Math.floor(diff / 3600000);
        const days = Math.floor(diff / 86400000);

        if (minutes < 1) return 'Just now';
        if (minutes < 60) return `${minutes}m ago`;
        if (hours < 24) return `${hours}h ago`;
        if (days < 7) return `${days}d ago`;
        
        return new Date(timestamp).toLocaleDateString();
    }
}

class HistoryItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string
    ) {
        super(label, collapsibleState);
    }
}
