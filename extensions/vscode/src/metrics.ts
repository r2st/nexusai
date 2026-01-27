import * as vscode from 'vscode';
import { NexusAIClient } from './client';

interface MetricItem {
    name: string;
    value: string | number;
    description?: string;
    trend?: 'up' | 'down' | 'stable';
}

export class MetricsViewProvider implements vscode.TreeDataProvider<MetricTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<MetricTreeItem | undefined | null | void> =
        new vscode.EventEmitter<MetricTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<MetricTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private client: NexusAIClient;
    private metrics: Map<string, MetricItem[]> = new Map();

    constructor(client: NexusAIClient) {
        this.client = client;
        this.initializeMetrics();
    }

    private initializeMetrics() {
        // Initialize with default categories
        this.metrics.set('Code Quality', [
            { name: 'Issues Found', value: 0, trend: 'stable' },
            { name: 'Error Count', value: 0, trend: 'stable' },
            { name: 'Warning Count', value: 0, trend: 'stable' },
            { name: 'Security Issues', value: 0, trend: 'stable' },
        ]);

        this.metrics.set('Complexity', [
            { name: 'Files Analyzed', value: 0, trend: 'stable' },
            { name: 'Avg Issues/File', value: '0', trend: 'stable' },
        ]);
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    updateMetrics(analysisResult: any) {
        const qualityMetrics = this.metrics.get('Code Quality') || [];

        // Update metrics from analysis result
        qualityMetrics[0] = {
            name: 'Issues Found',
            value: analysisResult.issue_count || 0,
            trend: this.getTrend(qualityMetrics[0]?.value, analysisResult.issue_count)
        };
        qualityMetrics[1] = {
            name: 'Error Count',
            value: analysisResult.error_count || 0,
            trend: this.getTrend(qualityMetrics[1]?.value, analysisResult.error_count)
        };
        qualityMetrics[2] = {
            name: 'Warning Count',
            value: analysisResult.warning_count || 0,
            trend: this.getTrend(qualityMetrics[2]?.value, analysisResult.warning_count)
        };
        qualityMetrics[3] = {
            name: 'Security Issues',
            value: analysisResult.security_issue_count || 0,
            trend: this.getTrend(qualityMetrics[3]?.value, analysisResult.security_issue_count)
        };

        this.metrics.set('Code Quality', qualityMetrics);
        this.refresh();
    }

    private getTrend(oldValue: any, newValue: any): 'up' | 'down' | 'stable' {
        const old = typeof oldValue === 'number' ? oldValue : parseFloat(oldValue) || 0;
        const current = typeof newValue === 'number' ? newValue : parseFloat(newValue) || 0;

        if (current > old) return 'up';
        if (current < old) return 'down';
        return 'stable';
    }

    getTreeItem(element: MetricTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: MetricTreeItem): Thenable<MetricTreeItem[]> {
        if (!element) {
            // Root level - show metric categories
            return Promise.resolve(this.getCategoryItems());
        } else if (element.contextValue === 'category') {
            // Category level - show metrics
            return Promise.resolve(this.getMetricItems(element.label as string));
        }
        return Promise.resolve([]);
    }

    private getCategoryItems(): MetricTreeItem[] {
        const items: MetricTreeItem[] = [];

        for (const category of this.metrics.keys()) {
            const item = new MetricTreeItem(
                category,
                vscode.TreeItemCollapsibleState.Expanded,
                'category'
            );
            item.iconPath = this.getCategoryIcon(category);
            items.push(item);
        }

        return items;
    }

    private getMetricItems(category: string): MetricTreeItem[] {
        const metrics = this.metrics.get(category) || [];

        return metrics.map(metric => {
            const item = new MetricTreeItem(
                metric.name,
                vscode.TreeItemCollapsibleState.None,
                'metric'
            );
            item.description = String(metric.value);
            item.iconPath = this.getTrendIcon(metric.trend);
            item.tooltip = metric.description || metric.name;
            return item;
        });
    }

    private getCategoryIcon(category: string): vscode.ThemeIcon {
        switch (category) {
            case 'Code Quality':
                return new vscode.ThemeIcon('checklist');
            case 'Complexity':
                return new vscode.ThemeIcon('graph');
            case 'Security':
                return new vscode.ThemeIcon('shield');
            default:
                return new vscode.ThemeIcon('dashboard');
        }
    }

    private getTrendIcon(trend?: 'up' | 'down' | 'stable'): vscode.ThemeIcon {
        switch (trend) {
            case 'up':
                return new vscode.ThemeIcon('arrow-up', new vscode.ThemeColor('charts.red'));
            case 'down':
                return new vscode.ThemeIcon('arrow-down', new vscode.ThemeColor('charts.green'));
            case 'stable':
            default:
                return new vscode.ThemeIcon('dash', new vscode.ThemeColor('charts.yellow'));
        }
    }
}

class MetricTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string
    ) {
        super(label, collapsibleState);
    }
}
