'use client';

/**
 * Assistant Thread Component
 *
 * Displays the conversation thread with messages using assistant-ui primitives
 */

import { useRef, useEffect, useState } from 'react';
import {
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  ActionBarPrimitive,
} from '@assistant-ui/react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import { User, Send, Copy, Check, Sparkles } from 'lucide-react';

// =============================================================================
// MESSAGE CONTENT COMPONENT
// =============================================================================

function MessageContent() {
  return (
    <MessagePrimitive.Content
      components={{
        Text: ({ text }) => (
          <div className="prose prose-sm dark:prose-invert max-w-none [&_p]:leading-relaxed [&_ul]:my-2 [&_li]:my-0.5">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{text}</ReactMarkdown>
          </div>
        ),
      }}
    />
  );
}

// =============================================================================
// MESSAGE COMPONENTS
// =============================================================================

function UserMessage() {
  return (
    <MessagePrimitive.Root className="flex gap-4 px-4 py-6 bg-background">
      {/* User Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary text-primary-foreground">
        <User className="h-4 w-4" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="text-sm font-medium">You</div>
        <MessageContent />
      </div>
    </MessagePrimitive.Root>
  );
}

function AssistantMessage() {
  return (
    <MessagePrimitive.Root className="flex gap-4 px-4 py-6 bg-muted/50">
      {/* Assistant Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground">
        <Sparkles className="h-4 w-4" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2 overflow-hidden">
        <div className="flex items-center gap-2">
          <span className="text-sm font-medium">NexusAI Assistant</span>
          <MessageActions />
        </div>
        <MessageContent />
      </div>
    </MessagePrimitive.Root>
  );
}

function MessageActions() {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    // Copy functionality would be handled by assistant-ui hooks
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <ActionBarPrimitive.Root className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
      <ActionBarPrimitive.Copy asChild onClick={handleCopy}>
        <button
          className="p-1 hover:bg-muted rounded-md transition-colors"
          title="Copy message"
        >
          {copied ? (
            <Check className="h-3.5 w-3.5 text-green-500" />
          ) : (
            <Copy className="h-3.5 w-3.5 text-muted-foreground" />
          )}
        </button>
      </ActionBarPrimitive.Copy>
    </ActionBarPrimitive.Root>
  );
}

// =============================================================================
// LOADING STATE
// =============================================================================

function LoadingMessage() {
  return (
    <div className="flex gap-4 px-4 py-6 bg-muted/50">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-primary to-primary/70 text-primary-foreground">
        <Sparkles className="h-4 w-4" />
      </div>
      <div className="flex items-center gap-2">
        <div className="flex gap-1">
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
          <span className="w-2 h-2 bg-primary/60 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
        </div>
        <span className="text-sm text-muted-foreground">Thinking...</span>
      </div>
    </div>
  );
}

// =============================================================================
// COMPOSER (INPUT)
// =============================================================================

function Composer() {
  return (
    <ComposerPrimitive.Root className="p-4 border-t bg-background">
      <div className="flex gap-2">
        <ComposerPrimitive.Input
          placeholder="Type your message..."
          className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 bg-background resize-none min-h-[44px] max-h-[200px]"
          autoFocus
        />
        <ComposerPrimitive.Send asChild>
          <button
            className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </ComposerPrimitive.Send>
      </div>
    </ComposerPrimitive.Root>
  );
}

// =============================================================================
// EMPTY STATE
// =============================================================================

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center h-full p-8 text-center">
      <div className="h-16 w-16 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center mb-4">
        <Sparkles className="h-8 w-8 text-primary-foreground" />
      </div>
      <h2 className="text-xl font-semibold mb-2">NexusAI Assistant</h2>
      <p className="text-muted-foreground max-w-md">
        I can help you connect data sources, view metrics, and set up your engineering analytics.
        Type a message to get started!
      </p>
    </div>
  );
}

// =============================================================================
// MAIN THREAD COMPONENT
// =============================================================================

interface AssistantThreadProps {
  className?: string;
  showComposer?: boolean;
}

export function AssistantThread({ className, showComposer = true }: AssistantThreadProps) {
  const scrollRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  });

  return (
    <ThreadPrimitive.Root className={cn('flex flex-col h-full', className)}>
      {/* Messages */}
      <ThreadPrimitive.Viewport
        ref={scrollRef}
        className="flex-1 overflow-y-auto"
      >
        <ThreadPrimitive.Empty>
          <EmptyState />
        </ThreadPrimitive.Empty>

        <ThreadPrimitive.Messages
          components={{
            UserMessage,
            AssistantMessage,
          }}
        />

        <ThreadPrimitive.If running>
          <LoadingMessage />
        </ThreadPrimitive.If>
      </ThreadPrimitive.Viewport>

      {/* Composer */}
      {showComposer && <Composer />}
    </ThreadPrimitive.Root>
  );
}
