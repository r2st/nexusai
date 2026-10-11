'use client';

import { useState, useCallback, useRef, useEffect } from 'react';
import {
  MessageSquare,
  Send,
  Reply,
  MoreVertical,
  Trash2,
  Edit2,
  ThumbsUp,
  Flag,
  ChevronDown,
  ChevronUp,
  AtSign,
  Loader2,
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
import { UserAvatar } from '@/components/ui/avatar';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

// =============================================================================
// Types
// =============================================================================

interface CommentAuthor {
  id: string;
  name: string;
  email?: string;
  image?: string;
}

interface Comment {
  id: string;
  author: CommentAuthor;
  content: string;
  timestamp: string;
  isEdited?: boolean;
  likes: number;
  isLiked?: boolean;
  replies?: Comment[];
  replyCount?: number;
  mentions?: string[];
}

interface CommentsProps {
  targetId: string;
  targetType: 'message' | 'conversation' | 'document';
  comments: Comment[];
  currentUser: CommentAuthor;
  isLoading?: boolean;
  onAddComment: (content: string, parentId?: string) => Promise<void>;
  onEditComment: (commentId: string, content: string) => Promise<void>;
  onDeleteComment: (commentId: string) => Promise<void>;
  onLikeComment: (commentId: string) => Promise<void>;
  onLoadReplies?: (commentId: string) => Promise<Comment[]>;
  className?: string;
}

// =============================================================================
// Comments Component
// =============================================================================

/**
 * Threaded comments/discussion component.
 * 
 * Features:
 * - Nested replies
 * - Likes
 * - Edit/delete
 * - @mentions
 * - Lazy-loaded replies
 */
export function Comments({
  targetId,
  targetType,
  comments,
  currentUser,
  isLoading,
  onAddComment,
  onEditComment,
  onDeleteComment,
  onLikeComment,
  onLoadReplies,
  className,
}: CommentsProps) {
  const [newComment, setNewComment] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const handleSubmit = useCallback(async () => {
    if (!newComment.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onAddComment(newComment.trim());
      setNewComment('');
      toast.success('Comment added');
    } catch (error) {
      toast.error('Failed to add comment');
    } finally {
      setIsSubmitting(false);
    }
  }, [newComment, isSubmitting, onAddComment]);

  return (
    <div className={cn('space-y-4', className)}>
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="h-5 w-5 text-muted-foreground" />
          <span className="font-medium">Comments</span>
          <span className="text-sm text-muted-foreground">
            ({comments.length})
          </span>
        </div>
      </div>

      {/* Add Comment */}
      <div className="flex gap-3">
        <UserAvatar user={currentUser} size="sm" />
        <div className="flex-1 flex gap-2">
          <Input
            value={newComment}
            onChange={(e) => setNewComment(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSubmit();
              }
            }}
            placeholder="Add a comment..."
            disabled={isSubmitting}
          />
          <Button
            onClick={handleSubmit}
            disabled={!newComment.trim() || isSubmitting}
          >
            {isSubmitting ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <Send className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Comments List */}
      {isLoading ? (
        <div className="space-y-4">
          {[1, 2, 3].map((i) => (
            <CommentSkeleton key={i} />
          ))}
        </div>
      ) : comments.length === 0 ? (
        <div className="text-center py-8">
          <MessageSquare className="h-10 w-10 mx-auto text-muted-foreground mb-2" />
          <p className="text-sm text-muted-foreground">
            No comments yet. Be the first to comment!
          </p>
        </div>
      ) : (
        <div className="space-y-4">
          {comments.map((comment) => (
            <CommentItem
              key={comment.id}
              comment={comment}
              currentUserId={currentUser.id}
              onReply={onAddComment}
              onEdit={onEditComment}
              onDelete={onDeleteComment}
              onLike={onLikeComment}
              onLoadReplies={onLoadReplies}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// =============================================================================
// Comment Item
// =============================================================================

interface CommentItemProps {
  comment: Comment;
  currentUserId: string;
  depth?: number;
  onReply: (content: string, parentId: string) => Promise<void>;
  onEdit: (commentId: string, content: string) => Promise<void>;
  onDelete: (commentId: string) => Promise<void>;
  onLike: (commentId: string) => Promise<void>;
  onLoadReplies?: (commentId: string) => Promise<Comment[]>;
}

function CommentItem({
  comment,
  currentUserId,
  depth = 0,
  onReply,
  onEdit,
  onDelete,
  onLike,
  onLoadReplies,
}: CommentItemProps) {
  const [isReplying, setIsReplying] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [editContent, setEditContent] = useState(comment.content);
  const [replyContent, setReplyContent] = useState('');
  const [showReplies, setShowReplies] = useState(false);
  const [replies, setReplies] = useState<Comment[]>(comment.replies || []);
  const [loadingReplies, setLoadingReplies] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const isOwn = comment.author.id === currentUserId;
  const maxDepth = 3;

  const handleReplySubmit = useCallback(async () => {
    if (!replyContent.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onReply(replyContent.trim(), comment.id);
      setReplyContent('');
      setIsReplying(false);
      toast.success('Reply added');
    } catch (error) {
      toast.error('Failed to add reply');
    } finally {
      setIsSubmitting(false);
    }
  }, [replyContent, isSubmitting, onReply, comment.id]);

  const handleEditSubmit = useCallback(async () => {
    if (!editContent.trim() || isSubmitting) return;

    setIsSubmitting(true);
    try {
      await onEdit(comment.id, editContent.trim());
      setIsEditing(false);
      toast.success('Comment updated');
    } catch (error) {
      toast.error('Failed to update comment');
    } finally {
      setIsSubmitting(false);
    }
  }, [editContent, isSubmitting, onEdit, comment.id]);

  const handleDelete = useCallback(async () => {
    try {
      await onDelete(comment.id);
      toast.success('Comment deleted');
    } catch (error) {
      toast.error('Failed to delete comment');
    }
  }, [onDelete, comment.id]);

  const handleLike = useCallback(async () => {
    try {
      await onLike(comment.id);
    } catch (error) {
      toast.error('Failed to like comment');
    }
  }, [onLike, comment.id]);

  const handleLoadReplies = useCallback(async () => {
    if (!onLoadReplies || loadingReplies) return;

    setLoadingReplies(true);
    try {
      const loadedReplies = await onLoadReplies(comment.id);
      setReplies(loadedReplies);
      setShowReplies(true);
    } catch (error) {
      toast.error('Failed to load replies');
    } finally {
      setLoadingReplies(false);
    }
  }, [onLoadReplies, loadingReplies, comment.id]);

  const hasMoreReplies = (comment.replyCount || 0) > replies.length;

  return (
    <div className={cn('group', depth > 0 && 'ml-8 mt-3')}>
      <div className="flex gap-3">
        <UserAvatar user={comment.author} size="sm" />
        <div className="flex-1 min-w-0">
          {/* Header */}
          <div className="flex items-center gap-2">
            <span className="font-medium text-sm">{comment.author.name}</span>
            <span className="text-xs text-muted-foreground">
              {formatRelativeTime(comment.timestamp)}
            </span>
            {comment.isEdited && (
              <span className="text-xs text-muted-foreground">(edited)</span>
            )}
          </div>

          {/* Content */}
          {isEditing ? (
            <div className="mt-2 flex gap-2">
              <Input
                value={editContent}
                onChange={(e) => setEditContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleEditSubmit();
                  }
                  if (e.key === 'Escape') {
                    setIsEditing(false);
                    setEditContent(comment.content);
                  }
                }}
                disabled={isSubmitting}
                autoFocus
              />
              <Button
                size="sm"
                onClick={handleEditSubmit}
                disabled={!editContent.trim() || isSubmitting}
              >
                Save
              </Button>
              <Button
                size="sm"
                variant="outline"
                onClick={() => {
                  setIsEditing(false);
                  setEditContent(comment.content);
                }}
              >
                Cancel
              </Button>
            </div>
          ) : (
            <p className="text-sm mt-1 whitespace-pre-wrap">{comment.content}</p>
          )}

          {/* Actions */}
          {!isEditing && (
            <div className="flex items-center gap-3 mt-2">
              <button
                onClick={handleLike}
                className={cn(
                  'flex items-center gap-1 text-xs transition-colors',
                  comment.isLiked
                    ? 'text-primary'
                    : 'text-muted-foreground hover:text-foreground'
                )}
              >
                <ThumbsUp className="h-3.5 w-3.5" />
                {comment.likes > 0 && <span>{comment.likes}</span>}
              </button>

              {depth < maxDepth && (
                <button
                  onClick={() => setIsReplying(!isReplying)}
                  className="flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground"
                >
                  <Reply className="h-3.5 w-3.5" />
                  Reply
                </button>
              )}

              {(comment.replyCount || replies.length > 0) && (
                <button
                  onClick={() => {
                    if (!showReplies && hasMoreReplies) {
                      handleLoadReplies();
                    } else {
                      setShowReplies(!showReplies);
                    }
                  }}
                  className="flex items-center gap-1 text-xs text-primary"
                >
                  {loadingReplies ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : showReplies ? (
                    <ChevronUp className="h-3.5 w-3.5" />
                  ) : (
                    <ChevronDown className="h-3.5 w-3.5" />
                  )}
                  {comment.replyCount || replies.length}{' '}
                  {(comment.replyCount || replies.length) === 1 ? 'reply' : 'replies'}
                </button>
              )}

              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-6 w-6 opacity-0 group-hover:opacity-100 focus:opacity-100"
                    aria-label="Comment actions"
                  >
                    <MoreVertical className="h-3.5 w-3.5" aria-hidden="true" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end">
                  {isOwn && (
                    <>
                      <DropdownMenuItem onClick={() => setIsEditing(true)}>
                        <Edit2 className="h-4 w-4 mr-2" />
                        Edit
                      </DropdownMenuItem>
                      <DropdownMenuItem
                        className="text-destructive"
                        onClick={handleDelete}
                      >
                        <Trash2 className="h-4 w-4 mr-2" />
                        Delete
                      </DropdownMenuItem>
                      <DropdownMenuSeparator />
                    </>
                  )}
                  <DropdownMenuItem>
                    <Flag className="h-4 w-4 mr-2" />
                    Report
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          )}

          {/* Reply Input */}
          {isReplying && (
            <div className="mt-3 flex gap-2">
              <Input
                value={replyContent}
                onChange={(e) => setReplyContent(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    handleReplySubmit();
                  }
                  if (e.key === 'Escape') {
                    setIsReplying(false);
                    setReplyContent('');
                  }
                }}
                placeholder={`Reply to ${comment.author.name}...`}
                disabled={isSubmitting}
                autoFocus
              />
              <Button
                size="sm"
                onClick={handleReplySubmit}
                disabled={!replyContent.trim() || isSubmitting}
              >
                {isSubmitting ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  'Reply'
                )}
              </Button>
            </div>
          )}

          {/* Nested Replies */}
          {showReplies && replies.length > 0 && (
            <div className="space-y-3 mt-3">
              {replies.map((reply) => (
                <CommentItem
                  key={reply.id}
                  comment={reply}
                  currentUserId={currentUserId}
                  depth={depth + 1}
                  onReply={onReply}
                  onEdit={onEdit}
                  onDelete={onDelete}
                  onLike={onLike}
                  onLoadReplies={onLoadReplies}
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// Skeleton
// =============================================================================

function CommentSkeleton() {
  return (
    <div className="flex gap-3">
      <div className="h-8 w-8 rounded-full bg-muted animate-pulse" />
      <div className="flex-1 space-y-2">
        <div className="flex gap-2">
          <div className="h-4 w-24 rounded bg-muted animate-pulse" />
          <div className="h-4 w-16 rounded bg-muted animate-pulse" />
        </div>
        <div className="h-4 w-full rounded bg-muted animate-pulse" />
        <div className="h-4 w-3/4 rounded bg-muted animate-pulse" />
      </div>
    </div>
  );
}

// =============================================================================
// Utilities
// =============================================================================

function formatRelativeTime(timestamp: string): string {
  const date = new Date(timestamp);
  const now = new Date();
  const diffInSeconds = Math.floor((now.getTime() - date.getTime()) / 1000);

  if (diffInSeconds < 60) return 'just now';
  if (diffInSeconds < 3600) return `${Math.floor(diffInSeconds / 60)}m ago`;
  if (diffInSeconds < 86400) return `${Math.floor(diffInSeconds / 3600)}h ago`;
  if (diffInSeconds < 604800) return `${Math.floor(diffInSeconds / 86400)}d ago`;

  return date.toLocaleDateString();
}

export default Comments;
