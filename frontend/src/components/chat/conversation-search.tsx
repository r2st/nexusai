'use client';

import { useState, useEffect, useCallback, useRef } from 'react';
import { useRouter } from 'next/navigation';
import {
  Search,
  X,
  MessageSquare,
  Clock,
  Filter,
  Calendar,
  Tag,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { chatApi, type Conversation, type Message } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';

interface SearchResult {
  conversation: Conversation;
  matchingMessages: {
    id: string;
    content: string;
    role: 'user' | 'assistant' | 'system';
    highlight: string;
  }[];
  relevanceScore: number;
}

interface ConversationSearchProps {
  isOpen: boolean;
  onClose: () => void;
  onSelectConversation: (id: string) => void;
}

export function ConversationSearch({
  isOpen,
  onClose,
  onSelectConversation,
}: ConversationSearchProps) {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const [dateFilter, setDateFilter] = useState<string>('all');
  const [conversations, setConversations] = useState<Conversation[]>([]);

  // Load conversations on mount
  useEffect(() => {
    if (isOpen) {
      loadConversations();
      inputRef.current?.focus();
    }
  }, [isOpen]);

  const loadConversations = async () => {
    try {
      const data = await chatApi.listConversations(100);
      setConversations(data);
    } catch (error) {
      console.error('Failed to load conversations:', error);
    }
  };

  // Search logic
  const performSearch = useCallback(
    async (searchQuery: string) => {
      if (!searchQuery.trim()) {
        setResults([]);
        return;
      }

      setIsSearching(true);
      
      try {
        // In a real implementation, this would be an API call
        // For now, we'll do client-side filtering
        const query = searchQuery.toLowerCase();
        const filteredResults: SearchResult[] = [];

        for (const conversation of conversations) {
          // Check if title matches
          const titleMatch = conversation.title?.toLowerCase().includes(query);
          
          // For each matching conversation, fetch messages to search
          // In production, this would be a server-side search
          let matchingMessages: SearchResult['matchingMessages'] = [];
          
          try {
            const messages = await chatApi.getMessages(conversation.id);
            matchingMessages = messages
              .filter((msg) => msg.content.toLowerCase().includes(query))
              .slice(0, 3) // Limit to 3 matches per conversation
              .map((msg) => {
                // Create a highlighted snippet
                const index = msg.content.toLowerCase().indexOf(query);
                const start = Math.max(0, index - 50);
                const end = Math.min(msg.content.length, index + query.length + 50);
                let snippet = msg.content.slice(start, end);
                if (start > 0) snippet = '...' + snippet;
                if (end < msg.content.length) snippet = snippet + '...';

                return {
                  id: msg.id,
                  content: msg.content,
                  role: msg.role,
                  highlight: snippet,
                };
              });
          } catch {
            // Ignore errors fetching messages
          }

          if (titleMatch || matchingMessages.length > 0) {
            // Apply date filter
            const conversationDate = new Date(conversation.created_at);
            const now = new Date();
            let passesDateFilter = true;

            if (dateFilter === 'today') {
              passesDateFilter =
                conversationDate.toDateString() === now.toDateString();
            } else if (dateFilter === 'week') {
              const weekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
              passesDateFilter = conversationDate >= weekAgo;
            } else if (dateFilter === 'month') {
              const monthAgo = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
              passesDateFilter = conversationDate >= monthAgo;
            }

            if (passesDateFilter) {
              filteredResults.push({
                conversation,
                matchingMessages,
                relevanceScore: titleMatch ? 2 : 1,
              });
            }
          }
        }

        // Sort by relevance
        filteredResults.sort((a, b) => b.relevanceScore - a.relevanceScore);
        
        setResults(filteredResults.slice(0, 10)); // Limit to 10 results
        setSelectedIndex(0);
      } catch (error) {
        console.error('Search failed:', error);
      } finally {
        setIsSearching(false);
      }
    },
    [conversations, dateFilter]
  );

  // Debounced search
  useEffect(() => {
    const timer = setTimeout(() => {
      performSearch(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query, performSearch]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!isOpen) return;

      switch (e.key) {
        case 'Escape':
          onClose();
          break;
        case 'ArrowDown':
          e.preventDefault();
          setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
          break;
        case 'ArrowUp':
          e.preventDefault();
          setSelectedIndex((prev) => Math.max(prev - 1, 0));
          break;
        case 'Enter':
          if (results[selectedIndex]) {
            handleSelect(results[selectedIndex].conversation.id);
          }
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, results, selectedIndex, onClose]);

  const handleSelect = (conversationId: string) => {
    onSelectConversation(conversationId);
    router.push(`/chat/${conversationId}`);
    onClose();
    setQuery('');
    setResults([]);
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-[15vh]" role="dialog" aria-modal="true" aria-label="Search conversations">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm"
        onClick={onClose}
        aria-hidden="true"
      />

      {/* Search Modal */}
      <div className="relative w-full max-w-2xl mx-4 rounded-xl border bg-background shadow-2xl">
        {/* Search Input */}
        <div className="flex items-center gap-3 border-b p-4">
          <Search className="h-5 w-5 text-muted-foreground shrink-0" />
          <Input
            ref={inputRef}
            type="text"
            placeholder="Search conversations..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="flex-1 border-0 bg-transparent p-0 text-lg focus-visible:ring-0"
          />
          {isSearching && (
            <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
          )}
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close search">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        {/* Filters */}
        <div className="flex items-center gap-2 border-b px-4 py-2">
          <Filter className="h-4 w-4 text-muted-foreground" />
          <span className="text-xs text-muted-foreground">Filter:</span>
          {['all', 'today', 'week', 'month'].map((filter) => (
            <button
              key={filter}
              onClick={() => setDateFilter(filter)}
              className={cn(
                'px-2 py-1 rounded text-xs font-medium transition-colors',
                dateFilter === filter
                  ? 'bg-primary text-primary-foreground'
                  : 'bg-muted hover:bg-muted/80'
              )}
            >
              {filter === 'all' ? 'All time' : filter.charAt(0).toUpperCase() + filter.slice(1)}
            </button>
          ))}
        </div>

        {/* Results */}
        <div className="max-h-[50vh] overflow-y-auto">
          {query && results.length === 0 && !isSearching ? (
            <div className="p-8 text-center">
              <MessageSquare className="mx-auto h-12 w-12 text-muted-foreground" />
              <p className="mt-4 font-medium">No conversations found</p>
              <p className="mt-1 text-sm text-muted-foreground">
                Try different keywords or adjust your filters
              </p>
            </div>
          ) : results.length > 0 ? (
            <div className="divide-y">
              {results.map((result, index) => (
                <button
                  key={result.conversation.id}
                  onClick={() => handleSelect(result.conversation.id)}
                  className={cn(
                    'w-full text-left p-4 transition-colors',
                    index === selectedIndex ? 'bg-muted' : 'hover:bg-muted/50'
                  )}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <MessageSquare className="h-4 w-4 text-primary shrink-0" />
                        <span className="font-medium truncate">
                          {result.conversation.title || 'Untitled'}
                        </span>
                      </div>
                      
                      {/* Matching messages preview */}
                      {result.matchingMessages.length > 0 && (
                        <div className="mt-2 space-y-1">
                          {result.matchingMessages.slice(0, 2).map((msg) => (
                            <p
                              key={msg.id}
                              className="text-sm text-muted-foreground line-clamp-1"
                            >
                              <span
                                className={cn(
                                  'text-xs px-1 py-0.5 rounded mr-1',
                                  msg.role === 'user'
                                    ? 'bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300'
                                    : 'bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300'
                                )}
                              >
                                {msg.role}
                              </span>
                              {msg.highlight}
                            </p>
                          ))}
                        </div>
                      )}
                    </div>
                    
                    <div className="flex items-center gap-2 text-xs text-muted-foreground ml-4">
                      <Clock className="h-3 w-3" />
                      {formatRelativeTime(result.conversation.updated_at || result.conversation.created_at)}
                    </div>
                  </div>
                  
                  {/* Metadata */}
                  <div className="mt-2 flex items-center gap-3 text-xs text-muted-foreground">
                    <span>{result.conversation.message_count} messages</span>
                    <span>•</span>
                    <span>{result.conversation.model_name}</span>
                  </div>
                </button>
              ))}
            </div>
          ) : !query ? (
            <div className="p-4">
              <p className="text-xs text-muted-foreground mb-3">Recent conversations</p>
              <div className="space-y-1">
                {conversations.slice(0, 5).map((conversation, index) => (
                  <button
                    key={conversation.id}
                    onClick={() => handleSelect(conversation.id)}
                    className={cn(
                      'w-full flex items-center gap-3 rounded-lg px-3 py-2 text-left transition-colors',
                      index === selectedIndex ? 'bg-muted' : 'hover:bg-muted/50'
                    )}
                  >
                    <MessageSquare className="h-4 w-4 text-muted-foreground" />
                    <span className="flex-1 truncate text-sm">
                      {conversation.title || 'Untitled'}
                    </span>
                    <span className="text-xs text-muted-foreground">
                      {formatRelativeTime(conversation.updated_at || conversation.created_at)}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ) : null}
        </div>

        {/* Footer */}
        <div className="border-t px-4 py-2">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-4">
              <span>
                <kbd className="px-1.5 py-0.5 bg-muted rounded">↑↓</kbd> Navigate
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-muted rounded">Enter</kbd> Select
              </span>
              <span>
                <kbd className="px-1.5 py-0.5 bg-muted rounded">Esc</kbd> Close
              </span>
            </div>
            {results.length > 0 && (
              <span>{results.length} result{results.length !== 1 ? 's' : ''}</span>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * Button to trigger the search modal
 */
interface SearchTriggerProps {
  onClick: () => void;
  className?: string;
}

export function SearchTrigger({ onClick, className }: SearchTriggerProps) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm text-muted-foreground transition-colors hover:bg-muted hover:text-foreground',
        className
      )}
    >
      <Search className="h-4 w-4" />
      <span>Search conversations...</span>
      <kbd className="ml-auto text-xs bg-muted px-1.5 py-0.5 rounded">⌘K</kbd>
    </button>
  );
}
