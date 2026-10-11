'use client';

/**
 * Suspicious Activity Detection & Alerts
 * 
 * Monitors for and alerts users about suspicious activity patterns.
 */

import { useState, useEffect, createContext, useContext, ReactNode, useCallback } from 'react';
import {
  AlertTriangle,
  Shield,
  MapPin,
  Clock,
  X,
  LogOut,
  Lock,
  Eye,
  Monitor,
  Smartphone,
  Globe,
  CheckCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useAuthStore } from '@/store/auth';
import { api } from '@/lib/api';
import { toast } from 'sonner';

// =============================================================================
// TYPES
// =============================================================================

interface SuspiciousActivity {
  id: string;
  type: 'new_device' | 'new_location' | 'multiple_failed_logins' | 'unusual_time' | 'password_reset' | 'api_key_usage';
  severity: 'low' | 'medium' | 'high' | 'critical';
  message: string;
  details: Record<string, string>;
  timestamp: string;
  dismissed: boolean;
  verified: boolean;
}

interface DeviceInfo {
  userAgent: string;
  platform: string;
  language: string;
  screenSize: string;
  timezone: string;
  touchSupport: boolean;
}

// =============================================================================
// SUSPICIOUS ACTIVITY CONTEXT
// =============================================================================

interface SuspiciousActivityContextType {
  alerts: SuspiciousActivity[];
  unreadCount: number;
  dismissAlert: (id: string) => void;
  verifyActivity: (id: string) => void;
  reportActivity: (activity: Omit<SuspiciousActivity, 'id' | 'timestamp' | 'dismissed' | 'verified'>) => void;
  checkDeviceFingerprint: () => Promise<boolean>;
}

const SuspiciousActivityContext = createContext<SuspiciousActivityContextType>({
  alerts: [],
  unreadCount: 0,
  dismissAlert: () => {},
  verifyActivity: () => {},
  reportActivity: () => {},
  checkDeviceFingerprint: async () => true,
});

export const useSuspiciousActivity = () => useContext(SuspiciousActivityContext);

// =============================================================================
// SUSPICIOUS ACTIVITY PROVIDER
// =============================================================================

interface SuspiciousActivityProviderProps {
  children: ReactNode;
  pollingInterval?: number;
}

