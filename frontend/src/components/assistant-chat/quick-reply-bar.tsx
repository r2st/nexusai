'use client';

/**
 * Quick Reply Bar Component
 *
 * Displays quick reply options from the assistant for easy selection
 */

import { useNexusRuntimeState } from '@/lib/assistant-runtime';
import { useComposerRuntime } from '@assistant-ui/react';
import { ChevronRight } from 'lucide-react';
import { cn } from '@/lib/utils';

interface QuickReplyBarProps {
  className?: string;
  onSelect?: (value: string) => void;
}

export function QuickReplyBar({ className, onSelect }: QuickReplyBarProps) {
  const { quickReplies } = useNexusRuntimeState();
  const composerRuntime = useComposerRuntime();

  if (quickReplies.length === 0) {
    return null;
  }

  const handleClick = (value: string) => {
    // Set the value in the composer and send
    composerRuntime.setText(value);
    composerRuntime.send();
    onSelect?.(value);
  };

  return (
    <div className={cn('flex flex-wrap gap-2 px-4 py-3 border-t bg-muted/30', className)}>
      {quickReplies.map((reply) => (
        <button
          key={reply.id || reply.value}
          onClick={() => handleClick(reply.value)}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-full hover:bg-muted transition-colors"
        >
          {reply.icon && <span>{reply.icon}</span>}
          <span>{reply.label}</span>
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        </button>
      ))}
    </div>
  );
}

/**
 * Standalone quick reply buttons (not connected to composer)
 */
interface QuickReplyButtonsProps {
  replies: Array<{
    id?: string;
    label: string;
    value: string;
    icon?: string;
    description?: string;
  }>;
  onSelect: (value: string) => void;
  disabled?: boolean;
  className?: string;
}

export function QuickReplyButtons({
  replies,
  onSelect,
  disabled = false,
  className,
}: QuickReplyButtonsProps) {
  if (replies.length === 0) {
    return null;
  }

  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {replies.map((reply) => (
        <button
          key={reply.id || reply.value}
          onClick={() => onSelect(reply.value)}
          disabled={disabled}
          className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-full hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          title={reply.description}
        >
          {reply.icon && <span>{reply.icon}</span>}
          <span>{reply.label}</span>
          <ChevronRight className="h-3 w-3 text-muted-foreground" />
        </button>
      ))}
    </div>
  );
}
