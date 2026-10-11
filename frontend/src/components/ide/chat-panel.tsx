'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  X,
  Minimize2,
  Maximize2,
  Settings,
  RefreshCw,
  Code2,
  FileText,
  Copy,
  Check,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  codeContext?: {
    filename?: string;
    language?: string;
    selection?: string;
  };
}

interface IDEChatPanelProps {
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  streamingContent?: string;
  onSendMessage: (message: string, context?: { code?: string; filename?: string }) => void;
  onClose?: () => void;
  onMinimize?: () => void;
  codeContext?: {
    filename?: string;
    language?: string;
    selection?: string;
  };
  theme?: 'light' | 'dark' | 'inherit';
  className?: string;
}

/**
 * Minimal chat panel designed for IDE integration (VS Code, JetBrains).
 * 
 * Features:
 * - Compact, slim design that fits in IDE sidebar
 * - Theme inheritance from IDE
 * - Code context support
 * - Keyboard shortcuts
 */
export function IDEChatPanel({
  messages,
  isLoading,
  isStreaming,
  streamingContent,
  onSendMessage,
  onClose,
  onMinimize,
  codeContext,
  theme = 'inherit',
  className,
}: IDEChatPanelProps) {
  const [inputValue, setInputValue] = useState('');
  const [isExpanded, setIsExpanded] = useState(true);
  const [includeContext, setIncludeContext] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Focus input on mount
  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !isLoading) {
      const context = includeContext && codeContext?.selection
        ? { code: codeContext.selection, filename: codeContext.filename }
        : undefined;
      onSendMessage(trimmed, context);
      setInputValue('');
    }
  }, [inputValue, isLoading, includeContext, codeContext, onSendMessage]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
    // Escape to clear or close
    if (e.key === 'Escape') {
      if (inputValue) {
        setInputValue('');
      } else {
        onMinimize?.();
      }
    }
  }, [handleSend, inputValue, onMinimize]);

  return (
    <div
      className={cn(
        'flex flex-col h-full bg-background text-foreground border-l',
        theme === 'dark' && 'dark',
        className
      )}
      data-ide-panel
    >
      {/* Header */}
      <header className="flex items-center justify-between px-3 py-2 border-b bg-muted/30">
        <div className="flex items-center gap-2">
          <Code2 className="h-4 w-4 text-primary" />
          <span className="text-sm font-medium">GSTIndia</span>
        </div>
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={() => setIsExpanded(!isExpanded)}
            aria-label={isExpanded ? 'Minimize' : 'Expand'}
          >
            {isExpanded ? (
              <Minimize2 className="h-3.5 w-3.5" aria-hidden="true" />
            ) : (
              <Maximize2 className="h-3.5 w-3.5" aria-hidden="true" />
            )}
          </Button>
          {onClose && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6"
              onClick={onClose}
              aria-label="Close"
            >
              <X className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          )}
        </div>
      </header>

      {isExpanded && (
        <>
          {/* Code Context Banner */}
          {codeContext?.selection && (
            <div className="px-3 py-2 bg-muted/50 border-b">
              <div className="flex items-center justify-between text-xs">
                <div className="flex items-center gap-2">
                  <FileText className="h-3.5 w-3.5 text-muted-foreground" />
                  <span className="text-muted-foreground">
                    {codeContext.filename || 'Selection'}
                  </span>
                  <span className="text-muted-foreground">
                    ({codeContext.selection.split('\n').length} lines)
                  </span>
                </div>
                <label className="flex items-center gap-1.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={includeContext}
                    onChange={(e) => setIncludeContext(e.target.checked)}
                    className="h-3 w-3 rounded"
                  />
                  <span className="text-muted-foreground">Include</span>
                </label>
              </div>
            </div>
          )}

          {/* Messages */}
          <div className="flex-1 overflow-y-auto">
            {messages.length === 0 ? (
              <div className="p-4 text-center">
                <p className="text-sm text-muted-foreground">
                  Ask me anything about your code
                </p>
                <div className="mt-3 space-y-1">
                  {IDE_QUICK_PROMPTS.map((prompt) => (
                    <button
                      key={prompt.id}
                      onClick={() => onSendMessage(prompt.text)}
                      className="block w-full text-left px-3 py-1.5 text-xs rounded hover:bg-muted transition-colors"
                    >
                      {prompt.text}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="divide-y">
                {messages.map((msg) => (
                  <IDEMessage key={msg.id} message={msg} />
                ))}
                {isStreaming && streamingContent && (
                  <IDEMessage
                    message={{
                      id: 'streaming',
                      role: 'assistant',
                      content: streamingContent,
                    }}
                    isStreaming
                  />
                )}
                {isLoading && !streamingContent && (
                  <div className="px-3 py-2">
                    <div className="flex items-center gap-2 text-xs text-muted-foreground">
                      <RefreshCw className="h-3 w-3 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>
            )}
          </div>

          {/* Input */}
          <div className="p-2 border-t bg-background">
            <div className="flex items-end gap-1">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about code..."
                disabled={isLoading}
                rows={1}
                className="flex-1 bg-muted/50 rounded px-2 py-1.5 text-sm resize-none outline-none focus:ring-1 focus:ring-primary min-h-[32px] max-h-[100px]"
              />
              <Button
                size="icon"
                variant="ghost"
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                className="h-8 w-8 shrink-0"
                aria-label="Send message"
              >
                <Send className="h-3.5 w-3.5" aria-hidden="true" />
              </Button>
            </div>
            <div className="flex items-center justify-between mt-1 text-[10px] text-muted-foreground">
              <span>Enter to send · Shift+Enter for newline</span>
              <span>Esc to clear</span>
            </div>
          </div>
        </>
      )}

      {/* Minimized state */}
      {!isExpanded && (
        <button
          onClick={() => setIsExpanded(true)}
          className="flex-1 flex items-center justify-center hover:bg-muted/50 transition-colors"
        >
          <span className="text-xs text-muted-foreground">Click to expand</span>
        </button>
      )}
    </div>
  );
}

/**
 * Individual message in IDE chat
 */
function IDEMessage({
  message,
  isStreaming,
}: {
  message: Message;
  isStreaming?: boolean;
}) {
  const [copied, setCopied] = useState(false);
  const isUser = message.role === 'user';

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  return (
    <div
      className={cn(
        'px-3 py-2 text-sm group',
        isUser ? 'bg-muted/30' : 'bg-background'
      )}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0">
          <span
            className={cn(
              'text-[10px] font-medium uppercase tracking-wide',
              isUser ? 'text-primary' : 'text-muted-foreground'
            )}
          >
            {isUser ? 'You' : 'AI'}
          </span>
          <div
            className={cn(
              'mt-1 prose prose-sm dark:prose-invert max-w-none',
              'prose-pre:bg-muted prose-pre:text-xs prose-pre:p-2 prose-pre:rounded',
              'prose-code:text-xs prose-code:bg-muted prose-code:px-1 prose-code:rounded',
              isStreaming && 'animate-pulse'
            )}
          >
            <IDEMarkdown content={message.content} />
          </div>
        </div>
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity shrink-0"
          onClick={handleCopy}
          aria-label={copied ? 'Copied' : 'Copy message'}
        >
          {copied ? (
            <Check className="h-3 w-3 text-green-500" aria-hidden="true" />
          ) : (
            <Copy className="h-3 w-3" aria-hidden="true" />
          )}
        </Button>
      </div>
    </div>
  );
}

/**
 * Simple markdown renderer for IDE (minimal styling)
 */
function IDEMarkdown({ content }: { content: string }) {
  // Simple markdown parsing for IDE context
  const lines = content.split('\n');
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeContent = '';
  let codeLanguage = '';

  lines.forEach((line, index) => {
    if (line.startsWith('```')) {
      if (inCodeBlock) {
        // End code block
        elements.push(
          <pre key={`code-${index}`} className="bg-muted p-2 rounded text-xs overflow-x-auto">
            <code>{codeContent.trim()}</code>
          </pre>
        );
        codeContent = '';
        inCodeBlock = false;
      } else {
        // Start code block
        codeLanguage = line.slice(3);
        inCodeBlock = true;
      }
    } else if (inCodeBlock) {
      codeContent += line + '\n';
    } else if (line.startsWith('# ')) {
      elements.push(<h3 key={index} className="font-semibold mt-2">{line.slice(2)}</h3>);
    } else if (line.startsWith('## ')) {
      elements.push(<h4 key={index} className="font-medium mt-2">{line.slice(3)}</h4>);
    } else if (line.startsWith('- ') || line.startsWith('* ')) {
      elements.push(<li key={index} className="ml-4">{line.slice(2)}</li>);
    } else if (line.trim()) {
      // Handle inline code
      const parts = line.split(/(`[^`]+`)/g);
      elements.push(
        <p key={index}>
          {parts.map((part, i) =>
            part.startsWith('`') && part.endsWith('`') ? (
              <code key={i} className="bg-muted px-1 rounded text-xs">
                {part.slice(1, -1)}
              </code>
            ) : (
              part
            )
          )}
        </p>
      );
    }
  });

  return <>{elements}</>;
}

/**
 * Quick prompts for IDE context
 */
const IDE_QUICK_PROMPTS = [
  { id: '1', text: 'Explain this code' },
  { id: '2', text: 'Find bugs in selection' },
  { id: '3', text: 'Suggest improvements' },
  { id: '4', text: 'Write unit tests' },
  { id: '5', text: 'Add documentation' },
];

export default IDEChatPanel;
