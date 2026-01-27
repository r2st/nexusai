'use client';

import {
  Bot,
  Play,
  Trash2,
  Settings,
  Globe,
  Lock,
  Zap,
  Clock,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import type { Agent } from '@/lib/api';

interface AgentCardProps {
  agent: Agent;
  onExecute: () => void;
  onDelete?: () => void;
  isPublic?: boolean;
}

export function AgentCard({ agent, onExecute, onDelete, isPublic }: AgentCardProps) {
  const getProviderColor = (provider: string) => {
    switch (provider) {
      case 'anthropic':
        return 'bg-orange-100 text-orange-700 dark:bg-orange-900 dark:text-orange-300';
      case 'openai':
        return 'bg-green-100 text-green-700 dark:bg-green-900 dark:text-green-300';
      case 'google':
        return 'bg-blue-100 text-blue-700 dark:bg-blue-900 dark:text-blue-300';
      default:
        return 'bg-gray-100 text-gray-700 dark:bg-gray-800 dark:text-gray-300';
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    });
  };

  return (
    <div className="rounded-lg border bg-card p-4 hover:shadow-md transition-shadow">
      {/* Header */}
      <div className="flex items-start justify-between">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
            <Bot className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h3 className="font-medium flex items-center gap-2">
              {agent.name}
              {agent.is_public ? (
                <Globe className="h-3 w-3 text-muted-foreground" />
              ) : (
                <Lock className="h-3 w-3 text-muted-foreground" />
              )}
            </h3>
            <div className="flex items-center gap-2 mt-1">
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${getProviderColor(
                  agent.model_provider
                )}`}
              >
                {agent.model_provider}
              </span>
              <span className="text-xs text-muted-foreground">
                {agent.model_name}
              </span>
            </div>
          </div>
        </div>
        <div
          className={`h-2 w-2 rounded-full ${
            agent.is_active ? 'bg-green-500' : 'bg-gray-300'
          }`}
          title={agent.is_active ? 'Active' : 'Inactive'}
        />
      </div>

      {/* Description */}
      {agent.description && (
        <p className="mt-3 text-sm text-muted-foreground line-clamp-2">
          {agent.description}
        </p>
      )}

      {/* Capabilities */}
      {agent.capabilities && agent.capabilities.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1">
          {agent.capabilities.slice(0, 3).map((cap) => (
            <span
              key={cap}
              className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground"
            >
              {cap}
            </span>
          ))}
          {agent.capabilities.length > 3 && (
            <span className="text-xs px-2 py-0.5 rounded-full bg-muted text-muted-foreground">
              +{agent.capabilities.length - 3} more
            </span>
          )}
        </div>
      )}

      {/* Footer */}
      <div className="mt-4 flex items-center justify-between">
        <div className="flex items-center gap-2 text-xs text-muted-foreground">
          <Clock className="h-3 w-3" />
          <span>Created {formatDate(agent.created_at)}</span>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={onExecute}>
            <Play className="h-3 w-3 mr-1" />
            Run
          </Button>
          {!isPublic && onDelete && (
            <Button
              variant="ghost"
              size="sm"
              onClick={onDelete}
              className="text-destructive hover:text-destructive"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          )}
        </div>
      </div>
    </div>
  );
}
