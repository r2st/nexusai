'use client';

import { cn } from '@/lib/utils';
import {
  Send,
  StopCircle,
  Copy,
  Check,
  User,
  Bot,
  Sparkles,
  ArrowDown,
  Loader2,
  Wrench,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useCallback, useEffect, useRef, useState, memo, useMemo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import type { Message } from '@/hooks/use-websocket-chat';
import { WidgetRenderer, parseWidgetBlocks } from '@/components/chat/widgets';

// ============================================================================
// Types
// ============================================================================

interface ChatUIProps {
  messages: Message[];
  isStreaming?: boolean;
  streamingContent?: string;
  streamingToolCalls?: Message['tool_calls'];
  streamingToolResults?: Message['tool_results'];
  isConnected?: boolean;
  isConnecting?: boolean;
  isLoading?: boolean;
  toolsEnabled?: boolean;
  onSend: (message: string) => void;
  onToggleTools?: (enabled: boolean) => void;
  className?: string;
}

// ============================================================================
// Main Component
// ============================================================================

export function ChatUI({
  messages,
  isStreaming = false,
  streamingContent = '',
  streamingToolCalls = [],
  streamingToolResults = [],
  isConnected = false,
  isConnecting = false,
  isLoading = false,
  toolsEnabled = true,
  onSend,
  onToggleTools,
  className,
}: ChatUIProps) {
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const scrollContainerRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);
  const [autoScroll, setAutoScroll] = useState(true);
  const prevMessagesLengthRef = useRef(messages.length);

  // Re-enable auto-scroll when new messages are added (user sent a message)
  useEffect(() => {
    if (messages.length > prevMessagesLengthRef.current) {
      // New message was added, re-enable auto-scroll
      setAutoScroll(true);
    }
    prevMessagesLengthRef.current = messages.length;
  }, [messages.length]);

  // Auto-scroll to bottom when new messages arrive or streaming content updates
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingContent, autoScroll]);

  // Track scroll position to show/hide scroll button
  const handleScroll = useCallback(() => {
    if (!scrollContainerRef.current) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollContainerRef.current;
    const isNearBottom = scrollHeight - scrollTop - clientHeight < 100;

    setShowScrollButton(!isNearBottom);
    setAutoScroll(isNearBottom);
  }, []);

  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    setAutoScroll(true);
  }, []);

  const hasMessages = messages.length > 0 || isStreaming;

  return (
    <div className={cn('flex h-full flex-col', className)}>
      {/* Connection Status Bar */}
      <div className="flex h-10 items-center justify-end border-b px-4 bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <ConnectionStatus isConnected={isConnected} isConnecting={isConnecting} />
      </div>

      {/* Messages Area */}
      <div
        ref={scrollContainerRef}
        className="flex-1 overflow-y-auto"
        onScroll={handleScroll}
      >
        <div className="mx-auto max-w-3xl px-4 py-4">
          {!hasMessages ? (
            <WelcomeScreen />
          ) : (
            <div className="space-y-4">
              {messages.map((msg) => (
                <MessageBubble key={msg.id} message={msg} />
              ))}
              {/* Only show streaming message if content is not already in messages list
                  This prevents duplicates during the race condition when message_complete
                  triggers query invalidation while streaming state is still clearing */}
              {isStreaming && !messages.some(
                (m) => m.role === 'assistant' && m.content === streamingContent
              ) && (
                <MessageBubble
                  message={{
                    id: 'streaming',
                    role: 'assistant',
                    content: streamingContent,
                    created_at: new Date().toISOString(),
                    tool_calls: streamingToolCalls,
                    tool_results: streamingToolResults,
                  }}
                  isStreaming
                />
              )}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>
      </div>

      {/* Scroll to Bottom Button */}
      {showScrollButton && (
        <Button
          variant="outline"
          size="icon"
          className="absolute bottom-24 right-8 z-10 rounded-full shadow-md"
          onClick={scrollToBottom}
          aria-label="Scroll to bottom"
        >
          <ArrowDown className="h-4 w-4" aria-hidden="true" />
        </Button>
      )}

      {/* Composer */}
      <div className="border-t bg-background p-4">
        <div className="mx-auto max-w-3xl">
          <ChatComposer
            onSend={onSend}
            isLoading={isLoading || isStreaming}
            isDisabled={!isConnected}
            toolsEnabled={toolsEnabled}
            onToggleTools={onToggleTools}
          />
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Sub-Components
// ============================================================================

function ConnectionStatus({
  isConnected,
  isConnecting
}: {
  isConnected: boolean;
  isConnecting: boolean;
}) {
  return (
    <div className="flex items-center gap-2">
      <div
        className={cn(
          'h-2 w-2 rounded-full transition-colors',
          isConnected ? 'bg-green-500' : isConnecting ? 'bg-yellow-500 animate-pulse' : 'bg-red-500'
        )}
      />
      <span className="text-xs text-muted-foreground">
        {isConnected ? 'Connected' : isConnecting ? 'Connecting...' : 'Disconnected'}
      </span>
    </div>
  );
}

function WelcomeScreen() {
  return (
    <div className="flex h-full min-h-[400px] flex-col items-center justify-center text-center">
      <div className="mb-6 flex h-16 w-16 items-center justify-center rounded-full bg-gradient-to-br from-primary/20 to-primary/10">
        <Sparkles className="h-8 w-8 text-primary" />
      </div>
      <h1 className="text-2xl font-semibold tracking-tight">
        Welcome to GSTIndia
      </h1>
      <p className="mt-2 max-w-md text-muted-foreground">
        Your AI-powered assistant for DevOps, analytics, and more.
        Start a conversation to explore DORA metrics, CI/CD insights, and code analysis.
      </p>
      <div className="mt-8 grid grid-cols-1 gap-3 sm:grid-cols-2">
        <SuggestionCard
          icon="📊"
          title="DORA Metrics"
          description="Analyze deployment frequency, lead time, MTTR, and change failure rate"
        />
        <SuggestionCard
          icon="🔍"
          title="Code Search"
          description="Search and explore your codebase semantically"
        />
        <SuggestionCard
          icon="🔧"
          title="CI/CD Analysis"
          description="Identify flaky tests and build failures"
        />
        <SuggestionCard
          icon="📈"
          title="Insights"
          description="Get actionable recommendations for your team"
        />
      </div>
    </div>
  );
}

function SuggestionCard({
  icon,
  title,
  description
}: {
  icon: string;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-4 text-left transition-colors hover:bg-accent cursor-pointer">
      <div className="flex items-start gap-3">
        <span className="text-2xl">{icon}</span>
        <div>
          <h3 className="font-medium">{title}</h3>
          <p className="text-sm text-muted-foreground">{description}</p>
        </div>
      </div>
    </div>
  );
}

const MessageBubble = memo(function MessageBubble({
  message,
  isStreaming = false,
}: {
  message: Message;
  isStreaming?: boolean;
}) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);

  // Parse widgets from message content
  const { content: cleanedContent, widgets } = useMemo(
    () => parseWidgetBlocks(message.content || ''),
    [message.content]
  );

  const handleCopy = useCallback(async () => {
    await navigator.clipboard.writeText(message.content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  }, [message.content]);

  return (
    <div
      className={cn(
        'group relative flex gap-4 py-4',
        isUser ? 'bg-background' : 'bg-muted/30 -mx-4 px-4 rounded-lg'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary'
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center justify-between">
          <div className="font-medium text-sm">{isUser ? 'You' : 'Assistant'}</div>
          {!isUser && !isStreaming && (
            <Button
              variant="ghost"
              size="icon"
              className="h-6 w-6 opacity-0 group-hover:opacity-100 focus:opacity-100 transition-opacity"
              onClick={handleCopy}
              aria-label={copied ? 'Copied' : 'Copy message'}
            >
              {copied ? (
                <Check className="h-3 w-3 text-green-500" aria-hidden="true" />
              ) : (
                <Copy className="h-3 w-3" aria-hidden="true" />
              )}
            </Button>
          )}
        </div>

        {/* Tool Calls */}
        {message.tool_calls && message.tool_calls.length > 0 && (
          <div className="space-y-2">
            {message.tool_calls.map((tool, idx) => (
              <ToolCallDisplay
                key={tool.id || idx}
                toolName={tool.name}
                args={tool.args}
                status={tool.status}
              />
            ))}
          </div>
        )}

        {/* Tool Results */}
        {message.tool_results && message.tool_results.length > 0 && (
          <div className="space-y-2">
            {message.tool_results.map((result, idx) => (
              <ToolResultDisplay
                key={result.id || idx}
                name={result.name}
                output={result.output}
                success={result.success}
              />
            ))}
          </div>
        )}

        {/* Widgets parsed from message content */}
        {widgets.length > 0 && (
          <div className="space-y-3">
            {widgets.map((widget, index) => (
              <WidgetRenderer key={`${widget.type}-${index}`} widget={widget} />
            ))}
          </div>
        )}

        {/* Message Content */}
        <div className={cn('prose prose-sm dark:prose-invert max-w-none', isStreaming && 'animate-pulse')}>
          {isUser ? (
            <p className="whitespace-pre-wrap">{message.content}</p>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const isInline = !match;

                  if (isInline) {
                    return (
                      <code className={cn('bg-muted px-1 py-0.5 rounded', className)} {...props}>
                        {children}
                      </code>
                    );
                  }

                  return (
                    <pre className="overflow-x-auto rounded-lg bg-muted p-4">
                      <code className={className} {...props}>
                        {children}
                      </code>
                    </pre>
                  );
                },
              }}
            >
              {cleanedContent || ''}
            </ReactMarkdown>
          )}
        </div>

        {/* Typing Indicator */}
        {isStreaming && !message.content && (
          <TypingIndicator />
        )}
      </div>
    </div>
  );
});

function ToolCallDisplay({
  toolName,
  args,
  status,
}: {
  toolName: string;
  args?: Record<string, unknown>;
  status?: string;
}) {
  const isRunning = status === 'running' || status === 'queued';

  return (
    <div className="rounded-md border bg-muted/50 p-3">
      <div className="flex items-center gap-2 text-sm">
        {isRunning ? (
          <Loader2 className="h-4 w-4 animate-spin text-yellow-500" />
        ) : (
          <Wrench className="h-4 w-4 text-blue-500" />
        )}
        <span className="font-medium">
          {isRunning ? 'Calling' : 'Called'}: {toolName}
        </span>
      </div>
      {args && Object.keys(args).length > 0 && (
        <pre className="mt-2 text-xs text-muted-foreground overflow-x-auto">
          {JSON.stringify(args, null, 2)}
        </pre>
      )}
    </div>
  );
}

function ToolResultDisplay({
  name,
  output,
  success,
}: {
  name?: string;
  output?: string;
  success?: boolean;
}) {
  // Parse widgets from output
  const { content: cleanedOutput, widgets } = useMemo(
    () => parseWidgetBlocks(output || ''),
    [output]
  );

  return (
    <div
      className={cn(
        'rounded-md border p-3',
        success === false ? 'border-red-500/50 bg-red-500/10' : 'bg-green-500/10 border-green-500/50'
      )}
    >
      <div className="flex items-center gap-2 text-sm">
        <Check className={cn('h-4 w-4', success === false ? 'text-red-500' : 'text-green-500')} />
        <span className="font-medium">
          {name ? `Result from ${name}` : 'Tool result'}
        </span>
      </div>
      {/* Render widgets if present */}
      {widgets.length > 0 && (
        <div className="mt-3 space-y-3">
          {widgets.map((widget, index) => (
            <WidgetRenderer key={`${widget.type}-${index}`} widget={widget} />
          ))}
        </div>
      )}
      {/* Show remaining text output */}
      {cleanedOutput && (
        <pre className="mt-2 text-xs text-muted-foreground overflow-x-auto whitespace-pre-wrap">
          {cleanedOutput.length > 500 ? `${cleanedOutput.slice(0, 500)}...` : cleanedOutput}
        </pre>
      )}
    </div>
  );
}

function TypingIndicator() {
  return (
    <div className="flex items-center gap-1 text-muted-foreground">
      <div className="flex gap-1">
        <span className="h-2 w-2 rounded-full bg-current animate-bounce" style={{ animationDelay: '0ms' }} />
        <span className="h-2 w-2 rounded-full bg-current animate-bounce" style={{ animationDelay: '150ms' }} />
        <span className="h-2 w-2 rounded-full bg-current animate-bounce" style={{ animationDelay: '300ms' }} />
      </div>
      <span className="text-xs ml-2">Thinking...</span>
    </div>
  );
}

// ============================================================================
// Composer
// ============================================================================

interface ChatComposerProps {
  onSend: (message: string) => void;
  isLoading?: boolean;
  isDisabled?: boolean;
  toolsEnabled?: boolean;
  onToggleTools?: (enabled: boolean) => void;
}

const ChatComposer = memo(function ChatComposer({
  onSend,
  isLoading = false,
  isDisabled = false,
  toolsEnabled = true,
  onToggleTools,
}: ChatComposerProps) {
  const [value, setValue] = useState('');
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      const newHeight = Math.min(textarea.scrollHeight, 200);
      textarea.style.height = `${newHeight}px`;
    }
  }, [value]);

  const handleSubmit = useCallback(() => {
    const trimmed = value.trim();
    if (trimmed && !isLoading && !isDisabled) {
      onSend(trimmed);
      setValue('');
    }
  }, [value, isLoading, isDisabled, onSend]);

  const handleKeyDown = useCallback((e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  }, [handleSubmit]);

  return (
    <div className="flex flex-col gap-2">
      <div
        className={cn(
          'flex items-end gap-2 rounded-lg border bg-background p-2 shadow-sm transition-shadow',
          'focus-within:ring-2 focus-within:ring-ring focus-within:ring-offset-1',
          isDisabled && 'opacity-50'
        )}
      >
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={isDisabled ? 'Connecting...' : 'Send a message... (Enter to send, Shift+Enter for new line)'}
          disabled={isDisabled}
          rows={1}
          className={cn(
            'flex-1 resize-none bg-transparent py-2 px-2 text-sm outline-none',
            'placeholder:text-muted-foreground',
            'disabled:cursor-not-allowed disabled:opacity-50',
            'min-h-[40px] max-h-[200px]'
          )}
        />
        <Button
          size="icon"
          onClick={handleSubmit}
          disabled={!value.trim() || isLoading || isDisabled}
          className="h-9 w-9 shrink-0"
          aria-label={isLoading ? 'Sending' : 'Send message'}
        >
          {isLoading ? (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          ) : (
            <Send className="h-4 w-4" aria-hidden="true" />
          )}
        </Button>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between text-xs text-muted-foreground px-1">
        <div className="flex items-center gap-2">
          <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Enter</kbd>
          <span>send</span>
          <span className="text-muted-foreground/50">·</span>
          <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">Shift+Enter</kbd>
          <span>new line</span>
        </div>
        {onToggleTools && (
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              className="h-3 w-3 rounded border-muted-foreground"
              checked={toolsEnabled}
              onChange={(e) => onToggleTools(e.target.checked)}
            />
            <span>Tools {toolsEnabled ? 'on' : 'off'}</span>
          </label>
        )}
      </div>
    </div>
  );
});

export default ChatUI;