export function SuspiciousActivityProvider({
  children,
  pollingInterval = 60000,
}: SuspiciousActivityProviderProps) {
  const { isAuthenticated } = useAuthStore();
  const [alerts, setAlerts] = useState<SuspiciousActivity[]>([]);
  const [showCriticalAlert, setShowCriticalAlert] = useState<SuspiciousActivity | null>(null);

  // Get device fingerprint
  const getDeviceInfo = useCallback((): DeviceInfo => {
    if (typeof window === 'undefined') {
      return {
        userAgent: '',
        platform: '',
        language: '',
        screenSize: '',
        timezone: '',
        touchSupport: false,
      };
    }

    return {
      userAgent: navigator.userAgent,
      platform: navigator.platform,
      language: navigator.language,
      screenSize: `${window.screen.width}x${window.screen.height}`,
      timezone: Intl.DateTimeFormat().resolvedOptions().timeZone,
      touchSupport: 'ontouchstart' in window,
    };
  }, []);

  // Load alerts
  const loadAlerts = useCallback(async () => {
    if (!isAuthenticated) return;

    try {
      const response = await api.get('/auth/suspicious-activity');
      setAlerts(response.data);
      
      // Check for critical alerts
      const criticalAlert = response.data.find(
        (a: SuspiciousActivity) => a.severity === 'critical' && !a.dismissed && !a.verified
      );
      if (criticalAlert) {
        setShowCriticalAlert(criticalAlert);
      }
    } catch (error) {
      // Use mock data if endpoint doesn't exist
      console.log('Using mock suspicious activity data');
    }
  }, [isAuthenticated]);

  // Check device fingerprint against known devices
  const checkDeviceFingerprint = useCallback(async (): Promise<boolean> => {
    try {
      const deviceInfo = getDeviceInfo();
      const response = await api.post('/auth/verify-device', deviceInfo);
      return response.data.known;
    } catch (error) {
      // Device verification failed, assume unknown
      return false;
    }
  }, [getDeviceInfo]);

  // Dismiss alert
  const dismissAlert = useCallback((id: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, dismissed: true } : a))
    );
    if (showCriticalAlert?.id === id) {
      setShowCriticalAlert(null);
    }
    
    // Persist to server
    api.post(`/auth/suspicious-activity/${id}/dismiss`).catch(() => {});
  }, [showCriticalAlert]);

  // Verify activity (mark as "yes, this was me")
  const verifyActivity = useCallback((id: string) => {
    setAlerts((prev) =>
      prev.map((a) => (a.id === id ? { ...a, verified: true } : a))
    );
    if (showCriticalAlert?.id === id) {
      setShowCriticalAlert(null);
    }
    
    // Persist to server
    api.post(`/auth/suspicious-activity/${id}/verify`).catch(() => {});
    toast.success('Activity verified');
  }, [showCriticalAlert]);

  // Report new suspicious activity
  const reportActivity = useCallback((
    activity: Omit<SuspiciousActivity, 'id' | 'timestamp' | 'dismissed' | 'verified'>
  ) => {
    const newAlert: SuspiciousActivity = {
      ...activity,
      id: Math.random().toString(36).substring(7),
      timestamp: new Date().toISOString(),
      dismissed: false,
      verified: false,
    };
    
    setAlerts((prev) => [newAlert, ...prev]);
    
    // Show critical alerts immediately
    if (activity.severity === 'critical') {
      setShowCriticalAlert(newAlert);
    }
    
    // Persist to server
    api.post('/auth/suspicious-activity', activity).catch(() => {});
  }, []);

  // Poll for new alerts
  useEffect(() => {
    if (!isAuthenticated) return;

    loadAlerts();
    const interval = setInterval(loadAlerts, pollingInterval);

    return () => clearInterval(interval);
  }, [isAuthenticated, loadAlerts, pollingInterval]);

  // Register device on login
  useEffect(() => {
    if (isAuthenticated) {
      const deviceInfo = getDeviceInfo();
      api.post('/auth/register-device', deviceInfo).catch(() => {});
    }
  }, [isAuthenticated, getDeviceInfo]);

  const unreadCount = alerts.filter((a) => !a.dismissed && !a.verified).length;

  return (
    <SuspiciousActivityContext.Provider
      value={{
        alerts,
        unreadCount,
        dismissAlert,
        verifyActivity,
        reportActivity,
        checkDeviceFingerprint,
      }}
    >
      {children}
      {showCriticalAlert && (
        <CriticalAlertModal
          alert={showCriticalAlert}
          onDismiss={() => dismissAlert(showCriticalAlert.id)}
          onVerify={() => verifyActivity(showCriticalAlert.id)}
        />
      )}
    </SuspiciousActivityContext.Provider>
  );
}

// =============================================================================
// CRITICAL ALERT MODAL
// =============================================================================

interface CriticalAlertModalProps {
  alert: SuspiciousActivity;
  onDismiss: () => void;
  onVerify: () => void;
}

