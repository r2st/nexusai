'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Bot,
  Plus,
  Settings,
  Play,
  Trash2,
  ChevronRight,
  Activity,
  Clock,
  Zap,
  Globe,
  Lock,
  RefreshCw,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import { agentsApi, type Agent } from '@/lib/api';
import { AgentCard } from '@/components/agents/agent-card';
import { CreateAgentModal } from '@/components/agents/create-agent-modal';
import { AgentExecutor } from '@/components/agents/agent-executor';

export default function AgentsPage() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [showCreateModal, setShowCreateModal] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [showExecutor, setShowExecutor] = useState(false);
  const [includePublic, setIncludePublic] = useState(false);

  useEffect(() => {
    loadAgents();
  }, [includePublic]);

  const loadAgents = async () => {
    setIsLoading(true);
    try {
      const data = await agentsApi.list(50, 0, includePublic);
      setAgents(data);
    } catch (error) {
      console.error('Failed to load agents:', error);
      toast.error('Failed to load agents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateAgent = async (agentData: Parameters<typeof agentsApi.create>[0]) => {
    try {
      const newAgent = await agentsApi.create(agentData);
      setAgents((prev) => [newAgent, ...prev]);
      setShowCreateModal(false);
    } catch (error) {
      console.error('Failed to create agent:', error);
      toast.error('Failed to create agent');
      throw error;
    }
  };

  const handleDeleteAgent = async (agentId: string) => {
    if (!confirm('Are you sure you want to delete this agent?')) return;

    try {
      await agentsApi.delete(agentId);
      setAgents((prev) => prev.filter((a) => a.id !== agentId));
    } catch (error) {
      console.error('Failed to delete agent:', error);
      toast.error('Failed to delete agent');
    }
  };

  const handleExecuteAgent = (agent: Agent) => {
    setSelectedAgent(agent);
    setShowExecutor(true);
  };

  const myAgents = agents.filter((a) => !a.is_public);
  const publicAgents = agents.filter((a) => a.is_public);

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Bot className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">GSTIndia Agents</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={loadAgents}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Refresh
            </Button>
            <Button size="sm" onClick={() => setShowCreateModal(true)}>
              <Plus className="mr-2 h-4 w-4" />
              Create Agent
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
        {/* Stats Overview */}
        <div className="mb-8 grid gap-4 md:grid-cols-4">
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Bot className="h-4 w-4" />
              <span className="text-sm">Total Agents</span>
            </div>
            <div className="mt-2 text-2xl font-bold">{agents.length}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Lock className="h-4 w-4" />
              <span className="text-sm">My Agents</span>
            </div>
            <div className="mt-2 text-2xl font-bold">{myAgents.length}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Globe className="h-4 w-4" />
              <span className="text-sm">Public Agents</span>
            </div>
            <div className="mt-2 text-2xl font-bold">{publicAgents.length}</div>
          </div>
          <div className="rounded-lg border bg-card p-4">
            <div className="flex items-center gap-2 text-muted-foreground">
              <Activity className="h-4 w-4" />
              <span className="text-sm">Active</span>
            </div>
            <div className="mt-2 text-2xl font-bold">
              {agents.filter((a) => a.is_active).length}
            </div>
          </div>
        </div>

        {/* Filter Toggle */}
        <div className="mb-6 flex items-center gap-4">
          <label className="flex items-center gap-2 cursor-pointer">
            <input
              type="checkbox"
              checked={includePublic}
              onChange={(e) => setIncludePublic(e.target.checked)}
              className="rounded border-gray-300"
            />
            <span className="text-sm">Include public agents</span>
          </label>
        </div>

        {/* Agents Grid */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <RefreshCw className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : agents.length === 0 ? (
          <div className="text-center py-12">
            <Bot className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">No agents yet</h3>
            <p className="mt-2 text-muted-foreground">
              Create your first agent to get started
            </p>
            <Button
              className="mt-4"
              onClick={() => setShowCreateModal(true)}
            >
              <Plus className="mr-2 h-4 w-4" />
              Create Agent
            </Button>
          </div>
        ) : (
          <>
            {/* My Agents Section */}
            {myAgents.length > 0 && (
              <section className="mb-8">
                <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
                  <Lock className="h-5 w-5" />
                  My Agents
                </h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {myAgents.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      onExecute={() => handleExecuteAgent(agent)}
                      onDelete={() => handleDeleteAgent(agent.id)}
                    />
                  ))}
                </div>
              </section>
            )}

            {/* Public Agents Section */}
            {publicAgents.length > 0 && includePublic && (
              <section>
                <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
                  <Globe className="h-5 w-5" />
                  Public Agents
                </h2>
                <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                  {publicAgents.map((agent) => (
                    <AgentCard
                      key={agent.id}
                      agent={agent}
                      onExecute={() => handleExecuteAgent(agent)}
                      isPublic
                    />
                  ))}
                </div>
              </section>
            )}
          </>
        )}

        {/* Quick Actions */}
        <section className="mt-12">
          <h2 className="mb-4 text-xl font-semibold">Quick Actions</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Link
              href="/devops"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">DevOps Agents</div>
                <div className="text-sm text-muted-foreground">
                  DORA metrics & adoption analysis
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              href="/knowledge-graph"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">Knowledge Graph</div>
                <div className="text-sm text-muted-foreground">
                  Explore data relationships
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              href="/actions"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Settings className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">OpenAPI Actions</div>
                <div className="text-sm text-muted-foreground">
                  Manage external integrations
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>
          </div>
        </section>
      </main>

      {/* Create Agent Modal */}
      {showCreateModal && (
        <CreateAgentModal
          onClose={() => setShowCreateModal(false)}
          onCreate={handleCreateAgent}
        />
      )}

      {/* Agent Executor */}
      {showExecutor && selectedAgent && (
        <AgentExecutor
          agent={selectedAgent}
          onClose={() => {
            setShowExecutor(false);
            setSelectedAgent(null);
          }}
        />
      )}
    </div>
  );
}
