'use client';

import { useState, useEffect } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Sparkles,
  Loader2,
  CheckCircle,
  Users,
  FolderOpen,
  Bot,
  Zap,
  Shield,
} from 'lucide-react';
import { toast } from 'sonner';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { organizationsApi, trialsApi, TenantContext } from '@/lib/api';
import { useAuthStore } from '@/store/auth';

const TRIAL_FEATURES = [
  {
    icon: Users,
    title: 'Up to 50 Team Members',
    description: 'Collaborate with your entire team',
  },
  {
    icon: FolderOpen,
    title: 'Up to 20 Projects',
    description: 'Organize your work efficiently',
  },
  {
    icon: Bot,
    title: 'Advanced AI Agents',
    description: 'Custom agents with MCP integration',
  },
  {
    icon: Zap,
    title: 'DevOps Analytics',
    description: 'DORA metrics and insights',
  },
  {
    icon: Shield,
    title: 'Enterprise Security',
    description: 'SSO, audit logs, and compliance',
  },
];

function generateSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 50);
}

export default function StartTrialPage() {
  const router = useRouter();
  const { user, isAuthenticated } = useAuthStore();
  const [isLoading, setIsLoading] = useState(false);
  const [formData, setFormData] = useState({
    name: '',
    slug: '',
  });

  // Auto-generate slug from name
  useEffect(() => {
    if (formData.name) {
      setFormData((prev) => ({
        ...prev,
        slug: generateSlug(prev.name),
      }));
    }
  }, [formData.name]);

  // Redirect if not authenticated
  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/register?redirect=/start-trial');
    }
  }, [isAuthenticated, router]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!formData.name.trim()) {
      toast.error('Please enter an organization name');
      return;
    }

    setIsLoading(true);

    try {
      // Step 1: Create the organization
      const org = await organizationsApi.create({
        name: formData.name,
        slug: formData.slug || generateSlug(formData.name),
      });

      // Step 2: Switch to the new organization context
      TenantContext.setCurrentTenantId(org.id);

      // Step 3: Start the trial
      await trialsApi.startTrial(org.id);

      toast.success('Trial started! Welcome to NexusAI.');

      // Redirect to chat
      router.push('/chat');
    } catch (error: unknown) {
      const message = error instanceof Error ? error.message : 'Failed to start trial';
      toast.error(message);
    } finally {
      setIsLoading(false);
    }
  };

  if (!isAuthenticated) {
    return (
      <div className="flex min-h-screen items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-primary" />
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-gradient-to-br from-background to-muted">
      {/* Left side - Form */}
      <div className="flex flex-1 flex-col justify-center px-8 py-12 lg:px-16">
        <div className="mx-auto w-full max-w-md space-y-8">
          {/* Logo */}
          <div>
            <Link href="/" className="inline-flex items-center gap-2">
              <Sparkles className="h-8 w-8 text-primary" />
              <span className="text-2xl font-bold">NexusAI</span>
            </Link>
            <h1 className="mt-8 text-3xl font-bold tracking-tight">
              Start your free trial
            </h1>
            <p className="mt-2 text-muted-foreground">
              Get full access to NexusAI Professional for 14 days. No credit
              card required.
            </p>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="space-y-6">
            <div className="space-y-2">
              <label htmlFor="name" className="text-sm font-medium">
                Organization Name
              </label>
              <Input
                id="name"
                name="name"
                type="text"
                placeholder="Acme Inc."
                value={formData.name}
                onChange={handleChange}
                required
                disabled={isLoading}
                className="h-12"
              />
            </div>

            <div className="space-y-2">
              <label htmlFor="slug" className="text-sm font-medium">
                Organization URL
              </label>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">
                  nexusai.app/
                </span>
                <Input
                  id="slug"
                  name="slug"
                  type="text"
                  placeholder="acme-inc"
                  value={formData.slug}
                  onChange={handleChange}
                  disabled={isLoading}
                  className="h-12"
                />
              </div>
              <p className="text-xs text-muted-foreground">
                This will be your organization's unique URL
              </p>
            </div>

            <Button
              type="submit"
              className="h-12 w-full text-base"
              disabled={isLoading}
            >
              {isLoading ? (
                <>
                  <Loader2 className="mr-2 h-5 w-5 animate-spin" />
                  Creating your workspace...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-5 w-5" />
                  Start Free Trial
                </>
              )}
            </Button>
          </form>

          {/* User info */}
          {user && (
            <p className="text-center text-sm text-muted-foreground">
              Signed in as <span className="font-medium">{user.email}</span>
            </p>
          )}
        </div>
      </div>

      {/* Right side - Features */}
      <div className="hidden flex-1 bg-primary/5 lg:flex lg:flex-col lg:justify-center lg:px-16">
        <div className="mx-auto max-w-md space-y-8">
          <div>
            <h2 className="text-2xl font-semibold">
              Everything you need to build with AI
            </h2>
            <p className="mt-2 text-muted-foreground">
              Your trial includes full access to Professional tier features
            </p>
          </div>

          <div className="space-y-6">
            {TRIAL_FEATURES.map((feature) => (
              <div key={feature.title} className="flex gap-4">
                <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10">
                  <feature.icon className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <h3 className="font-medium">{feature.title}</h3>
                  <p className="text-sm text-muted-foreground">
                    {feature.description}
                  </p>
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-lg bg-background/50 p-4">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-5 w-5 text-green-500" />
              <span className="font-medium">14-day free trial</span>
            </div>
            <p className="mt-1 text-sm text-muted-foreground">
              No credit card required. Cancel anytime.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
