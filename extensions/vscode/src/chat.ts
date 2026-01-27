import * as vscode from 'vscode';
import { NexusAIClient } from './client';

export class ChatViewProvider implements vscode.WebviewViewProvider {
    public static readonly viewType = 'nexusai.chat';

    private _view?: vscode.WebviewView;
    private _conversationId?: string;
    private client: NexusAIClient;

    constructor(
        private readonly _extensionUri: vscode.Uri,
        client: NexusAIClient
    ) {
        this.client = client;
    }

    public resolveWebviewView(
        webviewView: vscode.WebviewView,
        context: vscode.WebviewViewResolveContext,
        _token: vscode.CancellationToken
    ) {
        this._view = webviewView;

        webviewView.webview.options = {
            enableScripts: true,
            localResourceRoots: [this._extensionUri]
        };

        webviewView.webview.html = this._getHtmlForWebview(webviewView.webview);

        // Handle messages from the webview
        webviewView.webview.onDidReceiveMessage(async data => {
            switch (data.type) {
                case 'sendMessage':
                    await this._handleMessage(data.message, data.command, data.selection);
                    break;
                case 'applyCode':
                    await this._applyCode(data.code, data.language);
                    break;
                case 'copyCode':
                    await vscode.env.clipboard.writeText(data.code);
                    vscode.window.showInformationMessage('Code copied to clipboard');
                    break;
                case 'newConversation':
                    this._conversationId = undefined;
                    break;
            }
        });

        // Register command for sending messages from other parts of the extension
        vscode.commands.registerCommand('nexusai.chat.sendMessage', async (data: any) => {
            if (data.command && data.selection) {
                await this._handleMessage(data.selection, data.command, data.selection);
            }
        });
    }

    private async _handleMessage(
        message: string,
        command?: string,
        selection?: string
    ) {
        if (!this._view) {
            return;
        }

        // Show loading state
        this._view.webview.postMessage({
            type: 'loading',
            loading: true
        });

        try {
            // Get current file context
            const editor = vscode.window.activeTextEditor;
            const fileContext = editor ? {
                uri: editor.document.uri.toString(),
                language: editor.document.languageId,
                filename: editor.document.fileName.split('/').pop()
            } : undefined;

            const response = await this.client.chat(
                message,
                this._conversationId,
                fileContext,
                selection,
                command
            );

            this._conversationId = response.conversation_id;

            // Send response to webview
            this._view.webview.postMessage({
                type: 'response',
                message: response.message,
                codeBlocks: response.code_blocks,
                followUpQuestions: response.follow_up_questions
            });

        } catch (error: any) {
            this._view.webview.postMessage({
                type: 'error',
                message: error.message || 'Failed to get response'
            });
        }

        // Hide loading state
        this._view.webview.postMessage({
            type: 'loading',
            loading: false
        });
    }

    private async _applyCode(code: string, language: string) {
        const editor = vscode.window.activeTextEditor;
        if (!editor) {
            vscode.window.showWarningMessage('No active editor to apply code');
            return;
        }

        const selection = editor.selection;
        await editor.edit(editBuilder => {
            if (selection.isEmpty) {
                // Insert at cursor position
                editBuilder.insert(selection.active, code);
            } else {
                // Replace selection
                editBuilder.replace(selection, code);
            }
        });

        vscode.window.showInformationMessage('Code applied successfully');
    }

