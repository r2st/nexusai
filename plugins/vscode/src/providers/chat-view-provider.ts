/**
 * Chat View Provider
 * 
 * Provides the webview panel for the chat interface.
 */

import * as vscode from 'vscode';
import { NexusAIService, ChatMessage } from '../services/nexusai-service';

export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'nexusai.chatView';
    private _view?: vscode.WebviewView;
    private _isStreaming = false;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        private readonly _service: NexusAIService
    ) {}

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        _context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ): void {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri],
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async (message) => {
            switch (message.type) {
                case 'sendMessage':
                    await this._handleUserMessage(message.text, message.context);
                    break;
                case 'stopGeneration':
                    this._isStreaming = false;
                    break;
                case 'clearChat':
                    this._service.clearConversation();
                    this._postMessage({ type: 'cleared' });
                    break;
                case 'copyCode':
                    await vscode.env.clipboard.writeText(message.code);
                    vscode.window.showInformationMessage('Code copied to clipboard');
                    break;
                case 'insertCode':
                    await this._insertCodeAtCursor(message.code);
                    break;
                case 'ready':
                    // Send conversation history when webview is ready
                    const history = this._service.getConversationHistory();
                    this._postMessage({ type: 'history', messages: history });
                    break;
            }
        });
    }

    private async _handleUserMessage(text: string, context?: any): Promise<void> {
        if (this._isStreaming) {
            return;
        }

        // Get current editor context if not provided
        if (!context) {
            context = this._getEditorContext();
        }

        this._isStreaming = true;
        this._postMessage({ type: 'streamStart' });

        try {
            let fullResponse = '';
            
            for await (const chunk of this._service.chatStream(text, context)) {
                if (!this._isStreaming) {
                    break;
                }
                fullResponse += chunk;
                this._postMessage({ type: 'streamChunk', content: chunk });
            }

            this._postMessage({ type: 'streamEnd', content: fullResponse });
        } catch (error) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            this._postMessage({ type: 'error', message: errorMessage });
        } finally {
            this._isStreaming = false;
        }
    }

    private _getEditorContext(): { code?: string; language?: string; file?: string } | undefined {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            return undefined;
        }

        const selection = editor.selection;
        const code = selection.isEmpty
            ? undefined
            : editor.document.getText(selection);

        return {
            code,
            language: editor.document.languageId,
            file: editor.document.fileName,
        };
    }

    private async _insertCodeAtCursor(code: string): Promise<void> {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor to insert code');
            return;
        }

        await editor.edit((editBuilder) => {
            editBuilder.insert(editor.selection.active, code);
        });
    }

    public sendMessage(message: string, context?: any): void {
        this._handleUserMessage(message, context);
    }

    public addCodeContext(code: string, language: string, description: string): void {
        this._postMessage({
            type: 'addContext',
            code,
            language,
            description,
        });
    }

    public clearChat(): void {
        this._service.clearConversation();
        this._postMessage({ type: 'cleared' });
    }

    private _postMessage(message: any): void {
        this._view?.webview.postMessage(message);
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        const nonce = this._getNonce();

        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src ${webview.cspSource} 'unsafe-inline'; script-src 'nonce-${nonce}';">
    <title>NexusAI Chat</title>
    <style>
        * {
            box-sizing: border-box;
            margin: 0;
            padding: 0;
        }
        
        body {
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            color: var(--vscode-foreground);
            background: var(--vscode-sideBar-background);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }
        
        .chat-container {
            flex: 1;
            overflow-y: auto;
            padding: 12px;
        }
        
        .message {
            margin-bottom: 16px;
            animation: fadeIn 0.2s ease-in;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(4px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .message-header {
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 4px;
        }
        
        .message-role {
            font-weight: 600;
            font-size: 12px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .message-role.user {
            color: var(--vscode-textLink-foreground);
        }
        
        .message-role.assistant {
            color: var(--vscode-gitDecoration-addedResourceForeground);
        }
        
        .message-content {
            padding: 8px 12px;
            border-radius: 8px;
            line-height: 1.5;
            white-space: pre-wrap;
            word-wrap: break-word;
        }
        
        .message.user .message-content {
            background: var(--vscode-input-background);
            border: 1px solid var(--vscode-input-border);
        }
        
        .message.assistant .message-content {
            background: var(--vscode-editor-background);
            border: 1px solid var(--vscode-panel-border);
        }
        
        .code-block {
            position: relative;
            margin: 8px 0;
            background: var(--vscode-textCodeBlock-background);
            border-radius: 6px;
            overflow: hidden;
        }
        
        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 4px 12px;
            background: var(--vscode-titleBar-activeBackground);
            font-size: 11px;
            color: var(--vscode-descriptionForeground);
        }
        
        .code-actions {
            display: flex;
            gap: 4px;
        }
        
        .code-action {
            padding: 2px 8px;
            border: none;
            background: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border-radius: 4px;
            cursor: pointer;
            font-size: 11px;
        }
        
        .code-action:hover {
            background: var(--vscode-button-secondaryHoverBackground);
        }
        
        .code-content {
            padding: 12px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
        }
        
        .input-container {
            padding: 12px;
            border-top: 1px solid var(--vscode-panel-border);
            background: var(--vscode-sideBar-background);
        }
        
        .input-wrapper {
            display: flex;
            gap: 8px;
        }
        
        #message-input {
            flex: 1;
            padding: 8px 12px;
            border: 1px solid var(--vscode-input-border);
            background: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 6px;
            font-family: inherit;
            font-size: inherit;
            resize: none;
            min-height: 36px;
            max-height: 120px;
        }
        
        #message-input:focus {
            outline: none;
            border-color: var(--vscode-focusBorder);
        }
        
        #send-button {
            padding: 8px 16px;
            border: none;
            background: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border-radius: 6px;
            cursor: pointer;
            font-weight: 500;
        }
        
        #send-button:hover {
            background: var(--vscode-button-hoverBackground);
        }
        
        #send-button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        .typing-indicator {
            display: flex;
            gap: 4px;
            padding: 8px 12px;
        }
        
        .typing-dot {
            width: 8px;
            height: 8px;
            background: var(--vscode-descriptionForeground);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out;
        }
        
        .typing-dot:nth-child(1) { animation-delay: -0.32s; }
        .typing-dot:nth-child(2) { animation-delay: -0.16s; }
        
        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }
        
        .welcome {
            text-align: center;
            padding: 24px;
            color: var(--vscode-descriptionForeground);
        }
        
        .welcome h2 {
            margin-bottom: 8px;
            color: var(--vscode-foreground);
        }
        
        .quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
            margin-top: 16px;
        }
        
        .quick-action {
            padding: 6px 12px;
            border: 1px solid var(--vscode-button-border);
            background: transparent;
            color: var(--vscode-foreground);
            border-radius: 16px;
            cursor: pointer;
            font-size: 12px;
        }
        
        .quick-action:hover {
            background: var(--vscode-list-hoverBackground);
        }
        
        .context-badge {
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            background: var(--vscode-badge-background);
            color: var(--vscode-badge-foreground);
            border-radius: 4px;
            font-size: 11px;
            margin-bottom: 8px;
        }
    </style>
