'use client';

/**
 * Rate Limit Feedback Component
 * 
 * Shows users when they've been rate limited with countdown timer.
 */

import { useState, useEffect, createContext, useContext, ReactNode, useCallback } from 'react';
import { AlertTriangle, Clock, RefreshCw, Shield, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { checkRateLimit, resetRateLimit } from '@/lib/security';

// =============================================================================
// RATE LIMIT CONTEXT
// =============================================================================

interface RateLimitState {
  isLimited: boolean;
  resetTime: number | null;
  endpoint: string | null;
}

interface RateLimitContextType {
  rateLimitState: RateLimitState;
  setRateLimited: (endpoint: string, resetInMs: number) => void;
  clearRateLimit: () => void;
  checkEndpointLimit: (endpoint: string, maxRequests?: number, windowMs?: number) => boolean;
}

const RateLimitContext = createContext<RateLimitContextType>({
  rateLimitState: { isLimited: false, resetTime: null, endpoint: null },
  setRateLimited: () => {},
  clearRateLimit: () => {},
  checkEndpointLimit: () => true,
});

export const useRateLimit = () => useContext(RateLimitContext);

// =============================================================================
// RATE LIMIT PROVIDER
// =============================================================================

interface RateLimitProviderProps {
  children: ReactNode;
}

export function RateLimitProvider({ children }: RateLimitProviderProps) {
  const [rateLimitState, setRateLimitState] = useState<RateLimitState>({
    isLimited: false,
    resetTime: null,
    endpoint: null,
  });

  const setRateLimited = useCallback((endpoint: string, resetInMs: number) => {
    setRateLimitState({
      isLimited: true,
      resetTime: Date.now() + resetInMs,
      endpoint,
    });
  }, []);

  const clearRateLimit = useCallback(() => {
    setRateLimitState({
      isLimited: false,
      resetTime: null,
      endpoint: null,
    });
  }, []);

  const checkEndpointLimit = useCallback((
    endpoint: string,
    maxRequests: number = 10,
    windowMs: number = 60000
  ): boolean => {
    const result = checkRateLimit(endpoint, maxRequests, windowMs);
    
    if (!result.allowed) {
      setRateLimited(endpoint, result.resetIn);
    }
    
    return result.allowed;
  }, [setRateLimited]);

  // Auto-clear rate limit when time expires
  useEffect(() => {
    if (!rateLimitState.isLimited || !rateLimitState.resetTime) return;

    const timeout = setTimeout(() => {
      if (rateLimitState.endpoint) {
        resetRateLimit(rateLimitState.endpoint);
      }
      clearRateLimit();
    }, rateLimitState.resetTime - Date.now());

    return () => clearTimeout(timeout);
  }, [rateLimitState, clearRateLimit]);

  return (
    <RateLimitContext.Provider
      value={{
        rateLimitState,
        setRateLimited,
        clearRateLimit,
        checkEndpointLimit,
      }}
    >
      {children}
      {rateLimitState.isLimited && rateLimitState.resetTime && (
        <RateLimitModal
          resetTime={rateLimitState.resetTime}
          endpoint={rateLimitState.endpoint}
          onDismiss={clearRateLimit}
        />
      )}
    </RateLimitContext.Provider>
  );
}

// =============================================================================
// RATE LIMIT MODAL
// =============================================================================

interface RateLimitModalProps {
  resetTime: number;
  endpoint: string | null;
  onDismiss: () => void;
}

function RateLimitModal({ resetTime, endpoint, onDismiss }: RateLimitModalProps) {
  const [timeRemaining, setTimeRemaining] = useState(Math.max(0, resetTime - Date.now()));

  useEffect(() => {
    const interval = setInterval(() => {
      const remaining = Math.max(0, resetTime - Date.now());
      setTimeRemaining(remaining);
      
      if (remaining <= 0) {
        clearInterval(interval);
      }
    }, 1000);

    return () => clearInterval(interval);
  }, [resetTime]);

  const seconds = Math.ceil(timeRemaining / 1000);
  const minutes = Math.floor(seconds / 60);
  const remainingSeconds = seconds % 60;

  return (
    <div role="alertdialog" aria-modal="true" aria-labelledby="rate-limit-title" className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6 mx-4">
        <div className="flex items-center justify-between mb-4">
          <div className="flex items-center gap-3">
            <div className="h-10 w-10 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
              <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400" aria-hidden="true" />
            </div>
            <div>
              <h2 id="rate-limit-title" className="text-lg font-semibold">Too Many Requests</h2>
              <p className="text-sm text-muted-foreground">
                Please wait before trying again
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" onClick={onDismiss} aria-label="Dismiss">
            <X className="h-4 w-4" aria-hidden="true" />
          </Button>
        </div>

        <div className="text-center py-8">
          <Clock className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
          <div className="text-4xl font-mono font-bold text-foreground">
            {minutes > 0 ? (
              <>
                {String(minutes).padStart(2, '0')}:{String(remainingSeconds).padStart(2, '0')}
              </>
            ) : (
              <>{seconds}s</>
            )}
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            {timeRemaining > 0
              ? 'Time until you can try again'
              : 'You can try again now'}
          </p>
        </div>

        {endpoint && (
          <p className="text-xs text-muted-foreground text-center mb-4">
            Rate limited endpoint: <code className="bg-muted px-1 rounded">{endpoint}</code>
          </p>
        )}

        <div className="space-y-3">
          {timeRemaining <= 0 && (
            <Button className="w-full" onClick={onDismiss}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Try Again
            </Button>
          )}
          <p className="text-xs text-muted-foreground text-center">
            Rate limits help protect our service from abuse.
            Please try again in a moment.
          </p>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// RATE LIMIT BANNER
// =============================================================================

interface RateLimitBannerProps {
  className?: string;
}

export function RateLimitBanner({ className }: RateLimitBannerProps) {
  const { rateLimitState, clearRateLimit } = useRateLimit();
  const [timeRemaining, setTimeRemaining] = useState(0);

  useEffect(() => {
    if (!rateLimitState.isLimited || !rateLimitState.resetTime) {
      setTimeRemaining(0);
      return;
    }

    const updateTime = () => {
      const remaining = Math.max(0, (rateLimitState.resetTime || 0) - Date.now());
      setTimeRemaining(remaining);
    };

    updateTime();
    const interval = setInterval(updateTime, 1000);

    return () => clearInterval(interval);
  }, [rateLimitState]);

  if (!rateLimitState.isLimited || timeRemaining <= 0) return null;

  const seconds = Math.ceil(timeRemaining / 1000);

  return (
    <div
      className={cn(
        'bg-yellow-50 dark:bg-yellow-900/20 border border-yellow-200 dark:border-yellow-800 rounded-lg p-3',
        className
      )}
    >
      <div className="flex items-center gap-3">
        <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 shrink-0" />
        <div className="flex-1">
          <p className="text-sm font-medium text-yellow-700 dark:text-yellow-300">
            Rate limited - please wait {seconds} seconds
          </p>
        </div>
        <Button
          variant="ghost"
          size="sm"
          className="text-yellow-700 dark:text-yellow-300"
          onClick={clearRateLimit}
        >
          Dismiss
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// RATE LIMIT INDICATOR
// =============================================================================

interface RateLimitIndicatorProps {
  endpoint: string;
  maxRequests: number;
  windowMs: number;
  className?: string;
}

export function RateLimitIndicator({
  endpoint,
  maxRequests,
  windowMs,
  className,
}: RateLimitIndicatorProps) {
  const [usage, setUsage] = useState({ remaining: maxRequests, resetIn: 0 });

  const checkUsage = useCallback(() => {
    // Don't actually count this as a request, just check status
    const result = checkRateLimit(endpoint + '_check', maxRequests * 10, windowMs);
    // This is approximate since we're checking a different key
    setUsage({ remaining: result.remaining, resetIn: result.resetIn });
  }, [endpoint, maxRequests, windowMs]);

  useEffect(() => {
    checkUsage();
    const interval = setInterval(checkUsage, 5000);
    return () => clearInterval(interval);
  }, [checkUsage]);

  const usagePercent = ((maxRequests - usage.remaining) / maxRequests) * 100;

  return (
    <div className={cn('flex items-center gap-2', className)}>
      <div className="flex items-center gap-1 text-xs text-muted-foreground">
        <Shield className="h-3 w-3" />
        <span>
          {usage.remaining}/{maxRequests} requests
        </span>
      </div>
      <div className="w-20 h-1.5 bg-muted rounded-full overflow-hidden">
        <div
          className={cn(
            'h-full transition-all',
            usagePercent < 50 && 'bg-green-500',
            usagePercent >= 50 && usagePercent < 80 && 'bg-yellow-500',
            usagePercent >= 80 && 'bg-red-500'
          )}
          style={{ width: `${usagePercent}%` }}
        />
      </div>
    </div>
  );
}
