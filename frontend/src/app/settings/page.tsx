'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  User,
  Settings,
  Bell,
  Shield,
  CreditCard,
  Key,
  LogOut,
  Loader2,
  Check,
  Camera,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ThemeSelect } from '@/components/ui/theme-toggle';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';
import { FloatingAssistant } from '@/components/assistant';

type SettingsTab = 'profile' | 'appearance' | 'notifications' | 'security' | 'billing';

export default function SettingsPage() {
  const router = useRouter();
  const { user, isAuthenticated, logout } = useAuthStore();
  const [activeTab, setActiveTab] = useState<SettingsTab>('profile');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  // Profile form state
  const [fullName, setFullName] = useState(user?.full_name || '');
  const [email, setEmail] = useState(user?.email || '');
  const [username, setUsername] = useState(user?.username || '');

  // Notification settings
  const [emailNotifications, setEmailNotifications] = useState(true);
  const [marketingEmails, setMarketingEmails] = useState(false);
  const [securityAlerts, setSecurityAlerts] = useState(true);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  useEffect(() => {
    if (user) {
      setFullName(user.full_name || '');
      setEmail(user.email || '');
      setUsername(user.username || '');
    }
  }, [user]);

  const handleSaveProfile = async () => {
    setIsSaving(true);
    try {
      // Simulate API call
      await new Promise((resolve) => setTimeout(resolve, 1000));
      toast.success('Profile updated successfully');
    } catch (error) {
      toast.error('Failed to update profile');
    } finally {
      setIsSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    router.push('/login');
    toast.success('Logged out successfully');
  };

  if (!isAuthenticated) {
    return null;
  }

  const tabs: { id: SettingsTab; label: string; icon: typeof User }[] = [
    { id: 'profile', label: 'Profile', icon: User },
    { id: 'appearance', label: 'Appearance', icon: Settings },
    { id: 'notifications', label: 'Notifications', icon: Bell },
    { id: 'security', label: 'Security', icon: Shield },
    { id: 'billing', label: 'Billing', icon: CreditCard },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Settings className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Settings</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/chat">
              <Button variant="ghost" size="sm">
                Go to Chat
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="flex flex-col md:flex-row gap-8">
          {/* Sidebar */}
          <aside className="w-full md:w-64 shrink-0">
            <nav className="space-y-1" aria-label="Settings sections">
              {tabs.map((tab) => {
                const Icon = tab.icon;
                return (
                  <button
                    key={tab.id}
                    onClick={() => setActiveTab(tab.id)}
                    aria-current={activeTab === tab.id ? 'page' : undefined}
                    className={cn(
                      'w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors',
                      activeTab === tab.id
                        ? 'bg-primary/10 text-primary'
                        : 'text-muted-foreground hover:bg-muted hover:text-foreground'
                    )}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {tab.label}
                  </button>
                );
              })}
              <hr className="my-4" />
              <button
                onClick={handleLogout}
                className="w-full flex items-center gap-3 px-4 py-2.5 rounded-lg text-sm font-medium text-destructive hover:bg-destructive/10 transition-colors"
              >
                <LogOut className="h-4 w-4" />
                Log out
              </button>
            </nav>
          </aside>

          {/* Content */}
          <div className="flex-1 max-w-2xl">
            {/* Profile Tab */}
            {activeTab === 'profile' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Profile</h2>

                {/* Avatar */}
                <div className="flex items-center gap-4 mb-8">
                  <div className="relative">
                    <div className="h-20 w-20 rounded-full bg-primary/10 flex items-center justify-center text-2xl font-bold text-primary">
                      {fullName?.charAt(0) || email?.charAt(0) || 'U'}
                    </div>
                    <button
                      className="absolute bottom-0 right-0 h-8 w-8 rounded-full bg-primary text-primary-foreground flex items-center justify-center shadow-md hover:bg-primary/90 transition-colors"
                      aria-label="Change profile photo"
                    >
                      <Camera className="h-4 w-4" aria-hidden="true" />
                    </button>
                  </div>
                  <div>
                    <h3 className="font-medium">{fullName || 'User'}</h3>
                    <p className="text-sm text-muted-foreground">{email}</p>
                  </div>
                </div>

                {/* Form */}
                <div className="space-y-4">
                  <div>
                    <label htmlFor="settings-fullname" className="text-sm font-medium">Full Name</label>
                    <Input
                      id="settings-fullname"
                      value={fullName}
                      onChange={(e) => setFullName(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label htmlFor="settings-username" className="text-sm font-medium">Username</label>
                    <Input
                      id="settings-username"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      className="mt-1"
                    />
                  </div>
                  <div>
                    <label htmlFor="settings-email" className="text-sm font-medium">Email</label>
                    <Input
                      id="settings-email"
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      className="mt-1"
                    />
                    <p className="mt-1 text-xs text-muted-foreground">
                      Changing your email will require verification
                    </p>
                  </div>

                  <Button onClick={handleSaveProfile} disabled={isSaving}>
                    {isSaving ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Saving...
                      </>
                    ) : (
                      <>
                        <Check className="mr-2 h-4 w-4" />
                        Save Changes
                      </>
                    )}
                  </Button>
                </div>
              </div>
            )}

            {/* Appearance Tab */}
            {activeTab === 'appearance' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Appearance</h2>

                <div className="space-y-6">
                  <div>
                    <h3 className="font-medium mb-2">Theme</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Choose how GSTIndia looks to you
                    </p>
                    <ThemeSelect />
                  </div>

                  <div>
                    <h3 className="font-medium mb-2">Density</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Adjust the spacing and size of UI elements
                    </p>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm">
                        Comfortable
                      </Button>
                      <Button variant="ghost" size="sm">
                        Compact
                      </Button>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Notifications Tab */}
            {activeTab === 'notifications' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Notifications</h2>

                <div className="space-y-6">
                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium" id="label-email-notif">Email Notifications</h3>
                      <p className="text-sm text-muted-foreground">
                        Receive email updates about your activity
                      </p>
                    </div>
                    <button
                      role="switch"
                      aria-checked={emailNotifications}
                      aria-labelledby="label-email-notif"
                      onClick={() => setEmailNotifications(!emailNotifications)}
                      className={cn(
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        emailNotifications ? 'bg-primary' : 'bg-muted'
                      )}
                    >
                      <span
                        className={cn(
                          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                          emailNotifications ? 'translate-x-6' : 'translate-x-1'
                        )}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium" id="label-marketing">Marketing Emails</h3>
                      <p className="text-sm text-muted-foreground">
                        Receive updates about new features and offers
                      </p>
                    </div>
                    <button
                      role="switch"
                      aria-checked={marketingEmails}
                      aria-labelledby="label-marketing"
                      onClick={() => setMarketingEmails(!marketingEmails)}
                      className={cn(
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        marketingEmails ? 'bg-primary' : 'bg-muted'
                      )}
                    >
                      <span
                        className={cn(
                          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                          marketingEmails ? 'translate-x-6' : 'translate-x-1'
                        )}
                      />
                    </button>
                  </div>

                  <div className="flex items-center justify-between">
                    <div>
                      <h3 className="font-medium" id="label-security">Security Alerts</h3>
                      <p className="text-sm text-muted-foreground">
                        Get notified about security events on your account
                      </p>
                    </div>
                    <button
                      role="switch"
                      aria-checked={securityAlerts}
                      aria-labelledby="label-security"
                      onClick={() => setSecurityAlerts(!securityAlerts)}
                      className={cn(
                        'relative inline-flex h-6 w-11 items-center rounded-full transition-colors',
                        securityAlerts ? 'bg-primary' : 'bg-muted'
                      )}
                    >
                      <span
                        className={cn(
                          'inline-block h-4 w-4 transform rounded-full bg-white transition-transform',
                          securityAlerts ? 'translate-x-6' : 'translate-x-1'
                        )}
                      />
                    </button>
                  </div>
                </div>
              </div>
            )}

            {/* Security Tab */}
            {activeTab === 'security' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Security</h2>

                <div className="space-y-6">
                  <div className="rounded-lg border p-4">
                    <div className="flex items-start gap-4">
                      <Key className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div className="flex-1">
                        <h3 className="font-medium">Password</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Last changed 30 days ago
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Change
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4">
                    <div className="flex items-start gap-4">
                      <Shield className="h-5 w-5 text-muted-foreground mt-0.5" />
                      <div className="flex-1">
                        <h3 className="font-medium">Two-Factor Authentication</h3>
                        <p className="text-sm text-muted-foreground mt-1">
                          Add an extra layer of security to your account
                        </p>
                      </div>
                      <Button variant="outline" size="sm">
                        Enable
                      </Button>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4">
                    <h3 className="font-medium mb-4">Active Sessions</h3>
                    <div className="space-y-3">
                      <div className="flex items-center justify-between text-sm">
                        <div>
                          <p className="font-medium">Current session</p>
                          <p className="text-muted-foreground">
                            Chrome on macOS • San Francisco, CA
                          </p>
                        </div>
                        <span className="text-xs text-green-500">Active now</span>
                      </div>
                    </div>
                  </div>

                  <div className="rounded-lg border border-destructive/50 p-4">
                    <h3 className="font-medium text-destructive mb-2">Danger Zone</h3>
                    <p className="text-sm text-muted-foreground mb-4">
                      Permanently delete your account and all of its data
                    </p>
                    <Button variant="destructive" size="sm">
                      Delete Account
                    </Button>
                  </div>
                </div>
              </div>
            )}

            {/* Billing Tab */}
            {activeTab === 'billing' && (
              <div>
                <h2 className="text-2xl font-bold mb-6">Billing</h2>

                <div className="space-y-6">
                  <div className="rounded-lg border p-6">
                    <div className="flex items-center justify-between mb-4">
                      <div>
                        <h3 className="font-medium">Current Plan</h3>
                        <p className="text-2xl font-bold mt-1">Free</p>
                      </div>
                      <Link href="/pricing">
                        <Button>Upgrade</Button>
                      </Link>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <p>3 projects • 5 team members • 100 AI conversations/month</p>
                    </div>
                  </div>

                  <div className="rounded-lg border p-4">
                    <h3 className="font-medium mb-4">Payment Method</h3>
                    <p className="text-sm text-muted-foreground">
                      No payment method on file
                    </p>
                    <Button variant="outline" size="sm" className="mt-4">
                      Add Payment Method
                    </Button>
                  </div>

                  <div className="rounded-lg border p-4">
                    <h3 className="font-medium mb-4">Billing History</h3>
                    <p className="text-sm text-muted-foreground">
                      No billing history available
                    </p>
                  </div>
                </div>
              </div>
            )}
          </div>
        </div>
      </main>

      {/* AI Assistant */}
      <FloatingAssistant context="settings" />
    </div>
  );
}
