'use client';

import { cn } from '@/lib/utils';

interface StatusRailProps {
  status: 'idle' | 'responding' | 'tooling';
  detail?: string;
}

const STATUS_MAP = {
  idle: { label: 'Idle', tone: 'text-muted-foreground' },
  responding: { label: 'Responding', tone: 'text-emerald-600' },
  tooling: { label: 'Calling tools', tone: 'text-amber-600' },
};

export function StatusRail({ status, detail }: StatusRailProps) {
  if (status === 'idle') return null;

  const config = STATUS_MAP[status];

  return (
    <div role="status" aria-live="polite" className="mx-auto mt-3 flex max-w-3xl items-center justify-between rounded-full border border-border bg-muted/40 px-3 py-1 text-xs">
      <div className={cn('font-medium', config.tone)}>{config.label}</div>
      {detail && <div className="text-muted-foreground">{detail}</div>}
    </div>
  );
}
