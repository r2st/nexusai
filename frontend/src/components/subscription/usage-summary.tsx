'use client';

import { useState, useEffect } from 'react';
import { Users, FolderOpen, AlertTriangle } from 'lucide-react';
import { Progress } from '@/components/ui/progress';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui/card';
import {
  subscriptionsApi,
  type UsageSummary as UsageSummaryType,
  TenantContext,
} from '@/lib/api';
import { cn } from '@/lib/utils';

interface UsageSummaryProps {
  orgId?: string;
  className?: string;
}

function UsageBar({
  label,
  current,
  max,
  percentage,
  atLimit,
  icon: Icon,
}: {
  label: string;
  current: number;
  max: number;
  percentage: number;
  atLimit: boolean;
  icon: typeof Users;
}) {
  const isWarning = percentage >= 80;
  const isDanger = percentage >= 95 || atLimit;

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Icon
            className={cn(
              'h-4 w-4',
              isDanger
                ? 'text-red-500'
                : isWarning
                  ? 'text-amber-500'
                  : 'text-muted-foreground'
            )}
          />
          <span className="text-sm font-medium">{label}</span>
        </div>
        <span
          className={cn(
            'text-sm',
            isDanger
              ? 'text-red-500 font-medium'
              : isWarning
                ? 'text-amber-500'
                : 'text-muted-foreground'
          )}
        >
          {current} / {max}
        </span>
      </div>
      <Progress
        value={Math.min(percentage, 100)}
        className={cn(
          'h-2',
          isDanger
            ? '[&>div]:bg-red-500'
            : isWarning
              ? '[&>div]:bg-amber-500'
              : ''
        )}
      />
      {atLimit && (
        <p className="flex items-center gap-1 text-xs text-red-500">
          <AlertTriangle className="h-3 w-3" />
          Limit reached. Upgrade to add more.
        </p>
      )}
    </div>
  );
}

export function UsageSummary({ orgId, className }: UsageSummaryProps) {
  const [usage, setUsage] = useState<UsageSummaryType | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchUsage() {
      const currentOrgId = orgId || TenantContext.getCurrentTenantId();
      if (!currentOrgId) {
        setIsLoading(false);
        return;
      }

      try {
        const data = await subscriptionsApi.getUsage(currentOrgId);
        setUsage(data);
      } catch (error) {
        console.error('Failed to fetch usage:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchUsage();
  }, [orgId]);

  if (isLoading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-lg">Usage</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-4 animate-pulse">
            <div className="h-8 bg-muted rounded" />
            <div className="h-8 bg-muted rounded" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!usage) {
    return null;
  }

  return (
    <Card className={className}>
      <CardHeader className="pb-3">
        <CardTitle className="text-lg">Usage</CardTitle>
        <CardDescription>
          Current plan: <span className="capitalize">{usage.tier}</span>
          {usage.trial_active && (
            <span className="ml-2 text-amber-500">(Trial)</span>
          )}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <UsageBar
          label="Team Members"
          current={usage.members.current}
          max={usage.members.max}
          percentage={usage.members.percentage}
          atLimit={usage.members.at_limit}
          icon={Users}
        />
        <UsageBar
          label="Projects"
          current={usage.projects.current}
          max={usage.projects.max}
          percentage={usage.projects.percentage}
          atLimit={usage.projects.at_limit}
          icon={FolderOpen}
        />
      </CardContent>
    </Card>
  );
}

/**
 * Compact inline version of usage display
 */
export function UsageInline({ orgId, className }: UsageSummaryProps) {
  const [usage, setUsage] = useState<UsageSummaryType | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchUsage() {
      const currentOrgId = orgId || TenantContext.getCurrentTenantId();
      if (!currentOrgId) {
        setIsLoading(false);
        return;
      }

      try {
        const data = await subscriptionsApi.getUsage(currentOrgId);
        setUsage(data);
      } catch (error) {
        console.error('Failed to fetch usage:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchUsage();
  }, [orgId]);

  if (isLoading || !usage) {
    return null;
  }

  const membersWarning = usage.members.percentage >= 80;
  const projectsWarning = usage.projects.percentage >= 80;

  return (
    <div className={cn('flex items-center gap-4 text-sm', className)}>
      <div
        className={cn(
          'flex items-center gap-1.5',
          membersWarning && 'text-amber-500'
        )}
      >
        <Users className="h-4 w-4" />
        <span>
          {usage.members.current}/{usage.members.max}
        </span>
      </div>
      <div
        className={cn(
          'flex items-center gap-1.5',
          projectsWarning && 'text-amber-500'
        )}
      >
        <FolderOpen className="h-4 w-4" />
        <span>
          {usage.projects.current}/{usage.projects.max}
        </span>
      </div>
    </div>
  );
}
