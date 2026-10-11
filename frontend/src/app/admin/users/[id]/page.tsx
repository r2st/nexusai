'use client';

/**
 * Admin User Detail/Edit Page
 *
 * View and edit individual user details, permissions, and activity.
 */

import { useState, useEffect } from 'react';
import { useRouter, useParams } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Save,
  Trash2,
  Mail,
  Shield,
  Building2,
  Activity,
  Clock,
  CheckCircle,
  XCircle,
  Key,
  AlertTriangle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { api, User } from '@/lib/api';
import { toast } from 'sonner';

// Extended user type for admin
interface AdminUserDetail extends User {
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
  is_active: boolean;
  organizations: {
    id: string;
    name: string;
    role: string;
    joined_at: string;
  }[];
  login_history: {
    id: string;
    ip_address: string;
    user_agent: string;
    timestamp: string;
    success: boolean;
  }[];
}

type TabType = 'details' | 'organizations' | 'activity' | 'security';

export default function AdminUserDetailPage() {
  const router = useRouter();
  const params = useParams();
  const userId = params.id as string;

  const [user, setUser] = useState<AdminUserDetail | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [activeTab, setActiveTab] = useState<TabType>('details');
  const [formData, setFormData] = useState({
    email: '',
    username: '',
    full_name: '',
    role: 'user',
    is_active: true,
    is_verified: false,
  });
  const [hasChanges, setHasChanges] = useState(false);
  const [showDeleteModal, setShowDeleteModal] = useState(false);
  const [showPasswordResetModal, setShowPasswordResetModal] = useState(false);

  // Fetch user details
  useEffect(() => {
    const fetchUser = async () => {
      setIsLoading(true);
      try {
        // In production, this would be an actual API call
        // const response = await api.get(`/admin/users/${userId}`);

        // Mock data
        const mockUser: AdminUserDetail = {
          id: userId,
          email: 'john@example.com',
          username: 'johndoe',
          full_name: 'John Doe',
          role: 'user',
          is_verified: true,
          is_active: true,
          created_at: '2024-06-15T00:00:00Z',
          updated_at: '2024-12-01T00:00:00Z',
          last_login_at: new Date(Date.now() - 86400000).toISOString(),
          organizations: [
            {
              id: 'org1',
              name: 'Acme Corp',
              role: 'admin',
              joined_at: '2024-06-15T00:00:00Z',
            },
            {
              id: 'org2',
              name: 'TechStartup Inc',
              role: 'member',
              joined_at: '2024-09-20T00:00:00Z',
            },
          ],
          login_history: [
            {
              id: '1',
              ip_address: '192.168.1.100',
              user_agent: 'Chrome/120.0.0.0',
              timestamp: new Date(Date.now() - 86400000).toISOString(),
              success: true,
            },
            {
              id: '2',
              ip_address: '192.168.1.100',
              user_agent: 'Chrome/120.0.0.0',
              timestamp: new Date(Date.now() - 172800000).toISOString(),
              success: true,
            },
            {
              id: '3',
              ip_address: '10.0.0.50',
              user_agent: 'Firefox/121.0',
              timestamp: new Date(Date.now() - 259200000).toISOString(),
              success: false,
            },
          ],
        };

        setUser(mockUser);
        setFormData({
          email: mockUser.email,
          username: mockUser.username,
          full_name: mockUser.full_name || '',
          role: mockUser.role,
          is_active: mockUser.is_active,
          is_verified: mockUser.is_verified,
        });
      } catch (error) {
        console.error('Failed to fetch user:', error);
      } finally {
        setIsLoading(false);
      }
    };

    if (userId !== 'new') {
      fetchUser();
    } else {
      setIsLoading(false);
    }
  }, [userId]);

  const handleInputChange = (field: string, value: string | boolean) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    setHasChanges(true);
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      if (userId === 'new') {
        // await api.post('/admin/users', formData);
        console.log('Creating new user:', formData);
      } else {
        // await api.put(`/admin/users/${userId}`, formData);
        console.log('Updating user:', formData);
      }
      setHasChanges(false);
      if (userId === 'new') {
        router.push('/admin/users');
      }
    } catch (error) {
      console.error('Failed to save user:', error);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = async () => {
    try {
      // await api.delete(`/admin/users/${userId}`);
      router.push('/admin/users');
    } catch (error) {
      console.error('Failed to delete user:', error);
    }
  };

  const handlePasswordReset = async () => {
    try {
      // await api.post(`/admin/users/${userId}/reset-password`);
      setShowPasswordResetModal(false);
      toast.success('Password reset email sent');
    } catch (error) {
      console.error('Failed to send password reset:', error);
    }
  };

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'Never';
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'long',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const tabs: { id: TabType; label: string; icon: React.ReactNode }[] = [
    { id: 'details', label: 'Details', icon: <Mail className="h-4 w-4" /> },
    { id: 'organizations', label: 'Organizations', icon: <Building2 className="h-4 w-4" /> },
    { id: 'activity', label: 'Activity', icon: <Activity className="h-4 w-4" /> },
    { id: 'security', label: 'Security', icon: <Shield className="h-4 w-4" /> },
  ];

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        <div className="h-96 bg-muted rounded-lg animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <Link
            href="/admin/users"
            className="p-2 hover:bg-muted rounded-lg transition-colors"
          >
            <ArrowLeft className="h-5 w-5" />
          </Link>
          <div>
            <h1 className="text-2xl font-bold">
              {userId === 'new' ? 'New User' : user?.full_name || user?.username}
            </h1>
            {user && (
              <p className="text-muted-foreground">{user.email}</p>
            )}
          </div>
        </div>
        <div className="flex items-center gap-2">
          {userId !== 'new' && (
            <button
              onClick={() => setShowDeleteModal(true)}
              className="inline-flex items-center gap-2 px-4 py-2 border border-destructive text-destructive rounded-lg hover:bg-destructive/10 transition-colors"
            >
              <Trash2 className="h-4 w-4" />
              Delete
            </button>
          )}
          <button
            onClick={handleSave}
            disabled={!hasChanges || isSaving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </div>

      {/* Status Badges */}
      {user && (
        <div className="flex items-center gap-2">
          <span
            className={cn(
              'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
              user.is_active
                ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400'
            )}
          >
            {user.is_active ? <CheckCircle className="h-4 w-4" /> : <XCircle className="h-4 w-4" />}
            {user.is_active ? 'Active' : 'Inactive'}
          </span>
          <span
            className={cn(
              'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
              user.is_verified
                ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400'
                : 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900/30 dark:text-yellow-400'
            )}
          >
            {user.is_verified ? 'Verified' : 'Unverified'}
          </span>
          <span
            className={cn(
              'inline-flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium',
              user.role === 'admin'
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
            )}
          >
            <Shield className="h-4 w-4" />
            {user.role}
          </span>
        </div>
      )}

      {/* Tabs */}
      {userId !== 'new' && (
        <div className="border-b">
          <nav className="flex gap-4">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={cn(
                  'flex items-center gap-2 px-4 py-3 text-sm font-medium border-b-2 -mb-px transition-colors',
                  activeTab === tab.id
                    ? 'border-primary text-primary'
                    : 'border-transparent text-muted-foreground hover:text-foreground'
                )}
              >
                {tab.icon}
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      )}

      {/* Tab Content */}
      <div className="bg-card border rounded-lg p-6">
        {/* Details Tab */}
        {(activeTab === 'details' || userId === 'new') && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold">User Information</h2>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div>
                <label className="block text-sm font-medium mb-2">Email</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Username</label>
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Full Name</label>
                <input
                  type="text"
                  value={formData.full_name}
                  onChange={(e) => handleInputChange('full_name', e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Role</label>
                <select
                  value={formData.role}
                  onChange={(e) => handleInputChange('role', e.target.value)}
                  className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                >
                  <option value="user">User</option>
                  <option value="admin">Admin</option>
                  <option value="superadmin">Super Admin</option>
                </select>
              </div>
            </div>

            <div className="space-y-4">
              <h3 className="text-sm font-medium">Account Settings</h3>
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">Active Status</div>
                  <div className="text-sm text-muted-foreground">
                    Inactive users cannot log in
                  </div>
                </div>
                <button
                  onClick={() => handleInputChange('is_active', !formData.is_active)}
                  className={cn(
                    'relative w-12 h-6 rounded-full transition-colors',
                    formData.is_active ? 'bg-primary' : 'bg-gray-300'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                      formData.is_active ? 'left-7' : 'left-1'
                    )}
                  />
                </button>
              </div>
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div>
                  <div className="font-medium">Email Verified</div>
                  <div className="text-sm text-muted-foreground">
                    Manually verify user's email
                  </div>
                </div>
                <button
                  onClick={() => handleInputChange('is_verified', !formData.is_verified)}
                  className={cn(
                    'relative w-12 h-6 rounded-full transition-colors',
                    formData.is_verified ? 'bg-primary' : 'bg-gray-300'
                  )}
                >
                  <span
                    className={cn(
                      'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                      formData.is_verified ? 'left-7' : 'left-1'
                    )}
                  />
                </button>
              </div>
            </div>

            {user && (
              <div className="pt-4 border-t">
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                  <div>
                    <div className="text-muted-foreground">Created</div>
                    <div>{formatDate(user.created_at)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Updated</div>
                    <div>{formatDate(user.updated_at)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">Last Login</div>
                    <div>{formatDate(user.last_login_at)}</div>
                  </div>
                  <div>
                    <div className="text-muted-foreground">User ID</div>
                    <div className="font-mono text-xs">{user.id}</div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Organizations Tab */}
        {activeTab === 'organizations' && user && (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h2 className="text-lg font-semibold">Organizations</h2>
              <button className="text-sm text-primary hover:underline">
                Add to Organization
              </button>
            </div>
            {user.organizations.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Building2 className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>No organization memberships</p>
              </div>
            ) : (
              <div className="space-y-3">
                {user.organizations.map((org) => (
                  <div
                    key={org.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div className="h-10 w-10 rounded-lg bg-primary/10 flex items-center justify-center">
                        <Building2 className="h-5 w-5 text-primary" />
                      </div>
                      <div>
                        <div className="font-medium">{org.name}</div>
                        <div className="text-sm text-muted-foreground">
                          Joined {formatDate(org.joined_at)}
                        </div>
                      </div>
                    </div>
                    <div className="flex items-center gap-4">
                      <span
                        className={cn(
                          'px-2 py-1 rounded-full text-xs font-medium',
                          org.role === 'admin'
                            ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400'
                            : 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-400'
                        )}
                      >
                        {org.role}
                      </span>
                      <button className="text-sm text-destructive hover:underline">
                        Remove
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Activity Tab */}
        {activeTab === 'activity' && user && (
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Login History</h2>
            {user.login_history.length === 0 ? (
              <div className="text-center py-8 text-muted-foreground">
                <Activity className="h-12 w-12 mx-auto mb-4 opacity-20" />
                <p>No login activity</p>
              </div>
            ) : (
              <div className="space-y-3">
                {user.login_history.map((login) => (
                  <div
                    key={login.id}
                    className="flex items-center justify-between p-4 border rounded-lg"
                  >
                    <div className="flex items-center gap-3">
                      <div
                        className={cn(
                          'h-10 w-10 rounded-lg flex items-center justify-center',
                          login.success
                            ? 'bg-green-100 dark:bg-green-900/30'
                            : 'bg-red-100 dark:bg-red-900/30'
                        )}
                      >
                        {login.success ? (
                          <CheckCircle className="h-5 w-5 text-green-600" />
                        ) : (
                          <XCircle className="h-5 w-5 text-red-600" />
                        )}
                      </div>
                      <div>
                        <div className="font-medium">
                          {login.success ? 'Successful login' : 'Failed login attempt'}
                        </div>
                        <div className="text-sm text-muted-foreground">
                          {login.ip_address} • {login.user_agent}
                        </div>
                      </div>
                    </div>
                    <div className="text-sm text-muted-foreground">
                      <Clock className="h-4 w-4 inline mr-1" />
                      {formatDate(login.timestamp)}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}

        {/* Security Tab */}
        {activeTab === 'security' && user && (
          <div className="space-y-6">
            <h2 className="text-lg font-semibold">Security Settings</h2>

            <div className="space-y-4">
              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-yellow-100 dark:bg-yellow-900/30 rounded-lg">
                    <Key className="h-5 w-5 text-yellow-600" />
                  </div>
                  <div>
                    <div className="font-medium">Reset Password</div>
                    <div className="text-sm text-muted-foreground">
                      Send a password reset email to the user
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setShowPasswordResetModal(true)}
                  className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
                >
                  Send Reset Email
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-orange-100 dark:bg-orange-900/30 rounded-lg">
                    <AlertTriangle className="h-5 w-5 text-orange-600" />
                  </div>
                  <div>
                    <div className="font-medium">Force Logout</div>
                    <div className="text-sm text-muted-foreground">
                      Invalidate all active sessions
                    </div>
                  </div>
                </div>
                <button className="px-4 py-2 border border-orange-500 text-orange-500 rounded-lg hover:bg-orange-50 dark:hover:bg-orange-900/20 transition-colors">
                  Logout All Sessions
                </button>
              </div>

              <div className="flex items-center justify-between p-4 border border-destructive/30 rounded-lg">
                <div className="flex items-center gap-3">
                  <div className="p-2 bg-red-100 dark:bg-red-900/30 rounded-lg">
                    <Trash2 className="h-5 w-5 text-red-600" />
                  </div>
                  <div>
                    <div className="font-medium">Delete Account</div>
                    <div className="text-sm text-muted-foreground">
                      Permanently delete this user account
                    </div>
                  </div>
                </div>
                <button
                  onClick={() => setShowDeleteModal(true)}
                  className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
                >
                  Delete Account
                </button>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Delete Modal */}
      {showDeleteModal && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setShowDeleteModal(false)} aria-hidden="true" />
          <div role="dialog" aria-modal="true" aria-labelledby="delete-user-detail-title" className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-background rounded-lg shadow-lg p-6">
            <h3 id="delete-user-detail-title" className="text-lg font-semibold mb-2">Delete User</h3>
            <p className="text-muted-foreground mb-4">
              Are you sure you want to delete <strong>{user?.full_name || user?.username}</strong>?
              This will also remove them from all organizations. This action cannot be undone.
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowDeleteModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 bg-destructive text-destructive-foreground rounded-lg hover:bg-destructive/90 transition-colors"
              >
                Delete
              </button>
            </div>
          </div>
        </>
      )}

      {/* Password Reset Modal */}
      {showPasswordResetModal && (
        <>
          <div className="fixed inset-0 bg-black/50 z-40" onClick={() => setShowPasswordResetModal(false)} aria-hidden="true" />
          <div role="dialog" aria-modal="true" aria-labelledby="password-reset-title" className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-md bg-background rounded-lg shadow-lg p-6">
            <h3 id="password-reset-title" className="text-lg font-semibold mb-2">Send Password Reset</h3>
            <p className="text-muted-foreground mb-4">
              Send a password reset email to <strong>{user?.email}</strong>?
            </p>
            <div className="flex justify-end gap-2">
              <button
                onClick={() => setShowPasswordResetModal(false)}
                className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handlePasswordReset}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
              >
                Send Email
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
