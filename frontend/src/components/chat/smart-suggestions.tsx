'use client';

import { useMemo } from 'react';
import { Lightbulb, ArrowRight, Sparkles } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface Suggestion {
  id: string;
  text: string;
  category?: 'follow-up' | 'clarify' | 'explore' | 'action';
}

interface SmartSuggestionsProps {
  suggestions: Suggestion[];
  onSelect: (suggestion: Suggestion) => void;
  isLoading?: boolean;
  variant?: 'chips' | 'list' | 'cards';
  title?: string;
  maxVisible?: number;
  className?: string;
}

/**
 * Smart suggestions shown after AI responses.
 * 
 * Provides context-aware follow-up questions and actions
 * to help users continue the conversation naturally.
 */
export function SmartSuggestions({
  suggestions,
  onSelect,
  isLoading,
  variant = 'chips',
  title = 'Suggested follow-ups',
  maxVisible = 4,
  className,
}: SmartSuggestionsProps) {
  const visibleSuggestions = useMemo(
    () => suggestions.slice(0, maxVisible),
    [suggestions, maxVisible]
  );

  if (suggestions.length === 0 && !isLoading) {
    return null;
  }

  return (
    <div className={cn('space-y-2', className)}>
      {/* Header */}
      {title && (
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Lightbulb className="h-3 w-3" aria-hidden="true" />
          <span>{title}</span>
        </div>
      )}

      {/* Suggestions */}
      {isLoading ? (
        <SuggestionsSkeleton count={3} variant={variant} />
      ) : (
        <>
          {variant === 'chips' && (
            <ChipsSuggestions
              suggestions={visibleSuggestions}
              onSelect={onSelect}
            />
          )}
          {variant === 'list' && (
            <ListSuggestions
              suggestions={visibleSuggestions}
              onSelect={onSelect}
            />
          )}
          {variant === 'cards' && (
            <CardsSuggestions
              suggestions={visibleSuggestions}
              onSelect={onSelect}
            />
          )}
        </>
      )}
    </div>
  );
}

/**
 * Chip-style suggestions (compact)
 */
function ChipsSuggestions({
  suggestions,
  onSelect,
}: {
  suggestions: Suggestion[];
  onSelect: (s: Suggestion) => void;
}) {
  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion) => (
        <Button
          key={suggestion.id}
          variant="outline"
          size="sm"
          className="h-auto py-1.5 px-3 text-sm whitespace-normal text-left"
          onClick={() => onSelect(suggestion)}
        >
          {suggestion.text}
        </Button>
      ))}
    </div>
  );
}

/**
 * List-style suggestions (more readable)
 */
function ListSuggestions({
  suggestions,
  onSelect,
}: {
  suggestions: Suggestion[];
  onSelect: (s: Suggestion) => void;
}) {
  return (
    <ul className="space-y-1">
      {suggestions.map((suggestion) => (
        <li key={suggestion.id}>
          <button
            className="flex items-center gap-2 w-full p-2 rounded-md text-sm text-left hover:bg-muted transition-colors group"
            onClick={() => onSelect(suggestion)}
          >
            <ArrowRight
              className="h-4 w-4 text-muted-foreground group-hover:text-primary shrink-0"
              aria-hidden="true"
            />
            <span>{suggestion.text}</span>
          </button>
        </li>
      ))}
    </ul>
  );
}

/**
 * Card-style suggestions (prominent)
 */
function CardsSuggestions({
  suggestions,
  onSelect,
}: {
  suggestions: Suggestion[];
  onSelect: (s: Suggestion) => void;
}) {
  const getCategoryIcon = (category?: string) => {
    switch (category) {
      case 'follow-up':
        return '💬';
      case 'clarify':
        return '❓';
      case 'explore':
        return '🔍';
      case 'action':
        return '⚡';
      default:
        return '💡';
    }
  };

  return (
    <div className="grid grid-cols-2 gap-2">
      {suggestions.map((suggestion) => (
        <button
          key={suggestion.id}
          className="flex items-start gap-2 p-3 rounded-lg border bg-card text-sm text-left hover:bg-muted hover:border-primary/50 transition-colors"
          onClick={() => onSelect(suggestion)}
        >
          <span className="text-lg" aria-hidden="true">
            {getCategoryIcon(suggestion.category)}
          </span>
          <span className="line-clamp-2">{suggestion.text}</span>
        </button>
      ))}
    </div>
  );
}

/**
 * Loading skeleton for suggestions
 */
function SuggestionsSkeleton({
  count,
  variant,
}: {
  count: number;
  variant: 'chips' | 'list' | 'cards';
}) {
  if (variant === 'chips') {
    return (
      <div className="flex flex-wrap gap-2">
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="h-8 rounded-full bg-muted animate-pulse"
            style={{ width: `${80 + Math.random() * 60}px` }}
          />
        ))}
      </div>
    );
  }

  if (variant === 'list') {
    return (
      <div className="space-y-1">
        {Array.from({ length: count }).map((_, i) => (
          <div
            key={i}
            className="h-10 rounded-md bg-muted animate-pulse"
          />
        ))}
      </div>
    );
  }

  return (
    <div className="grid grid-cols-2 gap-2">
      {Array.from({ length: count }).map((_, i) => (
        <div
          key={i}
          className="h-20 rounded-lg bg-muted animate-pulse"
        />
      ))}
    </div>
  );
}

/**
 * Pre-built suggestion sets for common scenarios
 */
export const COMMON_SUGGESTIONS = {
  general: [
    { id: 'g1', text: 'Tell me more about this', category: 'follow-up' as const },
    { id: 'g2', text: 'Can you explain in simpler terms?', category: 'clarify' as const },
    { id: 'g3', text: 'What are the alternatives?', category: 'explore' as const },
    { id: 'g4', text: 'Show me an example', category: 'action' as const },
  ],
  code: [
    { id: 'c1', text: 'Explain this code', category: 'clarify' as const },
    { id: 'c2', text: 'How can I improve this?', category: 'explore' as const },
    { id: 'c3', text: 'Add error handling', category: 'action' as const },
    { id: 'c4', text: 'Write unit tests', category: 'action' as const },
  ],
  analysis: [
    { id: 'a1', text: 'What are the key insights?', category: 'follow-up' as const },
    { id: 'a2', text: 'Show me a chart', category: 'action' as const },
    { id: 'a3', text: 'Compare with last period', category: 'explore' as const },
    { id: 'a4', text: 'Export this data', category: 'action' as const },
  ],
  devops: [
    { id: 'd1', text: 'What metrics should I track?', category: 'explore' as const },
    { id: 'd2', text: 'How do I improve DORA metrics?', category: 'follow-up' as const },
    { id: 'd3', text: 'Show deployment frequency', category: 'action' as const },
    { id: 'd4', text: 'Identify bottlenecks', category: 'explore' as const },
  ],
};

export default SmartSuggestions;
