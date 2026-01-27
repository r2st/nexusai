'use client';

import { useState } from 'react';
import Link from 'next/link';
import { Plus, MessageSquare, Trash2, MoreHorizontal, Settings } from 'lucide-react';
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
  return (
    <aside className="flex h-full w-64 flex-col border-r bg-muted/30" data-sidebar aria-label="Chat conversations">
      {/* Header */}
      <div className="flex h-14 items-center justify-between border-b px-4">
        <Link href="/" className="font-semibold">
          NexusAI
        </Link>
        <Button variant="ghost" size="icon" onClick={onNewChat} aria-label="Create new chat">
          <Plus className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>

      {/* New Chat Button */}
      <div className="p-2">
        <Button
          variant="outline"
          className="w-full justify-start gap-2"
          onClick={onNewChat}
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
        <Button variant="ghost" className="w-full justify-start gap-2" data-nav="settings">
          <Settings className="h-4 w-4" aria-hidden="true" />
          Settings
        </Button>
      </div>
    </aside>
  );
}

interface ConversationItemProps {
  conversation: Conversation;
  isActive: boolean;
  onDelete: () => void;
  'data-conversation-item'?: boolean;
}

function ConversationItem({
  conversation,
  isActive,
  onDelete,
  ...props
}: ConversationItemProps) {
  const [showMenu, setShowMenu] = useState(false);

  return (
    <div
      className={cn(
        'group relative flex items-center gap-2 rounded-md px-2 py-2 text-sm',
        'hover:bg-muted cursor-pointer',
        isActive && 'bg-muted'
      )}
      onMouseEnter={() => setShowMenu(true)}
      onMouseLeave={() => setShowMenu(false)}
      {...props}
    >
      <MessageSquare className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden="true" />
      <Link
        href={`/chat/${conversation.id}`}
        className="flex-1 truncate"
      >
        {truncate(conversation.title, 25)}
      </Link>

      {/* Actions */}
      {showMenu && (
        <div className="flex items-center gap-1">
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6"
            onClick={(e) => {
              e.preventDefault();
              onDelete();
            }}
            aria-label="Delete conversation"
            data-testid="delete-conversation"
          >
            <Trash2 className="h-3 w-3" aria-hidden="true" />
          </Button>
        </div>
      )}
    </div>
  );
}
