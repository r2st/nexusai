'use client';

/**
 * Admin Dashboard Page
 *
 * Overview of platform statistics and quick actions for administrators.
 */

import { useState, useEffect } from 'react';
import Link from 'next/link';
import {
  Users,
  Building2,
  Activity,
  TrendingUp,
  AlertCircle,
  Clock,
  Shield,
  ArrowRight,
} from 'lucide-react';
import { api } from '@/lib/api';

interface DashboardStats {
  totalUsers: number;
  activeUsers: number;
  totalOrganizations: number;
  activeTrials: number;
  newUsersToday: number;
  pendingVerifications: number;
}

interface RecentActivity {
  id: string;
  type: 'user_created' | 'org_created' | 'trial_started' | 'subscription_changed';
  description: string;
  timestamp: string;
}

export default function AdminDashboardPage() {
  const [stats, setStats] = useState<DashboardStats>({
    totalUsers: 0,
    activeUsers: 0,
    totalOrganizations: 0,
    activeTrials: 0,
    newUsersToday: 0,
    pendingVerifications: 0,
  });
  const [recentActivity, setRecentActivity] = useState<RecentActivity[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // In production, these would be actual API calls
        // const statsResponse = await api.get('/admin/stats');
        // const activityResponse = await api.get('/admin/activity');

        // Mock data for now
        setStats({
          totalUsers: 1247,
          activeUsers: 892,
          totalOrganizations: 156,
          activeTrials: 34,
          newUsersToday: 12,
          pendingVerifications: 5,
        });

        setRecentActivity([
          {
            id: '1',
            type: 'user_created',
            description: 'New user registered: john@example.com',
            timestamp: new Date().toISOString(),
          },
          {
            id: '2',
            type: 'org_created',
            description: 'Organization created: Acme Corp',
            timestamp: new Date(Date.now() - 3600000).toISOString(),
          },
          {
            id: '3',
            type: 'trial_started',
            description: 'Trial started for: TechStartup Inc',
            timestamp: new Date(Date.now() - 7200000).toISOString(),
          },
        ]);
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  const statCards = [
    {
      label: 'Total Users',
      value: stats.totalUsers,
      icon: <Users className="h-5 w-5" />,
      href: '/admin/users',
      color: 'bg-blue-500/10 text-blue-500',
    },
    {
      label: 'Active Users',
      value: stats.activeUsers,
      icon: <Activity className="h-5 w-5" />,
      href: '/admin/users?status=active',
      color: 'bg-green-500/10 text-green-500',
    },
    {
      label: 'Organizations',
      value: stats.totalOrganizations,
      icon: <Building2 className="h-5 w-5" />,
      href: '/admin/organizations',
      color: 'bg-purple-500/10 text-purple-500',
    },
    {
      label: 'Active Trials',
      value: stats.activeTrials,
      icon: <TrendingUp className="h-5 w-5" />,
      href: '/admin/organizations?filter=trials',
      color: 'bg-orange-500/10 text-orange-500',
    },
  ];

  const getActivityIcon = (type: RecentActivity['type']) => {
    switch (type) {
      case 'user_created':
        return <Users className="h-4 w-4 text-blue-500" />;
      case 'org_created':
        return <Building2 className="h-4 w-4 text-purple-500" />;
      case 'trial_started':
        return <Clock className="h-4 w-4 text-orange-500" />;
      case 'subscription_changed':
        return <TrendingUp className="h-4 w-4 text-green-500" />;
      default:
        return <Activity className="h-4 w-4 text-muted-foreground" />;
    }
  };

  const formatTimeAgo = (timestamp: string) => {
    const diff = Date.now() - new Date(timestamp).getTime();
    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (days > 0) return `${days}d ago`;
    if (hours > 0) return `${hours}h ago`;
    if (minutes > 0) return `${minutes}m ago`;
    return 'Just now';
  };

  if (isLoading) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {[1, 2, 3, 4].map((i) => (
            <div key={i} className="h-32 bg-muted rounded-lg animate-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold">Admin Dashboard</h1>
          <p className="text-muted-foreground">Platform overview and management</p>
        </div>
        <Link
          href="/admin/users/new"
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors"
        >
          <Users className="h-4 w-4" />
          Add User
        </Link>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {statCards.map((stat) => (
          <Link
            key={stat.label}
            href={stat.href}
            className="p-6 bg-card border rounded-lg hover:shadow-md transition-shadow"
          >
            <div className="flex items-center justify-between mb-4">
              <div className={`p-2 rounded-lg ${stat.color}`}>{stat.icon}</div>
              <ArrowRight className="h-4 w-4 text-muted-foreground" />
            </div>
            <div className="text-2xl font-bold">{stat.value.toLocaleString()}</div>
            <div className="text-sm text-muted-foreground">{stat.label}</div>
          </Link>
        ))}
      </div>

      {/* Quick Stats & Activity */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Quick Stats */}
        <div className="p-6 bg-card border rounded-lg">
          <h2 className="text-lg font-semibold mb-4">Today's Activity</h2>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Users className="h-4 w-4 text-blue-500" />
                </div>
                <span>New Users Today</span>
              </div>
              <span className="font-semibold">{stats.newUsersToday}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-yellow-500/10 rounded-lg">
                  <AlertCircle className="h-4 w-4 text-yellow-500" />
                </div>
                <span>Pending Verifications</span>
              </div>
              <span className="font-semibold">{stats.pendingVerifications}</span>
            </div>
            <div className="flex items-center justify-between p-3 bg-muted/50 rounded-lg">
              <div className="flex items-center gap-3">
                <div className="p-2 bg-green-500/10 rounded-lg">
                  <Shield className="h-4 w-4 text-green-500" />
                </div>
                <span>Active Sessions</span>
              </div>
              <span className="font-semibold">{stats.activeUsers}</span>
            </div>
          </div>
        </div>

        {/* Recent Activity */}
        <div className="p-6 bg-card border rounded-lg">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold">Recent Activity</h2>
            <Link
              href="/admin/analytics"
              className="text-sm text-primary hover:underline"
            >
              View All
            </Link>
          </div>
          <div className="space-y-3">
            {recentActivity.map((activity) => (
              <div
                key={activity.id}
                className="flex items-center gap-3 p-3 bg-muted/50 rounded-lg"
              >
                <div className="p-2 bg-background rounded-lg">
                  {getActivityIcon(activity.type)}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="text-sm truncate">{activity.description}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatTimeAgo(activity.timestamp)}
                  </p>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="p-6 bg-card border rounded-lg">
        <h2 className="text-lg font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <Link
            href="/admin/users/new"
            className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
          >
            <Users className="h-4 w-4 text-primary" />
            <span className="text-sm">Add User</span>
          </Link>
          <Link
            href="/admin/organizations/new"
            className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
          >
            <Building2 className="h-4 w-4 text-primary" />
            <span className="text-sm">Add Organization</span>
          </Link>
          <Link
            href="/admin/users?filter=unverified"
            className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
          >
            <AlertCircle className="h-4 w-4 text-primary" />
            <span className="text-sm">Review Pending</span>
          </Link>
          <Link
            href="/admin/settings"
            className="flex items-center gap-2 p-3 bg-muted/50 rounded-lg hover:bg-muted transition-colors"
          >
            <Shield className="h-4 w-4 text-primary" />
            <span className="text-sm">System Settings</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