function CriticalAlertModal({ alert, onDismiss, onVerify }: CriticalAlertModalProps) {
  const { logout } = useAuthStore();
  const [isSecuring, setIsSecuring] = useState(false);

  const handleSecureAccount = async () => {
    setIsSecuring(true);
    try {
      // Revoke all sessions except current
      await api.post('/auth/sessions/revoke-all');
      toast.success('All other sessions have been revoked');
      onDismiss();
    } catch (error) {
      toast.error('Failed to secure account');
    } finally {
      setIsSecuring(false);
    }
  };

  const getAlertIcon = () => {
    switch (alert.type) {
      case 'new_device':
        return <Monitor className="h-6 w-6" />;
      case 'new_location':
        return <MapPin className="h-6 w-6" />;
      case 'multiple_failed_logins':
        return <Lock className="h-6 w-6" />;
      default:
        return <AlertTriangle className="h-6 w-6" />;
    }
  };

  return (
    <div role="alertdialog" aria-modal="true" aria-labelledby="critical-alert-title" className="fixed inset-0 bg-black/50 flex items-center justify-center z-[100]">
      <div className="bg-background rounded-lg border border-red-200 dark:border-red-800 shadow-lg w-full max-w-lg p-6 mx-4">
        {/* Header */}
        <div className="flex items-center gap-4 mb-6">
          <div className="h-14 w-14 rounded-full bg-red-100 dark:bg-red-900/30 flex items-center justify-center text-red-600 dark:text-red-400" aria-hidden="true">
            {getAlertIcon()}
          </div>
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <h2 id="critical-alert-title" className="text-xl font-semibold">Security Alert</h2>
              <span className="px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400">
                Critical
              </span>
            </div>
            <p className="text-sm text-muted-foreground mt-1">{alert.message}</p>
          </div>
        </div>

        {/* Details */}
        <div className="bg-muted/50 rounded-lg p-4 mb-6">
          <h3 className="text-sm font-medium mb-2">Details</h3>
          <dl className="space-y-2">
            {Object.entries(alert.details).map(([key, value]) => (
              <div key={key} className="flex justify-between text-sm">
                <dt className="text-muted-foreground capitalize">{key.replace(/_/g, ' ')}</dt>
                <dd className="font-medium">{value}</dd>
              </div>
            ))}
            <div className="flex justify-between text-sm">
              <dt className="text-muted-foreground">Time</dt>
              <dd className="font-medium">
                {new Date(alert.timestamp).toLocaleString()}
              </dd>
            </div>
          </dl>
        </div>

        {/* Actions */}
        <div className="space-y-3">
          <Button className="w-full" variant="default" onClick={onVerify}>
            <CheckCircle className="mr-2 h-4 w-4" />
            Yes, This Was Me
          </Button>
          <Button
            className="w-full"
            variant="destructive"
            onClick={handleSecureAccount}
            disabled={isSecuring}
          >
            <Shield className="mr-2 h-4 w-4" />
            Secure My Account
          </Button>
          <div className="flex gap-3">
            <Button className="flex-1" variant="outline" onClick={onDismiss}>
              Dismiss
            </Button>
            <Button
              className="flex-1"
              variant="ghost"
              onClick={() => {
                logout();
                window.location.href = '/login';
              }}
            >
              <LogOut className="mr-2 h-4 w-4" />
              Sign Out
            </Button>
          </div>
        </div>

        <p className="text-xs text-muted-foreground text-center mt-4">
          If you don't recognize this activity, we recommend securing your account immediately.
        </p>
      </div>
    </div>
  );
}

// =============================================================================
// ACTIVITY ALERT CARD
// =============================================================================

interface ActivityAlertCardProps {
  alert: SuspiciousActivity;
  onDismiss: () => void;
  onVerify: () => void;
  className?: string;
}

