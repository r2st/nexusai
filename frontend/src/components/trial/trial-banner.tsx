'use client';

import { useState, useEffect } from 'react';
import { X, Clock, Sparkles, AlertTriangle } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { trialsApi, type TrialStatus, TenantContext } from '@/lib/api';
import { cn } from '@/lib/utils';
import Link from 'next/link';

interface TrialBannerProps {
  orgId?: string;
  className?: string;
}

export function TrialBanner({ orgId, className }: TrialBannerProps) {
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [isDismissed, setIsDismissed] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchTrialStatus() {
      const currentOrgId = orgId || TenantContext.getCurrentTenantId();
      if (!currentOrgId) {
        setIsLoading(false);
        return;
      }

      // Check if banner was dismissed for this session
      const dismissedKey = `trial_banner_dismissed_${currentOrgId}`;
      if (sessionStorage.getItem(dismissedKey)) {
        setIsDismissed(true);
        setIsLoading(false);
        return;
      }

      try {
        const status = await trialsApi.getStatus(currentOrgId);
        setTrialStatus(status);
      } catch (error) {
        console.error('Failed to fetch trial status:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTrialStatus();
  }, [orgId]);

  const handleDismiss = () => {
    const currentOrgId = orgId || TenantContext.getCurrentTenantId();
    if (currentOrgId) {
      sessionStorage.setItem(`trial_banner_dismissed_${currentOrgId}`, 'true');
    }
    setIsDismissed(true);
  };

  // Don't show banner if:
  // - Still loading
  // - Dismissed
  // - No trial status
  // - Trial is not active
  // - User has an active subscription
  if (
    isLoading ||
    isDismissed ||
    !trialStatus ||
    !trialStatus.is_trial_active ||
    trialStatus.can_access_features === false
  ) {
    return null;
  }

  const daysRemaining = trialStatus.trial_days_remaining;
  const isUrgent = daysRemaining <= 3;

  return (
    <div
      className={cn(
        'relative flex items-center justify-between gap-4 px-4 py-3',
        isUrgent
          ? 'bg-amber-500/10 border-b border-amber-500/20'
          : 'bg-primary/5 border-b border-primary/10',
        className
      )}
    >
      <div className="flex items-center gap-3">
        {isUrgent ? (
          <AlertTriangle className="h-5 w-5 shrink-0 text-amber-500" />
        ) : (
          <Clock className="h-5 w-5 shrink-0 text-primary" />
        )}
        <p
          className={cn(
            'text-sm font-medium',
            isUrgent ? 'text-amber-700 dark:text-amber-400' : 'text-foreground'
          )}
        >
          {isUrgent ? (
            <>
              Your trial expires in {daysRemaining} day
              {daysRemaining !== 1 ? 's' : ''}!
            </>
          ) : (
            <>
              {daysRemaining} day{daysRemaining !== 1 ? 's' : ''} left in your
              trial
            </>
          )}
          <span className="ml-2 text-muted-foreground">
            ({trialStatus.current_tier} tier)
          </span>
        </p>
      </div>

      <div className="flex items-center gap-2">
        <Link href="/pricing">
          <Button
            size="sm"
            variant={isUrgent ? 'default' : 'outline'}
            className={cn(
              isUrgent && 'bg-amber-500 hover:bg-amber-600 text-white'
            )}
          >
            <Sparkles className="mr-1.5 h-4 w-4" />
            Upgrade Now
          </Button>
        </Link>
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={handleDismiss}
          aria-label="Dismiss trial banner"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

/**
 * Compact version of the trial banner for sidebars
 */
export function TrialBannerCompact({ orgId, className }: TrialBannerProps) {
  const [trialStatus, setTrialStatus] = useState<TrialStatus | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    async function fetchTrialStatus() {
      const currentOrgId = orgId || TenantContext.getCurrentTenantId();
      if (!currentOrgId) {
        setIsLoading(false);
        return;
      }

      try {
        const status = await trialsApi.getStatus(currentOrgId);
        setTrialStatus(status);
      } catch (error) {
        console.error('Failed to fetch trial status:', error);
      } finally {
        setIsLoading(false);
      }
    }

    fetchTrialStatus();
  }, [orgId]);

  if (
    isLoading ||
    !trialStatus ||
    !trialStatus.is_trial_active ||
    trialStatus.can_access_features === false
  ) {
    return null;
  }

  const daysRemaining = trialStatus.trial_days_remaining;
  const isUrgent = daysRemaining <= 3;

  return (
    <div
      className={cn(
        'rounded-lg p-3',
        isUrgent
          ? 'bg-amber-500/10 border border-amber-500/20'
          : 'bg-primary/5 border border-primary/10',
        className
      )}
    >
      <div className="flex items-center gap-2">
        {isUrgent ? (
          <AlertTriangle className="h-4 w-4 shrink-0 text-amber-500" />
        ) : (
          <Clock className="h-4 w-4 shrink-0 text-primary" />
        )}
        <p
          className={cn(
            'text-xs font-medium',
            isUrgent ? 'text-amber-700 dark:text-amber-400' : 'text-foreground'
          )}
        >
          {daysRemaining} day{daysRemaining !== 1 ? 's' : ''} left
        </p>
      </div>
      <Link href="/pricing" className="mt-2 block">
        <Button
          size="sm"
          variant={isUrgent ? 'default' : 'outline'}
          className={cn(
            'w-full text-xs',
            isUrgent && 'bg-amber-500 hover:bg-amber-600 text-white'
          )}
        >
          <Sparkles className="mr-1.5 h-3 w-3" />
          Upgrade
        </Button>
      </Link>
    </div>
  );
}
