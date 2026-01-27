import * as vscode from 'vscode';
import { DiagnosticsProvider } from './diagnostics';
import { AnalysisIssue } from './client';

export class IssuesViewProvider implements vscode.TreeDataProvider<IssueTreeItem> {
    private _onDidChangeTreeData: vscode.EventEmitter<IssueTreeItem | undefined | null | void> =
        new vscode.EventEmitter<IssueTreeItem | undefined | null | void>();
    readonly onDidChangeTreeData: vscode.Event<IssueTreeItem | undefined | null | void> =
        this._onDidChangeTreeData.event;

    private diagnosticsProvider: DiagnosticsProvider;

    constructor(diagnosticsProvider: DiagnosticsProvider) {
        this.diagnosticsProvider = diagnosticsProvider;

        // Refresh when diagnostics change
        vscode.languages.onDidChangeDiagnostics(() => {
            this.refresh();
        });
    }

    refresh(): void {
        this._onDidChangeTreeData.fire();
    }

    getTreeItem(element: IssueTreeItem): vscode.TreeItem {
        return element;
    }

    getChildren(element?: IssueTreeItem): Thenable<IssueTreeItem[]> {
        if (!element) {
            // Root level - show files with issues
            return Promise.resolve(this.getFileItems());
        } else if (element.contextValue === 'file') {
            // File level - show issues in file
            return Promise.resolve(this.getIssueItems(element.resourceUri!));
        }
        return Promise.resolve([]);
    }

    private getFileItems(): IssueTreeItem[] {
        const items: IssueTreeItem[] = [];
        const allIssues = this.diagnosticsProvider.getAllIssues();

        for (const { uri, issues } of allIssues) {
            if (issues.length === 0) {
                continue;
            }

            const counts = this.countBySeverity(issues);
            const label = uri.path.split('/').pop() || uri.toString();
            const description = this.formatCounts(counts);

            const item = new IssueTreeItem(
                label,
                vscode.TreeItemCollapsibleState.Expanded,
                'file',
                uri
            );
            item.description = description;
            item.iconPath = this.getFileIcon(counts);
            items.push(item);
        }

        // Sort by error count (most errors first)
        items.sort((a, b) => {
            const aIssues = this.diagnosticsProvider.getIssuesForDocument(a.resourceUri!);
            const bIssues = this.diagnosticsProvider.getIssuesForDocument(b.resourceUri!);
            const aErrors = aIssues.filter(i => i.severity === 'error').length;
            const bErrors = bIssues.filter(i => i.severity === 'error').length;
            return bErrors - aErrors;
        });

        return items;
    }

    private getIssueItems(uri: vscode.Uri): IssueTreeItem[] {
        const issues = this.diagnosticsProvider.getIssuesForDocument(uri);

        return issues.map(issue => {
            const item = new IssueTreeItem(
                issue.message,
                vscode.TreeItemCollapsibleState.None,
                'issue'
            );
            item.description = `Line ${issue.range.start.line + 1}`;
            item.iconPath = this.getSeverityIcon(issue.severity);
            item.tooltip = this.formatTooltip(issue);
            item.command = {
                command: 'vscode.open',
                title: 'Go to Issue',
                arguments: [
                    uri,
                    {
                        selection: new vscode.Range(
                            new vscode.Position(issue.range.start.line, issue.range.start.character),
                            new vscode.Position(issue.range.end.line, issue.range.end.character)
                        )
                    }
                ]
            };
            return item;
        });
    }

    private countBySeverity(issues: AnalysisIssue[]): Record<string, number> {
        const counts: Record<string, number> = {
            error: 0,
            warning: 0,
            info: 0,
            hint: 0
        };

        for (const issue of issues) {
            counts[issue.severity] = (counts[issue.severity] || 0) + 1;
        }

        return counts;
    }

    private formatCounts(counts: Record<string, number>): string {
        const parts: string[] = [];
        if (counts.error > 0) parts.push(`${counts.error} errors`);
        if (counts.warning > 0) parts.push(`${counts.warning} warnings`);
        if (counts.info > 0) parts.push(`${counts.info} info`);
        return parts.join(', ') || 'No issues';
    }

    private getFileIcon(counts: Record<string, number>): vscode.ThemeIcon {
        if (counts.error > 0) {
            return new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground'));
        } else if (counts.warning > 0) {
            return new vscode.ThemeIcon('warning', new vscode.ThemeColor('editorWarning.foreground'));
        } else {
            return new vscode.ThemeIcon('info', new vscode.ThemeColor('editorInfo.foreground'));
        }
    }

    private getSeverityIcon(severity: string): vscode.ThemeIcon {
        switch (severity) {
            case 'error':
                return new vscode.ThemeIcon('error', new vscode.ThemeColor('errorForeground'));
            case 'warning':
                return new vscode.ThemeIcon('warning', new vscode.ThemeColor('editorWarning.foreground'));
            case 'info':
                return new vscode.ThemeIcon('info', new vscode.ThemeColor('editorInfo.foreground'));
            case 'hint':
            default:
                return new vscode.ThemeIcon('lightbulb', new vscode.ThemeColor('editorHint.foreground'));
        }
    }

    private formatTooltip(issue: AnalysisIssue): vscode.MarkdownString {
        const md = new vscode.MarkdownString();
        md.appendMarkdown(`**${issue.severity.toUpperCase()}**: ${issue.message}\n\n`);
        md.appendMarkdown(`**Category**: ${issue.category}\n\n`);
        if (issue.code) {
            md.appendMarkdown(`**Code**: \`${issue.code}\`\n\n`);
        }
        if (issue.code_description) {
            md.appendMarkdown(`${issue.code_description}\n\n`);
        }
        if (issue.quick_fixes.length > 0) {
            md.appendMarkdown(`**Quick fixes available**: ${issue.quick_fixes.length}`);
        }
        return md;
    }
}

class IssueTreeItem extends vscode.TreeItem {
    constructor(
        public readonly label: string,
        public readonly collapsibleState: vscode.TreeItemCollapsibleState,
        public readonly contextValue: string,
        public readonly resourceUri?: vscode.Uri
    ) {
        super(label, collapsibleState);
    }
}
