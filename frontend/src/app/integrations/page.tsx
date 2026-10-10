'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Puzzle,
  Search,
  Check,
  ExternalLink,
  Settings,
  Trash2,
  RefreshCw,
  Loader2,
  Github,
  GitlabIcon as Gitlab,
  Slack,
  Trello,
  Figma,
  Cloud,
  Database,
  Mail,
  Calendar,
  FileText,
  Code,
  Zap,
  X,
  AlertCircle,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { FloatingAssistant } from '@/components/assistant';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { cn } from '@/lib/utils';
import { toast } from 'sonner';

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: typeof Github;
  category: 'development' | 'communication' | 'productivity' | 'data';
  status: 'available' | 'connected' | 'coming_soon';
  features: string[];
  docsUrl?: string;
}

const integrations: Integration[] = [
  {
    id: 'github',
    name: 'GitHub',
    description: 'Connect repositories for DORA metrics and code analysis',
    icon: Github,
    category: 'development',
    status: 'available',
    features: ['Repository sync', 'PR analysis', 'DORA metrics', 'Code search'],
    docsUrl: 'https://docs.nexusai.com/integrations/github',
  },
  {
    id: 'gitlab',
    name: 'GitLab',
    description: 'Integrate with GitLab for CI/CD insights',
    icon: Gitlab,
    category: 'development',
    status: 'available',
    features: ['Pipeline monitoring', 'MR analysis', 'Issue tracking'],
    docsUrl: 'https://docs.nexusai.com/integrations/gitlab',
  },
  {
    id: 'slack',
    name: 'Slack',
    description: 'Get notifications and interact via Slack',
    icon: Slack,
    category: 'communication',
    status: 'available',
    features: ['Notifications', 'Slash commands', 'Channel integration'],
    docsUrl: 'https://docs.nexusai.com/integrations/slack',
  },
  {
    id: 'jira',
    name: 'Jira',
    description: 'Sync issues and track project progress',
    icon: Trello,
    category: 'productivity',
    status: 'available',
    features: ['Issue sync', 'Sprint tracking', 'Backlog management'],
    docsUrl: 'https://docs.nexusai.com/integrations/jira',
  },
  {
    id: 'confluence',
    name: 'Confluence',
    description: 'Import documentation for RAG knowledge base',
    icon: FileText,
    category: 'productivity',
    status: 'available',
    features: ['Page import', 'Space sync', 'Search integration'],
  },
  {
    id: 'notion',
    name: 'Notion',
    description: 'Connect Notion pages to your knowledge base',
    icon: FileText,
    category: 'productivity',
    status: 'coming_soon',
    features: ['Database sync', 'Page import', 'Bidirectional updates'],
  },
  {
    id: 'figma',
    name: 'Figma',
    description: 'Analyze designs and generate code',
    icon: Figma,
    category: 'development',
    status: 'coming_soon',
    features: ['Design analysis', 'Component extraction', 'Style guide'],
  },
  {
    id: 'aws',
    name: 'AWS',
    description: 'Monitor cloud infrastructure',
    icon: Cloud,
    category: 'data',
    status: 'available',
    features: ['CloudWatch metrics', 'Cost analysis', 'Resource tracking'],
  },
  {
    id: 'gcp',
    name: 'Google Cloud',
    description: 'Connect GCP projects and services',
    icon: Cloud,
    category: 'data',
    status: 'coming_soon',
    features: ['Monitoring', 'BigQuery', 'Cloud Functions'],
  },
  {
    id: 'postgresql',
    name: 'PostgreSQL',
    description: 'Query databases with natural language',
    icon: Database,
    category: 'data',
    status: 'available',
    features: ['Natural language queries', 'Schema analysis', 'Data insights'],
  },
  {
    id: 'linear',
    name: 'Linear',
    description: 'Modern issue tracking integration',
    icon: Zap,
    category: 'productivity',
    status: 'available',
    features: ['Issue sync', 'Cycle tracking', 'Roadmap view'],
  },
  {
    id: 'google-calendar',
    name: 'Google Calendar',
    description: 'Schedule and manage meetings',
    icon: Calendar,
    category: 'communication',
    status: 'coming_soon',
    features: ['Meeting scheduling', 'Availability check', 'Event creation'],
  },
];

const categories = [
  { id: 'all', label: 'All' },
  { id: 'development', label: 'Development' },
  { id: 'communication', label: 'Communication' },
  { id: 'productivity', label: 'Productivity' },
  { id: 'data', label: 'Data & Cloud' },
];

