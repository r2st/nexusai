'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import {
  Network,
  Database,
  Search,
  RefreshCw,
  Activity,
  Table,
  BarChart3,
  Zap,
  ChevronRight,
  Loader2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { knowledgeGraphApi, type KnowledgeGraphStats, type DiscoveryResult } from '@/lib/api';
import { toast } from 'sonner';

export default function KnowledgeGraphPage() {
  const [stats, setStats] = useState<KnowledgeGraphStats | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSyncing, setIsSyncing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [discoveryResult, setDiscoveryResult] = useState<DiscoveryResult | null>(null);
  const [tables, setTables] = useState<string[]>([]);
  const [metrics, setMetrics] = useState<string[]>([]);

  useEffect(() => {
    loadData();
  }, []);

  const loadData = async () => {
    setIsLoading(true);
    try {
      const [statsData, tablesData, metricsData] = await Promise.all([
        knowledgeGraphApi.getStats(),
        knowledgeGraphApi.getTables(),
        knowledgeGraphApi.getMetrics(),
      ]);
      setStats(statsData);
      setTables(tablesData.tables);
      setMetrics(metricsData.metrics);
    } catch (error) {
      console.error('Failed to load knowledge graph data:', error);
      toast.error('Failed to load knowledge graph data');
    } finally {
      setIsLoading(false);
    }
  };

  const handleSync = async () => {
    setIsSyncing(true);
    try {
      const result = await knowledgeGraphApi.syncFromPostgres();
      toast.success(`Synced ${result.synced_entities} entities from PostgreSQL`);
      loadData();
    } catch {
      toast.error('Failed to sync from PostgreSQL');
    } finally {
      setIsSyncing(false);
    }
  };

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;

    setIsSearching(true);
    try {
      const result = await knowledgeGraphApi.discover(searchQuery);
      setDiscoveryResult(result);
    } catch (error) {
      console.error('Discovery failed:', error);
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Network className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">Knowledge Graph</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={isSyncing}
            >
              {isSyncing ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="mr-2 h-4 w-4" />
              )}
              Sync from PostgreSQL
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
        {/* Stats Overview */}
        {isLoading ? (
          <div className="flex items-center justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        ) : stats ? (
          <>
            <div className="mb-8 grid gap-4 md:grid-cols-4">
              <div className="rounded-lg border bg-card p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Database className="h-4 w-4" />
                  <span className="text-sm">Total Nodes</span>
                </div>
                <div className="mt-2 text-2xl font-bold">
                  {stats.total_nodes.toLocaleString()}
                </div>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Activity className="h-4 w-4" />
                  <span className="text-sm">Relationships</span>
                </div>
                <div className="mt-2 text-2xl font-bold">
                  {stats.total_relationships.toLocaleString()}
                </div>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <Table className="h-4 w-4" />
                  <span className="text-sm">Tables</span>
                </div>
                <div className="mt-2 text-2xl font-bold">{tables.length}</div>
              </div>
              <div className="rounded-lg border bg-card p-4">
                <div className="flex items-center gap-2 text-muted-foreground">
                  <BarChart3 className="h-4 w-4" />
                  <span className="text-sm">Metrics</span>
                </div>
                <div className="mt-2 text-2xl font-bold">{metrics.length}</div>
              </div>
            </div>

            {/* Discovery Search */}
            <section className="mb-8">
              <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
                <Search className="h-5 w-5" />
                Discovery Search
              </h2>
              <p className="mb-4 text-muted-foreground">
                Ask questions about your data to discover relevant tables, metrics, and relationships.
              </p>
              <form onSubmit={handleSearch} className="flex gap-2 max-w-2xl">
                <Input
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  placeholder="e.g., What metrics are related to deployment frequency?"
                  className="flex-1"
                />
                <Button type="submit" disabled={isSearching || !searchQuery.trim()} aria-label="Search knowledge graph">
                  {isSearching ? (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  ) : (
                    <Search className="h-4 w-4" aria-hidden="true" />
                  )}
                </Button>
              </form>

              {/* Discovery Results */}
              {discoveryResult && (
                <div className="mt-6 rounded-lg border p-4">
                  <h3 className="font-medium mb-3">Discovery Results</h3>

                  {discoveryResult.query_suggestion && (
                    <div className="mb-4 p-3 rounded-lg bg-primary/10">
                      <p className="text-sm font-medium mb-1">Suggested Query</p>
                      <code className="text-sm">{discoveryResult.query_suggestion}</code>
                    </div>
                  )}

                  <div className="grid gap-4 md:grid-cols-3">
                    {/* Tables */}
                    <div>
                      <p className="text-sm font-medium mb-2">Related Tables</p>
                      <div className="space-y-1">
                        {discoveryResult.tables.length > 0 ? (
                          discoveryResult.tables.map((table) => (
                            <div
                              key={table}
                              className="text-sm px-2 py-1 rounded bg-muted"
                            >
                              {table}
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">None found</p>
                        )}
                      </div>
                    </div>

                    {/* Metrics */}
                    <div>
                      <p className="text-sm font-medium mb-2">Related Metrics</p>
                      <div className="space-y-1">
                        {discoveryResult.metrics.length > 0 ? (
                          discoveryResult.metrics.map((metric) => (
                            <div
                              key={metric}
                              className="text-sm px-2 py-1 rounded bg-muted"
                            >
                              {metric}
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">None found</p>
                        )}
                      </div>
                    </div>

                    {/* DORA Entities */}
                    <div>
                      <p className="text-sm font-medium mb-2">DORA Entities</p>
                      <div className="space-y-1">
                        {discoveryResult.dora_entities.length > 0 ? (
                          discoveryResult.dora_entities.map((entity) => (
                            <div
                              key={entity}
                              className="text-sm px-2 py-1 rounded bg-muted"
                            >
                              {entity}
                            </div>
                          ))
                        ) : (
                          <p className="text-sm text-muted-foreground">None found</p>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </section>

            {/* Node Labels */}
            <section className="mb-8">
              <h2 className="mb-4 text-xl font-semibold">Node Labels</h2>
              <div className="grid gap-3 md:grid-cols-4 lg:grid-cols-6">
                {Object.entries(stats.node_labels).map(([label, count]) => (
                  <div key={label} className="rounded-lg border p-3">
                    <div className="font-medium text-sm">{label}</div>
                    <div className="text-2xl font-bold mt-1">{count}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* Relationship Types */}
            <section className="mb-8">
              <h2 className="mb-4 text-xl font-semibold">Relationship Types</h2>
              <div className="grid gap-3 md:grid-cols-4 lg:grid-cols-6">
                {Object.entries(stats.relationship_types).map(([type, count]) => (
                  <div key={type} className="rounded-lg border p-3">
                    <div className="font-medium text-sm">{type}</div>
                    <div className="text-2xl font-bold mt-1">{count}</div>
                  </div>
                ))}
              </div>
            </section>

            {/* Tables List */}
            <section className="mb-8">
              <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
                <Table className="h-5 w-5" />
                Database Tables
              </h2>
              <div className="grid gap-2 md:grid-cols-4 lg:grid-cols-6">
                {tables.map((table) => (
                  <div
                    key={table}
                    className="rounded-lg border p-3 text-sm hover:bg-muted transition-colors cursor-pointer"
                  >
                    {table}
                  </div>
                ))}
              </div>
            </section>

            {/* Metrics List */}
            <section>
              <h2 className="mb-4 text-xl font-semibold flex items-center gap-2">
                <BarChart3 className="h-5 w-5" />
                Available Metrics
              </h2>
              <div className="grid gap-2 md:grid-cols-4 lg:grid-cols-6">
                {metrics.map((metric) => (
                  <div
                    key={metric}
                    className="rounded-lg border p-3 text-sm hover:bg-muted transition-colors cursor-pointer"
                  >
                    {metric}
                  </div>
                ))}
              </div>
            </section>
          </>
        ) : (
          <div className="text-center py-12">
            <Network className="mx-auto h-12 w-12 text-muted-foreground" />
            <h3 className="mt-4 text-lg font-medium">Knowledge Graph Not Available</h3>
            <p className="mt-2 text-muted-foreground">
              Neo4j may not be configured or running.
            </p>
          </div>
        )}

        {/* Quick Actions */}
        <section className="mt-12">
          <h2 className="mb-4 text-xl font-semibold">Related Features</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <Link
              href="/agents"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Zap className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">AI Agents</div>
                <div className="text-sm text-muted-foreground">
                  Create and manage agents
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              href="/devops"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Activity className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">DevOps Analytics</div>
                <div className="text-sm text-muted-foreground">
                  DORA metrics & adoption
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>

            <Link
              href="/chat"
              className="flex items-center gap-4 rounded-lg border p-4 hover:bg-muted transition-colors"
            >
              <div className="flex h-12 w-12 items-center justify-center rounded-lg bg-primary/10">
                <Search className="h-6 w-6 text-primary" />
              </div>
              <div>
                <div className="font-medium">Ask AI</div>
                <div className="text-sm text-muted-foreground">
                  Query your data with AI
                </div>
              </div>
              <ChevronRight className="ml-auto h-4 w-4 text-muted-foreground" />
            </Link>
          </div>
        </section>
      </main>
    </div>
  );
}
