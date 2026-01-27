'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import {
  Key,
  Plus,
  Copy,
  Trash2,
  Eye,
  EyeOff,
  RefreshCw,
  Loader2,
  AlertTriangle,
  Check,
  X,
  Shield,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuthStore } from '@/store/auth';
import { api } from '@/lib/api';
import { cn, formatRelativeTime } from '@/lib/utils';
import { toast } from 'sonner';

interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  scopes: string[];
  last_used_at: string | null;
  expires_at: string | null;
  created_at: string;
  is_active: boolean;
}

interface NewApiKey extends ApiKey {
  key: string; // Full key, only shown once
}

const availableScopes = [
  { id: 'chat:read', label: 'Read Conversations', description: 'View chat history' },
  { id: 'chat:write', label: 'Send Messages', description: 'Send messages to AI' },
  { id: 'documents:read', label: 'Read Documents', description: 'View uploaded documents' },
  { id: 'documents:write', label: 'Upload Documents', description: 'Upload and process documents' },
  { id: 'agents:read', label: 'Read Agents', description: 'View agent configurations' },
  { id: 'agents:write', label: 'Manage Agents', description: 'Create and modify agents' },
  { id: 'agents:execute', label: 'Execute Agents', description: 'Run agent tasks' },
];

export default function ApiKeysPage() {
  const router = useRouter();
  const { isAuthenticated } = useAuthStore();
  const [apiKeys, setApiKeys] = useState<ApiKey[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [newKeyName, setNewKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['chat:read', 'chat:write']);
  const [expiresIn, setExpiresIn] = useState<string>('never');
  const [isCreating, setIsCreating] = useState(false);
  const [newlyCreatedKey, setNewlyCreatedKey] = useState<NewApiKey | null>(null);
  const [showKey, setShowKey] = useState(false);

  useEffect(() => {
    if (!isAuthenticated) {
      router.push('/login');
    }
  }, [isAuthenticated, router]);

  const loadApiKeys = async () => {
    setIsLoading(true);
    try {
      // Mock API call - replace with actual endpoint
      const response = await api.get('/api-keys');
      setApiKeys(response.data);
    } catch (error) {
      // If endpoint doesn't exist, show empty state
      console.error('Failed to load API keys:', error);
      setApiKeys([]);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isAuthenticated) {
      loadApiKeys();
    }
  }, [isAuthenticated]);

  const handleCreateKey = async () => {
    if (!newKeyName.trim()) {
      toast.error('Please enter a name for the API key');
      return;
    }

    setIsCreating(true);
    try {
      const response = await api.post('/api-keys', {
        name: newKeyName,
        scopes: selectedScopes,
        expires_in_days: expiresIn === 'never' ? null : parseInt(expiresIn),
      });
      setNewlyCreatedKey(response.data);
      setShowCreateModal(false);
      setNewKeyName('');
      setSelectedScopes(['chat:read', 'chat:write']);
      setExpiresIn('never');
      loadApiKeys();
    } catch (error) {
      console.error('Failed to create API key:', error);
      toast.error('Failed to create API key');
    } finally {
      setIsCreating(false);
    }
  };

  const handleDeleteKey = async (id: string, name: string) => {
    if (!confirm(`Are you sure you want to delete the API key "${name}"? This action cannot be undone.`)) {
      return;
    }

    try {
      await api.delete(`/api-keys/${id}`);
      toast.success('API key deleted');
      loadApiKeys();
    } catch (error) {
      console.error('Failed to delete API key:', error);
      toast.error('Failed to delete API key');
    }
  };

  const copyToClipboard = (text: string) => {
    navigator.clipboard.writeText(text);
    toast.success('Copied to clipboard');
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope)
        ? prev.filter((s) => s !== scope)
        : [...prev, scope]
    );
  };

  if (!isAuthenticated) return null;

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Key className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">API Keys</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadApiKeys}>
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

      <main className="container mx-auto px-4 py-8 max-w-4xl">
        {/* Info Banner */}
        <div className="rounded-lg border border-blue-200 bg-blue-50 dark:border-blue-900 dark:bg-blue-950 p-4 mb-8">
          <div className="flex gap-3">
            <Shield className="h-5 w-5 text-blue-600 dark:text-blue-400 shrink-0 mt-0.5" />
            <div>
              <h3 className="font-medium text-blue-900 dark:text-blue-100">
                API Key Security
              </h3>
              <p className="text-sm text-blue-700 dark:text-blue-300 mt-1">
                API keys provide programmatic access to NexusAI. Keep them secure and never share them publicly.
                You can create multiple keys with different scopes for different use cases.
              </p>
            </div>
          </div>
        </div>

        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold">Your API Keys</h1>
            <p className="text-muted-foreground mt-1">
              Manage API keys for programmatic access
            </p>
          </div>
          <Button onClick={() => setShowCreateModal(true)}>
            <Plus className="mr-2 h-4 w-4" />
            Create API Key
          </Button>
        </div>

        {/* Newly Created Key Alert */}
        {newlyCreatedKey && (
          <div className="rounded-lg border border-green-200 bg-green-50 dark:border-green-900 dark:bg-green-950 p-4 mb-6">
            <div className="flex items-start gap-3">
              <Check className="h-5 w-5 text-green-600 dark:text-green-400 shrink-0 mt-0.5" />
              <div className="flex-1">
                <h3 className="font-medium text-green-900 dark:text-green-100">
                  API Key Created
                </h3>
                <p className="text-sm text-green-700 dark:text-green-300 mt-1">
                  Make sure to copy your API key now. You won&apos;t be able to see it again!
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <code className="flex-1 rounded bg-green-100 dark:bg-green-900 px-3 py-2 font-mono text-sm">
                    {showKey ? newlyCreatedKey.key : '•'.repeat(40)}
                  </code>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => setShowKey(!showKey)}
                  >
                    {showKey ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                  </Button>
                  <Button
                    size="sm"
                    variant="outline"
                    onClick={() => copyToClipboard(newlyCreatedKey.key)}
                  >
                    <Copy className="h-4 w-4" />
                  </Button>
                </div>
                <Button
                  size="sm"
                  variant="ghost"
                  className="mt-2"
                  onClick={() => setNewlyCreatedKey(null)}
                >
                  Dismiss
                </Button>
              </div>
            </div>
          </div>
        )}

        {/* API Keys List */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : apiKeys.length === 0 ? (
          <div className="text-center py-12 rounded-lg border bg-card">
            <Key className="mx-auto h-12 w-12 text-muted-foreground" />
            <h2 className="mt-4 text-lg font-medium">No API Keys</h2>
            <p className="mt-2 text-muted-foreground">
              Create your first API key to get started
            </p>
            <Button className="mt-4" onClick={() => setShowCreateModal(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create API Key
            </Button>
          </div>
        ) : (
          <div className="space-y-4">
            {apiKeys.map((key) => (
              <div
                key={key.id}
                className={cn(
                  'rounded-lg border bg-card p-4',
                  !key.is_active && 'opacity-60'
                )}
              >
                <div className="flex items-start justify-between">
                  <div>
                    <div className="flex items-center gap-2">
                      <h3 className="font-medium">{key.name}</h3>
                      {!key.is_active && (
                        <span className="text-xs bg-red-100 text-red-700 dark:bg-red-900 dark:text-red-300 px-2 py-0.5 rounded">
                          Inactive
                        </span>
                      )}
                    </div>
                    <code className="text-sm text-muted-foreground font-mono">
                      {key.key_prefix}...
                    </code>
                  </div>
                  <Button
                    size="sm"
                    variant="ghost"
                    className="text-destructive hover:text-destructive"
                    onClick={() => handleDeleteKey(key.id, key.name)}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                <div className="mt-3 flex flex-wrap gap-1">
                  {key.scopes.map((scope) => (
                    <span
                      key={scope}
                      className="text-xs bg-muted px-2 py-0.5 rounded"
                    >
                      {scope}
                    </span>
                  ))}
                </div>

                <div className="mt-3 flex items-center gap-4 text-xs text-muted-foreground">
                  <span>Created {formatRelativeTime(key.created_at)}</span>
                  {key.last_used_at && (
                    <span>Last used {formatRelativeTime(key.last_used_at)}</span>
                  )}
                  {key.expires_at && (
                    <span>
                      Expires {formatRelativeTime(key.expires_at)}
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Usage Example */}
        <div className="mt-12">
          <h2 className="text-lg font-semibold mb-4">Usage Example</h2>
          <div className="rounded-lg bg-muted p-4">
            <pre className="text-sm overflow-x-auto">
              <code>{`curl -X POST https://api.nexusai.com/v1/chat \\
  -H "Authorization: Bearer YOUR_API_KEY" \\
  -H "Content-Type: application/json" \\
  -d '{
    "message": "Hello, how can I help?",
    "conversation_id": "conv_123"
  }'`}</code>
            </pre>
          </div>
          <p className="text-sm text-muted-foreground mt-2">
            Replace <code className="bg-muted px-1 rounded">YOUR_API_KEY</code> with your actual API key.
          </p>
        </div>
      </main>

      {/* Create API Key Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
          <div className="bg-background rounded-lg border shadow-lg w-full max-w-lg p-6 max-h-[90vh] overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold">Create API Key</h2>
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowCreateModal(false)}
              >
                <X className="h-4 w-4" />
              </Button>
            </div>

            <div className="space-y-6">
              {/* Name */}
              <div>
                <label className="text-sm font-medium">Name</label>
                <Input
                  value={newKeyName}
                  onChange={(e) => setNewKeyName(e.target.value)}
                  placeholder="e.g., Production API, Development"
                  className="mt-1"
                />
                <p className="text-xs text-muted-foreground mt-1">
                  A descriptive name to identify this key
                </p>
              </div>

              {/* Scopes */}
              <div>
                <label className="text-sm font-medium">Permissions</label>
                <div className="mt-2 space-y-2">
                  {availableScopes.map((scope) => (
                    <label
                      key={scope.id}
                      className={cn(
                        'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                        selectedScopes.includes(scope.id)
                          ? 'border-primary bg-primary/5'
                          : 'hover:bg-muted'
                      )}
                    >
                      <input
                        type="checkbox"
                        checked={selectedScopes.includes(scope.id)}
                        onChange={() => toggleScope(scope.id)}
                        className="mt-0.5"
                      />
                      <div>
                        <p className="font-medium text-sm">{scope.label}</p>
                        <p className="text-xs text-muted-foreground">
                          {scope.description}
                        </p>
                      </div>
                    </label>
                  ))}
                </div>
              </div>

              {/* Expiration */}
              <div>
                <label className="text-sm font-medium">Expiration</label>
                <select
                  value={expiresIn}
                  onChange={(e) => setExpiresIn(e.target.value)}
                  className="mt-1 w-full rounded-md border bg-background px-3 py-2 text-sm"
                >
                  <option value="never">Never expires</option>
                  <option value="30">30 days</option>
                  <option value="60">60 days</option>
                  <option value="90">90 days</option>
                  <option value="365">1 year</option>
                </select>
              </div>

              {/* Warning */}
              <div className="flex gap-2 p-3 rounded-lg bg-yellow-50 dark:bg-yellow-950 border border-yellow-200 dark:border-yellow-900">
                <AlertTriangle className="h-5 w-5 text-yellow-600 dark:text-yellow-400 shrink-0" />
                <p className="text-sm text-yellow-700 dark:text-yellow-300">
                  The API key will only be shown once after creation. Make sure to copy it immediately.
                </p>
              </div>

              {/* Actions */}
              <div className="flex gap-2">
                <Button
                  className="flex-1"
                  onClick={handleCreateKey}
                  disabled={isCreating || !newKeyName.trim() || selectedScopes.length === 0}
                >
                  {isCreating ? (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  ) : (
                    <Key className="mr-2 h-4 w-4" />
                  )}
                  Create Key
                </Button>
                <Button variant="outline" onClick={() => setShowCreateModal(false)}>
                  Cancel
                </Button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
