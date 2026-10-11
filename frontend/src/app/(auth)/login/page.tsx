'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Loader2, Building2, User, AlertCircle, Eye, EyeOff } from 'lucide-react';
import { DoAideLogo } from '@/components/ui/doaide-logo';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { authApi, organizationsApi, type Organization } from '@/lib/api';
import { useAuthStore, type AuthUser } from '@/store/auth';
import { type UserRole } from '@/lib/security';
import { cn } from '@/lib/utils';

// -----------------------------------------------------------------------------
// Login Type Selection
// -----------------------------------------------------------------------------

type LoginType = 'organization' | 'staff';

function LoginPageLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export default function LoginPage() {
  return (
    <Suspense fallback={<LoginPageLoading />}>
      <LoginPageContent />
    </Suspense>
  );
}

function LoginPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirectTo = searchParams.get('redirect') || '/chat';
  const expired = searchParams.get('expired') === 'true';
  const inviteToken = searchParams.get('invite');

  const { login, setCurrentOrganization, setOrganizations } = useAuthStore();

  const [loginType, setLoginType] = useState<LoginType>('organization');
  const [isLoading, setIsLoading] = useState(false);
  const [showPassword, setShowPassword] = useState(false);

  // Form fields
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [orgSlug, setOrgSlug] = useState('');

  // Show expired session message
  useEffect(() => {
    if (expired) {
      toast.error('Your session has expired. Please sign in again.');
    }
  }, [expired]);

  // Auto-detect staff invite
  useEffect(() => {
    if (inviteToken) {
      setLoginType('staff');
    }
  }, [inviteToken]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);

    try {
      // Perform login
      const response = await authApi.login(email, password);

      // Cast user to AuthUser type with role
      const authUser: AuthUser = {
        ...response.user,
        role: (response.user.role as UserRole) || 'staff_viewer',
        organization_id: response.user.organization_id || null,
      };

      // Store auth state
      login(
        authUser,
        response.tokens.access_token,
        response.tokens.refresh_token,
        response.tokens.expires_in
      );

      // For organization login, validate org access
      if (loginType === 'organization' && orgSlug) {
        try {
          const orgs = await organizationsApi.list();
          const targetOrg = orgs.find(org => org.slug === orgSlug);

          if (!targetOrg) {
            toast.error('You do not have access to this organization');
            return;
          }

          setOrganizations(orgs);
          setCurrentOrganization(targetOrg);
          organizationsApi.switchTo(targetOrg.id);
        } catch {
          // If org fetch fails, continue anyway
          console.warn('Failed to fetch organizations');
        }
      } else {
        // For staff login, fetch available orgs
        try {
          const orgs = await organizationsApi.list();
          setOrganizations(orgs);

          if (orgs.length === 1) {
            setCurrentOrganization(orgs[0]);
            organizationsApi.switchTo(orgs[0].id);
          }
        } catch {
          console.warn('Failed to fetch organizations');
        }
      }

      toast.success('Welcome back!');

      // Check for pending chat message
      const pendingMessage = sessionStorage.getItem('pending_chat_message');
      if (pendingMessage && redirectTo === '/chat') {
        // Keep the message for the chat page to pick up
        router.push('/chat');
      } else {
        sessionStorage.removeItem('pending_chat_message');
        router.push(redirectTo);
      }
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Invalid email or password';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuth = async (provider: 'google' | 'github') => {
    try {
      const apiBase = process.env.NEXT_PUBLIC_API_URL || '';
      window.location.href = `${apiBase}/api/v1/auth/oauth/${provider}`;
    } catch {
      toast.error(`Failed to start ${provider} login`);
    }
  };

  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-2">
            <DoAideLogo size={32} />
            <span className="text-2xl font-bold">GSTIndia</span>
          </Link>
          <h1 className="mt-6 text-2xl font-semibold">Welcome back</h1>
          <p className="mt-2 text-muted-foreground">
            Sign in to your account to continue
          </p>
        </div>

        {/* Login Type Tabs */}
        <div className="flex rounded-lg border bg-muted/50 p-1" role="tablist" aria-label="Login type">
          <button
            type="button"
            role="tab"
            aria-selected={loginType === 'organization'}
            aria-controls="login-form"
            onClick={() => setLoginType('organization')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              loginType === 'organization'
                ? 'bg-background shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <Building2 className="h-4 w-4" aria-hidden="true" />
            Organization
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={loginType === 'staff'}
            aria-controls="login-form"
            onClick={() => setLoginType('staff')}
            className={cn(
              'flex-1 flex items-center justify-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors',
              loginType === 'staff'
                ? 'bg-background shadow-sm'
                : 'text-muted-foreground hover:text-foreground'
            )}
          >
            <User className="h-4 w-4" aria-hidden="true" />
            Staff
          </button>
        </div>

        {/* Expired Session Alert */}
        {expired && (
          <div role="alert" className="flex items-center gap-2 rounded-lg border border-yellow-200 bg-yellow-50 p-3 text-sm text-yellow-800 dark:border-yellow-800 dark:bg-yellow-900/20 dark:text-yellow-200">
            <AlertCircle className="h-4 w-4 shrink-0" aria-hidden="true" />
            Your session has expired. Please sign in again.
          </div>
        )}

        {/* Staff Invite Banner */}
        {inviteToken && (
          <div className="flex items-center gap-2 rounded-lg border border-primary/20 bg-primary/5 p-3 text-sm">
            <AlertCircle className="h-4 w-4 shrink-0 text-primary" />
            You&apos;ve been invited to join an organization. Sign in or create an account to accept.
          </div>
        )}

        {/* Form */}
        <form id="login-form" onSubmit={handleSubmit} className="space-y-4" role="tabpanel">
          {/* Organization Slug (for org login) */}
          {loginType === 'organization' && (
            <div className="space-y-2">
              <label htmlFor="orgSlug" className="text-sm font-medium">
                Organization
              </label>
              <Input
                id="orgSlug"
                type="text"
                placeholder="your-org-slug"
                value={orgSlug}
                onChange={(e) => setOrgSlug(e.target.value.toLowerCase().replace(/[^a-z0-9-]/g, ''))}
                disabled={isLoading}
                autoComplete="organization"
              />
              <p className="text-xs text-muted-foreground">
                Enter your organization&apos;s unique identifier
              </p>
            </div>
          )}

          <div className="space-y-2">
            <label htmlFor="email" className="text-sm font-medium">
              Email
            </label>
            <Input
              id="email"
              type="email"
              placeholder="you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              disabled={isLoading}
              autoComplete="email"
            />
          </div>

          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <label htmlFor="password" className="text-sm font-medium">
                Password
              </label>
              <Link
                href="/forgot-password"
                className="text-sm text-primary hover:underline"
              >
                Forgot password?
              </Link>
            </div>
            <div className="relative">
              <Input
                id="password"
                type={showPassword ? 'text' : 'password'}
                placeholder="••••••••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
                disabled={isLoading}
                autoComplete="current-password"
                className="pr-10"
              />
              <button
                type="button"
                onClick={() => setShowPassword(!showPassword)}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                aria-label={showPassword ? 'Hide password' : 'Show password'}
              >
                {showPassword ? (
                  <EyeOff className="h-4 w-4" />
                ) : (
                  <Eye className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          <Button type="submit" className="w-full" disabled={isLoading}>
            {isLoading ? (
              <>
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Signing in...
              </>
            ) : (
              'Sign in'
            )}
          </Button>
        </form>

        {/* Divider */}
        <div className="relative">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t" />
          </div>
          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-background px-2 text-muted-foreground">
              Or continue with
            </span>
          </div>
        </div>

        {/* OAuth buttons */}
        <div className="grid grid-cols-2 gap-4">
          <Button
            type="button"
            variant="outline"
            disabled={isLoading}
            onClick={() => handleOAuth('google')}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" aria-hidden="true">
              <path
                fill="currentColor"
                d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
              />
              <path
                fill="currentColor"
                d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
              />
              <path
                fill="currentColor"
                d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"
              />
              <path
                fill="currentColor"
                d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"
              />
            </svg>
            Google
          </Button>
          <Button
            type="button"
            variant="outline"
            disabled={isLoading}
            onClick={() => handleOAuth('github')}
          >
            <svg className="mr-2 h-4 w-4" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
              <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
            </svg>
            GitHub
          </Button>
        </div>

        {/* Sign up link */}
        <p className="text-center text-sm text-muted-foreground">
          Don&apos;t have an account?{' '}
          <Link href="/register" className="text-primary hover:underline">
            Sign up
          </Link>
        </p>

        {/* Organization creation link (for org admins) */}
        {loginType === 'organization' && (
          <p className="text-center text-sm text-muted-foreground">
            Need to create an organization?{' '}
            <Link href="/register?type=organization" className="text-primary hover:underline">
              Create one
            </Link>
          </p>
        )}
      </div>
    </div>
  );
}
