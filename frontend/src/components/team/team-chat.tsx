'use client';

import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Users,
  Send,
  AtSign,
  Hash,
  Plus,
  Settings,
  Bell,
  BellOff,
  MoreVertical,
  UserPlus,
  LogOut,
  Trash2,
  Pin,
  Search,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { UserAvatar, AvatarGroup } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// =============================================================================
// Types
// =============================================================================

interface TeamMember {
  id: string;
  name: string;
  email: string;
  image?: string;
  status: 'online' | 'away' | 'offline';
  role: 'owner' | 'admin' | 'member';
}

interface TeamChannel {
  id: string;
  name: string;
  description?: string;
  isPrivate: boolean;
  members: TeamMember[];
  unreadCount: number;
  lastMessageAt?: string;
  isPinned?: boolean;
}

interface TeamMessage {
  id: string;
  channelId: string;
  author: TeamMember;
  content: string;
  timestamp: string;
  mentions?: string[];
  reactions?: { emoji: string; users: string[] }[];
  isEdited?: boolean;
  replyTo?: string;
  attachments?: { name: string; url: string; type: string }[];
}

interface TeamChatProps {
  teamId: string;
  teamName: string;
  currentUser: TeamMember;
  channels: TeamChannel[];
  members: TeamMember[];
  onSendMessage: (channelId: string, content: string, mentions?: string[]) => void;
  onCreateChannel: (name: string, isPrivate: boolean, members: string[]) => void;
  onJoinChannel: (channelId: string) => void;
  onLeaveChannel: (channelId: string) => void;
  onInviteMember: (email: string) => void;
  className?: string;
}

// =============================================================================
// Team Chat Component
// =============================================================================

/**
 * Multi-user team chat interface.
 * 
 * Features:
 * - Channels (public and private)
 * - Direct messages
 * - @mentions
 * - Member presence
 * - Notifications
 */
