'use client';

/**
 * Session Manager Component
 * 
 * Handles session timeout, auto-logout, and activity tracking.
 * Shows warning before session expires and allows extension.
 */

import { useEffect, useState, useCallback, useRef, createContext, useContext, ReactNode } from 'react';
import { useRouter } from 'next/navigation';
import { Clock, AlertTriangle, RefreshCw } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useAuthStore } from '@/store/auth';
import { api } from '@/lib/api';

// =============================================================================
// CONFIGURATION
// =============================================================================

const SESSION_CONFIG = {
  // Session timeout in milliseconds (30 minutes)
  TIMEOUT_MS: 30 * 60 * 1000,
  // Warning shown before timeout (5 minutes before)
  WARNING_BEFORE_MS: 5 * 60 * 1000,
  // Check interval (every 30 seconds)
  CHECK_INTERVAL_MS: 30 * 1000,
  // Events that reset the activity timer
  ACTIVITY_EVENTS: ['mousedown', 'keydown', 'scroll', 'touchstart', 'mousemove'],
  // Debounce activity updates (1 second)
  ACTIVITY_DEBOUNCE_MS: 1000,
  // Storage key for last activity
  STORAGE_KEY: 'last_activity_time',
};

// =============================================================================
// SESSION CONTEXT
// =============================================================================

interface SessionContextType {
  lastActivity: number;
  timeUntilTimeout: number;
  isWarningVisible: boolean;
  extendSession: () => void;
  logout: () => void;
}

const SessionContext = createContext<SessionContextType>({
  lastActivity: Date.now(),
  timeUntilTimeout: SESSION_CONFIG.TIMEOUT_MS,
  isWarningVisible: false,
  extendSession: () => {},
  logout: () => {},
});

export const useSession = () => useContext(SessionContext);

// =============================================================================
// SESSION PROVIDER
// =============================================================================

interface SessionProviderProps {
  children: ReactNode;
  enabled?: boolean;
  timeoutMs?: number;
  warningBeforeMs?: number;
}

export function SessionProvider({
  children,
  enabled = true,
  timeoutMs = SESSION_CONFIG.TIMEOUT_MS,
  warningBeforeMs = SESSION_CONFIG.WARNING_BEFORE_MS,
}: SessionProviderProps) {
  const router = useRouter();
  const { isAuthenticated, logout: authLogout } = useAuthStore();
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [timeUntilTimeout, setTimeUntilTimeout] = useState(timeoutMs);
  const [isWarningVisible, setIsWarningVisible] = useState(false);
  const activityTimeoutRef = useRef<NodeJS.Timeout | null>(null);

  // Update last activity time
  const updateActivity = useCallback(() => {
    const now = Date.now();
    setLastActivity(now);
    setIsWarningVisible(false);
    
    // Persist to localStorage for cross-tab sync
    try {
      localStorage.setItem(SESSION_CONFIG.STORAGE_KEY, now.toString());
    } catch (e) {
      // Ignore localStorage errors
    }
  }, []);

  // Debounced activity handler
  const handleActivity = useCallback(() => {
    if (activityTimeoutRef.current) {
      clearTimeout(activityTimeoutRef.current);
    }
    
    activityTimeoutRef.current = setTimeout(() => {
      updateActivity();
    }, SESSION_CONFIG.ACTIVITY_DEBOUNCE_MS);
  }, [updateActivity]);

  // Logout handler
  const handleLogout = useCallback(() => {
    authLogout();
    router.push('/login?reason=session_expired');
  }, [authLogout, router]);

  // Extend session
  const extendSession = useCallback(async () => {
    updateActivity();
    
    // Optionally refresh the token
    try {
      const refreshToken = localStorage.getItem('refresh_token');
      if (refreshToken) {
        const response = await api.post('/auth/refresh', {
          refresh_token: refreshToken,
        });
        localStorage.setItem('access_token', response.data.access_token);
        if (response.data.refresh_token) {
          localStorage.setItem('refresh_token', response.data.refresh_token);
        }
      }
    } catch (error) {
      console.error('Failed to refresh token:', error);
    }
  }, [updateActivity]);

  // Set up activity listeners
  useEffect(() => {
    if (!enabled || !isAuthenticated) return;

    // Add event listeners
    SESSION_CONFIG.ACTIVITY_EVENTS.forEach((event) => {
      window.addEventListener(event, handleActivity, { passive: true });
    });

    // Sync across tabs
    const handleStorage = (e: StorageEvent) => {
      if (e.key === SESSION_CONFIG.STORAGE_KEY && e.newValue) {
        const newTime = parseInt(e.newValue, 10);
        if (!isNaN(newTime)) {
          setLastActivity(newTime);
          setIsWarningVisible(false);
        }
      }
    };
    window.addEventListener('storage', handleStorage);

    // Load last activity from storage
    try {
      const stored = localStorage.getItem(SESSION_CONFIG.STORAGE_KEY);
      if (stored) {
        const storedTime = parseInt(stored, 10);
        if (!isNaN(storedTime)) {
          setLastActivity(storedTime);
        }
      }
    } catch (e) {
      // Ignore
    }

    return () => {
      SESSION_CONFIG.ACTIVITY_EVENTS.forEach((event) => {
        window.removeEventListener(event, handleActivity);
      });
      window.removeEventListener('storage', handleStorage);
      if (activityTimeoutRef.current) {
        clearTimeout(activityTimeoutRef.current);
      }
    };
  }, [enabled, isAuthenticated, handleActivity]);

  // Check session timeout
  useEffect(() => {
    if (!enabled || !isAuthenticated) return;

    const checkSession = () => {
      const now = Date.now();
      const timeSinceActivity = now - lastActivity;
      const remaining = timeoutMs - timeSinceActivity;

      setTimeUntilTimeout(Math.max(0, remaining));

      if (remaining <= 0) {
        // Session expired
        handleLogout();
      } else if (remaining <= warningBeforeMs && !isWarningVisible) {
        // Show warning
        setIsWarningVisible(true);
      }
    };

    // Initial check
    checkSession();

    // Set up interval
    const interval = setInterval(checkSession, SESSION_CONFIG.CHECK_INTERVAL_MS);

    return () => clearInterval(interval);
  }, [enabled, isAuthenticated, lastActivity, timeoutMs, warningBeforeMs, isWarningVisible, handleLogout]);

  return (
    <SessionContext.Provider
      value={{
        lastActivity,
        timeUntilTimeout,
        isWarningVisible,
        extendSession,
        logout: handleLogout,
      }}
    >
      {children}
      {isWarningVisible && isAuthenticated && (
        <SessionWarningModal
          timeRemaining={timeUntilTimeout}
          onExtend={extendSession}
          onLogout={handleLogout}
        />
      )}
    </SessionContext.Provider>
  );
}

