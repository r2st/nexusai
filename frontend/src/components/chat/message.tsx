'use client';

import { memo, useMemo } from 'react';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { WidgetRenderer, parseWidgetBlocks, type WidgetPayload } from '@/components/chat/widgets';
import { ToolRenderer, parseToolBlocks, type ToolPayload } from '@/components/chat/tools';

interface MessageProps {
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  widgets?: WidgetPayload[];
  tools?: ToolPayload[];
}

export const ChatMessage = memo(function ChatMessage({
  role,
  content,
  isStreaming,
  widgets = [],
  tools = [],
}: MessageProps) {
  const isUser = role === 'user';
  const { content: widgetCleaned, widgets: parsedWidgets } = useMemo(
    () => parseWidgetBlocks(content),
    [content]
  );
  const { content: cleanedContent, tools: parsedTools } = useMemo(
    () => parseToolBlocks(widgetCleaned),
    [widgetCleaned]
  );
  const allWidgets = widgets.length ? [...widgets, ...parsedWidgets] : parsedWidgets;
  const allTools = tools.length ? tools : parsedTools;

  return (
    <div
      className={cn(
        'flex gap-4 px-4 py-6',
        isUser ? 'bg-background' : 'bg-muted/50'
      )}
      data-role={role}
      data-streaming={isStreaming ? 'true' : undefined}
      role="article"
      aria-label={`Message from ${isUser ? 'you' : 'assistant'}`}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary'
        )}
      >
        {isUser ? <User className="h-4 w-4" aria-hidden="true" /> : <Bot className="h-4 w-4" aria-hidden="true" />}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="text-sm font-medium">
          {isUser ? 'You' : 'Assistant'}
        </div>
        {allWidgets.length > 0 && (
          <div className="space-y-3">
            {allWidgets.map((widget, index) => (
              <WidgetRenderer key={`${widget.type}-${index}`} widget={widget} />
            ))}
          </div>
        )}
        {allTools.length > 0 && (
          <div className="space-y-3">
            {allTools.map((tool, index) => (
              <ToolRenderer key={`${tool.type}-${index}`} tool={tool} />
            ))}
          </div>
        )}
        <div className={cn('prose prose-sm dark:prose-invert max-w-none', isStreaming && 'cursor-blink')}>
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const isInline = !match;

                if (isInline) {
                  return (
                    <code className={className} {...props}>
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
            {cleanedContent}
          </ReactMarkdown>
        </div>
      </div>
    </div>
  );
});