</head>
<body>
    <div class="chat-container" id="chat-container">
        <div class="welcome" id="welcome">
            <h2>NexusAI Assistant</h2>
            <p>Ask questions about your code, get explanations, find bugs, and more.</p>
            <div class="quick-actions">
                <button class="quick-action" data-action="Explain this code">Explain Code</button>
                <button class="quick-action" data-action="Find bugs in this code">Find Bugs</button>
                <button class="quick-action" data-action="How can I improve this code?">Improve Code</button>
                <button class="quick-action" data-action="Generate tests for this code">Generate Tests</button>
            </div>
        </div>
    </div>
    
    <div class="input-container">
        <div class="input-wrapper">
            <textarea 
                id="message-input" 
                placeholder="Ask anything about your code..." 
                rows="1"
            ></textarea>
            <button id="send-button">Send</button>
        </div>
    </div>
    
    <script nonce="${nonce}">
        const vscode = acquireVsCodeApi();
        const chatContainer = document.getElementById('chat-container');
        const welcome = document.getElementById('welcome');
        const messageInput = document.getElementById('message-input');
        const sendButton = document.getElementById('send-button');
        
        let isStreaming = false;
        let currentStreamMessage = null;
        
        // Auto-resize textarea
        messageInput.addEventListener('input', () => {
            messageInput.style.height = 'auto';
            messageInput.style.height = Math.min(messageInput.scrollHeight, 120) + 'px';
        });
        
        // Handle Enter key
        messageInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendMessage();
            }
        });
        
        // Send button click
        sendButton.addEventListener('click', sendMessage);
        
        // Quick actions
        document.querySelectorAll('.quick-action').forEach(btn => {
            btn.addEventListener('click', () => {
                messageInput.value = btn.dataset.action;
                sendMessage();
            });
        });
        
        function sendMessage() {
            const text = messageInput.value.trim();
            if (!text || isStreaming) return;
            
            // Hide welcome
            welcome.style.display = 'none';
            
            // Add user message
            addMessage('user', text);
            
            // Clear input
            messageInput.value = '';
            messageInput.style.height = 'auto';
            
            // Send to extension
            vscode.postMessage({ type: 'sendMessage', text });
        }
        
        function addMessage(role, content) {
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message ' + role;
            messageDiv.innerHTML = \`
                <div class="message-header">
                    <span class="message-role \${role}">\${role === 'user' ? 'You' : 'NexusAI'}</span>
                </div>
                <div class="message-content">\${formatContent(content)}</div>
            \`;
            chatContainer.appendChild(messageDiv);
            scrollToBottom();
            return messageDiv;
        }
        
        function formatContent(content) {
            // Simple markdown-like formatting
            let formatted = escapeHtml(content);
            
            // Code blocks
            formatted = formatted.replace(/\`\`\`(\\w*)\\n([\\s\\S]*?)\`\`\`/g, (_, lang, code) => {
                return \`<div class="code-block">
                    <div class="code-header">
                        <span>\${lang || 'code'}</span>
                        <div class="code-actions">
                            <button class="code-action" onclick="copyCode(this)">Copy</button>
                            <button class="code-action" onclick="insertCode(this)">Insert</button>
                        </div>
                    </div>
                    <pre class="code-content">\${code.trim()}</pre>
                </div>\`;
            });
            
            // Inline code
            formatted = formatted.replace(/\`([^\`]+)\`/g, '<code>$1</code>');
            
            // Bold
            formatted = formatted.replace(/\\*\\*([^*]+)\\*\\*/g, '<strong>$1</strong>');
            
            // Line breaks
            formatted = formatted.replace(/\\n/g, '<br>');
            
            return formatted;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        function scrollToBottom() {
            chatContainer.scrollTop = chatContainer.scrollHeight;
        }
        
        function showTypingIndicator() {
            const indicator = document.createElement('div');
            indicator.id = 'typing-indicator';
            indicator.className = 'message assistant';
            indicator.innerHTML = \`
                <div class="message-header">
                    <span class="message-role assistant">NexusAI</span>
                </div>
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            \`;
            chatContainer.appendChild(indicator);
            scrollToBottom();
        }
        
        function removeTypingIndicator() {
            const indicator = document.getElementById('typing-indicator');
            if (indicator) indicator.remove();
        }
        
        // Copy code to clipboard
        window.copyCode = function(btn) {
            const code = btn.closest('.code-block').querySelector('.code-content').textContent;
            vscode.postMessage({ type: 'copyCode', code });
        };
        
        // Insert code at cursor
        window.insertCode = function(btn) {
            const code = btn.closest('.code-block').querySelector('.code-content').textContent;
            vscode.postMessage({ type: 'insertCode', code });
        };
        
        // Handle messages from extension
        window.addEventListener('message', (event) => {
            const message = event.data;
            
            switch (message.type) {
                case 'streamStart':
                    isStreaming = true;
                    sendButton.textContent = 'Stop';
                    showTypingIndicator();
                    break;
                    
                case 'streamChunk':
                    removeTypingIndicator();
                    if (!currentStreamMessage) {
                        currentStreamMessage = addMessage('assistant', '');
                    }
                    const content = currentStreamMessage.querySelector('.message-content');
                    content.innerHTML = formatContent(
                        content.textContent + message.content
                    );
                    scrollToBottom();
                    break;
                    
                case 'streamEnd':
                    isStreaming = false;
                    currentStreamMessage = null;
                    sendButton.textContent = 'Send';
                    removeTypingIndicator();
                    break;
                    
                case 'error':
                    isStreaming = false;
                    currentStreamMessage = null;
                    sendButton.textContent = 'Send';
                    removeTypingIndicator();
                    addMessage('assistant', '❌ Error: ' + message.message);
                    break;
                    
                case 'cleared':
                    chatContainer.innerHTML = '';
                    chatContainer.appendChild(welcome);
                    welcome.style.display = 'block';
                    break;
                    
                case 'history':
                    if (message.messages && message.messages.length > 0) {
                        welcome.style.display = 'none';
                        message.messages.forEach(msg => {
                            addMessage(msg.role, msg.content);
                        });
                    }
                    break;
                    
                case 'addContext':
                    // Show context badge and auto-include in next message
                    break;
            }
        });
        
        // Notify extension that webview is ready
        vscode.postMessage({ type: 'ready' });
    </script>
</body>
</html>`;
    }

    private _getNonce(): string {
        let text = '';
        const possible = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
        for (let i = 0; i < 32; i++) {
            text += possible.charAt(Math.floor(Math.random() * possible.length));
        }
        return text;
    }
}
