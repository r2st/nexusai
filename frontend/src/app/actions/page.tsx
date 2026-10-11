'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Plug,
  Plus,
  Play,
  Trash2,
  RefreshCw,
  Loader2,
  ExternalLink,
  ChevronDown,
  ChevronRight,
  CheckCircle,
  XCircle,
  Settings,
  Key,
  Globe,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { actionsApi, type OpenAPIAction } from '@/lib/api';
import { toast } from 'sonner';

export default function ActionsPage() {
  const [actions, setActions] = useState<OpenAPIAction[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showRegisterModal, setShowRegisterModal] = useState(false);
  const [selectedAction, setSelectedAction] = useState<OpenAPIAction | null>(null);
  const [expandedActions, setExpandedActions] = useState<Set<string>>(new Set());

  useEffect(() => {
    loadActions();
  }, []);

  const loadActions = async () => {
    setIsLoading(true);
    try {
      const data = await actionsApi.list();
      setActions(data);
    } catch (error) {
      console.error('Failed to load actions:', error);
      toast.error('Failed to load actions');
    } finally {
      setIsLoading(false);
    }
  };

  const handleDelete = async (actionId: string) => {
    if (!confirm('Are you sure you want to delete this action?')) return;

    try {
      await actionsApi.delete(actionId);
      setActions((prev) => prev.filter((a) => a.action_id !== actionId));
    } catch (error) {
      console.error('Failed to delete action:', error);
      toast.error('Failed to delete action');
    }
  };

  const toggleExpanded = (actionId: string) => {
    setExpandedActions((prev) => {
      const next = new Set(prev);
      if (next.has(actionId)) {
        next.delete(actionId);
      } else {
        next.add(actionId);
      }
      return next;
    });
  };

  const getAuthIcon = (authType: string) => {
    switch (authType) {
      case 'api_key':
      case 'bearer':
        return <Key className="h-4 w-4" />;
      case 'oauth2':
        return <Globe className="h-4 w-4" />;
      default:
        return <Plug className="h-4 w-4" />;
    }
  };

  const getMethodColor = (method: string) => {
    switch (method.toUpperCase()) {
      case 'GET':
        return 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300';
      case 'POST':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300';
      case 'PUT':
        return 'bg-yellow-100 text-yellow-700 dark:bg-yellow-900 dark:text-yellow-300';
      case 'DELETE':
        return 'bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300';
      case 'PATCH':
        return 'bg-purple-100 text-purple-700 dark:bg-purple-900 dark:text-purple-300';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Plug className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">OpenAPI Actions</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadActions}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setShowRegisterModal(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Register Action
            </Button>
            <Link href="/agents">
              <Button variant="ghost" size="sm">
                Go to Agents
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Stats */}
        <div className="mb-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Plug className="h-4 w-4" />
              <span className="text-sm">Total Actions</span>
            </div>
            <div className="mt-2 text-2xl font-bold">{actions.length}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <CheckCircle className="h-4 w-4" />
              <span className="text-sm">Enabled</span>
            </div>
            <div className="mt-2 text-2xl font-bold">
              {actions.filter((a) => a.is_enabled).length}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Settings className="h-4 w-4" />
              <span className="text-sm">Total Operations</span>
            </div>
            <div className="mt-2 text-2xl font-bold">
              {actions.reduce((acc, a) => acc + a.operations.length, 0)}
            </div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Key className="h-4 w-4" />
              <span className="text-sm">Authenticated</span>
            </div>
            <div className="mt-2 text-2xl font-bold">
              {actions.filter((a) => a.auth_type !== 'none').length}
            </div>
          </div>
        </div>

        {/* Actions List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : actions.length === 0 ? (
          <div className="text-center py-12">
            <Plug className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No Actions Registered</h3>
            <p className="mt-2 text-muted-foreground">
              Register an OpenAPI action to enable external integrations
            </p>
            <Button
              className="mt-4"
              onClick={() => setShowRegisterModal(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              Register Action
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {actions.map((action) => (
              <div key={action.id} className="rounded-lg border bg-card">
                {/* Action Header */}
                <div
                  className="p-4 flex items-center justify-between cursor-pointer hover:bg-muted/50 transition-colors"
                  onClick={() => toggleExpanded(action.action_id)}
                >
                  <div className="flex items-center gap-4">
                    {expandedActions.has(action.action_id) ? (
                      <ChevronDown className="h-4 w-4" />
                    ) : (
                      <ChevronRight className="h-4 w-4" />
                    )}
                    <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                      {getAuthIcon(action.auth_type)}
                    </div>
                    <div>
                      <h3 className="font-medium flex items-center gap-2">
                        {action.name}
                        {action.is_enabled ? (
                          <CheckCircle className="h-3 w-3 text-green-500" />
                        ) : (
                          <XCircle className="h-3 w-3 text-red-500" />
                        )}
                      </h3>
                      <p className="text-sm text-muted-foreground">
                        {action.base_url}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-4">
                    <span className="text-sm text-muted-foreground">
                      {action.operations.length} operations
                    </span>
                    <span
                      className={`text-xs px-2 py-1 rounded ${
                        action.auth_type === 'none'
                          ? 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                          : 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300'
                      }`}
                    >
                      {action.auth_type}
                    </span>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleDelete(action.action_id);
                      }}
                      className="text-destructive hover:text-destructive"
                      aria-label={`Delete ${action.name}`}
                    >
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </Button>
                  </div>
                </div>

                {/* Operations */}
                {expandedActions.has(action.action_id) && (
                  <div className="border-t px-4 py-3">
                    {action.description && (
                      <p className="text-sm text-muted-foreground mb-4">
                        {action.description}
                      </p>
                    )}
                    <h4 className="text-sm font-medium mb-3">Operations</h4>
                    <div className="space-y-2">
                      {action.operations.map((op) => (
                        <div
                          key={op.operation_id}
                          className="flex items-center gap-4 p-3 rounded-lg bg-muted"
                        >
                          <span
                            className={`text-xs font-mono px-2 py-1 rounded ${getMethodColor(
                              op.method
                            )}`}
                          >
                            {op.method}
                          </span>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm">{op.name}</div>
                            <div className="text-xs text-muted-foreground truncate">
                              {op.path}
                            </div>
                          </div>
                          <Button
                            variant="ghost"
                            size="sm"
                            onClick={() => {
                              setSelectedAction(action);
                            }}
                          >
                            <Play className="h-3 w-3" />
                          </Button>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Quick Links */}
        <section className="mt-12">
          <h2 className="mb-4 text-xl font-semibold">Pre-built Actions</h2>
          <p className="mb-4 text-muted-foreground">
            These popular API integrations can be registered with one click.
          </p>
          <div className="grid gap-4 md:grid-cols-3">
            {[
              {
                name: 'GitHub',
                description: 'Repository, PR, and issue management',
                url: 'https://api.github.com',
              },
              {
                name: 'Slack',
                description: 'Send messages and manage channels',
                url: 'https://slack.com/api',
              },
              {
                name: 'Jira',
                description: 'Issue tracking and project management',
                url: 'https://api.atlassian.com',
              },
              {
                name: 'Linear',
                description: 'Modern issue tracking',
                url: 'https://api.linear.app',
              },
              {
                name: 'Notion',
                description: 'Pages, databases, and blocks',
                url: 'https://api.notion.com',
              },
              {
                name: 'Discord',
                description: 'Bot and server management',
                url: 'https://discord.com/api',
              },
            ].map((preset) => (
              <div
                key={preset.name}
                className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
              >
                <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                  <ExternalLink className="h-6 w-6 text-primary" />
                </div>
                <div className="flex-1">
                  <div className="font-medium">{preset.name}</div>
                  <div className="text-sm text-muted-foreground">
                    {preset.description}
                  </div>
                </div>
                <Button variant="outline" size="sm">
                  Add
                </Button>
              </div>
            ))}
          </div>
        </section>
      </main>

      {/* Register Modal */}
      {showRegisterModal && (
        <RegisterActionModal
          onClose={() => setShowRegisterModal(false)}
          onRegister={async (data) => {
            const newAction = await actionsApi.register(data);
            setActions((prev) => [newAction, ...prev]);
            setShowRegisterModal(false);
          }}
        />
      )}
    </div>
  );
}

interface RegisterActionModalProps {
  onClose: () => void;
  onRegister: (data: {
    action_id: string;
    name: string;
    base_url: string;
    auth_type?: string;
    operations: Record<string, unknown>[];
    description?: string;
  }) => Promise<void>;
}

function RegisterActionModal({ onClose, onRegister }: RegisterActionModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [specUrl, setSpecUrl] = useState('');
  const [isFromSpec, setIsFromSpec] = useState(true);
  const [formData, setFormData] = useState({
    action_id: '',
    name: '',
    base_url: '',
    auth_type: 'none',
    description: '',
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitting(true);

    try {
      if (isFromSpec && specUrl) {
        const action = await actionsApi.registerFromSpec(specUrl);
        // Action already created, just close
        onClose();
        window.location.reload();
      } else {
        await onRegister({
          action_id: formData.action_id,
          name: formData.name,
          base_url: formData.base_url,
          auth_type: formData.auth_type,
          description: formData.description || undefined,
          operations: [],
        });
      }
    } catch (error) {
      console.error('Failed to register action:', error);
      toast.error('Failed to register action');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative z-10 w-full max-w-lg rounded-lg bg-background p-6 shadow-lg">
        <h2 className="text-xl font-semibold mb-6">Register OpenAPI Action</h2>

        {/* Tab Selection */}
        <div className="flex gap-2 mb-6">
          <button
            onClick={() => setIsFromSpec(true)}
            className={`px-4 py-2 rounded-lg text-sm ${
              isFromSpec
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            From OpenAPI Spec
          </button>
          <button
            onClick={() => setIsFromSpec(false)}
            className={`px-4 py-2 rounded-lg text-sm ${
              !isFromSpec
                ? 'bg-primary text-primary-foreground'
                : 'bg-muted text-muted-foreground'
            }`}
          >
            Manual
          </button>
        </div>

        <form onSubmit={handleSubmit} className="space-y-4">
          {isFromSpec ? (
            <div>
              <label className="text-sm font-medium">OpenAPI Spec URL</label>
              <Input
                value={specUrl}
                onChange={(e) => setSpecUrl(e.target.value)}
                placeholder="https://api.example.com/openapi.json"
                className="mt-1"
                required
              />
              <p className="text-xs text-muted-foreground mt-1">
                URL to your OpenAPI/Swagger specification (JSON or YAML)
              </p>
            </div>
          ) : (
            <>
              <div>
                <label className="text-sm font-medium">Action ID</label>
                <Input
                  value={formData.action_id}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, action_id: e.target.value }))
                  }
                  placeholder="my-custom-action"
                  className="mt-1"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={formData.name}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, name: e.target.value }))
                  }
                  placeholder="My Custom Action"
                  className="mt-1"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Base URL</label>
                <Input
                  value={formData.base_url}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, base_url: e.target.value }))
                  }
                  placeholder="https://api.example.com"
                  className="mt-1"
                  required
                />
              </div>
              <div>
                <label className="text-sm font-medium">Auth Type</label>
                <select
                  value={formData.auth_type}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, auth_type: e.target.value }))
                  }
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2"
                >
                  <option value="none">None</option>
                  <option value="api_key">API Key</option>
                  <option value="bearer">Bearer Token</option>
                  <option value="basic">Basic Auth</option>
                  <option value="oauth2">OAuth 2.0</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium">Description</label>
                <Textarea
                  value={formData.description}
                  onChange={(e) =>
                    setFormData((prev) => ({ ...prev, description: e.target.value }))
                  }
                  placeholder="What does this action do?"
                  className="mt-1"
                  rows={2}
                />
              </div>
            </>
          )}

          <div className="flex justify-end gap-3 pt-4">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Registering...
                </>
              ) : (
                'Register Action'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