    private _getHtmlForWebview(webview: vscode.Webview): string {
        return `<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
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
            background-color: var(--vscode-sideBar-background);
            height: 100vh;
            display: flex;
            flex-direction: column;
        }

        .header {
            padding: 10px;
            border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border);
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .header h3 {
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }

        .new-chat-btn {
            background: none;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 3px;
        }

        .new-chat-btn:hover {
            background-color: var(--vscode-toolbar-hoverBackground);
        }

        .messages {
            flex: 1;
            overflow-y: auto;
            padding: 10px;
        }

        .message {
            margin-bottom: 15px;
            padding: 10px;
            border-radius: 8px;
        }

        .message.user {
            background-color: var(--vscode-input-background);
            margin-left: 20px;
        }

        .message.assistant {
            background-color: var(--vscode-editor-background);
            margin-right: 20px;
        }

        .message-content {
            white-space: pre-wrap;
            word-break: break-word;
        }

        .code-block {
            margin: 10px 0;
            background-color: var(--vscode-textCodeBlock-background);
            border-radius: 4px;
            overflow: hidden;
        }

        .code-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 5px 10px;
            background-color: var(--vscode-editorGroupHeader-tabsBackground);
            font-size: 11px;
        }

        .code-actions button {
            background: none;
            border: none;
            color: var(--vscode-foreground);
            cursor: pointer;
            padding: 2px 6px;
            margin-left: 5px;
            border-radius: 3px;
        }

        .code-actions button:hover {
            background-color: var(--vscode-toolbar-hoverBackground);
        }

        .code-content {
            padding: 10px;
            overflow-x: auto;
            font-family: var(--vscode-editor-font-family);
            font-size: var(--vscode-editor-font-size);
        }

        .follow-up {
            margin-top: 10px;
        }

        .follow-up-btn {
            display: block;
            width: 100%;
            text-align: left;
            padding: 8px;
            margin-bottom: 5px;
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
        }

        .follow-up-btn:hover {
            background-color: var(--vscode-button-secondaryHoverBackground);
        }

        .input-area {
            padding: 10px;
            border-top: 1px solid var(--vscode-sideBarSectionHeader-border);
        }

        .input-container {
            display: flex;
            gap: 8px;
        }

        textarea {
            flex: 1;
            padding: 8px;
            border: 1px solid var(--vscode-input-border);
            background-color: var(--vscode-input-background);
            color: var(--vscode-input-foreground);
            border-radius: 4px;
            resize: none;
            font-family: var(--vscode-font-family);
            font-size: var(--vscode-font-size);
            min-height: 60px;
        }

        textarea:focus {
            outline: 1px solid var(--vscode-focusBorder);
        }

        .send-btn {
            background-color: var(--vscode-button-background);
            color: var(--vscode-button-foreground);
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            cursor: pointer;
            align-self: flex-end;
        }

        .send-btn:hover {
            background-color: var(--vscode-button-hoverBackground);
        }

        .send-btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }

        .loading {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px;
            color: var(--vscode-descriptionForeground);
        }

        .loading-dots {
            display: flex;
            gap: 4px;
        }

        .loading-dots span {
            width: 6px;
            height: 6px;
            background-color: var(--vscode-foreground);
            border-radius: 50%;
            animation: bounce 1.4s infinite ease-in-out both;
        }

        .loading-dots span:nth-child(1) { animation-delay: -0.32s; }
        .loading-dots span:nth-child(2) { animation-delay: -0.16s; }

        @keyframes bounce {
            0%, 80%, 100% { transform: scale(0); }
            40% { transform: scale(1); }
        }

        .error {
            color: var(--vscode-errorForeground);
            padding: 10px;
            background-color: var(--vscode-inputValidation-errorBackground);
            border: 1px solid var(--vscode-inputValidation-errorBorder);
            border-radius: 4px;
            margin: 10px;
        }

        .welcome {
            text-align: center;
            padding: 20px;
            color: var(--vscode-descriptionForeground);
        }

        .welcome h2 {
            margin-bottom: 10px;
        }

        .welcome p {
            margin-bottom: 15px;
        }

        .quick-actions {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
        }

        .quick-action {
            padding: 6px 12px;
            background-color: var(--vscode-button-secondaryBackground);
            color: var(--vscode-button-secondaryForeground);
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-size: 12px;
        }

        .quick-action:hover {
            background-color: var(--vscode-button-secondaryHoverBackground);
        }
    </style>
</head>
<body>
    <div class="header">
        <h3>NexusAI Chat</h3>
        <button class="new-chat-btn" onclick="newConversation()">+ New Chat</button>
    </div>

    <div class="messages" id="messages">
        <div class="welcome">
            <h2>Welcome to NexusAI</h2>
            <p>Ask me anything about your code or select code and use commands.</p>
            <div class="quick-actions">
                <button class="quick-action" onclick="sendQuickAction('explain')">Explain code</button>
                <button class="quick-action" onclick="sendQuickAction('review')">Review code</button>
                <button class="quick-action" onclick="sendQuickAction('optimize')">Optimize</button>
                <button class="quick-action" onclick="sendQuickAction('document')">Add docs</button>
            </div>
        </div>
    </div>

    <div id="loading" class="loading" style="display: none;">
        <div class="loading-dots">
            <span></span>
            <span></span>
            <span></span>
        </div>
        <span>Thinking...</span>
    </div>

    <div class="input-area">
        <div class="input-container">
            <textarea
                id="input"
                placeholder="Ask NexusAI..."
                onkeydown="handleKeyDown(event)"
            ></textarea>
            <button class="send-btn" onclick="sendMessage()">Send</button>
        </div>
    </div>

    <script>
        const vscode = acquireVsCodeApi();
        const messagesContainer = document.getElementById('messages');
        const inputField = document.getElementById('input');
        const loadingIndicator = document.getElementById('loading');
        let isLoading = false;

        function sendMessage() {
            const message = inputField.value.trim();
            if (!message || isLoading) return;

            addMessage(message, 'user');
            inputField.value = '';

            vscode.postMessage({
                type: 'sendMessage',
                message: message
            });
        }

        function sendQuickAction(action) {
            vscode.postMessage({
                type: 'sendMessage',
                message: \`Please \${action} the selected code or current file.\`,
                command: action
            });
        }

        function handleKeyDown(event) {
            if (event.key === 'Enter' && !event.shiftKey) {
                event.preventDefault();
                sendMessage();
            }
        }

        function newConversation() {
            messagesContainer.innerHTML = \`
                <div class="welcome">
                    <h2>Welcome to NexusAI</h2>
                    <p>Ask me anything about your code or select code and use commands.</p>
                    <div class="quick-actions">
                        <button class="quick-action" onclick="sendQuickAction('explain')">Explain code</button>
                        <button class="quick-action" onclick="sendQuickAction('review')">Review code</button>
                        <button class="quick-action" onclick="sendQuickAction('optimize')">Optimize</button>
                        <button class="quick-action" onclick="sendQuickAction('document')">Add docs</button>
                    </div>
                </div>
            \`;
            vscode.postMessage({ type: 'newConversation' });
        }

        function addMessage(content, role, codeBlocks = [], followUpQuestions = []) {
            // Remove welcome message if present
            const welcome = messagesContainer.querySelector('.welcome');
            if (welcome) welcome.remove();

            const messageDiv = document.createElement('div');
            messageDiv.className = \`message \${role}\`;

            let html = \`<div class="message-content">\${escapeHtml(content)}</div>\`;

            // Add code blocks
            for (const block of codeBlocks) {
                html += \`
                    <div class="code-block">
                        <div class="code-header">
                            <span>\${block.language || 'code'}</span>
                            <div class="code-actions">
                                <button onclick="copyCode('\${encodeURIComponent(block.code)}')">Copy</button>
                                <button onclick="applyCode('\${encodeURIComponent(block.code)}', '\${block.language}')">Apply</button>
                            </div>
                        </div>
                        <pre class="code-content">\${escapeHtml(block.code)}</pre>
                    </div>
                \`;
            }

            // Add follow-up questions
            if (followUpQuestions.length > 0) {
                html += '<div class="follow-up">';
                for (const question of followUpQuestions) {
                    html += \`<button class="follow-up-btn" onclick="askFollowUp('\${encodeURIComponent(question)}')">\${escapeHtml(question)}</button>\`;
                }
                html += '</div>';
            }

            messageDiv.innerHTML = html;
            messagesContainer.appendChild(messageDiv);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }

        function copyCode(encodedCode) {
            vscode.postMessage({
                type: 'copyCode',
                code: decodeURIComponent(encodedCode)
            });
        }

        function applyCode(encodedCode, language) {
            vscode.postMessage({
                type: 'applyCode',
                code: decodeURIComponent(encodedCode),
                language: language
            });
        }

        function askFollowUp(encodedQuestion) {
            inputField.value = decodeURIComponent(encodedQuestion);
            sendMessage();
        }

        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }

        // Handle messages from the extension
        window.addEventListener('message', event => {
            const data = event.data;
            switch (data.type) {
                case 'response':
                    addMessage(data.message, 'assistant', data.codeBlocks || [], data.followUpQuestions || []);
                    break;
                case 'error':
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'error';
                    errorDiv.textContent = data.message;
                    messagesContainer.appendChild(errorDiv);
                    break;
                case 'loading':
                    isLoading = data.loading;
                    loadingIndicator.style.display = data.loading ? 'flex' : 'none';
                    break;
            }
        });
    </script>
</body>
</html>`;
    }
}
