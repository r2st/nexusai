import * as vscode from 'vscode';
import { NexusAIClient, CompletionItem } from './client';

export class CompletionProvider implements vscode.CompletionItemProvider {
    private client: NexusAIClient;

    constructor(client: NexusAIClient) {
        this.client = client;
    }

    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        token: vscode.CancellationToken,
        context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[] | vscode.CompletionList | undefined> {
        // Check if AI completions are enabled
        const config = vscode.workspace.getConfiguration('nexusai');
        if (!config.get<boolean>('enabled', true)) {
            return undefined;
        }

        // Map trigger kind
        const triggerKind = context.triggerKind === vscode.CompletionTriggerKind.Invoke ? 1 :
            context.triggerKind === vscode.CompletionTriggerKind.TriggerCharacter ? 2 : 3;

        try {
            const completions = await this.client.getCompletions(
                document.uri.toString(),
                document.getText(),
                { line: position.line, character: position.character },
                document.languageId,
                triggerKind,
                context.triggerCharacter
            );

            if (token.isCancellationRequested) {
                return undefined;
            }

            return completions.map(item => this.toVSCodeCompletion(item, position));

        } catch (error) {
            console.error('Completion error:', error);
            return undefined;
        }
    }

    private toVSCodeCompletion(
        item: CompletionItem,
        position: vscode.Position
    ): vscode.CompletionItem {
        const completion = new vscode.CompletionItem(
            item.label,
            this.mapKind(item.kind)
        );

        completion.detail = item.detail;
        completion.documentation = item.documentation
            ? new vscode.MarkdownString(item.documentation)
            : undefined;
        completion.sortText = item.sort_text;
        completion.filterText = item.filter_text;

        if (item.insert_text) {
            if (item.insert_text_format === 2) {
                // Snippet format
                completion.insertText = new vscode.SnippetString(item.insert_text);
            } else {
                completion.insertText = item.insert_text;
            }
        }

        // Add NexusAI badge
        completion.detail = completion.detail
            ? `$(sparkle) ${completion.detail}`
            : '$(sparkle) NexusAI';

        return completion;
    }

    private mapKind(kind: number): vscode.CompletionItemKind {
        // Map LSP completion kinds to VS Code kinds
        const kindMap: Record<number, vscode.CompletionItemKind> = {
            1: vscode.CompletionItemKind.Text,
            2: vscode.CompletionItemKind.Method,
            3: vscode.CompletionItemKind.Function,
            4: vscode.CompletionItemKind.Constructor,
            5: vscode.CompletionItemKind.Field,
            6: vscode.CompletionItemKind.Variable,
            7: vscode.CompletionItemKind.Class,
            8: vscode.CompletionItemKind.Interface,
            9: vscode.CompletionItemKind.Module,
            10: vscode.CompletionItemKind.Property,
            11: vscode.CompletionItemKind.Unit,
            12: vscode.CompletionItemKind.Value,
            13: vscode.CompletionItemKind.Enum,
            14: vscode.CompletionItemKind.Keyword,
            15: vscode.CompletionItemKind.Snippet,
            16: vscode.CompletionItemKind.Color,
            17: vscode.CompletionItemKind.File,
            18: vscode.CompletionItemKind.Reference,
            19: vscode.CompletionItemKind.Folder,
            20: vscode.CompletionItemKind.EnumMember,
            21: vscode.CompletionItemKind.Constant,
            22: vscode.CompletionItemKind.Struct,
            23: vscode.CompletionItemKind.Event,
            24: vscode.CompletionItemKind.Operator,
            25: vscode.CompletionItemKind.TypeParameter,
        };

        return kindMap[kind] || vscode.CompletionItemKind.Text;
    }
}
