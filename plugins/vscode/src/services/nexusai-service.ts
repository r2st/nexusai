/**
 * NexusAI Service
 * 
 * Handles all communication with the NexusAI backend API.
 */

import * as vscode from 'vscode';
import axios, { AxiosInstance } from 'axios';

// =============================================================================
// Types
// =============================================================================

export interface ChatMessage {
    role: 'user' | 'assistant' | 'system';
    content: string;
    timestamp?: number;
}

export interface ChatResponse {
    message: string;
    conversationId: string;
    suggestions?: string[];
}

export interface CodeIssue {
    line: number;
    column: number;
    endLine?: number;
    endColumn?: number;
    severity: 'error' | 'warning' | 'info' | 'hint';
    message: string;
    code?: string;
    source: string;
    fix?: {
        description: string;
        changes: Array<{
            range: { start: number; end: number };
            newText: string;
        }>;
    };
}

export interface AnalysisResult {
    issues: CodeIssue[];
    metrics?: {
        complexity: number;
        maintainability: number;
        duplication: number;
    };
    summary?: string;
}

export interface ExplanationResult {
    explanation: string;
    concepts?: string[];
    references?: Array<{ title: string; url: string }>;
}

export interface DocumentationResult {
    documentation: string;
    format: 'jsdoc' | 'docstring' | 'markdown';
}

export interface RefactoringResult {
    suggestions: Array<{
        title: string;
        description: string;
        code: string;
        impact: 'low' | 'medium' | 'high';
    }>;
}

export interface TestResult {
    tests: string;
    framework: string;
    coverage?: number;
}

export interface PRReviewResult {
    summary: string;
    issues: CodeIssue[];
    suggestions: string[];
    approvalStatus: 'approve' | 'request_changes' | 'comment';
}

// =============================================================================
// Service
// =============================================================================

export class NexusAIService {
    private client: AxiosInstance;
    private context: vscode.ExtensionContext;
    private conversationId: string | null = null;
    private conversationHistory: ChatMessage[] = [];

    constructor(context: vscode.ExtensionContext) {
        this.context = context;
        this.client = this.createClient();
    }

