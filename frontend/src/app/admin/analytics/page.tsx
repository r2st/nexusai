'use client';

import { useState, useEffect } from 'react';
import {
  BarChart3,
  Users,
  MessageSquare,
  FileText,
  TrendingUp,
  Activity,
  Loader2,
} from 'lucide-react';
import { api } from '@/lib/api';
import { toast } from 'sonner';

interface PlatformMetrics {
  totalConversations: number;
  totalMessages: number;
  totalDocuments: number;
  activeUsersToday: number;
  avgResponseTime: string;
  tokenUsage: number;
}

export default function AdminAnalyticsPage() {
  const [metrics, setMetrics] = useState<PlatformMetrics | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [timeRange, setTimeRange] = useState<'7d' | '30d' | '90d'>('30d');

  useEffect(() => {
    loadMetrics();
  }, [timeRange]);

  const loadMetrics = async () => {
    setIsLoading(true);
    try {
      const response = await api.get('/admin/analytics', {
        params: { range: timeRange },
      });
      setMetrics(response.data);
    } catch {
      setMetrics({
        totalConversations: 0,
        totalMessages: 0,
        totalDocuments: 0,
        activeUsersToday: 0,
        avgResponseTime: '—',
        tokenUsage: 0,
      });
      toast.error('Failed to load analytics data');
    } finally {
      setIsLoading(false);
    }
  };

  const statCards = metrics
    ? [
        {
          label: 'Total Conversations',
          value: metrics.totalConversations.toLocaleString(),
          icon: MessageSquare,
          color: 'text-blue-500',
        },
        {
          label: 'Total Messages',
          value: metrics.totalMessages.toLocaleString(),
          icon: Activity,
          color: 'text-green-500',
        },
        {
          label: 'Documents Processed',
          value: metrics.totalDocuments.toLocaleString(),
          icon: FileText,
          color: 'text-purple-500',
        },
        {
          label: 'Active Users Today',
          value: metrics.activeUsersToday.toLocaleString(),
          icon: Users,
          color: 'text-orange-500',
        },
        {
          label: 'Avg Response Time',
          value: metrics.avgResponseTime,
          icon: TrendingUp,
          color: 'text-cyan-500',
        },
        {
          label: 'Token Usage',
          value: metrics.tokenUsage.toLocaleString(),
          icon: BarChart3,
          color: 'text-pink-500',
        },
      ]
    : [];

  return (
    <div>
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Platform Analytics</h1>
          <p className="text-muted-foreground mt-1">
            Usage statistics and platform performance
          </p>
        </div>
        <div className="flex gap-1 rounded-lg border bg-muted/50 p-1">
          {(['7d', '30d', '90d'] as const).map((range) => (
            <button
              key={range}
              onClick={() => setTimeRange(range)}
              className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                timeRange === range
                  ? 'bg-background shadow-sm font-medium'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              {range === '7d' ? '7 Days' : range === '30d' ? '30 Days' : '90 Days'}
            </button>
          ))}
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
        </div>
      ) : (
        <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
          {statCards.map((card) => (
            <div
              key={card.label}
              className="rounded-xl border bg-card p-6"
            >
              <div className="flex items-center gap-3 mb-4">
                <div className={`p-2 rounded-lg bg-muted ${card.color}`}>
                  <card.icon className="h-5 w-5" />
                </div>
                <p className="text-sm text-muted-foreground">{card.label}</p>
              </div>
              <p className="text-3xl font-bold">{card.value}</p>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
