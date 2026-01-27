/**
 * Inline Hint Provider
 * 
 * Provides inline hints for code analysis results.
 */

import * as vscode from 'vscode';
import { NexusAIService } from '../services/nexusai-service';

export class InlineHintProvider implements vscode.InlayHintsProvider {
    private hints: Map<string, vscode.InlayHint[]> = new Map();

    constructor(private readonly service: NexusAIService) {}

    async provideInlayHints(
        document: vscode.TextDocument,
        range: vscode.Range,
        _token: vscode.CancellationToken
    ): Promise<vscode.InlayHint[]> {
        // Return cached hints for this document
        const cachedHints = this.hints.get(document.uri.toString());
        if (cachedHints) {
            return cachedHints.filter(hint => 
                range.contains(hint.position)
            );
        }

        return [];
    }

    updateHints(uri: vscode.Uri, hints: Array<{
        line: number;
        column: number;
        label: string;
        kind: 'type' | 'parameter' | 'other';
    }>): void {
        const inlayHints = hints.map(h => {
            const position = new vscode.Position(h.line - 1, h.column - 1);
            const hint = new vscode.InlayHint(
                position,
                h.label,
                h.kind === 'type' ? vscode.InlayHintKind.Type :
                h.kind === 'parameter' ? vscode.InlayHintKind.Parameter :
                undefined
            );
            hint.paddingLeft = true;
            hint.paddingRight = true;
            return hint;
        });

        this.hints.set(uri.toString(), inlayHints);
    }

    clearHints(uri: vscode.Uri): void {
        this.hints.delete(uri.toString());
    }
}