    private createClient(): AxiosInstance {
        const config = vscode.workspace.getConfiguration('nexusai');
        const endpoint = config.get<string>('apiEndpoint') || 'https://api.nexusai.dev';
        const apiKey = config.get<string>('apiKey') || '';

        return axios.create({
            baseURL: endpoint,
            timeout: 60000,
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
                'X-Client': 'vscode-extension',
                'X-Client-Version': '1.0.0',
            },
        });
    }

    public updateConfiguration(): void {
        this.client = this.createClient();
    }

    public async testConnection(): Promise<boolean> {
        try {
            const response = await this.client.get('/api/v1/health');
            return response.status === 200;
        } catch {
            return false;
        }
    }

    // =========================================================================
    // Chat
    // =========================================================================

    public async chat(
        message: string,
        context?: { code?: string; language?: string; file?: string }
    ): Promise<ChatResponse> {
        this.conversationHistory.push({
            role: 'user',
            content: message,
            timestamp: Date.now(),
        });

        try {
            const response = await this.client.post('/api/v1/chat', {
                message,
                conversationId: this.conversationId,
                context,
                history: this.conversationHistory.slice(-10), // Last 10 messages
            });

            const assistantMessage = response.data.message;
            this.conversationId = response.data.conversationId;

            this.conversationHistory.push({
                role: 'assistant',
                content: assistantMessage,
                timestamp: Date.now(),
            });

            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async *chatStream(
        message: string,
        context?: { code?: string; language?: string; file?: string }
    ): AsyncGenerator<string, void, unknown> {
        this.conversationHistory.push({
            role: 'user',
            content: message,
            timestamp: Date.now(),
        });

        try {
            const response = await this.client.post(
                '/api/v1/chat/stream',
                {
                    message,
                    conversationId: this.conversationId,
                    context,
                    history: this.conversationHistory.slice(-10),
                },
                { responseType: 'stream' }
            );

            let fullMessage = '';
            
            for await (const chunk of response.data) {
                const text = chunk.toString();
                const lines = text.split('\n').filter((line: string) => line.startsWith('data: '));
                
                for (const line of lines) {
                    const data = line.slice(6);
                    if (data === '[DONE]') {
                        break;
                    }
                    try {
                        const parsed = JSON.parse(data);
                        if (parsed.content) {
                            fullMessage += parsed.content;
                            yield parsed.content;
                        }
                        if (parsed.conversationId) {
                            this.conversationId = parsed.conversationId;
                        }
                    } catch {
                        // Skip invalid JSON
                    }
                }
            }

            this.conversationHistory.push({
                role: 'assistant',
                content: fullMessage,
                timestamp: Date.now(),
            });
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public clearConversation(): void {
        this.conversationId = null;
        this.conversationHistory = [];
    }

    public getConversationHistory(): ChatMessage[] {
        return [...this.conversationHistory];
    }

    // =========================================================================
    // Code Analysis
    // =========================================================================

    public async analyzeCode(
        code: string,
        language: string,
        filename?: string
    ): Promise<CodeIssue[]> {
        try {
            const response = await this.client.post('/api/v1/analyze', {
                code,
                language,
                filename,
                checks: ['bugs', 'security', 'style', 'complexity'],
            });
            return response.data.issues;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async analyzeWorkspace(
        files: Array<{ path: string; content: string; language: string }>
    ): Promise<AnalysisResult> {
        try {
            const response = await this.client.post('/api/v1/analyze/workspace', {
                files,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    // =========================================================================
    // Code Intelligence
    // =========================================================================

    public async explainCode(
        code: string,
        language: string,
        question?: string
    ): Promise<ExplanationResult> {
        try {
            const response = await this.client.post('/api/v1/explain', {
                code,
                language,
                question,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async generateDocumentation(
        code: string,
        language: string,
        style?: string
    ): Promise<DocumentationResult> {
        try {
            const response = await this.client.post('/api/v1/document', {
                code,
                language,
                style: style || 'auto',
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async suggestRefactoring(
        code: string,
        language: string
    ): Promise<RefactoringResult> {
        try {
            const response = await this.client.post('/api/v1/refactor', {
                code,
                language,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async generateTests(
        code: string,
        language: string,
        framework?: string
    ): Promise<TestResult> {
        try {
            const response = await this.client.post('/api/v1/generate-tests', {
                code,
                language,
                framework,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async fixIssue(
        code: string,
        issue: CodeIssue,
        language: string
    ): Promise<string> {
        try {
            const response = await this.client.post('/api/v1/fix', {
                code,
                issue,
                language,
            });
            return response.data.fixedCode;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    // =========================================================================
    // PR Review
    // =========================================================================

    public async reviewPullRequest(
        diff: string,
        context?: { title?: string; description?: string; baseBranch?: string }
    ): Promise<PRReviewResult> {
        try {
            const response = await this.client.post('/api/v1/review-pr', {
                diff,
                context,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    // =========================================================================
    // Metrics
    // =========================================================================

    public async getCodeMetrics(
        code: string,
        language: string
    ): Promise<{
        complexity: number;
        maintainability: number;
        linesOfCode: number;
        functions: number;
        classes: number;
    }> {
        try {
            const response = await this.client.post('/api/v1/metrics', {
                code,
                language,
            });
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    // =========================================================================
    // Authentication
    // =========================================================================

    public async signIn(credentials: { email: string; password: string }): Promise<{
        token: string;
        user: { id: string; email: string; name: string };
    }> {
        try {
            const response = await this.client.post('/api/v1/auth/login', credentials);
            const { token } = response.data;
            
            // Store token
            await this.context.secrets.store('nexusai.token', token);
            
            // Update client with new token
            this.client.defaults.headers['Authorization'] = `Bearer ${token}`;
            
            return response.data;
        } catch (error) {
            throw this.handleError(error);
        }
    }

    public async signOut(): Promise<void> {
        await this.context.secrets.delete('nexusai.token');
        this.client.defaults.headers['Authorization'] = '';
        this.clearConversation();
    }

    public async getStoredToken(): Promise<string | undefined> {
        return await this.context.secrets.get('nexusai.token');
    }

    // =========================================================================
    // Error Handling
    // =========================================================================

    private handleError(error: unknown): Error {
        if (axios.isAxiosError(error)) {
            if (error.response) {
                const message = error.response.data?.message || error.response.statusText;
                return new Error(`NexusAI API Error: ${message}`);
            } else if (error.request) {
                return new Error('NexusAI API is unreachable. Please check your connection.');
            }
        }
        return error instanceof Error ? error : new Error('Unknown error occurred');
    }
}
