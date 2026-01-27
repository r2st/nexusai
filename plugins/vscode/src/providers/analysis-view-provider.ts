/**
 * Analysis View Provider
 * 
 * Tree view for showing analysis results and issues.
 */

import * as vscode from 'vscode';
import { NexusAIService, CodeIssue } from '../services/nexusai-service';

export class AnalysisViewProvider implements vscode.TreeDataProvider<AnalysisItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<AnalysisItem | undefined | null | void> = 
        new vscode.EventEmitter<AnalysisItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<AnalysisItem | undefined | null | void> = 
        this._onDidChangeTreeData.event;

    private issues: Map<string, CodeIssue[]> = new Map();
    private metrics: { complexity: number; maintainability: number } | null = null;

    constructor(private readonly service: NexusAIService) {}

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    updateIssues(file: string, issues: CodeIssue[]): void {
        this.issues.set(file, issues);
        this.refresh();
    }

    updateMetrics(metrics: { complexity: number; maintainability: number }): void {
        this.metrics = metrics;
        this.refresh();
    }

    clearAll(): void {
        this.issues.clear();
        this.metrics = null;
        this.refresh();
    }

    getTreeItem(element: AnalysisItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: AnalysisItem): Thenable<AnalysisItem[]> {
        if (!element) {
            // Root level - show categories
            return Promise.resolve(this.getRootItems());
        }

        if (element.contextValue === 'category-issues') {
            return Promise.resolve(this.getIssueItems());
        }

        if (element.contextValue === 'category-metrics') {
            return Promise.resolve(this.getMetricItems());
        }

        if (element.contextValue === 'file') {
            return Promise.resolve(this.getFileIssues(element.resourceUri?.fsPath || ''));
        }

        return Promise.resolve([]);
    }

    private getRootItems(): AnalysisItem[] {
        const items: AnalysisItem[] = [];

        // Issues category
        const totalIssues = Array.from(this.issues.values()).reduce((sum, arr) => sum + arr.length, 0);
        const issuesItem = new AnalysisItem(
            `Issues (${totalIssues})`,
            vscode.TreeItemCollapsibleState.Expanded,
            'category-issues'
        );
        issuesItem.iconPath = new vscode.ThemeIcon('warning');
        items.push(issuesItem);

        // Metrics category
        if (this.metrics) {
            const metricsItem = new AnalysisItem(
                'Code Metrics',
                vscode.TreeItemCollapsibleState.Expanded,
                'category-metrics'
            );
            metricsItem.iconPath = new vscode.ThemeIcon('graph');
            items.push(metricsItem);
        }

        return items;
    }

    private getIssueItems(): AnalysisItem[] {
        const items: AnalysisItem[] = [];

        for (const [file, issues] of this.issues) {
            if (issues.length === 0) continue;

            const fileName = file.split('/').pop() || file;
            const fileItem = new AnalysisItem(
                `${fileName} (${issues.length})`,
                vscode.TreeItemCollapsibleState.Collapsed,
                'file'
            );
            fileItem.resourceUri = vscode.Uri.file(file);
            fileItem.iconPath = vscode.ThemeIcon.File;
            items.push(fileItem);
        }

        if (items.length === 0) {
            const noIssuesItem = new AnalysisItem(
                'No issues found',
                vscode.TreeItemCollapsibleState.None,
                'empty'
            );
            noIssuesItem.iconPath = new vscode.ThemeIcon('check');
            items.push(noIssuesItem);
        }

        return items;
    }

    private getFileIssues(file: string): AnalysisItem[] {
        const issues = this.issues.get(file) || [];
        
        return issues.map((issue, index) => {
            const item = new AnalysisItem(
                `Line ${issue.line}: ${issue.message}`,
                vscode.TreeItemCollapsibleState.None,
                'issue'
            );
            
            item.iconPath = this.getSeverityIcon(issue.severity);
            item.tooltip = `${issue.source}: ${issue.message}`;
            item.command = {
                command: 'vscode.open',
                title: 'Go to Issue',
                arguments: [
                    vscode.Uri.file(file),
                    {
                        selection: new vscode.Range(
                            issue.line - 1, issue.column - 1,
                            (issue.endLine || issue.line) - 1, (issue.endColumn || issue.column) - 1
                        )
                    }
                ]
            };
            
            return item;
        });
    }

    private getMetricItems(): AnalysisItem[] {
        if (!this.metrics) return [];

        const items: AnalysisItem[] = [];

        // Complexity
        const complexityItem = new AnalysisItem(
            `Complexity: ${this.metrics.complexity}`,
            vscode.TreeItemCollapsibleState.None,
            'metric'
        );
        complexityItem.iconPath = new vscode.ThemeIcon(
            this.metrics.complexity > 20 ? 'warning' : 'check'
        );
        complexityItem.tooltip = 'Cyclomatic complexity score';
        items.push(complexityItem);

        // Maintainability
        const maintainabilityItem = new AnalysisItem(
            `Maintainability: ${this.metrics.maintainability}%`,
            vscode.TreeItemCollapsibleState.None,
            'metric'
        );
        maintainabilityItem.iconPath = new vscode.ThemeIcon(
            this.metrics.maintainability < 50 ? 'warning' : 'check'
        );
        maintainabilityItem.tooltip = 'Maintainability index (0-100)';
        items.push(maintainabilityItem);

        return items;
    }

    private getSeverityIcon(severity: string): vscode.ThemeIcon {
        switch (severity) {
            case 'error':
                return new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground'));
            case 'warning':
                return new vscode.ThemeIcon('warning', new vscode.ThemeColor('editorWarning.foreground'));
            case 'info':
                return new vscode.ThemeIcon('info', new vscode.ThemeColor('editorInfo.foreground'));
            default:
                return new vscode.ThemeIcon('lightbulb');
        }
    }
}

class AnalysisItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string
    ) {
        super(label, collapsibleState);
    }
}
