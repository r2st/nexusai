'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Plus, MessageSquare, Trash2, Settings, Menu, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn, formatRelativeTime, truncate } from '@/lib/utils';
import type { Conversation } from '@/lib/api';

interface SidebarProps {
  conversations: Conversation[];
  currentId?: string;
  onNewChat: () => void;
  onDelete: (id: string) => void;
}

export function ChatSidebar({
  conversations,
  currentId,
  onNewChat,
  onDelete,
}: SidebarProps) {
  const [mobileOpen, setMobileOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle button */}
      <Button
        variant="ghost"
        size="icon"
        className="fixed top-3 left-3 z-50 md:hidden"
        onClick={() => setMobileOpen(true)}
        aria-label="Open sidebar"
      >
        <Menu className="h-5 w-5" aria-hidden="true" />
      </Button>

      {/* Mobile backdrop */}
      {mobileOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      <aside
        className={cn(
          'flex h-full w-64 flex-col border-r bg-muted/30 shrink-0',
          'max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:shadow-lg',
          'max-md:transition-transform max-md:duration-200',
          mobileOpen ? 'max-md:translate-x-0' : 'max-md:-translate-x-full'
        )}
        data-sidebar
        aria-label="Chat conversations"
      >
        {/* Header */}
        <div className="flex h-14 items-center justify-between border-b px-4">
          <Link href="/" className="font-semibold">
            GSTIndia
          </Link>
          <div className="flex items-center gap-1">
            <Button variant="ghost" size="icon" onClick={onNewChat} aria-label="Create new chat">
              <Plus className="h-4 w-4" aria-hidden="true" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              className="md:hidden"
              onClick={() => setMobileOpen(false)}
              aria-label="Close sidebar"
            >
              <X className="h-4 w-4" aria-hidden="true" />
            </Button>
          </div>
        </div>

        {/* New Chat Button */}
        <div className="p-2">
          <Button
            variant="outline"
            className="w-full justify-start gap-2"
            onClick={() => {
              onNewChat();
              setMobileOpen(false);
            }}
            data-testid="new-chat-button"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            New Chat
          </Button>
        </div>

        {/* Conversations List */}
        <div className="flex-1 overflow-y-auto p-2">
          <div className="space-y-1">
            {conversations.map((conversation) => (
              <ConversationItem
                key={conversation.id}
                conversation={conversation}
                isActive={conversation.id === currentId}
                onDelete={() => onDelete(conversation.id)}
                onNavigate={() => setMobileOpen(false)}
                data-conversation-item
              />
            ))}
          </div>

          {conversations.length === 0 && (
            <div className="px-2 py-8 text-center text-sm text-muted-foreground">
              No conversations yet.
              <br />
              Start a new chat!
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="border-t p-2">
          <Link href="/settings">
            <Button variant="ghost" className="w-full justify-start gap-2" data-nav="settings">
              <Settings className="h-4 w-4" aria-hidden="true" />
              Settings
            </Button>
          </Link>
        </div>
      </aside>
    </>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onDelete: () => void;
  onNavigate: () => void;
  'data-conversation-item'?: boolean;
}

function ConversationItem({
  conversation,
  isActive,
  onDelete,
  onNavigate,
  ...props
}: ConversationItemProps) {
  return (
    <div
      className={cn(
        'group relative flex items-center gap-2 rounded-md px-2 py-2 text-sm',
        'hover:bg-muted',
        isActive && 'bg-muted'
      )}
      {...props}
    >
      <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <Link
        href={`/chat/${conversation.id}`}
        className="flex-1 truncate"
        onClick={onNavigate}
      >
        {truncate(conversation.title, 25)}
      </Link>

      {/* Actions — visible on hover/focus-within for keyboard accessibility */}
      <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 group-focus-within:opacity-100 transition-opacity">
        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={(e) => {
            e.preventDefault();
            onDelete();
          }}
          aria-label={`Delete conversation: ${conversation.title}`}
          data-testid="delete-conversation"
        >
          <Trash2 className="h-3 w-3" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}
