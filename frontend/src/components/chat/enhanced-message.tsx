'use client';

import { useState } from 'react';
import { User, Bot } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { CodeBlock, InlineCode } from './code-block';
import { MessageActions } from './message-actions';
import { usePreferencesStore } from '@/store/preferences';

interface EnhancedMessageProps {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  isStreaming?: boolean;
  timestamp?: string;
  modelName?: string;
  onRegenerate?: () => void;
  onFeedback?: (type: 'positive' | 'negative', messageId: string) => void;
}

/**
 * Enhanced chat message with actions, code blocks, and accessibility.
 * 
 * Implements conversational AI UI best practices:
 * - Clear visual distinction between user and AI messages
 * - Hover actions for copy, feedback, regenerate
 * - Proper markdown rendering with code highlighting
 * - Accessibility with proper ARIA attributes
 */
export function EnhancedMessage({
  id,
  role,
  content,
  isStreaming,
  timestamp,
  modelName,
  onRegenerate,
  onFeedback,
}: EnhancedMessageProps) {
  const [showActions, setShowActions] = useState(false);
  const isUser = role === 'user';
  const { chatDensity, showCodeLineNumbers, enableAnimations } = usePreferencesStore();

  // Get padding based on density
  const getPadding = () => {
    switch (chatDensity) {
      case 'compact':
        return 'px-3 py-3';
      case 'spacious':
        return 'px-6 py-8';
      default:
        return 'px-4 py-6';
    }
  };

  return (
    <div
      className={cn(
        'group relative flex gap-4',
        getPadding(),
        isUser ? 'bg-background' : 'bg-muted/50',
        enableAnimations && 'transition-colors duration-200'
      )}
      onMouseEnter={() => setShowActions(true)}
      onMouseLeave={() => setShowActions(false)}
      data-role={role}
      data-streaming={isStreaming ? 'true' : undefined}
      data-message-id={id}
      role="article"
      aria-label={`Message from ${isUser ? 'you' : 'assistant'}`}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex shrink-0 items-center justify-center rounded-full',
          chatDensity === 'compact' ? 'h-6 w-6' : 'h-8 w-8',
          isUser ? 'bg-primary text-primary-foreground' : 'bg-secondary'
        )}
        aria-hidden="true"
      >
        {isUser ? (
          <User className={chatDensity === 'compact' ? 'h-3 w-3' : 'h-4 w-4'} />
        ) : (
          <Bot className={chatDensity === 'compact' ? 'h-3 w-3' : 'h-4 w-4'} />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden min-w-0">
        {/* Header */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="text-sm font-medium">
              {isUser ? 'You' : 'Assistant'}
            </span>
            {modelName && !isUser && (
              <span className="text-xs text-muted-foreground">
                {modelName}
              </span>
            )}
          </div>
          
          {/* Actions */}
          {(showActions || isStreaming) && (
            <MessageActions
              messageId={id}
              content={content}
              role={role}
              onRegenerate={!isUser ? onRegenerate : undefined}
              onFeedback={onFeedback}
              className={cn(
                isStreaming && 'opacity-50 pointer-events-none'
              )}
            />
          )}
        </div>

        {/* Message content */}
        <div
          className={cn(
            'prose prose-sm dark:prose-invert max-w-none',
            isStreaming && 'animate-pulse'
          )}
        >
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              code({ className, children, ...props }) {
                const match = /language-(\w+)/.exec(className || '');
                const isCodeBlock = match !== null;
                const language = match?.[1] || 'text';
                const codeContent = String(children).replace(/\n$/, '');

                if (isCodeBlock) {
                  return (
                    <CodeBlock
                      code={codeContent}
                      language={language}
                      showLineNumbers={showCodeLineNumbers}
                      className="my-4"
                    />
                  );
                }

                return <InlineCode {...props}>{children}</InlineCode>;
              },
              // Enhanced table rendering
              table({ children }) {
                return (
                  <div className="my-4 overflow-x-auto rounded-lg border">
                    <table className="w-full">{children}</table>
                  </div>
                );
              },
              // Enhanced link rendering
              a({ href, children }) {
                return (
                  <a
                    href={href}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-primary hover:underline"
                  >
                    {children}
                  </a>
                );
              },
              // Enhanced blockquote
              blockquote({ children }) {
                return (
                  <blockquote className="border-l-4 border-primary/30 pl-4 italic text-muted-foreground">
                    {children}
                  </blockquote>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
        </div>

        {/* Timestamp */}
        {timestamp && !isStreaming && (
          <time
            dateTime={timestamp}
            className="text-xs text-muted-foreground"
          >
            {formatTime(timestamp)}
          </time>
        )}

        {/* Streaming cursor */}
        {isStreaming && (
          <span
            className="inline-block w-2 h-4 bg-primary animate-pulse"
            aria-label="AI is typing"
          />
        )}
      </div>
    </div>
  );
}

/**
 * Format timestamp for display
 */
function formatTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const isToday = date.toDateString() === now.toDateString();

  if (isToday) {
    return date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
  }

  return date.toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

export default EnhancedMessage;
