'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  BarChart3,
  MessageSquare,
  FileText,
  Bot,
  Users,
  TrendingUp,
  TrendingDown,
  Minus,
  RefreshCw,
  Loader2,
  Calendar,
  Zap,
  CreditCard,
  AlertTriangle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import {
  subscriptionsApi,
  organizationsApi,
  type UsageSummary,
} from '@/lib/api';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface UsageMetric {
  label: string;
  current: number;
  limit: number | null;
  unit: string;
  icon: typeof MessageSquare;
  trend?: number; // percentage change
}

interface DailyUsage {
  date: string;
  conversations: number;
  messages: number;
  documents: number;
  tokens: number;
}

export default function UsagePage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [isLoading, setIsLoading] = useState(true);
  const [usage, setUsage] = useState<UsageSummary | null>(null);
  const [period, setPeriod] = useState<'7d' | '30d' | '90d'>('30d');
  const [dailyUsage, setDailyUsage] = useState<DailyUsage[]>([]);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const loadUsage = useCallback(async () => {
    setIsLoading(true);
    try {
      const orgId = organizationsApi.getCurrentId();
      if (orgId) {
        const usageData = await subscriptionsApi.getUsage(orgId);
        setUsage(usageData);

        // Generate mock daily usage data for the chart
        const days = period === '7d' ? 7 : period === '30d' ? 30 : 90;
        const mockDaily: DailyUsage[] = [];
        for (let i = days - 1; i >= 0; i--) {
          const date = new Date();
          date.setDate(date.getDate() - i);
          mockDaily.push({
            date: date.toISOString().split('T')[0],
            conversations: Math.floor(Math.random() * 20) + 5,
            messages: Math.floor(Math.random() * 100) + 20,
            documents: Math.floor(Math.random() * 5),
            tokens: Math.floor(Math.random() * 50000) + 10000,
          });
        }
        setDailyUsage(mockDaily);
      }
    } catch (error) {
      console.error('Failed to load usage:', error);
      toast.error('Failed to load usage data');
    } finally {
      setIsLoading(false);
    }
  }, [period]);

  useEffect(() => {
    if (isAuthenticated) {
      loadUsage();
    }
  }, [isAuthenticated, loadUsage]);

  if (!isAuthenticated) return null;

  const metrics: UsageMetric[] = [
    {
      label: 'Team Members',
      current: usage?.members.current || 0,
      limit: usage?.members.max || null,
      unit: 'members',
      icon: Users,
      trend: 0,
    },
    {
      label: 'Projects',
      current: usage?.projects.current || 0,
      limit: usage?.projects.max || null,
      unit: 'projects',
      icon: FileText,
      trend: 5,
    },
    {
      label: 'Conversations',
      current: dailyUsage.reduce((sum, d) => sum + d.conversations, 0),
      limit: null,
      unit: 'this period',
      icon: MessageSquare,
      trend: 12,
    },
    {
      label: 'AI Messages',
      current: dailyUsage.reduce((sum, d) => sum + d.messages, 0),
      limit: null,
      unit: 'this period',
      icon: Bot,
      trend: 8,
    },
  ];

  const totalTokens = dailyUsage.reduce((sum, d) => sum + d.tokens, 0);
  const avgTokensPerDay = dailyUsage.length > 0 ? Math.round(totalTokens / dailyUsage.length) : 0;

  const getTrendIcon = (trend?: number) => {
    if (!trend || trend === 0) return <Minus className="h-4 w-4 text-muted-foreground" />;
    if (trend > 0) return <TrendingUp className="h-4 w-4 text-green-500" />;
    return <TrendingDown className="h-4 w-4 text-red-500" />;
  };

  const getProgressColor = (percentage: number) => {
    if (percentage >= 90) return 'bg-red-500';
    if (percentage >= 70) return 'bg-yellow-500';
    return 'bg-primary';
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Usage</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadUsage}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Link href="/settings">
              <Button variant="ghost" size="sm">
                Settings
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <>
            {/* Plan Info */}
            <div className="mb-8 flex flex-col md:flex-row md:items-center md:justify-between gap-4">
              <div>
                <h1 className="text-2xl font-bold">Usage Dashboard</h1>
                <p className="text-muted-foreground mt-1">
                  Monitor your team&apos;s AI usage and resource consumption
                </p>
              </div>
              <div className="flex items-center gap-4">
                {/* Period Selector */}
                <div className="flex items-center gap-1 rounded-lg border p-1">
                  {(['7d', '30d', '90d'] as const).map((p) => (
                    <button
                      key={p}
                      onClick={() => setPeriod(p)}
                      className={cn(
                        'px-3 py-1 text-sm font-medium rounded-md transition-colors',
                        period === p
                          ? 'bg-primary text-primary-foreground'
                          : 'hover:bg-muted'
                      )}
                    >
                      {p === '7d' ? '7 days' : p === '30d' ? '30 days' : '90 days'}
                    </button>
                  ))}
                </div>

                {/* Plan Badge */}
                <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-primary/10">
                  <Zap className="h-4 w-4 text-primary" />
                  <span className="text-sm font-medium capitalize">
                    {usage?.tier || 'Free'} Plan
                  </span>
                </div>
              </div>
            </div>

            {/* Warning Banner */}
            {usage && (usage.members.at_limit || usage.projects.at_limit) && (
              <div className="mb-8 rounded-lg border border-yellow-200 bg-yellow-50 dark:border-yellow-900 dark:bg-yellow-950 p-4">
                <div className="flex gap-3">
                  <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 shrink-0 mt-0.5" />
                  <div>
                    <h3 className="font-medium text-yellow-900 dark:text-yellow-100">
                      Approaching Limits
                    </h3>
                    <p className="text-sm text-yellow-700 dark:text-yellow-300 mt-1">
                      You&apos;re close to your plan limits. Consider upgrading to continue growing.
                    </p>
                    <Link href="/pricing">
                      <Button size="sm" variant="outline" className="mt-2">
                        <CreditCard className="mr-2 h-4 w-4" />
                        Upgrade Plan
                      </Button>
                    </Link>
                  </div>
                </div>
              </div>
            )}

            {/* Metrics Grid */}
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4 mb-8">
              {metrics.map((metric) => {
                const Icon = metric.icon;
                const percentage = metric.limit
                  ? Math.round((metric.current / metric.limit) * 100)
                  : null;

                return (
                  <div
                    key={metric.label}
                    className="rounded-lg border bg-card p-4"
                  >
                    <div className="flex items-center justify-between mb-2">
                      <div className="flex items-center gap-2 text-muted-foreground">
                        <Icon className="h-4 w-4" />
                        <span className="text-sm">{metric.label}</span>
                      </div>
                      <div className="flex items-center gap-1">
                        {getTrendIcon(metric.trend)}
                        {metric.trend !== undefined && metric.trend !== 0 && (
                          <span
                            className={cn(
                              'text-xs font-medium',
                              metric.trend > 0 ? 'text-green-500' : 'text-red-500'
                            )}
                          >
                            {metric.trend > 0 ? '+' : ''}{metric.trend}%
                          </span>
                        )}
                      </div>
                    </div>

                    <div className="text-2xl font-bold">
                      {metric.current.toLocaleString()}
                      {metric.limit && (
                        <span className="text-sm font-normal text-muted-foreground">
                          {' '}/ {metric.limit}
                        </span>
                      )}
                    </div>

                    {percentage !== null && (
                      <div className="mt-2">
                        <div
                          className="h-2 rounded-full bg-muted overflow-hidden"
                          role="progressbar"
                          aria-valuenow={metric.current}
                          aria-valuemax={metric.limit || undefined}
                          aria-label={`${metric.label} usage`}
                        >
                          <div
                            className={cn(
                              'h-full rounded-full transition-all',
                              getProgressColor(percentage)
                            )}
                            style={{ width: `${Math.min(percentage, 100)}%` }}
                          />
                        </div>
                        <p className="text-xs text-muted-foreground mt-1">
                          {percentage}% used
                        </p>
                      </div>
                    )}

                    {!metric.limit && (
                      <p className="text-xs text-muted-foreground mt-2">
                        {metric.unit}
                      </p>
                    )}
                  </div>
                );
              })}
            </div>

            {/* Token Usage */}
            <div className="grid gap-8 lg:grid-cols-2 mb-8">
              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">Token Consumption</h2>
                <div className="space-y-4">
                  <div>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-sm text-muted-foreground">Total Tokens</span>
                      <span className="font-medium">{totalTokens.toLocaleString()}</span>
                    </div>
                    <div className="h-2 rounded-full bg-muted overflow-hidden">
                      <div className="h-full w-3/4 rounded-full bg-primary" />
                    </div>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t">
                    <div>
                      <p className="text-sm text-muted-foreground">Avg. per day</p>
                      <p className="text-xl font-bold">{avgTokensPerDay.toLocaleString()}</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Est. monthly</p>
                      <p className="text-xl font-bold">
                        {(avgTokensPerDay * 30).toLocaleString()}
                      </p>
                    </div>
                  </div>
                </div>
              </div>

              <div className="rounded-lg border bg-card p-6">
                <h2 className="text-lg font-semibold mb-4">Cost Estimate</h2>
                <div className="space-y-4">
                  <div className="text-center py-4">
                    <p className="text-3xl font-bold">
                      ${((totalTokens / 1000) * 0.002).toFixed(2)}
                    </p>
                    <p className="text-sm text-muted-foreground mt-1">
                      Estimated cost this period
                    </p>
                  </div>
                  <div className="grid grid-cols-2 gap-4 pt-4 border-t text-center">
                    <div>
                      <p className="text-sm text-muted-foreground">Per 1K tokens</p>
                      <p className="font-medium">$0.002</p>
                    </div>
                    <div>
                      <p className="text-sm text-muted-foreground">Monthly est.</p>
                      <p className="font-medium">
                        ${((avgTokensPerDay * 30 / 1000) * 0.002).toFixed(2)}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Usage Chart (Simple bar representation) */}
            <div className="rounded-lg border bg-card p-6">
              <div className="flex items-center justify-between mb-4">
                <h2 className="text-lg font-semibold">Daily Activity</h2>
                <div className="flex items-center gap-4 text-sm">
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded bg-primary" />
                    <span className="text-muted-foreground">Messages</span>
                  </div>
                  <div className="flex items-center gap-2">
                    <div className="h-3 w-3 rounded bg-blue-500" />
                    <span className="text-muted-foreground">Conversations</span>
                  </div>
                </div>
              </div>

              {/* Simple bar chart */}
              <div className="h-48 flex items-end gap-1">
                {dailyUsage.slice(-14).map((day, index) => {
                  const maxMessages = Math.max(...dailyUsage.map((d) => d.messages));
                  const height = (day.messages / maxMessages) * 100;
                  return (
                    <div
                      key={day.date}
                      className="flex-1 flex flex-col items-center gap-1"
                    >
                      <div
                        className="w-full bg-primary/80 rounded-t hover:bg-primary transition-colors"
                        style={{ height: `${height}%` }}
                        title={`${day.messages} messages on ${day.date}`}
                      />
                      {index % 2 === 0 && (
                        <span className="text-[10px] text-muted-foreground">
                          {new Date(day.date).getDate()}
                        </span>
                      )}
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Quick Links */}
            <div className="mt-8 grid gap-4 md:grid-cols-3">
              <Link
                href="/pricing"
                className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
              >
                <CreditCard className="h-8 w-8 text-primary mb-2" />
                <h3 className="font-medium">Upgrade Plan</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Get more resources and features
                </p>
              </Link>
              <Link
                href="/api-keys"
                className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
              >
                <Zap className="h-8 w-8 text-primary mb-2" />
                <h3 className="font-medium">API Access</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage your API keys
                </p>
              </Link>
              <Link
                href="/team"
                className="rounded-lg border p-4 hover:bg-muted/50 transition-colors"
              >
                <Users className="h-8 w-8 text-primary mb-2" />
                <h3 className="font-medium">Team Settings</h3>
                <p className="text-sm text-muted-foreground mt-1">
                  Manage team members
                </p>
              </Link>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
