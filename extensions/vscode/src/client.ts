import axios, { AxiosInstance, AxiosError } from 'axios';
import * as WebSocket from 'ws';

export interface Capabilities {
    diagnostics: boolean;
    code_actions: boolean;
    completion: boolean;
    hover: boolean;
    document_symbols: boolean;
    workspace_symbols: boolean;
    formatting: boolean;
    rename: boolean;
    references: boolean;
    definition: boolean;
    chat: boolean;
    inline_suggestions: boolean;
}

export interface Position {
    line: number;
    character: number;
}

export interface Range {
    start: Position;
    end: Position;
}

export interface QuickFix {
    title: string;
    kind: string;
    edit?: Record<string, unknown>;
    command?: string;
    arguments?: unknown[];
    is_preferred: boolean;
}

export interface AnalysisIssue {
    id: string;
    message: string;
    severity: 'error' | 'warning' | 'info' | 'hint';
    category: string;
    range: Range;
    source: string;
    code?: string;
    code_description?: string;
    related_information?: Record<string, unknown>[];
    quick_fixes: QuickFix[];
    tags: string[];
}

export interface AnalysisResult {
    file_uri: string;
    version: number;
    issue_count: number;
    error_count: number;
    warning_count: number;
    security_issue_count: number;
    analysis_time_ms: number;
    issues: AnalysisIssue[];
    metrics: Record<string, unknown>;
}

export interface CompletionItem {
    label: string;
    kind: number;
    detail?: string;
    documentation?: string;
    sort_text?: string;
    filter_text?: string;
    insert_text?: string;
    insert_text_format: number;
    text_edit?: Record<string, unknown>;
    additional_text_edits?: Record<string, unknown>[];
    command?: Record<string, unknown>;
    data?: unknown;
}

export interface ChatResponse {
    message: string;
    conversation_id: string;
    code_blocks: { id: number; language: string; code: string }[];
    suggested_edits: Record<string, unknown>[];
    references: Record<string, unknown>[];
    follow_up_questions: string[];
}

export interface HoverInfo {
    contents: string;
    range?: Range;
}

export class NexusAIClient {
    private axios: AxiosInstance;
    private ws: WebSocket | null = null;
    private serverUrl: string;
    private apiKey: string;
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private eventHandlers: Map<string, ((data: unknown) => void)[]> = new Map();

    constructor(serverUrl: string, apiKey: string) {
        this.serverUrl = serverUrl;
        this.apiKey = apiKey;
        this.axios = this.createAxiosInstance();
    }

    private createAxiosInstance(): AxiosInstance {
        return axios.create({
            baseURL: `${this.serverUrl}/api/v1/extensions`,
            headers: {
                'Content-Type': 'application/json',
                ...(this.apiKey && { 'Authorization': `Bearer ${this.apiKey}` })
            },
            timeout: 30000
        });
    }

    updateConfig(serverUrl: string, apiKey: string) {
        this.serverUrl = serverUrl;
        this.apiKey = apiKey;
        this.axios = this.createAxiosInstance();

        // Reconnect WebSocket if connected
        if (this.ws) {
            this.ws.close();
            this.connectWebSocket();
        }
    }

    async getCapabilities(): Promise<Capabilities> {
        const response = await this.axios.get<Capabilities>('/capabilities');
        return response.data;
    }

    async analyze(
        fileUri: string,
        content: string,
        languageId: string,
        version: number = 1,
        analysisTypes: string[] = ['diagnostics', 'smells', 'security']
    ): Promise<AnalysisResult> {
        const response = await this.axios.post<AnalysisResult>('/analyze', {
            file_uri: fileUri,
            content,
            language_id: languageId,
            version,
            analysis_types: analysisTypes
        });
        return response.data;
    }

    async getDiagnostics(
        fileUri: string,
        content: string,
        languageId: string,
        version: number = 1
    ): Promise<{ file_uri: string; version: number; diagnostics: AnalysisIssue[] }> {
        const response = await this.axios.post('/diagnostics', {
            file_uri: fileUri,
            content,
            language_id: languageId,
            version
        });
        return response.data;
    }

    async getCompletions(
        fileUri: string,
        content: string,
        position: Position,
        languageId: string,
        triggerKind: number = 1,
        triggerCharacter?: string
    ): Promise<CompletionItem[]> {
        const response = await this.axios.post<CompletionItem[]>('/completions', {
            file_uri: fileUri,
            content,
            position,
            language_id: languageId,
            trigger_kind: triggerKind,
            trigger_character: triggerCharacter,
            max_results: 10
        });
        return response.data;
    }

    async getHover(
        fileUri: string,
        content: string,
        position: Position,
        languageId: string
    ): Promise<HoverInfo | null> {
        const response = await this.axios.post<HoverInfo | null>('/hover', {
            file_uri: fileUri,
            content,
            position,
            language_id: languageId
        });
        return response.data;
    }

    async getQuickFixes(
        issue: AnalysisIssue,
        fileUri: string,
        content: string,
        languageId: string
    ): Promise<QuickFix[]> {
        const response = await this.axios.post<QuickFix[]>('/quick-fixes', {
            issue,
            file_uri: fileUri,
            content,
            language_id: languageId
        });
        return response.data;
    }

    async chat(
        message: string,
        conversationId?: string,
        fileContext?: Record<string, unknown>,
        selection?: string,
        command?: string
    ): Promise<ChatResponse> {
        const response = await this.axios.post<ChatResponse>('/chat', {
            message,
            conversation_id: conversationId,
            file_context: fileContext,
            selection,
            command
        });
        return response.data;
    }

    // WebSocket for real-time sync
    connectWebSocket(token?: string): void {
        const wsUrl = this.serverUrl.replace('http', 'ws');
        const wsToken = token || this.apiKey || 'anonymous';

        try {
            this.ws = new WebSocket(`${wsUrl}/api/v1/extensions/ws/${wsToken}`);

            this.ws.on('open', () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
            });

            this.ws.on('message', (data: WebSocket.Data) => {
                try {
                    const message = JSON.parse(data.toString());
                    this.handleWebSocketMessage(message);
                } catch (error) {
                    console.error('WebSocket message parse error:', error);
                }
            });

            this.ws.on('close', () => {
                console.log('WebSocket disconnected');
                this.attemptReconnect();
            });

            this.ws.on('error', (error) => {
                console.error('WebSocket error:', error);
            });
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.attemptReconnect();
        }
    }

    private handleWebSocketMessage(message: { type: string; payload?: unknown }) {
        const handlers = this.eventHandlers.get(message.type);
        if (handlers) {
            handlers.forEach(handler => handler(message.payload));
        }
    }

    private attemptReconnect(): void {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Attempting WebSocket reconnect in ${delay}ms...`);
            setTimeout(() => this.connectWebSocket(), delay);
        }
    }

    on(event: string, handler: (data: unknown) => void): void {
        if (!this.eventHandlers.has(event)) {
            this.eventHandlers.set(event, []);
        }
        this.eventHandlers.get(event)!.push(handler);
    }

    off(event: string, handler: (data: unknown) => void): void {
        const handlers = this.eventHandlers.get(event);
        if (handlers) {
            const index = handlers.indexOf(handler);
            if (index !== -1) {
                handlers.splice(index, 1);
            }
        }
    }

    sendWebSocketMessage(type: string, payload: unknown): void {
        if (this.ws && this.ws.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type, payload }));
        }
    }

    disconnect(): void {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}
