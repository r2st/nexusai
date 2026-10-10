'use client';

/**
 * Security Settings Page
 * 
 * Centralized security controls including:
 * - Password management
 * - Two-factor authentication
 * - Active sessions / device management
 * - Login history
 * - Security alerts
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Shield,
  Key,
  Smartphone,
  Monitor,
  Globe,
  Clock,
  AlertTriangle,
  LogOut,
  RefreshCw,
  Loader2,
  Check,
  X,
  ChevronRight,
  MapPin,
  Trash2,
  Bell,
  Lock,
  Eye,
  EyeOff,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { api } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';
import { TwoFactorSetup, TwoFactorStatus } from '@/components/security/two-factor-auth';
import { PasswordInput, PasswordRequirements, DEFAULT_REQUIREMENTS, calculatePasswordStrength } from '@/components/security/password-strength';

// =============================================================================
// TYPES
// =============================================================================

interface Session {
  id: string;
  device_type: 'desktop' | 'mobile' | 'tablet';
  browser: string;
  os: string;
  ip_address: string;
  location: string;
  last_active: string;
  created_at: string;
  is_current: boolean;
}

interface LoginHistoryEntry {
  id: string;
  timestamp: string;
  ip_address: string;
  location: string;
  device: string;
  browser: string;
  status: 'success' | 'failed' | 'blocked';
  failure_reason?: string;
}

interface SecurityAlert {
  id: string;
  type: 'new_device' | 'password_changed' | 'suspicious_login' | '2fa_disabled' | 'api_key_created';
  message: string;
  timestamp: string;
  read: boolean;
}

// =============================================================================
// MAIN COMPONENT
// =============================================================================

export default function SecuritySettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [activeSection, setActiveSection] = useState<string>('password');

  // State
  const [isLoading, setIsLoading] = useState(false);
  const [sessions, setSessions] = useState<Session[]>([]);
  const [loginHistory, setLoginHistory] = useState<LoginHistoryEntry[]>([]);
  const [securityAlerts, setSecurityAlerts] = useState<SecurityAlert[]>([]);
  const [show2FASetup, setShow2FASetup] = useState(false);

  // Password change state
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isChangingPassword, setIsChangingPassword] = useState(false);

  // Notification settings
  const [notifyNewDevice, setNotifyNewDevice] = useState(true);
  const [notifySuspiciousLogin, setNotifySuspiciousLogin] = useState(true);
  const [notifyPasswordChange, setNotifyPasswordChange] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (isAuthenticated) {
      loadSecurityData();
    }
  }, [isAuthenticated]);

  const loadSecurityData = async () => {
    setIsLoading(true);
    try {
      // Load sessions, login history, and alerts in parallel
      const [sessionsRes, historyRes, alertsRes] = await Promise.allSettled([
        api.get('/auth/sessions'),
        api.get('/auth/login-history'),
        api.get('/auth/security-alerts'),
      ]);

      if (sessionsRes.status === 'fulfilled') {
        setSessions(sessionsRes.value.data);
      } else {
        // Mock data for demo
        setSessions([
          {
            id: '1',
            device_type: 'desktop',
            browser: 'Chrome 120',
            os: 'macOS 14.2',
            ip_address: '192.168.1.100',
            location: 'San Francisco, CA',
            last_active: new Date().toISOString(),
            created_at: new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString(),
            is_current: true,
          },
          {
            id: '2',
            device_type: 'mobile',
            browser: 'Safari',
            os: 'iOS 17.2',
            ip_address: '192.168.1.101',
            location: 'San Francisco, CA',
            last_active: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(),
            created_at: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000).toISOString(),
            is_current: false,
          },
        ]);
      }

      if (historyRes.status === 'fulfilled') {
        setLoginHistory(historyRes.value.data);
      } else {
        // Mock data
        setLoginHistory([
          {
            id: '1',
            timestamp: new Date().toISOString(),
            ip_address: '192.168.1.100',
            location: 'San Francisco, CA',
            device: 'MacBook Pro',
            browser: 'Chrome 120',
            status: 'success',
          },
          {
            id: '2',
            timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
            ip_address: '203.0.113.42',
            location: 'Unknown',
            device: 'Unknown',
            browser: 'Unknown',
            status: 'blocked',
            failure_reason: 'Suspicious IP address',
          },
          {
            id: '3',
            timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            ip_address: '192.168.1.101',
            location: 'San Francisco, CA',
            device: 'iPhone 15',
            browser: 'Safari',
            status: 'success',
          },
        ]);
      }

      if (alertsRes.status === 'fulfilled') {
        setSecurityAlerts(alertsRes.value.data);
      } else {
        // Mock data
        setSecurityAlerts([
          {
            id: '1',
            type: 'new_device',
            message: 'New device signed in: iPhone 15 from San Francisco, CA',
            timestamp: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
            read: true,
          },
          {
            id: '2',
            type: 'suspicious_login',
            message: 'Blocked login attempt from unknown location',
            timestamp: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
            read: false,
          },
        ]);
      }
    } catch (error) {
      console.error('Failed to load security data:', error);
    } finally {
      setIsLoading(false);
    }
  };

  const handleChangePassword = async () => {
    if (!currentPassword || !newPassword || !confirmPassword) {
      toast.error('Please fill in all fields');
      return;
    }

    if (newPassword !== confirmPassword) {
      toast.error('New passwords do not match');
      return;
    }

    const strength = calculatePasswordStrength(newPassword);
    if (strength.score < 2) {
      toast.error('Password is too weak');
      return;
    }

    const allRequirementsMet = DEFAULT_REQUIREMENTS.every((req) => req.test(newPassword));
    if (!allRequirementsMet) {
      toast.error('Password does not meet all requirements');
      return;
    }

    setIsChangingPassword(true);
    try {
      await api.post('/auth/change-password', {
        current_password: currentPassword,
        new_password: newPassword,
      });
      toast.success('Password changed successfully');
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (error: any) {
      toast.error(error.response?.data?.detail || 'Failed to change password');
    } finally {
      setIsChangingPassword(false);
    }
  };

  const handleRevokeSession = async (sessionId: string) => {
    if (!confirm('Are you sure you want to end this session?')) return;

    try {
      await api.delete(`/auth/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      toast.success('Session revoked');
    } catch (error) {
      toast.error('Failed to revoke session');
    }
  };

  const handleRevokeAllSessions = async () => {
    if (!confirm('This will log you out of all devices except this one. Continue?')) return;

    try {
      await api.post('/auth/sessions/revoke-all');
      setSessions((prev) => prev.filter((s) => s.is_current));
      toast.success('All other sessions have been revoked');
    } catch (error) {
      toast.error('Failed to revoke sessions');
    }
  };

  if (!isAuthenticated) return null;

  const sections = [
    { id: 'password', label: 'Password', icon: Key },
    { id: '2fa', label: 'Two-Factor Auth', icon: Smartphone },
    { id: 'sessions', label: 'Active Sessions', icon: Monitor },
    { id: 'history', label: 'Login History', icon: Clock },
    { id: 'alerts', label: 'Security Alerts', icon: Bell },
  ];

  const getDeviceIcon = (type: string) => {
    switch (type) {
      case 'mobile':
        return Smartphone;
      case 'tablet':
        return Monitor;
      default:
        return Monitor;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/settings" className="flex items-center gap-2">
              <Shield className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Security Settings</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadSecurityData}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col lg:flex-row gap-8">
          {/* Sidebar Navigation */}
          <aside className="w-full lg:w-64 shrink-0">
            <nav className="space-y-1">
              {sections.map((section) => {
                const Icon = section.icon;
                return (
                  <button
                    key={section.id}
                    onClick={() => setActiveSection(section.id)}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      activeSection === section.id
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {section.label}
                    {section.id === 'alerts' &&
                      securityAlerts.filter((a) => !a.read).length > 0 && (
                        <span className="ml-auto bg-destructive text-destructive-foreground text-xs px-1.5 py-0.5 rounded-full">
                          {securityAlerts.filter((a) => !a.read).length}
                        </span>
                      )}
                  </button>
                );
              })}
            </nav>

            <hr className="my-4" />

            <Link
              href="/settings"
              className="flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
            >
              <ChevronRight className="h-4 w-4 rotate-180" />
              Back to Settings
            </Link>
          </aside>

          {/* Main Content */}
          <div className="flex-1 max-w-3xl">
            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              </div>
            ) : (
              <>
                {/* Password Section */}
                {activeSection === 'password' && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold">Change Password</h2>
                      <p className="text-muted-foreground mt-1">
                        Update your password to keep your account secure
                      </p>
                    </div>

                    <div className="rounded-lg border p-6 space-y-4">
                      <div>
                        <label className="text-sm font-medium mb-1.5 block">
                          Current Password
                        </label>
                        <Input
                          type="password"
                          value={currentPassword}
                          onChange={(e) => setCurrentPassword(e.target.value)}
                          placeholder="Enter current password"
                        />
                      </div>

                      <div>
                        <label className="text-sm font-medium mb-1.5 block">
                          New Password
                        </label>
                        <PasswordInput
                          value={newPassword}
                          onChange={setNewPassword}
                          showStrength
                          showRequirements
                          placeholder="Enter new password"
                        />
                      </div>

                      <div>
                        <label className="text-sm font-medium mb-1.5 block">
                          Confirm New Password
                        </label>
                        <Input
                          type="password"
                          value={confirmPassword}
                          onChange={(e) => setConfirmPassword(e.target.value)}
                          placeholder="Confirm new password"
                        />
                        {confirmPassword && newPassword !== confirmPassword && (
                          <p className="text-sm text-destructive mt-1 flex items-center gap-1">
                            <X className="h-4 w-4" />
                            Passwords do not match
                          </p>
                        )}
                      </div>

                      <Button
                        onClick={handleChangePassword}
                        disabled={isChangingPassword}
                      >
                        {isChangingPassword ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : (
                          <Key className="mr-2 h-4 w-4" />
                        )}
                        Change Password
                      </Button>
                    </div>
                  </div>
                )}

                {/* 2FA Section */}
                {activeSection === '2fa' && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold">Two-Factor Authentication</h2>
                      <p className="text-muted-foreground mt-1">
                        Add an extra layer of security to your account
                      </p>
                    </div>

                    <TwoFactorStatus
                      onSetup={() => setShow2FASetup(true)}
                      onDisable={() => {
                        if (confirm('Are you sure you want to disable 2FA?')) {
                          api.post('/auth/2fa/disable').then(() => {
                            toast.success('2FA disabled');
                          });
                        }
                      }}
                      onRegenerateCodes={() => {
                        toast.info('Regenerating backup codes...');
                      }}
                    />
                  </div>
                )}

                {/* Active Sessions Section */}
                {activeSection === 'sessions' && (
                  <div className="space-y-6">
                    <div className="flex items-center justify-between">
                      <div>
                        <h2 className="text-2xl font-bold">Active Sessions</h2>
                        <p className="text-muted-foreground mt-1">
                          Manage devices that are logged into your account
                        </p>
                      </div>
                      <Button variant="outline" onClick={handleRevokeAllSessions}>
                        <LogOut className="mr-2 h-4 w-4" />
                        Sign Out All
                      </Button>
                    </div>

                    <div className="space-y-4">
                      {sessions.map((session) => {
                        const DeviceIcon = getDeviceIcon(session.device_type);
                        return (
                          <div
                            key={session.id}
                            className={cn(
                              'rounded-lg border p-4',
                              session.is_current && 'border-primary bg-primary/5'
                            )}
                          >
                            <div className="flex items-start justify-between">
                              <div className="flex items-start gap-4">
                                <div className="h-10 w-10 rounded-full bg-muted flex items-center justify-center">
                                  <DeviceIcon className="h-5 w-5 text-muted-foreground" />
                                </div>
                                <div>
                                  <div className="flex items-center gap-2">
                                    <span className="font-medium">
                                      {session.browser} on {session.os}
                                    </span>
                                    {session.is_current && (
                                      <span className="text-xs bg-primary text-primary-foreground px-2 py-0.5 rounded-full">
                                        Current
                                      </span>
                                    )}
                                  </div>
                                  <div className="flex items-center gap-4 mt-1 text-sm text-muted-foreground">
                                    <span className="flex items-center gap-1">
                                      <MapPin className="h-3 w-3" />
                                      {session.location}
                                    </span>
                                    <span className="flex items-center gap-1">
                                      <Globe className="h-3 w-3" />
                                      {session.ip_address}
                                    </span>
                                  </div>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Last active {formatRelativeTime(session.last_active)}
                                  </p>
                                </div>
                              </div>
                              {!session.is_current && (
                                <Button
                                  variant="ghost"
                                  size="sm"
                                  className="text-destructive hover:text-destructive"
                                  onClick={() => handleRevokeSession(session.id)}
                                >
                                  <LogOut className="h-4 w-4" />
                                </Button>
                              )}
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                )}

                {/* Login History Section */}
                {activeSection === 'history' && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold">Login History</h2>
                      <p className="text-muted-foreground mt-1">
                        Recent login attempts to your account
                      </p>
                    </div>

                    <div className="rounded-lg border overflow-hidden">
                      <table className="w-full">
                        <thead className="bg-muted/50">
                          <tr>
                            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                              Time
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                              Device
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                              Location
                            </th>
                            <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground">
                              Status
                            </th>
                          </tr>
                        </thead>
                        <tbody className="divide-y">
                          {loginHistory.map((entry) => (
                            <tr key={entry.id} className="hover:bg-muted/50">
                              <td className="px-4 py-3 text-sm">
                                {formatRelativeTime(entry.timestamp)}
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <div>
                                  <p>{entry.device}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {entry.browser}
                                  </p>
                                </div>
                              </td>
                              <td className="px-4 py-3 text-sm">
                                <div>
                                  <p>{entry.location}</p>
                                  <p className="text-xs text-muted-foreground">
                                    {entry.ip_address}
                                  </p>
                                </div>
                              </td>
                              <td className="px-4 py-3">
                                <span
                                  className={cn(
                                    'inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium',
                                    entry.status === 'success' &&
                                      'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400',
                                    entry.status === 'failed' &&
                                      'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400',
                                    entry.status === 'blocked' &&
                                      'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
                                  )}
                                >
                                  {entry.status === 'success' && <Check className="h-3 w-3" />}
                                  {entry.status === 'failed' && (
                                    <AlertTriangle className="h-3 w-3" />
                                  )}
                                  {entry.status === 'blocked' && <X className="h-3 w-3" />}
                                  {entry.status}
                                </span>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    </div>
                  </div>
                )}

                {/* Security Alerts Section */}
                {activeSection === 'alerts' && (
                  <div className="space-y-6">
                    <div>
                      <h2 className="text-2xl font-bold">Security Alerts</h2>
                      <p className="text-muted-foreground mt-1">
                        Notifications about security events on your account
                      </p>
                    </div>

                    {/* Notification Settings */}
                    <div className="rounded-lg border p-4">
                      <h3 className="font-medium mb-4">Notification Preferences</h3>
                      <div className="space-y-4">
                        {[
                          {
                            id: 'new_device',
                            label: 'New device sign-in',
                            value: notifyNewDevice,
                            onChange: setNotifyNewDevice,
                          },
                          {
                            id: 'suspicious',
                            label: 'Suspicious login attempts',
                            value: notifySuspiciousLogin,
                            onChange: setNotifySuspiciousLogin,
                          },
                          {
                            id: 'password',
                            label: 'Password changes',
                            value: notifyPasswordChange,
                            onChange: setNotifyPasswordChange,
                          },
                        ].map((setting) => (
                          <div
                            key={setting.id}
                            className="flex items-center justify-between"
                          >
                            <span className="text-sm">{setting.label}</span>
                            <button
                              onClick={() => setting.onChange(!setting.value)}
                              role="switch"
                              aria-checked={setting.value}
                              aria-label={setting.label}
                              className={cn(
                                'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                                setting.value ? 'bg-primary' : 'bg-muted'
                              )}
                            >
                              <span
                                className={cn(
                                  'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                                  setting.value ? 'translate-x-6' : 'translate-x-1'
                                )}
                              />
                            </button>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Alert List */}
                    <div className="space-y-3">
                      {securityAlerts.length === 0 ? (
                        <div className="text-center py-8 text-muted-foreground">
                          <Bell className="h-8 w-8 mx-auto mb-2 opacity-50" />
                          <p>No security alerts</p>
                        </div>
                      ) : (
                        securityAlerts.map((alert) => (
                          <div
                            key={alert.id}
                            className={cn(
                              'rounded-lg border p-4',
                              !alert.read && 'bg-primary/5 border-primary/20'
                            )}
                          >
                            <div className="flex items-start gap-3">
                              <div
                                className={cn(
                                  'h-8 w-8 rounded-full flex items-center justify-center',
                                  alert.type === 'suspicious_login'
                                    ? 'bg-red-100 dark:bg-red-900/30'
                                    : 'bg-muted'
                                )}
                              >
                                {alert.type === 'suspicious_login' ? (
                                  <AlertTriangle className="h-4 w-4 text-red-600" />
                                ) : alert.type === 'new_device' ? (
                                  <Smartphone className="h-4 w-4 text-muted-foreground" />
                                ) : (
                                  <Bell className="h-4 w-4 text-muted-foreground" />
                                )}
                              </div>
                              <div className="flex-1">
                                <p className="text-sm">{alert.message}</p>
                                <p className="text-xs text-muted-foreground mt-1">
                                  {formatRelativeTime(alert.timestamp)}
                                </p>
                              </div>
                              {!alert.read && (
                                <span className="h-2 w-2 rounded-full bg-primary" />
                              )}
                            </div>
                          </div>
                        ))
                      )}
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        </div>
      </main>

      {/* 2FA Setup Modal */}
      {show2FASetup && (
        <TwoFactorSetup
          onComplete={() => {
            setShow2FASetup(false);
            loadSecurityData();
          }}
          onCancel={() => setShow2FASetup(false)}
        />
      )}
    </div>
  );
}
