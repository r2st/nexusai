'use client';

import * as React from 'react';
import * as AvatarPrimitive from '@radix-ui/react-avatar';
import { User, Bot, Users } from 'lucide-react';
import { cn } from '@/lib/utils';

// =============================================================================
// Base Avatar Components
// =============================================================================

const Avatar = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Root>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Root>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Root
    ref={ref}
    className={cn(
      'relative flex h-10 w-10 shrink-0 overflow-hidden rounded-full',
      className
    )}
    {...props}
  />
));
Avatar.displayName = AvatarPrimitive.Root.displayName;

const AvatarImage = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Image>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Image>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Image
    ref={ref}
    className={cn('aspect-square h-full w-full', className)}
    {...props}
  />
));
AvatarImage.displayName = AvatarPrimitive.Image.displayName;

const AvatarFallback = React.forwardRef<
  React.ElementRef<typeof AvatarPrimitive.Fallback>,
  React.ComponentPropsWithoutRef<typeof AvatarPrimitive.Fallback>
>(({ className, ...props }, ref) => (
  <AvatarPrimitive.Fallback
    ref={ref}
    className={cn(
      'flex h-full w-full items-center justify-center rounded-full bg-muted',
      className
    )}
    {...props}
  />
));
AvatarFallback.displayName = AvatarPrimitive.Fallback.displayName;

// =============================================================================
// Extended Avatar Components
// =============================================================================

interface UserAvatarProps {
  user?: {
    name?: string | null;
    email?: string | null;
    image?: string | null;
  } | null;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  className?: string;
}

/**
 * User avatar with fallback to initials or icon
 */
export function UserAvatar({ user, size = 'md', className }: UserAvatarProps) {
  const sizeClasses = {
    xs: 'h-6 w-6 text-xs',
    sm: 'h-8 w-8 text-sm',
    md: 'h-10 w-10 text-base',
    lg: 'h-12 w-12 text-lg',
    xl: 'h-16 w-16 text-xl',
  };

  const iconSizes = {
    xs: 'h-3 w-3',
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
    xl: 'h-8 w-8',
  };

  const getInitials = (name?: string | null, email?: string | null): string => {
    if (name) {
      return name
        .split(' ')
        .map((part) => part[0])
        .join('')
        .toUpperCase()
        .slice(0, 2);
    }
    if (email) {
      return email[0].toUpperCase();
    }
    return '';
  };

  const initials = getInitials(user?.name, user?.email);

  return (
    <Avatar className={cn(sizeClasses[size], className)}>
      {user?.image && (
        <AvatarImage src={user.image} alt={user.name || 'User avatar'} />
      )}
      <AvatarFallback className="bg-primary/10 text-primary">
        {initials || <User className={iconSizes[size]} aria-hidden="true" />}
      </AvatarFallback>
    </Avatar>
  );
}

interface AIAvatarProps {
  name?: string;
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  variant?: 'default' | 'gradient' | 'outline';
  animated?: boolean;
  className?: string;
}

/**
 * AI/Bot avatar with customizable appearance
 */
export function AIAvatar({
  name = 'AI',
  size = 'md',
  variant = 'default',
  animated = false,
  className,
}: AIAvatarProps) {
  const sizeClasses = {
    xs: 'h-6 w-6',
    sm: 'h-8 w-8',
    md: 'h-10 w-10',
    lg: 'h-12 w-12',
    xl: 'h-16 w-16',
  };

  const iconSizes = {
    xs: 'h-3 w-3',
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
    xl: 'h-8 w-8',
  };

  const variantClasses = {
    default: 'bg-secondary text-secondary-foreground',
    gradient: 'bg-gradient-to-br from-primary to-primary/60 text-primary-foreground',
    outline: 'border-2 border-primary bg-transparent text-primary',
  };

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-full shrink-0',
        sizeClasses[size],
        variantClasses[variant],
        animated && 'animate-pulse',
        className
      )}
      role="img"
      aria-label={`${name} avatar`}
    >
      <Bot className={iconSizes[size]} aria-hidden="true" />
    </div>
  );
}

interface AvatarGroupProps {
  users: Array<{
    id: string;
    name?: string | null;
    email?: string | null;
    image?: string | null;
  }>;
  max?: number;
  size?: 'xs' | 'sm' | 'md' | 'lg';
  className?: string;
}

/**
 * Group of avatars with overflow indicator
 */
export function AvatarGroup({
  users,
  max = 4,
  size = 'sm',
  className,
}: AvatarGroupProps) {
  const visibleUsers = users.slice(0, max);
  const remainingCount = users.length - max;

  const sizeClasses = {
    xs: 'h-6 w-6 text-[10px]',
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
  };

  const overlapClasses = {
    xs: '-ml-2',
    sm: '-ml-2.5',
    md: '-ml-3',
    lg: '-ml-4',
  };

  return (
    <div className={cn('flex items-center', className)}>
      {visibleUsers.map((user, index) => (
        <div
          key={user.id}
          className={cn(
            'relative ring-2 ring-background rounded-full',
            index > 0 && overlapClasses[size]
          )}
          style={{ zIndex: visibleUsers.length - index }}
        >
          <UserAvatar user={user} size={size} />
        </div>
      ))}
      {remainingCount > 0 && (
        <div
          className={cn(
            'flex items-center justify-center rounded-full bg-muted ring-2 ring-background',
            sizeClasses[size],
            overlapClasses[size]
          )}
        >
          <span className="font-medium">+{remainingCount}</span>
        </div>
      )}
    </div>
  );
}

interface TeamAvatarProps {
  name: string;
  size?: 'sm' | 'md' | 'lg';
  color?: string;
  className?: string;
}

/**
 * Team/Organization avatar
 */
export function TeamAvatar({
  name,
  size = 'md',
  color,
  className,
}: TeamAvatarProps) {
  const sizeClasses = {
    sm: 'h-8 w-8 text-xs',
    md: 'h-10 w-10 text-sm',
    lg: 'h-12 w-12 text-base',
  };

  const iconSizes = {
    sm: 'h-4 w-4',
    md: 'h-5 w-5',
    lg: 'h-6 w-6',
  };

  // Generate consistent color from name
  const getColorFromName = (name: string): string => {
    const colors = [
      'bg-red-100 text-red-600',
      'bg-orange-100 text-orange-600',
      'bg-amber-100 text-amber-600',
      'bg-yellow-100 text-yellow-600',
      'bg-lime-100 text-lime-600',
      'bg-green-100 text-green-600',
      'bg-emerald-100 text-emerald-600',
      'bg-teal-100 text-teal-600',
      'bg-cyan-100 text-cyan-600',
      'bg-sky-100 text-sky-600',
      'bg-blue-100 text-blue-600',
      'bg-indigo-100 text-indigo-600',
      'bg-violet-100 text-violet-600',
      'bg-purple-100 text-purple-600',
      'bg-fuchsia-100 text-fuchsia-600',
      'bg-pink-100 text-pink-600',
    ];
    const hash = name.split('').reduce((acc, char) => acc + char.charCodeAt(0), 0);
    return colors[hash % colors.length];
  };

  const initials = name
    .split(' ')
    .map((word) => word[0])
    .join('')
    .toUpperCase()
    .slice(0, 2);

  return (
    <div
      className={cn(
        'flex items-center justify-center rounded-lg font-medium',
        sizeClasses[size],
        color || getColorFromName(name),
        className
      )}
      role="img"
      aria-label={`${name} team avatar`}
    >
      {initials || <Users className={iconSizes[size]} aria-hidden="true" />}
    </div>
  );
}

export { Avatar, AvatarImage, AvatarFallback };
