'use client';

import { cn } from '@/lib/utils';

export function DoAideLogo({ size = 24, className }: { size?: number; className?: string }) {
  return (
    <svg
      viewBox="0 0 24 24"
      width={size}
      height={size}
      aria-hidden="true"
      className={cn('shrink-0', className)}
    >
      <circle cx="3" cy="3" r="2.6" fill="var(--da-teal)" opacity=".92" />
      <circle cx="12" cy="3" r="2.6" fill="var(--da-amber)" opacity=".92" />
      <circle cx="21" cy="3" r="2.6" fill="var(--da-pink)" opacity=".92" />
      <circle cx="3" cy="12" r="2.6" fill="var(--da-purple)" opacity=".92" />
      <circle cx="12" cy="12" r="2.6" fill="var(--da-blue)" opacity=".92" />
      <circle cx="21" cy="12" r="2.6" fill="var(--da-green)" opacity=".92" />
      <circle cx="3" cy="21" r="2.6" fill="var(--da-rose)" opacity=".92" />
      <circle cx="12" cy="21" r="2.6" fill="var(--da-orange)" opacity=".92" />
      <circle cx="21" cy="21" r="2.6" fill="var(--da-indigo)" opacity=".92" />
    </svg>
  );
}
