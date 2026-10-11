'use client';

/**
 * Create New User Page
 *
 * Form for administrators to create new user accounts.
 */

import { useState } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  ArrowLeft,
  Save,
  Mail,
  User,
  Lock,
  Shield,
  Eye,
  EyeOff,
  AlertCircle,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { adminUsersApi, CreateUserRequest } from '@/lib/admin-api';

export default function CreateUserPage() {
  const router = useRouter();

  const [formData, setFormData] = useState<CreateUserRequest>({
    email: '',
    username: '',
    password: '',
    full_name: '',
    role: 'user',
    is_active: true,
    is_verified: false,
    send_welcome_email: true,
  });
  const [showPassword, setShowPassword] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [generalError, setGeneralError] = useState<string | null>(null);

  const validateForm = (): boolean => {
    const newErrors: Record<string, string> = {};

    if (!formData.email) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Invalid email format';
    }

    if (!formData.username) {
      newErrors.username = 'Username is required';
    } else if (formData.username.length < 3) {
      newErrors.username = 'Username must be at least 3 characters';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      newErrors.username = 'Username can only contain letters, numbers, underscores, and hyphens';
    }

    if (!formData.password && !formData.send_welcome_email) {
      newErrors.password = 'Password is required when not sending welcome email';
    } else if (formData.password && formData.password.length < 8) {
      newErrors.password = 'Password must be at least 8 characters';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleInputChange = (
    field: keyof CreateUserRequest,
    value: string | boolean
  ) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
    // Clear error for this field when user starts typing
    if (errors[field]) {
      setErrors((prev) => ({ ...prev, [field]: '' }));
    }
    setGeneralError(null);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    setIsSaving(true);
    setGeneralError(null);

    try {
      // In production, this would be an actual API call
      // await adminUsersApi.create(formData);

      // Mock success
      console.log('Creating user:', formData);

      // Redirect to users list
      router.push('/admin/users');
    } catch (error: unknown) {
      console.error('Failed to create user:', error);
      setGeneralError(
        error instanceof Error ? error.message : 'Failed to create user. Please try again.'
      );
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="max-w-2xl">
      {/* Header */}
      <div className="flex items-center gap-4 mb-6">
        <Link
          href="/admin/users"
          className="p-2 hover:bg-muted rounded-lg transition-colors"
        >
          <ArrowLeft className="h-5 w-5" />
        </Link>
        <div>
          <h1 className="text-2xl font-bold">Create New User</h1>
          <p className="text-muted-foreground">Add a new user account to the system</p>
        </div>
      </div>

      {/* Error Alert */}
      {generalError && (
        <div className="mb-6 p-4 bg-destructive/10 border border-destructive/20 rounded-lg flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-destructive shrink-0 mt-0.5" />
          <div>
            <p className="font-medium text-destructive">Error</p>
            <p className="text-sm text-destructive/80">{generalError}</p>
          </div>
        </div>
      )}

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-6">
        <div className="bg-card border rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <User className="h-5 w-5" />
            Account Information
          </h2>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Email */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Email <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => handleInputChange('email', e.target.value)}
                  className={cn(
                    'w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50',
                    errors.email && 'border-destructive focus:ring-destructive/50'
                  )}
                  placeholder="user@example.com"
                />
              </div>
              {errors.email && (
                <p className="text-sm text-destructive mt-1">{errors.email}</p>
              )}
            </div>

            {/* Username */}
            <div>
              <label className="block text-sm font-medium mb-2">
                Username <span className="text-destructive">*</span>
              </label>
              <div className="relative">
                <User className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <input
                  type="text"
                  value={formData.username}
                  onChange={(e) => handleInputChange('username', e.target.value)}
                  className={cn(
                    'w-full pl-10 pr-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50',
                    errors.username && 'border-destructive focus:ring-destructive/50'
                  )}
                  placeholder="johndoe"
                />
              </div>
              {errors.username && (
                <p className="text-sm text-destructive mt-1">{errors.username}</p>
              )}
            </div>

            {/* Full Name */}
            <div className="md:col-span-2">
              <label className="block text-sm font-medium mb-2">Full Name</label>
              <input
                type="text"
                value={formData.full_name}
                onChange={(e) => handleInputChange('full_name', e.target.value)}
                className="w-full px-4 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50"
                placeholder="John Doe"
              />
            </div>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Lock className="h-5 w-5" />
            Password & Security
          </h2>

          {/* Password */}
          <div>
            <label className="block text-sm font-medium mb-2">
              Password {!formData.send_welcome_email && <span className="text-destructive">*</span>}
            </label>
            <div className="relative">
              <Lock className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <input
                type={showPassword ? 'text' : 'password'}
                value={formData.password}
                onChange={(e) => handleInputChange('password', e.target.value)}
                className={cn(
                  'w-full pl-10 pr-12 py-2 border rounded-lg bg-background focus:outline-none focus:ring-2 focus:ring-primary/50',
                  errors.password && 'border-destructive focus:ring-destructive/50'
                )}
                placeholder={formData.send_welcome_email ? 'Optional - user will set their own' : 'Enter password'}
                disabled={formData.send_welcome_email}
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
              >
                {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
              </button>
            </div>
            {errors.password && (
              <p className="text-sm text-destructive mt-1">{errors.password}</p>
            )}
          </div>

          {/* Send Welcome Email */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <div className="font-medium">Send Welcome Email</div>
              <div className="text-sm text-muted-foreground">
                User will receive an email to set their password
              </div>
            </div>
            <button
              type="button"
              onClick={() => handleInputChange('send_welcome_email', !formData.send_welcome_email)}
              className={cn(
                'relative w-12 h-6 rounded-full transition-colors',
                formData.send_welcome_email ? 'bg-primary' : 'bg-gray-300'
              )}
            >
              <span
                className={cn(
                  'absolute top-1 w-4 h-4 bg-white rounded-full transition-transform',
                  formData.send_welcome_email ? 'left-7' : 'left-1'
                )}
              />
            </button>
          </div>
        </div>

        <div className="bg-card border rounded-lg p-6 space-y-6">
          <h2 className="text-lg font-semibold flex items-center gap-2">
            <Shield className="h-5 w-5" />
            Role & Permissions
          </h2>

          {/* Role */}
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
            <p className="text-sm text-muted-foreground mt-1">
              {formData.role === 'superadmin' && 'Full access to all system features and settings'}
              {formData.role === 'admin' && 'Access to admin features, can manage users and organizations'}
              {formData.role === 'user' && 'Standard user access to assigned organizations'}
            </p>
          </div>

          {/* Account Status */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <div className="font-medium">Active Status</div>
              <div className="text-sm text-muted-foreground">
                Inactive users cannot log in
              </div>
            </div>
            <button
              type="button"
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

          {/* Email Verified */}
          <div className="flex items-center justify-between p-4 border rounded-lg">
            <div>
              <div className="font-medium">Email Verified</div>
              <div className="text-sm text-muted-foreground">
                Skip email verification for this user
              </div>
            </div>
            <button
              type="button"
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

        {/* Actions */}
        <div className="flex items-center justify-end gap-4">
          <Link
            href="/admin/users"
            className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors"
          >
            Cancel
          </Link>
          <button
            type="submit"
            disabled={isSaving}
            className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Save className="h-4 w-4" />
            {isSaving ? 'Creating...' : 'Create User'}
          </button>
        </div>
      </form>
    </div>
  );
}
