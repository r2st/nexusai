'use client';

import { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  ScrollText,
  Search,
  Filter,
  Download,
  RefreshCw,
  Loader2,
  User,
  Settings,
  Key,
  FileText,
  MessageSquare,
  Shield,
  AlertTriangle,
  LogIn,
  LogOut,
  UserPlus,
  Trash2,
  Edit,
  Eye,
  Calendar,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { cn, formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';

interface AuditLogEntry {
  id: string;
  timestamp: string;
  action: string;
  actor: {
    id: string;
    name: string;
    email: string;
  };
  resource_type: string;
  resource_id: string;
  resource_name?: string;
  ip_address: string;
  user_agent: string;
  metadata: Record<string, unknown>;
  severity: 'info' | 'warning' | 'critical';
}

const getActionIcon = (action: string) => {
  if (action.includes('login')) return LogIn;
  if (action.includes('logout')) return LogOut;
  if (action.includes('create') || action.includes('invite')) return UserPlus;
  if (action.includes('delete') || action.includes('remove')) return Trash2;
  if (action.includes('update') || action.includes('edit')) return Edit;
  if (action.includes('view') || action.includes('read')) return Eye;
  if (action.includes('api_key')) return Key;
  if (action.includes('setting')) return Settings;
  if (action.includes('document')) return FileText;
  if (action.includes('message') || action.includes('chat')) return MessageSquare;
  if (action.includes('security')) return Shield;
  return ScrollText;
};

const getActionLabel = (action: string): string => {
  const labels: Record<string, string> = {
    'user.login': 'User logged in',
    'user.logout': 'User logged out',
    'user.login_failed': 'Failed login attempt',
    'user.password_changed': 'Password changed',
    'user.2fa_enabled': '2FA enabled',
    'user.2fa_disabled': '2FA disabled',
    'member.invited': 'Team member invited',
    'member.removed': 'Team member removed',
    'member.role_changed': 'Member role changed',
    'api_key.created': 'API key created',
    'api_key.deleted': 'API key deleted',
    'api_key.used': 'API key used',
    'document.uploaded': 'Document uploaded',
    'document.deleted': 'Document deleted',
    'agent.created': 'Agent created',
    'agent.updated': 'Agent updated',
    'agent.deleted': 'Agent deleted',
    'agent.executed': 'Agent executed',
    'conversation.created': 'Conversation started',
    'settings.updated': 'Settings updated',
    'integration.connected': 'Integration connected',
    'integration.disconnected': 'Integration disconnected',
    'subscription.upgraded': 'Subscription upgraded',
    'subscription.cancelled': 'Subscription cancelled',
  };
  return labels[action] || action.replace(/_/g, ' ').replace(/\./g, ' - ');
};

const getSeverityColor = (severity: string) => {
  switch (severity) {
    case 'critical':
      return 'text-red-600 bg-red-50 dark:bg-red-950';
    case 'warning':
      return 'text-yellow-600 bg-yellow-50 dark:bg-yellow-950';
    default:
      return 'text-blue-600 bg-blue-50 dark:bg-blue-950';
  }
};

// Generate mock audit log data
const generateMockLogs = (): AuditLogEntry[] => {
  const actions = [
    { action: 'user.login', severity: 'info' as const, resource_type: 'user' },
    { action: 'user.logout', severity: 'info' as const, resource_type: 'user' },
    { action: 'user.login_failed', severity: 'warning' as const, resource_type: 'user' },
    { action: 'member.invited', severity: 'info' as const, resource_type: 'member' },
    { action: 'member.removed', severity: 'warning' as const, resource_type: 'member' },
    { action: 'api_key.created', severity: 'info' as const, resource_type: 'api_key' },
    { action: 'api_key.deleted', severity: 'warning' as const, resource_type: 'api_key' },
    { action: 'document.uploaded', severity: 'info' as const, resource_type: 'document' },
    { action: 'document.deleted', severity: 'warning' as const, resource_type: 'document' },
    { action: 'agent.executed', severity: 'info' as const, resource_type: 'agent' },
    { action: 'settings.updated', severity: 'info' as const, resource_type: 'settings' },
    { action: 'integration.connected', severity: 'info' as const, resource_type: 'integration' },
  ];

  const users = [
    { id: '1', name: 'John Doe', email: 'john@example.com' },
    { id: '2', name: 'Jane Smith', email: 'jane@example.com' },
    { id: '3', name: 'Bob Wilson', email: 'bob@example.com' },
  ];

  const logs: AuditLogEntry[] = [];
  
  for (let i = 0; i < 50; i++) {
    const actionData = actions[Math.floor(Math.random() * actions.length)];
    const user = users[Math.floor(Math.random() * users.length)];
    const date = new Date();
    date.setMinutes(date.getMinutes() - i * 30);

    logs.push({
      id: `log-${i}`,
      timestamp: date.toISOString(),
      action: actionData.action,
      actor: user,
      resource_type: actionData.resource_type,
      resource_id: `${actionData.resource_type}-${Math.random().toString(36).substr(2, 9)}`,
      resource_name: `${actionData.resource_type.charAt(0).toUpperCase() + actionData.resource_type.slice(1)} ${i + 1}`,
      ip_address: `192.168.${Math.floor(Math.random() * 255)}.${Math.floor(Math.random() * 255)}`,
      user_agent: 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)',
      metadata: {},
      severity: actionData.severity,
    });
  }

  return logs;
};

export default function AuditLogsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [logs, setLogs] = useState<AuditLogEntry[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedAction, setSelectedAction] = useState<string>('all');
  const [selectedSeverity, setSelectedSeverity] = useState<string>('all');
  const [dateRange, setDateRange] = useState<string>('7d');
  const [expandedLog, setExpandedLog] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const loadLogs = useCallback(async () => {
    setIsLoading(true);
    try {
      // In production, this would be an API call
      await new Promise((resolve) => setTimeout(resolve, 500));
      setLogs(generateMockLogs());
    } catch (error) {
      console.error('Failed to load audit logs:', error);
      toast.error('Failed to load audit logs');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      loadLogs();
    }
  }, [isAuthenticated, loadLogs]);

  const filteredLogs = logs.filter((log) => {
    const matchesSearch =
      searchQuery === '' ||
      log.action.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.actor.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      log.actor.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (log.resource_name?.toLowerCase().includes(searchQuery.toLowerCase()) ?? false);
    
    const matchesAction = selectedAction === 'all' || log.action.startsWith(selectedAction);
    const matchesSeverity = selectedSeverity === 'all' || log.severity === selectedSeverity;
    
    return matchesSearch && matchesAction && matchesSeverity;
  });

  const handleExport = () => {
    const csv = [
      ['Timestamp', 'Action', 'Actor', 'Email', 'Resource', 'IP Address', 'Severity'],
      ...filteredLogs.map((log) => [
        log.timestamp,
        log.action,
        log.actor.name,
        log.actor.email,
        log.resource_name || log.resource_id,
        log.ip_address,
        log.severity,
      ]),
    ]
      .map((row) => row.join(','))
      .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `audit-logs-${new Date().toISOString().split('T')[0]}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success('Audit logs exported');
  };

  if (!isAuthenticated) return null;

  const actionTypes = [
    { id: 'all', label: 'All Actions' },
    { id: 'user', label: 'User Actions' },
    { id: 'member', label: 'Team Actions' },
    { id: 'api_key', label: 'API Keys' },
    { id: 'document', label: 'Documents' },
    { id: 'agent', label: 'Agents' },
    { id: 'settings', label: 'Settings' },
    { id: 'integration', label: 'Integrations' },
  ];

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <ScrollText className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Audit Logs</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadLogs}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button variant="outline" size="sm" onClick={handleExport}>
              <Download className="mr-2 h-4 w-4" />
              Export
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Info Banner */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950 p-4 mb-8">
          <div className="flex gap-3">
            <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-blue-900 dark:text-blue-100">
                Security & Compliance
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                Audit logs track all security-relevant actions in your organization.
                Logs are retained for 90 days on Pro plans and 1 year on Enterprise.
              </p>
            </div>
          </div>
        </div>

        {/* Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search by action, user, or resource..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>

          <select
            value={selectedAction}
            onChange={(e) => setSelectedAction(e.target.value)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            {actionTypes.map((type) => (
              <option key={type.id} value={type.id}>
                {type.label}
              </option>
            ))}
          </select>

          <select
            value={selectedSeverity}
            onChange={(e) => setSelectedSeverity(e.target.value)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="all">All Severities</option>
            <option value="info">Info</option>
            <option value="warning">Warning</option>
            <option value="critical">Critical</option>
          </select>

          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="rounded-md border bg-background px-3 py-2 text-sm"
          >
            <option value="24h">Last 24 hours</option>
            <option value="7d">Last 7 days</option>
            <option value="30d">Last 30 days</option>
            <option value="90d">Last 90 days</option>
          </select>
        </div>

        {/* Logs List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : filteredLogs.length === 0 ? (
          <div className="text-center py-12 rounded-lg border bg-card">
            <ScrollText className="mx-auto h-12 w-12 text-muted-foreground" />
            <h2 className="mt-4 text-lg font-medium">No audit logs found</h2>
            <p className="mt-2 text-muted-foreground">
              Try adjusting your filters or search query
            </p>
          </div>
        ) : (
          <div className="rounded-lg border bg-card overflow-hidden">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead className="bg-muted/50">
                  <tr>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Time
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Action
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Actor
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Resource
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      IP Address
                    </th>
                    <th className="px-4 py-3 text-left text-xs font-medium text-muted-foreground uppercase tracking-wider">
                      Severity
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {filteredLogs.map((log) => {
                    const ActionIcon = getActionIcon(log.action);
                    const isExpanded = expandedLog === log.id;

                    return (
                      <>
                        <tr
                          key={log.id}
                          className="hover:bg-muted/50 cursor-pointer"
                          onClick={() => setExpandedLog(isExpanded ? null : log.id)}
                        >
                          <td className="px-4 py-3 whitespace-nowrap">
                            <div className="flex items-center gap-2">
                              <ChevronDown
                                className={cn(
                                  'h-4 w-4 text-muted-foreground transition-transform',
                                  isExpanded && 'rotate-180'
                                )}
                              />
                              <span className="text-sm">
                                {formatRelativeTime(log.timestamp)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <ActionIcon className="h-4 w-4 text-muted-foreground" />
                              <span className="text-sm font-medium">
                                {getActionLabel(log.action)}
                              </span>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <div className="flex items-center gap-2">
                              <div className="h-6 w-6 rounded-full bg-primary/10 flex items-center justify-center text-xs font-medium text-primary">
                                {log.actor.name.charAt(0)}
                              </div>
                              <div>
                                <p className="text-sm font-medium">{log.actor.name}</p>
                                <p className="text-xs text-muted-foreground">
                                  {log.actor.email}
                                </p>
                              </div>
                            </div>
                          </td>
                          <td className="px-4 py-3">
                            <span className="text-sm">
                              {log.resource_name || log.resource_id}
                            </span>
                          </td>
                          <td className="px-4 py-3">
                            <code className="text-xs bg-muted px-2 py-1 rounded">
                              {log.ip_address}
                            </code>
                          </td>
                          <td className="px-4 py-3">
                            <span
                              className={cn(
                                'inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize',
                                getSeverityColor(log.severity)
                              )}
                            >
                              {log.severity}
                            </span>
                          </td>
                        </tr>
                        {isExpanded && (
                          <tr key={`${log.id}-details`}>
                            <td colSpan={6} className="px-4 py-3 bg-muted/30">
                              <div className="grid gap-4 md:grid-cols-2 text-sm">
                                <div>
                                  <p className="text-muted-foreground">Timestamp</p>
                                  <p className="font-mono">
                                    {new Date(log.timestamp).toLocaleString()}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">Resource ID</p>
                                  <p className="font-mono">{log.resource_id}</p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">User Agent</p>
                                  <p className="font-mono text-xs truncate">
                                    {log.user_agent}
                                  </p>
                                </div>
                                <div>
                                  <p className="text-muted-foreground">Actor ID</p>
                                  <p className="font-mono">{log.actor.id}</p>
                                </div>
                              </div>
                            </td>
                          </tr>
                        )}
                      </>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* Pagination placeholder */}
        {filteredLogs.length > 0 && (
          <div className="flex items-center justify-between mt-4">
            <p className="text-sm text-muted-foreground">
              Showing {filteredLogs.length} of {logs.length} entries
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" disabled>
                Previous
              </Button>
              <Button variant="outline" size="sm" disabled>
                Next
              </Button>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
