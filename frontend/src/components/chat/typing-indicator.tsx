'use client';

import { Bot, Loader2 } from 'lucide-react';
import { cn } from '@/lib/utils';

interface TypingIndicatorProps {
  variant?: 'dots' | 'text' | 'pulse';
  message?: string;
  className?: string;
}

/**
 * Typing indicator shown while AI is generating a response.
 * 
 * Provides visual feedback that the AI is "thinking" - crucial for
 * conversational UI to maintain user engagement and set expectations.
 */
export function TypingIndicator({
  variant = 'dots',
  message = 'AI is thinking',
  className,
}: TypingIndicatorProps) {
  return (
    <div
      className={cn(
        'flex gap-4 px-4 py-6 bg-muted/50',
        className
      )}
      role="status"
      aria-label={message}
      aria-live="polite"
    >
      {/* Avatar */}
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
        <Bot className="h-4 w-4" aria-hidden="true" />
      </div>

      {/* Content */}
      <div className="flex-1 space-y-2">
        <div className="text-sm font-medium">Assistant</div>
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          {variant === 'dots' && <DotsAnimation />}
          {variant === 'text' && <TextAnimation message={message} />}
          {variant === 'pulse' && <PulseAnimation message={message} />}
        </div>
      </div>
    </div>
  );
}

/**
 * Animated dots (classic typing indicator)
 */
function DotsAnimation() {
  return (
    <div className="flex items-center gap-1" aria-hidden="true">
      <span className="sr-only">AI is typing</span>
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="h-2 w-2 rounded-full bg-primary/60 animate-bounce"
          style={{
            animationDelay: `${i * 0.15}s`,
            animationDuration: '0.6s',
          }}
        />
      ))}
    </div>
  );
}

/**
 * Text-based indicator with spinner
 */
function TextAnimation({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2">
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{message}...</span>
    </div>
  );
}

/**
 * Pulse animation for a more subtle indicator
 */
function PulseAnimation({ message }: { message: string }) {
  return (
    <div className="flex items-center gap-2">
      <span className="relative flex h-3 w-3">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-primary opacity-75" />
        <span className="relative inline-flex rounded-full h-3 w-3 bg-primary" />
      </span>
      <span>{message}...</span>
    </div>
  );
}

/**
 * Skeleton loader for message content (used during initial load)
 */
export function MessageSkeleton({ lines = 3 }: { lines?: number }) {
  return (
    <div className="flex gap-4 px-4 py-6 bg-muted/50">
      {/* Avatar skeleton */}
      <div className="h-8 w-8 shrink-0 rounded-full bg-muted animate-pulse" />

      {/* Content skeleton */}
      <div className="flex-1 space-y-3">
        <div className="h-4 w-20 rounded bg-muted animate-pulse" />
        <div className="space-y-2">
          {Array.from({ length: lines }).map((_, i) => (
            <div
              key={i}
              className="h-4 rounded bg-muted animate-pulse"
              style={{ width: `${Math.max(40, Math.random() * 100)}%` }}
            />
          ))}
        </div>
      </div>
    </div>
  );
}

export default TypingIndicator;