export function TeamChat({
  teamId,
  teamName,
  currentUser,
  channels,
  members,
  onSendMessage,
  onCreateChannel,
  onJoinChannel,
  onLeaveChannel,
  onInviteMember,
  className,
}: TeamChatProps) {
  const [selectedChannel, setSelectedChannel] = useState<TeamChannel | null>(
    channels[0] || null
  );
  const [messages, setMessages] = useState<TeamMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [showMentions, setShowMentions] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [notifications, setNotifications] = useState(true);
  const [showCreateChannel, setShowCreateChannel] = useState(false);
  const [showInvite, setShowInvite] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // Handle @mention detection
  useEffect(() => {
    const lastAtIndex = inputValue.lastIndexOf('@');
    if (lastAtIndex !== -1 && lastAtIndex === inputValue.length - 1) {
      setShowMentions(true);
      setMentionQuery('');
    } else if (lastAtIndex !== -1) {
      const query = inputValue.slice(lastAtIndex + 1);
      if (!query.includes(' ')) {
        setShowMentions(true);
        setMentionQuery(query);
      } else {
        setShowMentions(false);
      }
    } else {
      setShowMentions(false);
    }
  }, [inputValue]);

  const handleSend = useCallback(() => {
    if (!inputValue.trim() || !selectedChannel) return;

    // Extract mentions
    const mentionRegex = /@(\w+)/g;
    const mentions: string[] = [];
    let match: RegExpExecArray | null;
    while ((match = mentionRegex.exec(inputValue)) !== null) {
      const mentioned = members.find(
        (m) => m.name.toLowerCase().includes(match![1].toLowerCase())
      );
      if (mentioned) {
        mentions.push(mentioned.id);
      }
    }

    onSendMessage(selectedChannel.id, inputValue.trim(), mentions);
    setInputValue('');
    setShowMentions(false);
  }, [inputValue, selectedChannel, members, onSendMessage]);

  const handleMentionSelect = useCallback((member: TeamMember) => {
    const lastAtIndex = inputValue.lastIndexOf('@');
    const newValue = inputValue.slice(0, lastAtIndex) + `@${member.name} `;
    setInputValue(newValue);
    setShowMentions(false);
    inputRef.current?.focus();
  }, [inputValue]);

  const filteredMembers = members.filter(
    (m) =>
      m.id !== currentUser.id &&
      m.name.toLowerCase().includes(mentionQuery.toLowerCase())
  );

  const onlineMembers = members.filter((m) => m.status === 'online');

  return (
    <div className={cn('flex h-full bg-background', className)}>
      {/* Sidebar */}
      <aside className="w-64 border-r flex flex-col">
        {/* Team Header */}
        <div className="p-4 border-b">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Users className="h-5 w-5 text-primary" />
              <span className="font-semibold">{teamName}</span>
            </div>
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Team settings">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end">
                <DropdownMenuItem onClick={() => setShowInvite(true)}>
                  <UserPlus className="h-4 w-4 mr-2" />
                  Invite Member
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => setNotifications(!notifications)}>
                  {notifications ? (
                    <BellOff className="h-4 w-4 mr-2" />
                  ) : (
                    <Bell className="h-4 w-4 mr-2" />
                  )}
                  {notifications ? 'Mute' : 'Unmute'} Notifications
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem className="text-destructive">
                  <LogOut className="h-4 w-4 mr-2" />
                  Leave Team
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Channels */}
        <div className="flex-1 overflow-y-auto">
          <div className="p-2">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-xs font-medium text-muted-foreground uppercase">
                Channels
              </span>
              <Button
                variant="ghost"
                size="icon"
                className="h-5 w-5"
                onClick={() => setShowCreateChannel(true)}
                aria-label="Create channel"
              >
                <Plus className="h-3 w-3" aria-hidden="true" />
              </Button>
            </div>
            <nav className="space-y-1">
              {channels
                .filter((c) => !c.isPrivate)
                .map((channel) => (
                  <ChannelItem
                    key={channel.id}
                    channel={channel}
                    isSelected={selectedChannel?.id === channel.id}
                    onClick={() => setSelectedChannel(channel)}
                  />
                ))}
            </nav>
          </div>

          <div className="p-2">
            <div className="flex items-center justify-between px-2 py-1">
              <span className="text-xs font-medium text-muted-foreground uppercase">
                Direct Messages
              </span>
            </div>
            <nav className="space-y-1">
              {channels
                .filter((c) => c.isPrivate)
                .map((channel) => (
                  <ChannelItem
                    key={channel.id}
                    channel={channel}
                    isSelected={selectedChannel?.id === channel.id}
                    onClick={() => setSelectedChannel(channel)}
                    isPrivate
                  />
                ))}
            </nav>
          </div>
        </div>

        {/* Online Members */}
        <div className="p-4 border-t">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-medium text-muted-foreground">
              Online ({onlineMembers.length})
            </span>
          </div>
          <AvatarGroup users={onlineMembers} max={5} size="xs" />
        </div>
      </aside>

      {/* Main Chat Area */}
      <main className="flex-1 flex flex-col min-w-0">
        {selectedChannel ? (
          <>
            {/* Channel Header */}
            <header className="flex items-center justify-between px-4 py-3 border-b">
              <div className="flex items-center gap-2">
                {selectedChannel.isPrivate ? (
                  <AtSign className="h-5 w-5 text-muted-foreground" />
                ) : (
                  <Hash className="h-5 w-5 text-muted-foreground" />
                )}
                <span className="font-medium">{selectedChannel.name}</span>
                {selectedChannel.description && (
                  <span className="text-sm text-muted-foreground">
                    — {selectedChannel.description}
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Search messages">
                  <Search className="h-4 w-4" aria-hidden="true" />
                </Button>
                <Button variant="ghost" size="icon" className="h-8 w-8" aria-label="Pinned messages">
                  <Pin className="h-4 w-4" aria-hidden="true" />
                </Button>
                <AvatarGroup users={selectedChannel.members} max={3} size="xs" />
              </div>
            </header>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-8">
                  <Hash className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                  <h3 className="font-medium">Welcome to #{selectedChannel.name}</h3>
                  <p className="text-sm text-muted-foreground mt-1">
                    This is the start of the channel. Say hello!
                  </p>
                </div>
              ) : (
                messages.map((message) => (
                  <TeamMessageItem
                    key={message.id}
                    message={message}
                    currentUserId={currentUser.id}
                  />
                ))
              )}
              <div ref={messagesEndRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t relative">
              {/* Mention suggestions */}
              {showMentions && filteredMembers.length > 0 && (
                <div className="absolute bottom-full left-4 right-4 mb-2 bg-popover border rounded-lg shadow-lg max-h-48 overflow-y-auto">
                  {filteredMembers.map((member) => (
                    <button
                      key={member.id}
                      onClick={() => handleMentionSelect(member)}
                      className="flex items-center gap-2 w-full px-3 py-2 hover:bg-muted text-left"
                    >
                      <UserAvatar user={member} size="xs" />
                      <span className="text-sm">{member.name}</span>
                      <span className="text-xs text-muted-foreground">
                        {member.email}
                      </span>
                    </button>
                  ))}
                </div>
              )}

              <div className="flex items-center gap-2">
                <Input
                  ref={inputRef}
                  value={inputValue}
                  onChange={(e) => setInputValue(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && !e.shiftKey) {
                      e.preventDefault();
                      handleSend();
                    }
                  }}
                  placeholder={`Message #${selectedChannel.name}`}
                  className="flex-1"
                />
                <Button onClick={handleSend} disabled={!inputValue.trim()}>
                  <Send className="h-4 w-4" />
                </Button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center">
              <Users className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
              <h3 className="font-medium">Select a channel</h3>
              <p className="text-sm text-muted-foreground mt-1">
                Choose a channel from the sidebar to start chatting
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

// =============================================================================
// Sub-components
// =============================================================================

function ChannelItem({
  channel,
  isSelected,
  onClick,
  isPrivate,
}: {
  channel: TeamChannel;
  isSelected: boolean;
  onClick: () => void;
  isPrivate?: boolean;
}) {
  return (
    <button
      onClick={onClick}
      className={cn(
        'flex items-center gap-2 w-full px-2 py-1.5 rounded-md text-sm transition-colors',
        isSelected ? 'bg-primary/10 text-primary' : 'hover:bg-muted'
      )}
    >
      {isPrivate ? (
        <AtSign className="h-4 w-4 text-muted-foreground" />
      ) : (
        <Hash className="h-4 w-4 text-muted-foreground" />
      )}
      <span className="flex-1 text-left truncate">{channel.name}</span>
      {channel.unreadCount > 0 && (
        <span className="px-1.5 py-0.5 rounded-full bg-primary text-primary-foreground text-xs">
          {channel.unreadCount}
        </span>
      )}
      {channel.isPinned && <Pin className="h-3 w-3 text-muted-foreground" />}
    </button>
  );
}

function TeamMessageItem({
  message,
  currentUserId,
}: {
  message: TeamMessage;
  currentUserId: string;
}) {
  const isOwn = message.author.id === currentUserId;

  return (
    <div className="group flex gap-3">
      <UserAvatar user={message.author} size="sm" />
      <div className="flex-1 min-w-0">
        <div className="flex items-baseline gap-2">
          <span className="font-medium text-sm">{message.author.name}</span>
          <span className="text-xs text-muted-foreground">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: '2-digit',
              minute: '2-digit',
            })}
          </span>
          {message.isEdited && (
            <span className="text-xs text-muted-foreground">(edited)</span>
          )}
        </div>
        <p className="text-sm mt-0.5 whitespace-pre-wrap">{message.content}</p>

        {/* Reactions */}
        {message.reactions && message.reactions.length > 0 && (
          <div className="flex gap-1 mt-1">
            {message.reactions.map((reaction, index) => (
              <button
                key={index}
                className="px-2 py-0.5 rounded-full bg-muted text-xs hover:bg-muted/80"
              >
                {reaction.emoji} {reaction.users.length}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Actions */}
      <div className="opacity-0 group-hover:opacity-100 transition-opacity">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-7 w-7" aria-label="Message actions">
              <MoreVertical className="h-4 w-4" aria-hidden="true" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem>Reply</DropdownMenuItem>
            <DropdownMenuItem>Add Reaction</DropdownMenuItem>
            <DropdownMenuItem>Copy Link</DropdownMenuItem>
            {isOwn && (
              <>
                <DropdownMenuSeparator />
                <DropdownMenuItem>Edit</DropdownMenuItem>
                <DropdownMenuItem className="text-destructive">
                  <Trash2 className="h-4 w-4 mr-2" />
                  Delete
                </DropdownMenuItem>
              </>
            )}
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </div>
  );
}

export default TeamChat;
