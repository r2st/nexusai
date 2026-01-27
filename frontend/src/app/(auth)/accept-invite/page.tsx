'use client';

import { useState, useEffect, Suspense } from 'react';
import Link from 'next/link';
import { useRouter, useSearchParams } from 'next/navigation';
import { Sparkles, Loader2, CheckCircle2, XCircle, Eye, EyeOff, Building2 } from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { api, authApi } from '@/lib/api';
import { useAuthStore, type AuthUser } from '@/store/auth';
import { type UserRole, getRoleDisplayName } from '@/lib/security';
import { cn } from '@/lib/utils';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

interface InviteDetails {
  email: string;
  role: UserRole;
  organization_name: string;
  organization_slug: string;
  invited_by: string;
  expires_at: string;
  is_valid: boolean;
  error?: string;
}

// -----------------------------------------------------------------------------
// Loading Fallback
// -----------------------------------------------------------------------------

function AcceptInviteLoading() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
      <div className="flex flex-col items-center gap-4">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
        <p className="text-sm text-muted-foreground">Loading...</p>
      </div>
    </div>
  );
}

// -----------------------------------------------------------------------------
// Accept Invite Page Wrapper (with Suspense for useSearchParams)
// -----------------------------------------------------------------------------

export default function AcceptInvitePage() {
  return (
    <Suspense fallback={<AcceptInviteLoading />}>
      <AcceptInviteContent />
    </Suspense>
  );
}

// -----------------------------------------------------------------------------
// Accept Invite Content
// -----------------------------------------------------------------------------

function AcceptInviteContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const token = searchParams.get('token');

  const { login, isAuthenticated } = useAuthStore();

  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [inviteDetails, setInviteDetails] = useState<InviteDetails | null>(null);
  const [error, setError] = useState<string | null>(null);

  // Form state (for new users)
  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');

  // Fetch invite details
  useEffect(() => {
    const fetchInviteDetails = async () => {
      if (!token) {
        setError('No invitation token provided');
        setIsLoading(false);
        return;
      }

      try {
        const response = await api.get(`/auth/invites/${token}`);
        setInviteDetails(response.data);
      } catch (err) {
        setError('This invitation is invalid or has expired');
      } finally {
        setIsLoading(false);
      }
    };

    fetchInviteDetails();
  }, [token]);

  // Handle accept invite for existing user
  const handleAcceptExisting = async () => {
    if (!token) return;

    setIsSubmitting(true);
    try {
      await api.post(`/auth/invites/${token}/accept`);
      toast.success('You have joined the organization!');
      router.push('/chat');
    } catch (err) {
      toast.error('Failed to accept invitation');
    } finally {
      setIsSubmitting(false);
    }
  };

  // Handle accept invite for new user (create account)
  const handleAcceptNew = async (e: React.FormEvent) => {
    e.preventDefault();

    if (password !== confirmPassword) {
      toast.error('Passwords do not match');
      return;
    }

    if (password.length < 8) {
      toast.error('Password must be at least 8 characters');
      return;
    }

    if (!token || !inviteDetails) return;

    setIsSubmitting(true);
    try {
      // Create account and accept invite in one request
      const response = await api.post(`/auth/invites/${token}/accept-with-registration`, {
        full_name: fullName,
        password,
      });

      // Log the user in
      const authUser: AuthUser = {
        ...response.data.user,
        role: inviteDetails.role,
        organization_id: response.data.organization_id,
      };

      login(
        authUser,
        response.data.tokens.access_token,
        response.data.tokens.refresh_token,
        response.data.tokens.expires_in
      );

      toast.success('Account created and joined organization!');
      router.push('/chat');
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to create account';
      toast.error(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  // Loading state
  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted">
        <div className="flex flex-col items-center gap-4">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Validating invitation...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error || !inviteDetails?.is_valid) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted p-4">
        <div className="w-full max-w-md space-y-6 text-center">
          <XCircle className="h-16 w-16 mx-auto text-destructive" />
          <h1 className="text-2xl font-semibold">Invalid Invitation</h1>
          <p className="text-muted-foreground">
            {error || inviteDetails?.error || 'This invitation is invalid or has expired.'}
          </p>
          <div className="flex items-center justify-center gap-4">
            <Button variant="outline" asChild>
              <Link href="/login">Sign In</Link>
            </Button>
            <Button asChild>
              <Link href="/register">Create Account</Link>
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // Valid invite - show accept UI
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-background to-muted p-4">
      <div className="w-full max-w-md space-y-6">
        {/* Logo */}
        <div className="text-center">
          <Link href="/" className="inline-flex items-center gap-2">
            <Sparkles className="h-8 w-8 text-primary" />
            <span className="text-2xl font-bold">NexusAI</span>
          </Link>
        </div>

        {/* Invite Card */}
        <div className="rounded-lg border bg-card p-6 space-y-4">
          <div className="text-center space-y-2">
            <CheckCircle2 className="h-12 w-12 mx-auto text-green-500" />
            <h1 className="text-xl font-semibold">You&apos;ve been invited!</h1>
          </div>

          {/* Organization Info */}
          <div className="flex items-center gap-4 p-4 rounded-lg bg-muted/50">
            <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
              <Building2 className="h-6 w-6 text-primary" />
            </div>
            <div>
              <p className="font-medium">{inviteDetails.organization_name}</p>
              <p className="text-sm text-muted-foreground">
                Role: {getRoleDisplayName(inviteDetails.role)}
              </p>
            </div>
          </div>

          <p className="text-sm text-muted-foreground text-center">
            <span className="font-medium">{inviteDetails.invited_by}</span> has invited you to join their organization.
          </p>
        </div>

        {/* If user is already logged in */}
        {isAuthenticated ? (
          <div className="space-y-4">
            <Button
              className="w-full"
              onClick={handleAcceptExisting}
              disabled={isSubmitting}
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Joining...
                </>
              ) : (
                'Accept Invitation'
              )}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              You&apos;re signed in. Click above to join the organization.
            </p>
          </div>
        ) : (
          <>
            {/* New user registration form */}
            <form onSubmit={handleAcceptNew} className="space-y-4">
              <div className="space-y-2">
                <label htmlFor="email" className="text-sm font-medium">
                  Email
                </label>
                <Input
                  id="email"
                  type="email"
                  value={inviteDetails.email}
                  disabled
                  className="bg-muted"
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="fullName" className="text-sm font-medium">
                  Full Name
                </label>
                <Input
                  id="fullName"
                  type="text"
                  placeholder="Your full name"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                  required
                  disabled={isSubmitting}
                />
              </div>

              <div className="space-y-2">
                <label htmlFor="password" className="text-sm font-medium">
                  Password
                </label>
                <div className="relative">
                  <Input
                    id="password"
                    type={showPassword ? 'text' : 'password'}
                    placeholder="••••••••"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    required
                    disabled={isSubmitting}
                    minLength={8}
                    className="pr-10"
                  />
                  <button
                    type="button"
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground"
                  >
                    {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </button>
                </div>
              </div>

              <div className="space-y-2">
                <label htmlFor="confirmPassword" className="text-sm font-medium">
                  Confirm Password
                </label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  disabled={isSubmitting}
                  minLength={8}
                />
              </div>

              <Button type="submit" className="w-full" disabled={isSubmitting}>
                {isSubmitting ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    Creating account...
                  </>
                ) : (
                  'Create Account & Join'
                )}
              </Button>
            </form>

            <div className="relative">
              <div className="absolute inset-0 flex items-center">
                <div className="w-full border-t" />
              </div>
              <div className="relative flex justify-center text-xs uppercase">
                <span className="bg-background px-2 text-muted-foreground">
                  Already have an account?
                </span>
              </div>
            </div>

            <Button variant="outline" className="w-full" asChild>
              <Link href={`/login?invite=${token}`}>
                Sign in to accept
              </Link>
            </Button>
          </>
        )}

        {/* Expiry notice */}
        <p className="text-center text-xs text-muted-foreground">
          This invitation expires on{' '}
          {new Date(inviteDetails.expires_at).toLocaleDateString(undefined, {
            dateStyle: 'medium',
          })}
        </p>
      </div>
    </div>
  );
}
