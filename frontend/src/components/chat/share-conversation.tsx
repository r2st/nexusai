'use client';

import { useState, useCallback } from 'react';
import {
  Share2,
  Copy,
  Check,
  Link as LinkIcon,
  Mail,
  Download,
  FileText,
  FileJson,
  Loader2,
  Globe,
  Lock,
  Users,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
}

interface ShareConversationProps {
  conversationId: string;
  conversationTitle?: string;
  messages: Message[];
  onShare?: (type: 'link' | 'email', options?: ShareOptions) => Promise<string>;
  className?: string;
}

interface ShareOptions {
  visibility: 'public' | 'private' | 'team';
  expiresIn?: '1h' | '24h' | '7d' | '30d' | 'never';
  includeTimestamps?: boolean;
}

/**
 * Share and export conversation functionality.
 * 
 * Features:
 * - Share via link
 * - Export as Markdown, JSON, or plain text
 * - Visibility controls
 * - Expiration settings
 */
export function ShareConversation({
  conversationId,
  conversationTitle = 'Conversation',
  messages,
  onShare,
  className,
}: ShareConversationProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [shareLink, setShareLink] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
  const [visibility, setVisibility] = useState<'public' | 'private' | 'team'>('private');
  const [expiresIn, setExpiresIn] = useState<'1h' | '24h' | '7d' | '30d' | 'never'>('7d');

  const handleShare = useCallback(async () => {
    setIsLoading(true);
    try {
      if (onShare) {
        const link = await onShare('link', { visibility, expiresIn });
        setShareLink(link);
      } else {
        // Mock share link generation
        const mockLink = `https://nexusai.dev/share/${conversationId}?v=${visibility}&e=${expiresIn}`;
        setShareLink(mockLink);
      }
      toast.success('Share link created');
    } catch (error) {
      toast.error('Failed to create share link');
    } finally {
      setIsLoading(false);
    }
  }, [conversationId, visibility, expiresIn, onShare]);

  const handleCopyLink = useCallback(async () => {
    if (!shareLink) return;
    await navigator.clipboard.writeText(shareLink);
    setCopied(true);
    toast.success('Link copied to clipboard');
    setTimeout(() => setCopied(false), 2000);
  }, [shareLink]);

  const handleExport = useCallback(
    (format: 'markdown' | 'json' | 'text') => {
      const content = formatConversation(messages, conversationTitle, format);
      const mimeType =
        format === 'json' ? 'application/json' : 'text/plain';
      const extension = format === 'markdown' ? 'md' : format === 'json' ? 'json' : 'txt';

      const blob = new Blob([content], { type: mimeType });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${conversationTitle.replace(/\s+/g, '-').toLowerCase()}.${extension}`;
      a.click();
      URL.revokeObjectURL(url);

      toast.success(`Exported as ${format.toUpperCase()}`);
    },
    [messages, conversationTitle]
  );

  return (
    <Dialog open={isOpen} onOpenChange={setIsOpen}>
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" className={cn('gap-2', className)}>
          <Share2 className="h-4 w-4" />
          Share
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Share Conversation</DialogTitle>
          <DialogDescription>
            Share this conversation or export it for later use.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          {/* Visibility Options */}
          <fieldset className="space-y-2">
            <legend className="text-sm font-medium">Visibility</legend>
            <div className="grid grid-cols-3 gap-2" role="radiogroup" aria-label="Sharing visibility">
              <VisibilityOption
                icon={<Globe className="h-4 w-4" />}
                label="Public"
                description="Anyone with link"
                selected={visibility === 'public'}
                onClick={() => setVisibility('public')}
              />
              <VisibilityOption
                icon={<Lock className="h-4 w-4" />}
                label="Private"
                description="Only you"
                selected={visibility === 'private'}
                onClick={() => setVisibility('private')}
              />
              <VisibilityOption
                icon={<Users className="h-4 w-4" />}
                label="Team"
                description="Your organization"
                selected={visibility === 'team'}
                onClick={() => setVisibility('team')}
              />
            </div>
          </fieldset>

          {/* Expiration */}
          <div className="space-y-2">
            <label htmlFor="share-expiry" className="text-sm font-medium">Link Expires</label>
            <select
              id="share-expiry"
              value={expiresIn}
              onChange={(e) => setExpiresIn(e.target.value as typeof expiresIn)}
              className="w-full rounded-md border bg-background px-3 py-2 text-sm"
            >
              <option value="1h">1 hour</option>
              <option value="24h">24 hours</option>
              <option value="7d">7 days</option>
              <option value="30d">30 days</option>
              <option value="never">Never</option>
            </select>
          </div>

          {/* Share Link */}
          {shareLink ? (
            <div className="space-y-2">
              <label className="text-sm font-medium">Share Link</label>
              <div className="flex gap-2">
                <Input
                  value={shareLink}
                  readOnly
                  className="flex-1 text-sm"
                />
                <Button
                  size="icon"
                  variant="outline"
                  onClick={handleCopyLink}
                  aria-label={copied ? 'Link copied' : 'Copy link'}
                >
                  {copied ? (
                    <Check className="h-4 w-4 text-green-500" aria-hidden="true" />
                  ) : (
                    <Copy className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </div>
            </div>
          ) : (
            <Button
              onClick={handleShare}
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? (
                <>
                  <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                  Creating link...
                </>
              ) : (
                <>
                  <LinkIcon className="h-4 w-4 mr-2" />
                  Create Share Link
                </>
              )}
            </Button>
          )}

          {/* Export Options */}
          <div className="pt-4 border-t">
            <label className="text-sm font-medium">Export As</label>
            <div className="grid grid-cols-3 gap-2 mt-2">
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('markdown')}
                className="flex-col h-auto py-3"
                aria-label="Export as Markdown"
              >
                <FileText className="h-5 w-5 mb-1" aria-hidden="true" />
                <span className="text-xs">Markdown</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('json')}
                className="flex-col h-auto py-3"
                aria-label="Export as JSON"
              >
                <FileJson className="h-5 w-5 mb-1" aria-hidden="true" />
                <span className="text-xs">JSON</span>
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={() => handleExport('text')}
                className="flex-col h-auto py-3"
                aria-label="Export as plain text"
              >
                <Download className="h-5 w-5 mb-1" aria-hidden="true" />
                <span className="text-xs">Plain Text</span>
              </Button>
            </div>
          </div>
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => setIsOpen(false)}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/**
 * Visibility option button
 */
function VisibilityOption({
  icon,
  label,
  description,
  selected,
  onClick,
}: {
  icon: React.ReactNode;
  label: string;
  description: string;
  selected: boolean;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      role="radio"
      aria-checked={selected}
      aria-label={`${label}: ${description}`}
      className={cn(
        'flex flex-col items-center gap-1 p-3 rounded-lg border text-center transition-colors',
        selected
          ? 'border-primary bg-primary/5 text-primary'
          : 'hover:bg-muted'
      )}
    >
      {icon}
      <span className="text-sm font-medium">{label}</span>
      <span className="text-[10px] text-muted-foreground">{description}</span>
    </button>
  );
}

/**
 * Format conversation for export
 */
function formatConversation(
  messages: Message[],
  title: string,
  format: 'markdown' | 'json' | 'text'
): string {
  if (format === 'json') {
    return JSON.stringify(
      {
        title,
        exportedAt: new Date().toISOString(),
        messages: messages.map((m) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        })),
      },
      null,
      2
    );
  }

  if (format === 'markdown') {
    let md = `# ${title}\n\n`;
    md += `*Exported on ${new Date().toLocaleDateString()}*\n\n---\n\n`;

    for (const msg of messages) {
      const role = msg.role === 'user' ? '**You**' : '**Assistant**';
      md += `### ${role}\n\n${msg.content}\n\n`;
    }

    return md;
  }

  // Plain text
  let text = `${title}\n`;
  text += `Exported on ${new Date().toLocaleDateString()}\n`;
  text += '='.repeat(50) + '\n\n';

  for (const msg of messages) {
    const role = msg.role === 'user' ? 'You' : 'Assistant';
    text += `[${role}]\n${msg.content}\n\n`;
  }

  return text;
}

export default ShareConversation;