// =============================================================================
// SESSION WARNING MODAL
// =============================================================================

interface SessionWarningModalProps {
  timeRemaining: number;
  onExtend: () => void;
  onLogout: () => void;
}

function SessionWarningModal({ timeRemaining, onExtend, onLogout }: SessionWarningModalProps) {
  const minutes = Math.floor(timeRemaining / 60000);
  const seconds = Math.floor((timeRemaining % 60000) / 1000);

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6 mx-4">
        <div className="flex items-center gap-4 mb-4">
          <div className="h-12 w-12 rounded-full bg-yellow-100 dark:bg-yellow-900/30 flex items-center justify-center">
            <Clock className="h-6 w-6 text-yellow-600 dark:text-yellow-400" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Session Expiring</h2>
            <p className="text-sm text-muted-foreground">
              Your session will expire due to inactivity
            </p>
          </div>
        </div>

        <div className="text-center py-6">
          <div className="text-4xl font-mono font-bold text-yellow-600 dark:text-yellow-400">
            {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Time remaining before automatic logout
          </p>
        </div>

        <div className="flex gap-3">
          <Button onClick={onExtend} className="flex-1">
            <RefreshCw className="mr-2 h-4 w-4" />
            Stay Logged In
          </Button>
          <Button variant="outline" onClick={onLogout}>
            Logout Now
          </Button>
        </div>
      </div>
    </div>
  );
}

// =============================================================================
// SESSION TIMEOUT INDICATOR
// =============================================================================

interface SessionIndicatorProps {
  className?: string;
  showAlways?: boolean;
}

export function SessionIndicator({ className, showAlways = false }: SessionIndicatorProps) {
  const { timeUntilTimeout, isWarningVisible } = useSession();
  const { isAuthenticated } = useAuthStore();

  if (!isAuthenticated) return null;
  if (!showAlways && !isWarningVisible) return null;

  const minutes = Math.floor(timeUntilTimeout / 60000);
  const seconds = Math.floor((timeUntilTimeout % 60000) / 1000);

  return (
    <div
      className={`flex items-center gap-2 text-sm ${
        isWarningVisible ? 'text-yellow-600 dark:text-yellow-400' : 'text-muted-foreground'
      } ${className}`}
    >
      <Clock className="h-4 w-4" />
      <span className="font-mono">
        {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
      </span>
    </div>
  );
}