export default function IntegrationsPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('all');
  const [connectedIntegrations, setConnectedIntegrations] = useState<string[]>([]);
  const [connectingId, setConnectingId] = useState<string | null>(null);
  const [showConfigModal, setShowConfigModal] = useState<string | null>(null);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const filteredIntegrations = integrations.filter((integration) => {
    const matchesSearch =
      integration.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      integration.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory =
      selectedCategory === 'all' || integration.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const handleConnect = async (integration: Integration) => {
    if (integration.status === 'coming_soon') {
      toast.info(`${integration.name} integration is coming soon!`);
      return;
    }

    setConnectingId(integration.id);
    
    // Simulate OAuth flow
    try {
      await new Promise((resolve) => setTimeout(resolve, 1500));
      
      if (connectedIntegrations.includes(integration.id)) {
        // Disconnect
        setConnectedIntegrations((prev) => prev.filter((id) => id !== integration.id));
        toast.success(`Disconnected from ${integration.name}`);
      } else {
        // Connect
        setConnectedIntegrations((prev) => [...prev, integration.id]);
        toast.success(`Connected to ${integration.name}`);
      }
    } catch (error) {
      toast.error(`Failed to connect to ${integration.name}`);
    } finally {
      setConnectingId(null);
    }
  };

  if (!isAuthenticated) return null;

  const connectedCount = connectedIntegrations.length;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Puzzle className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Integrations</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/settings">
              <Button variant="ghost" size="sm">
                Settings
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-2xl font-bold">Integrations</h1>
          <p className="text-muted-foreground mt-1">
            Connect your tools to supercharge NexusAI
          </p>
        </div>

        {/* Stats */}
        <div className="grid gap-4 md:grid-cols-3 mb-8">
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">Connected</p>
            <p className="text-2xl font-bold">{connectedCount}</p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">Available</p>
            <p className="text-2xl font-bold">
              {integrations.filter((i) => i.status === 'available').length}
            </p>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <p className="text-sm text-muted-foreground">Coming Soon</p>
            <p className="text-2xl font-bold">
              {integrations.filter((i) => i.status === 'coming_soon').length}
            </p>
          </div>
        </div>

        {/* Search & Filters */}
        <div className="flex flex-col md:flex-row gap-4 mb-6">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              placeholder="Search integrations..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="pl-10"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-2 md:pb-0">
            {categories.map((category) => (
              <button
                key={category.id}
                onClick={() => setSelectedCategory(category.id)}
                className={cn(
                  'px-4 py-2 rounded-lg text-sm font-medium whitespace-nowrap transition-colors',
                  selectedCategory === category.id
                    ? 'bg-primary text-primary-foreground'
                    : 'bg-muted hover:bg-muted/80'
                )}
              >
                {category.label}
              </button>
            ))}
          </div>
        </div>

        {/* Connected Integrations */}
        {connectedCount > 0 && (
          <section className="mb-8">
            <h2 className="text-lg font-semibold mb-4">Connected ({connectedCount})</h2>
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {integrations
                .filter((i) => connectedIntegrations.includes(i.id))
                .map((integration) => {
                  const Icon = integration.icon;
                  return (
                    <div
                      key={integration.id}
                      className="rounded-lg border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950/30 p-4"
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 rounded-lg bg-background flex items-center justify-center">
                            <Icon className="h-5 w-5" />
                          </div>
                          <div>
                            <h3 className="font-medium">{integration.name}</h3>
                            <div className="flex items-center gap-1 text-xs text-green-600 dark:text-green-400">
                              <Check className="h-3 w-3" />
                              Connected
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-1">
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => setShowConfigModal(integration.id)}
                          >
                            <Settings className="h-4 w-4" />
                          </Button>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="text-destructive hover:text-destructive"
                            onClick={() => handleConnect(integration)}
                            disabled={connectingId === integration.id}
                          >
                            {connectingId === integration.id ? (
                              <Loader2 className="h-4 w-4 animate-spin" />
                            ) : (
                              <Trash2 className="h-4 w-4" />
                            )}
                          </Button>
                        </div>
                      </div>
                    </div>
                  );
                })}
            </div>
          </section>
        )}

        {/* Available Integrations */}
        <section>
          <h2 className="text-lg font-semibold mb-4">
            {connectedCount > 0 ? 'Available' : 'All Integrations'}
          </h2>
          
          {filteredIntegrations.length === 0 ? (
            <div className="text-center py-12 rounded-lg border bg-card">
              <Search className="mx-auto h-12 w-12 text-muted-foreground" />
              <h3 className="mt-4 text-lg font-medium">No integrations found</h3>
              <p className="mt-2 text-muted-foreground">
                Try adjusting your search or filters
              </p>
            </div>
          ) : (
            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
              {filteredIntegrations
                .filter((i) => !connectedIntegrations.includes(i.id))
                .map((integration) => {
                  const Icon = integration.icon;
                  const isComingSoon = integration.status === 'coming_soon';
                  const isConnecting = connectingId === integration.id;

                  return (
                    <div
                      key={integration.id}
                      className={cn(
                        'rounded-lg border bg-card p-4 transition-colors',
                        isComingSoon ? 'opacity-75' : 'hover:shadow-md'
                      )}
                    >
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-center gap-3">
                          <div
                            className={cn(
                              'h-10 w-10 rounded-lg flex items-center justify-center',
                              isComingSoon ? 'bg-muted' : 'bg-primary/10'
                            )}
                          >
                            <Icon
                              className={cn(
                                'h-5 w-5',
                                isComingSoon ? 'text-muted-foreground' : 'text-primary'
                              )}
                            />
                          </div>
                          <div>
                            <h3 className="font-medium">{integration.name}</h3>
                            {isComingSoon && (
                              <span className="text-xs bg-muted px-2 py-0.5 rounded">
                                Coming Soon
                              </span>
                            )}
                          </div>
                        </div>
                        {integration.docsUrl && (
                          <a
                            href={integration.docsUrl}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-muted-foreground hover:text-foreground"
                          >
                            <ExternalLink className="h-4 w-4" />
                          </a>
                        )}
                      </div>

                      <p className="text-sm text-muted-foreground mb-3">
                        {integration.description}
                      </p>

                      <div className="flex flex-wrap gap-1 mb-4">
                        {integration.features.slice(0, 3).map((feature) => (
                          <span
                            key={feature}
                            className="text-xs bg-muted px-2 py-0.5 rounded"
                          >
                            {feature}
                          </span>
                        ))}
                      </div>

                      <Button
                        className="w-full"
                        variant={isComingSoon ? 'outline' : 'default'}
                        disabled={isComingSoon || isConnecting}
                        onClick={() => handleConnect(integration)}
                      >
                        {isConnecting ? (
                          <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        ) : null}
                        {isComingSoon ? 'Notify Me' : 'Connect'}
                      </Button>
                    </div>
                  );
                })}
            </div>
          )}
        </section>

        {/* Custom Integration */}
        <section className="mt-12">
          <div className="rounded-lg border bg-card p-6">
            <div className="flex items-start gap-4">
              <div className="h-12 w-12 rounded-lg bg-primary/10 flex items-center justify-center shrink-0">
                <Code className="h-6 w-6 text-primary" />
              </div>
              <div className="flex-1">
                <h2 className="text-lg font-semibold">Build Custom Integrations</h2>
                <p className="text-muted-foreground mt-1">
                  Use our API and webhooks to build custom integrations with any tool
                </p>
                <div className="flex gap-3 mt-4">
                  <Link href="/api-keys">
                    <Button variant="outline" size="sm">
                      API Keys
                    </Button>
                  </Link>
                  <a
                    href="https://docs.nexusai.com/api"
                    target="_blank"
                    rel="noopener noreferrer"
                  >
                    <Button variant="outline" size="sm">
                      <ExternalLink className="mr-2 h-4 w-4" />
                      API Docs
                    </Button>
                  </a>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Config Modal */}
      {showConfigModal && (
        <div
          className="fixed inset-0 bg-black/50 flex items-center justify-center z-50"
          onKeyDown={(e) => { if (e.key === 'Escape') setShowConfigModal(null); }}
        >
          <div className="bg-background rounded-lg border shadow-lg w-full max-w-md p-6">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Integration Settings</h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowConfigModal(null)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/50">
                <p className="text-sm text-muted-foreground">
                  Configure sync settings, permissions, and notifications for this integration.
                </p>
              </div>

              <div>
                <label className="text-sm font-medium">Sync Frequency</label>
                <select className="w-full mt-1 rounded-md border bg-background px-3 py-2 text-sm">
                  <option>Real-time</option>
                  <option>Every 5 minutes</option>
                  <option>Every hour</option>
                  <option>Daily</option>
                </select>
              </div>

              <div>
                <label className="text-sm font-medium">Permissions</label>
                <div className="mt-2 space-y-2">
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked />
                    <span className="text-sm">Read access</span>
                  </label>
                  <label className="flex items-center gap-2">
                    <input type="checkbox" defaultChecked />
                    <span className="text-sm">Write access</span>
                  </label>
                </div>
              </div>

              <div className="flex gap-2 pt-4">
                <Button className="flex-1" onClick={() => setShowConfigModal(null)}>
                  Save Settings
                </Button>
                <Button variant="outline" onClick={() => setShowConfigModal(null)}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* AI Assistant */}
      <FloatingAssistant context="integrations" />
    </div>
  );
}