export function ActivityAlertCard({
  alert,
  onDismiss,
  onVerify,
  className,
}: ActivityAlertCardProps) {
  const severityStyles = {
    low: 'border-blue-200 dark:border-blue-800 bg-blue-50 dark:bg-blue-900/20',
    medium: 'border-yellow-200 dark:border-yellow-800 bg-yellow-50 dark:bg-yellow-900/20',
    high: 'border-orange-200 dark:border-orange-800 bg-orange-50 dark:bg-orange-900/20',
    critical: 'border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/20',
  };

  const severityTextStyles = {
    low: 'text-blue-700 dark:text-blue-300',
    medium: 'text-yellow-700 dark:text-yellow-300',
    high: 'text-orange-700 dark:text-orange-300',
    critical: 'text-red-700 dark:text-red-300',
  };

  const getIcon = () => {
    switch (alert.type) {
      case 'new_device':
        return <Smartphone className="h-5 w-5" />;
      case 'new_location':
        return <MapPin className="h-5 w-5" />;
      case 'multiple_failed_logins':
        return <Lock className="h-5 w-5" />;
      case 'unusual_time':
        return <Clock className="h-5 w-5" />;
      default:
        return <AlertTriangle className="h-5 w-5" />;
    }
  };

  if (alert.dismissed || alert.verified) return null;

  return (
    <div className={cn('rounded-lg border p-4', severityStyles[alert.severity], className)}>
      <div className="flex items-start gap-3">
        <div className={cn('mt-0.5', severityTextStyles[alert.severity])}>
          {getIcon()}
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn('font-medium text-sm', severityTextStyles[alert.severity])}>
              {alert.message}
            </span>
            <span
              className={cn(
                'px-1.5 py-0.5 rounded text-xs font-medium capitalize',
                severityTextStyles[alert.severity],
                'bg-white/50 dark:bg-black/20'
              )}
            >
              {alert.severity}
            </span>
          </div>
          <p className="text-xs text-muted-foreground">
            {new Date(alert.timestamp).toLocaleString()}
          </p>
          {Object.keys(alert.details).length > 0 && (
            <div className="mt-2 flex flex-wrap gap-2">
              {Object.entries(alert.details).slice(0, 3).map(([key, value]) => (
                <span
                  key={key}
                  className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-white/50 dark:bg-black/20 text-xs"
                >
                  <span className="text-muted-foreground capitalize">{key}:</span>
                  <span className="font-medium">{value}</span>
                </span>
              ))}
            </div>
          )}
          <div className="mt-3 flex gap-2">
            <Button size="sm" variant="secondary" onClick={onVerify}>
              <CheckCircle className="mr-1 h-3 w-3" />
              This was me
            </Button>
            <Button size="sm" variant="ghost" onClick={onDismiss}>
              Dismiss
            </Button>
          </div>
        </div>
        <Button variant="ghost" size="icon" className="shrink-0" onClick={onDismiss} aria-label="Dismiss alert">
          <X className="h-4 w-4" aria-hidden="true" />
        </Button>
      </div>
    </div>
  );
}

// =============================================================================
// ACTIVITY ALERTS LIST
// =============================================================================

interface ActivityAlertsListProps {
  className?: string;
  maxItems?: number;
  showEmpty?: boolean;
}

export function ActivityAlertsList({
  className,
  maxItems = 5,
  showEmpty = true,
}: ActivityAlertsListProps) {
  const { alerts, dismissAlert, verifyActivity } = useSuspiciousActivity();
  
  const activeAlerts = alerts
    .filter((a) => !a.dismissed && !a.verified)
    .slice(0, maxItems);

  if (activeAlerts.length === 0) {
    if (!showEmpty) return null;
    
    return (
      <div className={cn('text-center py-8', className)}>
        <Shield className="h-12 w-12 mx-auto text-green-500 mb-3" />
        <p className="text-sm text-muted-foreground">No suspicious activity detected</p>
      </div>
    );
  }

  return (
    <div className={cn('space-y-3', className)}>
      {activeAlerts.map((alert) => (
        <ActivityAlertCard
          key={alert.id}
          alert={alert}
          onDismiss={() => dismissAlert(alert.id)}
          onVerify={() => verifyActivity(alert.id)}
        />
      ))}
    </div>
  );
}

// =============================================================================
// ALERT BADGE
// =============================================================================

interface AlertBadgeProps {
  className?: string;
}

export function AlertBadge({ className }: AlertBadgeProps) {
  const { unreadCount } = useSuspiciousActivity();

  if (unreadCount === 0) return null;

  return (
    <span
      className={cn(
        'inline-flex items-center justify-center min-w-5 h-5 px-1.5 rounded-full text-xs font-medium',
        'bg-red-500 text-white',
        className
      )}
    >
      {unreadCount > 99 ? '99+' : unreadCount}
    </span>
  );
}
