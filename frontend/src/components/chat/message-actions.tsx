'use client';

import { useState, useCallback } from 'react';
import {
  ThumbsUp,
  ThumbsDown,
  Copy,
  Check,
  RefreshCw,
  MoreHorizontal,
  Flag,
  Share2,
  Bookmark,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface MessageActionsProps {
  messageId: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  onRegenerate?: () => void;
  onFeedback?: (type: 'positive' | 'negative', messageId: string) => void;
  className?: string;
}

/**
 * Action buttons for chat messages.
 * 
 * For AI messages: copy, regenerate, thumbs up/down
 * For user messages: copy, edit (future)
 * 
 * Shows on hover to keep interface clean.
 */
export function MessageActions({
  messageId,
  content,
  role,
  onRegenerate,
  onFeedback,
  className,
}: MessageActionsProps) {
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState<'positive' | 'negative' | null>(null);

  const handleCopy = useCallback(async () => {
    try {
      await navigator.clipboard.writeText(content);
      setCopied(true);
      toast.success('Copied to clipboard');
      setTimeout(() => setCopied(false), 2000);
    } catch (error) {
      toast.error('Failed to copy');
    }
  }, [content]);

  const handleFeedback = useCallback(
    (type: 'positive' | 'negative') => {
      setFeedback(type);
      onFeedback?.(type, messageId);
      toast.success(
        type === 'positive'
          ? 'Thanks for the feedback!'
          : 'Sorry about that. We\'ll improve.'
      );
    },
    [messageId, onFeedback]
  );

  const handleRegenerate = useCallback(() => {
    onRegenerate?.();
    toast.info('Regenerating response...');
  }, [onRegenerate]);

  const isAssistant = role === 'assistant';

  return (
    <div
      className={cn(
        'flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity',
        className
      )}
    >
      {/* Copy button */}
      <Button
        variant="ghost"
        size="icon"
        className="h-7 w-7"
        onClick={handleCopy}
        title="Copy message"
        aria-label="Copy message to clipboard"
      >
        {copied ? (
          <Check className="h-3.5 w-3.5 text-green-500" aria-hidden="true" />
        ) : (
          <Copy className="h-3.5 w-3.5" aria-hidden="true" />
        )}
      </Button>

      {/* Assistant-only actions */}
      {isAssistant && (
        <>
          {/* Regenerate */}
          {onRegenerate && (
            <Button
              variant="ghost"
              size="icon"
              className="h-7 w-7"
              onClick={handleRegenerate}
              title="Regenerate response"
              aria-label="Regenerate AI response"
            >
              <RefreshCw className="h-3.5 w-3.5" aria-hidden="true" />
            </Button>
          )}

          {/* Thumbs up */}
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'h-7 w-7',
              feedback === 'positive' && 'text-green-500 bg-green-50 dark:bg-green-950'
            )}
            onClick={() => handleFeedback('positive')}
            title="Good response"
            aria-label="Mark as good response"
            aria-pressed={feedback === 'positive'}
          >
            <ThumbsUp className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>

          {/* Thumbs down */}
          <Button
            variant="ghost"
            size="icon"
            className={cn(
              'h-7 w-7',
              feedback === 'negative' && 'text-red-500 bg-red-50 dark:bg-red-950'
            )}
            onClick={() => handleFeedback('negative')}
            title="Bad response"
            aria-label="Mark as bad response"
            aria-pressed={feedback === 'negative'}
          >
            <ThumbsDown className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </>
      )}

      {/* More options menu */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            title="More options"
            aria-label="More message options"
          >
            <MoreHorizontal className="h-3.5 w-3.5" aria-hidden="true" />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end">
          <DropdownMenuItem onClick={handleCopy}>
            <Copy className="h-4 w-4 mr-2" aria-hidden="true" />
            Copy message
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Bookmark className="h-4 w-4 mr-2" aria-hidden="true" />
            Save to collection
          </DropdownMenuItem>
          <DropdownMenuItem>
            <Share2 className="h-4 w-4 mr-2" aria-hidden="true" />
            Share
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem className="text-destructive">
            <Flag className="h-4 w-4 mr-2" aria-hidden="true" />
            Report issue
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  );
}

export default MessageActions;
