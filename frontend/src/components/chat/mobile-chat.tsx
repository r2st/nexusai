'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Menu,
  X,
  ChevronLeft,
  Send,
  Mic,
  Plus,
  MoreVertical,
  Trash2,
  Share2,
  Settings,
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
import { VoiceInput } from './voice-input';
import { TypingIndicator } from './typing-indicator';
import { EnhancedMessage } from './enhanced-message';
import { WelcomeMessage } from './welcome-message';
import { SmartSuggestions, COMMON_SUGGESTIONS } from './smart-suggestions';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface Conversation {
  id: string;
  title: string;
  updatedAt: string;
}

interface MobileChatProps {
  conversations: Conversation[];
  currentConversation?: Conversation | null;
  messages: Message[];
  isLoading?: boolean;
  isStreaming?: boolean;
  streamingContent?: string;
  onSendMessage: (message: string) => void;
  onNewChat: () => void;
  onSelectConversation: (id: string) => void;
  onDeleteConversation: (id: string) => void;
  className?: string;
}

/**
 * Mobile-optimized chat interface.
 * 
 * Features:
 * - Full-screen chat experience
 * - Swipe-able sidebar
 * - Touch-friendly input
 * - Voice input support
 * - Pull-to-refresh (future)
 */
export function MobileChat({
  conversations,
  currentConversation,
  messages,
  isLoading,
  isStreaming,
  streamingContent,
  onSendMessage,
  onNewChat,
  onSelectConversation,
  onDeleteConversation,
  className,
}: MobileChatProps) {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [inputValue, setInputValue] = useState('');
  const [showSuggestions, setShowSuggestions] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  // Auto-resize input
  useEffect(() => {
    const textarea = inputRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 120)}px`;
    }
  }, [inputValue]);

  const handleSend = useCallback(() => {
    const trimmed = inputValue.trim();
    if (trimmed && !isLoading) {
      onSendMessage(trimmed);
      setInputValue('');
      setShowSuggestions(false);
    }
  }, [inputValue, isLoading, onSendMessage]);

  const handleVoiceTranscript = useCallback((text: string) => {
    setInputValue((prev) => prev + (prev ? ' ' : '') + text);
  }, []);

  const handleSuggestionClick = useCallback((suggestion: { text: string }) => {
    onSendMessage(suggestion.text);
    setShowSuggestions(false);
  }, [onSendMessage]);

  const handleExampleClick = useCallback((query: string) => {
    onSendMessage(query);
    setShowSuggestions(false);
  }, [onSendMessage]);

  return (
    <div className={cn('flex h-screen bg-background', className)}>
      {/* Sidebar Overlay */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-40 lg:hidden"
          onClick={() => setSidebarOpen(false)}
          onKeyDown={(e) => {
            if (e.key === 'Escape') setSidebarOpen(false);
          }}
          role="button"
          tabIndex={0}
          aria-label="Close sidebar overlay"
        />
      )}

      {/* Sidebar */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 w-72 bg-background border-r transform transition-transform duration-200 ease-in-out lg:relative lg:translate-x-0',
          sidebarOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Sidebar Header */}
        <div className="flex items-center justify-between p-4 border-b">
          <h2 className="font-semibold">Conversations</h2>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(false)}
            className="lg:hidden"
            aria-label="Close sidebar"
          >
            <X className="h-5 w-5" aria-hidden="true" />
          </Button>
        </div>

        {/* New Chat Button */}
        <div className="p-3">
          <Button
            onClick={() => {
              onNewChat();
              setSidebarOpen(false);
            }}
            className="w-full"
          >
            <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
            New Chat
          </Button>
        </div>

        {/* Conversation List */}
        <nav className="flex-1 overflow-y-auto p-2" aria-label="Conversation history">
          {conversations.length === 0 ? (
            <p className="text-center text-muted-foreground text-sm p-4">
              No conversations yet
            </p>
          ) : (
            <ul className="space-y-1">
              {conversations.map((conv) => (
                <li key={conv.id}>
                  <button
                    onClick={() => {
                      onSelectConversation(conv.id);
                      setSidebarOpen(false);
                    }}
                    className={cn(
                      'w-full flex items-center gap-3 p-3 rounded-lg text-left transition-colors',
                      currentConversation?.id === conv.id
                        ? 'bg-primary/10 text-primary'
                        : 'hover:bg-muted'
                    )}
                  >
                    <span className="flex-1 truncate text-sm">{conv.title}</span>
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild onClick={(e) => e.stopPropagation()}>
                        <Button variant="ghost" size="icon" className="h-7 w-7 shrink-0" aria-label="Conversation options">
                          <MoreVertical className="h-4 w-4" aria-hidden="true" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem>
                          <Share2 className="h-4 w-4 mr-2" aria-hidden="true" />
                          Share
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          className="text-destructive"
                          onClick={() => onDeleteConversation(conv.id)}
                        >
                          <Trash2 className="h-4 w-4 mr-2" aria-hidden="true" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </nav>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center gap-3 p-3 border-b bg-background sticky top-0 z-10">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setSidebarOpen(true)}
            className="lg:hidden"
            aria-label="Open sidebar"
          >
            <Menu className="h-5 w-5" aria-hidden="true" />
          </Button>

          <div className="flex-1 min-w-0">
            <h1 className="font-medium truncate">
              {currentConversation?.title || 'New Chat'}
            </h1>
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="icon" aria-label="Chat options">
                <MoreVertical className="h-5 w-5" aria-hidden="true" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={onNewChat}>
                <Plus className="h-4 w-4 mr-2" aria-hidden="true" />
                New Chat
              </DropdownMenuItem>
              <DropdownMenuItem>
                <Settings className="h-4 w-4 mr-2" aria-hidden="true" />
                Settings
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 && !isStreaming ? (
            <WelcomeMessage
              onExampleClick={handleExampleClick}
              className="px-4"
            />
          ) : (
            <div className="pb-4">
              {messages.map((msg) => (
                <EnhancedMessage
                  key={msg.id}
                  id={msg.id}
                  role={msg.role}
                  content={msg.content}
                  timestamp={msg.timestamp}
                />
              ))}

              {isStreaming && streamingContent && (
                <EnhancedMessage
                  id="streaming"
                  role="assistant"
                  content={streamingContent}
                  isStreaming
                />
              )}

              {isLoading && !streamingContent && (
                <TypingIndicator variant="dots" />
              )}

              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Suggestions */}
        {showSuggestions && messages.length > 0 && !isLoading && (
          <div className="px-4 pb-2">
            <SmartSuggestions
              suggestions={COMMON_SUGGESTIONS.general}
              onSelect={handleSuggestionClick}
              variant="chips"
              maxVisible={3}
            />
          </div>
        )}

        {/* Loading announcement for screen readers */}
        {isLoading && (
          <div className="sr-only" role="status" aria-live="assertive">
            Loading response...
          </div>
        )}

        {/* Input Area */}
        <div className="p-3 border-t bg-background sticky bottom-0">
          <div className="flex items-end gap-2">
            {/* Voice Input */}
            <VoiceInput
              onTranscript={handleVoiceTranscript}
              disabled={isLoading}
            />

            {/* Text Input */}
            <div className="flex-1 flex items-end gap-2 rounded-lg border bg-muted/50 p-2">
              <textarea
                ref={inputRef}
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleSend();
                  }
                }}
                placeholder="Message..."
                disabled={isLoading}
                rows={1}
                aria-label="Message input"
                className="flex-1 bg-transparent resize-none outline-none text-sm min-h-[24px] max-h-[120px]"
              />

              <Button
                size="icon"
                onClick={handleSend}
                disabled={!inputValue.trim() || isLoading}
                className="h-8 w-8 shrink-0"
                aria-label="Send message"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>
        </div>
      </main>
    </div>
  );
}

export default MobileChat;
