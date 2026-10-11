'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  ArrowUpRight,
  BarChart3,
  Clock,
  GitBranch,
  Activity,
  AlertTriangle,
  ExternalLink,
  Settings,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FloatingAssistant } from '@/components/assistant';

interface DORAMetrics {
  deploymentFrequency: number | null;
  leadTimeForChanges: number | null;
  meanTimeToRecovery: number | null;
  changeFailureRate: number | null;
}

interface DevLakeStatus {
  available: boolean;
  message: string;
}

export default function AnalyticsPage() {
  const [status, setStatus] = useState<DevLakeStatus | null>(null);
  const [metrics, setMetrics] = useState<DORAMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  const devlakeUrl = process.env.NEXT_PUBLIC_DEVLAKE_URL || 'http://localhost:4000';
  const grafanaUrl = process.env.NEXT_PUBLIC_GRAFANA_URL || 'http://localhost:3002';

  useEffect(() => {
    checkDevLakeStatus();
  }, []);

  const checkDevLakeStatus = async () => {
    setIsLoading(true);
    try {
      const response = await fetch('/api/v1/analytics/health');
      if (response.ok) {
        const data = await response.json();
        setStatus({
          available: data.devlake_available,
          message: data.message,
        });
      } else {
        setStatus({ available: false, message: 'Failed to check DevLake status' });
      }
    } catch {
      setStatus({ available: false, message: 'DevLake is not available' });
    } finally {
      setIsLoading(false);
    }
  };

  const getDORALevel = (metric: string, value: number | null): { level: string; color: string } => {
    if (value === null) return { level: 'N/A', color: 'text-muted-foreground' };

    switch (metric) {
      case 'deploymentFrequency':
        if (value >= 1) return { level: 'Elite', color: 'text-green-500' };
        if (value >= 0.14) return { level: 'High', color: 'text-blue-500' };
        if (value >= 0.03) return { level: 'Medium', color: 'text-yellow-500' };
        return { level: 'Low', color: 'text-red-500' };

      case 'leadTimeForChanges':
        if (value <= 24) return { level: 'Elite', color: 'text-green-500' };
        if (value <= 168) return { level: 'High', color: 'text-blue-500' };
        if (value <= 720) return { level: 'Medium', color: 'text-yellow-500' };
        return { level: 'Low', color: 'text-red-500' };

      case 'meanTimeToRecovery':
        if (value <= 1) return { level: 'Elite', color: 'text-green-500' };
        if (value <= 24) return { level: 'High', color: 'text-blue-500' };
        if (value <= 168) return { level: 'Medium', color: 'text-yellow-500' };
        return { level: 'Low', color: 'text-red-500' };

      case 'changeFailureRate':
        if (value <= 5) return { level: 'Elite', color: 'text-green-500' };
        if (value <= 10) return { level: 'High', color: 'text-blue-500' };
        if (value <= 15) return { level: 'Medium', color: 'text-yellow-500' };
        return { level: 'Low', color: 'text-red-500' };

      default:
        return { level: 'N/A', color: 'text-muted-foreground' };
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <BarChart3 className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">GSTIndia Analytics</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={checkDevLakeStatus}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Link href="/chat">
              <Button variant="ghost" size="sm">
                Go to Chat
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Status Banner */}
        <div
          className={`mb-8 rounded-lg p-4 ${
            status?.available
              ? 'bg-green-50 border border-green-200 dark:bg-green-950 dark:border-green-800'
              : 'bg-yellow-50 border border-yellow-200 dark:bg-yellow-950 dark:border-yellow-800'
          }`}
        >
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity
                className={`h-5 w-5 ${
                  status?.available ? 'text-green-600' : 'text-yellow-600'
                }`}
              />
              <span className="font-medium">
                {isLoading
                  ? 'Checking DevLake status...'
                  : status?.message || 'Unknown status'}
              </span>
            </div>
            {status?.available && (
              <div className="flex gap-2">
                <a href={devlakeUrl} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm">
                    <Settings className="mr-2 h-4 w-4" />
                    Configure DevLake
                    <ExternalLink className="ml-2 h-3 w-3" />
                  </Button>
                </a>
                <a href={grafanaUrl} target="_blank" rel="noopener noreferrer">
                  <Button variant="outline" size="sm">
                    <BarChart3 className="mr-2 h-4 w-4" />
                    Open Grafana
                    <ExternalLink className="ml-2 h-3 w-3" />
                  </Button>
                </a>
              </div>
            )}
          </div>
        </div>

        {/* DORA Metrics */}
        <section className="mb-8">
          <h2 className="mb-4 text-2xl font-bold">DORA Metrics</h2>
          <p className="mb-6 text-muted-foreground">
            DevOps Research and Assessment (DORA) metrics help measure software
            delivery performance.
          </p>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            {/* Deployment Frequency */}
            <div className="rounded-lg border bg-card p-6">
              <div className="flex items-center gap-2 text-muted-foreground">
                <GitBranch className="h-4 w-4" />
                <span className="text-sm">Deployment Frequency</span>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-bold">
                  {metrics?.deploymentFrequency?.toFixed(2) || '—'}
                </div>
                <div className="text-sm text-muted-foreground">per day</div>
              </div>
              <div className="mt-2">
                <span
                  className={`text-sm font-medium ${
                    getDORALevel('deploymentFrequency', metrics?.deploymentFrequency ?? null).color
                  }`}
                >
                  {getDORALevel('deploymentFrequency', metrics?.deploymentFrequency ?? null).level}{' '}
                  Performer
                </span>
              </div>
            </div>

            {/* Lead Time for Changes */}
            <div className="rounded-lg border bg-card p-6">
              <div className="flex items-center gap-2 text-muted-foreground">
                <Clock className="h-4 w-4" />
                <span className="text-sm">Lead Time for Changes</span>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-bold">
                  {metrics?.leadTimeForChanges?.toFixed(1) || '—'}
                </div>
                <div className="text-sm text-muted-foreground">hours</div>
              </div>
              <div className="mt-2">
                <span
                  className={`text-sm font-medium ${
                    getDORALevel('leadTimeForChanges', metrics?.leadTimeForChanges ?? null).color
                  }`}
                >
                  {getDORALevel('leadTimeForChanges', metrics?.leadTimeForChanges ?? null).level}{' '}
                  Performer
                </span>
              </div>
            </div>

            {/* Mean Time to Recovery */}
            <div className="rounded-lg border bg-card p-6">
              <div className="flex items-center gap-2 text-muted-foreground">
                <ArrowUpRight className="h-4 w-4" />
                <span className="text-sm">Mean Time to Recovery</span>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-bold">
                  {metrics?.meanTimeToRecovery?.toFixed(1) || '—'}
                </div>
                <div className="text-sm text-muted-foreground">hours</div>
              </div>
              <div className="mt-2">
                <span
                  className={`text-sm font-medium ${
                    getDORALevel('meanTimeToRecovery', metrics?.meanTimeToRecovery ?? null).color
                  }`}
                >
                  {getDORALevel('meanTimeToRecovery', metrics?.meanTimeToRecovery ?? null).level}{' '}
                  Performer
                </span>
              </div>
            </div>

            {/* Change Failure Rate */}
            <div className="rounded-lg border bg-card p-6">
              <div className="flex items-center gap-2 text-muted-foreground">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm">Change Failure Rate</span>
              </div>
              <div className="mt-4">
                <div className="text-3xl font-bold">
                  {metrics?.changeFailureRate?.toFixed(1) || '—'}
                </div>
                <div className="text-sm text-muted-foreground">%</div>
              </div>
              <div className="mt-2">
                <span
                  className={`text-sm font-medium ${
                    getDORALevel('changeFailureRate', metrics?.changeFailureRate ?? null).color
                  }`}
                >
                  {getDORALevel('changeFailureRate', metrics?.changeFailureRate ?? null).level}{' '}
                  Performer
                </span>
              </div>
            </div>
          </div>
        </section>

        {/* Quick Links */}
        <section className="mb-8">
          <h2 className="mb-4 text-2xl font-bold">Quick Actions</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <a
              href={devlakeUrl}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Settings className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">Configure Data Sources</div>
                <div className="text-sm text-muted-foreground">
                  Connect GitHub, Jira, Jenkins, and more
                </div>
              </div>
              <ExternalLink className="ml-auto h-4 w-4 text-muted-foreground" />
            </a>

            <a
              href={`${grafanaUrl}/dashboards`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <BarChart3 className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">View Dashboards</div>
                <div className="text-sm text-muted-foreground">
                  60+ pre-built Grafana dashboards
                </div>
              </div>
              <ExternalLink className="ml-auto h-4 w-4 text-muted-foreground" />
            </a>

            <Link
              href="/chat"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">Ask AI About Metrics</div>
                <div className="text-sm text-muted-foreground">
                  Chat with AI about your analytics
                </div>
              </div>
              <ArrowUpRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>
          </div>
        </section>

        {/* Supported Plugins */}
        <section>
          <h2 className="mb-4 text-2xl font-bold">Supported Data Sources</h2>
          <p className="mb-6 text-muted-foreground">
            DevLake supports 40+ plugins to collect data from your development tools.
          </p>
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 md:grid-cols-6 lg:grid-cols-8">
            {[
              'GitHub',
              'GitLab',
              'Bitbucket',
              'Jira',
              'Jenkins',
              'Azure DevOps',
              'CircleCI',
              'PagerDuty',
              'SonarQube',
              'Bamboo',
              'Zentao',
              'Tapd',
              'Feishu',
              'Slack',
              'Teambition',
              'Trello',
            ].map((plugin) => (
              <div
                key={plugin}
                className="rounded-lg border bg-card p-3 text-center text-sm"
              >
                {plugin}
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* AI Assistant */}
      <FloatingAssistant context="analytics" />
    </div>
  );
}
