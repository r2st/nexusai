'use client';

import { useState } from 'react';
import Link from 'next/link';
import {
  Activity,
  BarChart3,
  Clock,
  GitBranch,
  AlertTriangle,
  ArrowUpRight,
  Play,
  Loader2,
  CheckCircle,
  XCircle,
  Users,
  TrendingUp,
  RefreshCw,
  ChevronRight,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { devopsApi, type DORAAnalysis, type WorkflowExecution } from '@/lib/api';

export default function DevOpsPage() {
  const [projectId, setProjectId] = useState('');
  const [organizationId, setOrganizationId] = useState('');
  const [periodDays, setPeriodDays] = useState(30);
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [doraAnalysis, setDoraAnalysis] = useState<DORAAnalysis | null>(null);
  const [adoptionAnalysis, setAdoptionAnalysis] = useState<Record<string, unknown> | null>(null);
  const [workflow, setWorkflow] = useState<WorkflowExecution | null>(null);
  const [activeTab, setActiveTab] = useState<'dora' | 'adoption' | 'workflow'>('dora');

  const handleDORAAnalysis = async () => {
    if (!projectId.trim()) return;

    setIsAnalyzing(true);
    try {
      const result = await devopsApi.analyzeDORA(projectId, periodDays);
      setDoraAnalysis(result);
    } catch (error) {
      console.error('DORA analysis failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleAdoptionAnalysis = async () => {
    if (!organizationId.trim()) return;

    setIsAnalyzing(true);
    try {
      const result = await devopsApi.analyzeAdoption(organizationId, periodDays);
      setAdoptionAnalysis(result);
    } catch (error) {
      console.error('Adoption analysis failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const handleRunWorkflow = async (workflowType: string) => {
    setIsAnalyzing(true);
    try {
      const result = await devopsApi.createWorkflow(workflowType, {
        project_id: projectId || 'default-project',
        organization_id: organizationId || 'default-org',
        period_days: periodDays,
      });
      setWorkflow(result);
      setActiveTab('workflow');
    } catch (error) {
      console.error('Workflow failed:', error);
    } finally {
      setIsAnalyzing(false);
    }
  };

  const getLevelColor = (level: string) => {
    switch (level.toLowerCase()) {
      case 'elite':
        return 'text-green-500 bg-green-100 dark:bg-green-900';
      case 'high':
        return 'text-blue-500 bg-blue-100 dark:bg-blue-900';
      case 'medium':
        return 'text-yellow-500 bg-yellow-100 dark:bg-yellow-900';
      case 'low':
        return 'text-red-500 bg-red-100 dark:bg-red-900';
      default:
        return 'text-gray-500 bg-gray-100 dark:bg-gray-800';
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="h-4 w-4 text-green-500" />;
      case 'running':
        return <Loader2 className="h-4 w-4 animate-spin text-blue-500" />;
      case 'failed':
        return <XCircle className="h-4 w-4 text-red-500" />;
      default:
        return <Clock className="h-4 w-4 text-gray-500" />;
    }
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b">
        <div className="container mx-auto flex h-16 items-center justify-between px-4">
          <div className="flex items-center gap-4">
            <Link href="/" className="flex items-center gap-2">
              <Activity className="h-6 w-6 text-primary" />
              <span className="text-xl font-bold">DevOps Intelligence</span>
            </Link>
          </div>
          <div className="flex items-center gap-2">
            <Link href="/analytics">
              <Button variant="outline" size="sm">
                <BarChart3 className="mr-2 h-4 w-4" />
                DevLake Dashboard
              </Button>
            </Link>
            <Link href="/agents">
              <Button variant="ghost" size="sm">
                Go to Agents
              </Button>
            </Link>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        {/* Input Section */}
        <div className="mb-8 rounded-lg border p-6">
          <h2 className="text-lg font-semibold mb-4">Analysis Configuration</h2>
          <div className="grid gap-4 md:grid-cols-3">
            <div>
              <label className="text-sm font-medium">Project ID</label>
              <Input
                value={projectId}
                onChange={(e) => setProjectId(e.target.value)}
                placeholder="e.g., nexusai-backend"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Organization ID</label>
              <Input
                value={organizationId}
                onChange={(e) => setOrganizationId(e.target.value)}
                placeholder="e.g., my-organization"
                className="mt-1"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Period (Days)</label>
              <Input
                type="number"
                value={periodDays}
                onChange={(e) => setPeriodDays(parseInt(e.target.value) || 30)}
                min={7}
                max={365}
                className="mt-1"
              />
            </div>
          </div>
          <div className="mt-4 flex flex-wrap gap-2">
            <Button onClick={handleDORAAnalysis} disabled={isAnalyzing || !projectId}>
              {isAnalyzing && activeTab === 'dora' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Play className="mr-2 h-4 w-4" />
              )}
              Analyze DORA Metrics
            </Button>
            <Button
              variant="outline"
              onClick={handleAdoptionAnalysis}
              disabled={isAnalyzing || !organizationId}
            >
              {isAnalyzing && activeTab === 'adoption' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <Users className="mr-2 h-4 w-4" />
              )}
              Analyze AI Adoption
            </Button>
            <Button
              variant="secondary"
              onClick={() => handleRunWorkflow('dora_full')}
              disabled={isAnalyzing}
            >
              {isAnalyzing && activeTab === 'workflow' ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <TrendingUp className="mr-2 h-4 w-4" />
              )}
              Run Full Workflow
            </Button>
          </div>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b">
          <button
            onClick={() => setActiveTab('dora')}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === 'dora'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            DORA Metrics
          </button>
          <button
            onClick={() => setActiveTab('adoption')}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === 'adoption'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            AI Adoption
          </button>
          <button
            onClick={() => setActiveTab('workflow')}
            className={`px-4 py-2 border-b-2 transition-colors ${
              activeTab === 'workflow'
                ? 'border-primary text-primary'
                : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Workflow
          </button>
        </div>

        {/* DORA Tab */}
        {activeTab === 'dora' && (
          <div>
            {doraAnalysis ? (
              <>
                {/* Overall Level */}
                <div className="mb-6 flex items-center gap-4">
                  <span className="text-lg font-medium">Overall Performance:</span>
                  <span
                    className={`px-3 py-1 rounded-full font-medium ${getLevelColor(
                      doraAnalysis.overall_level
                    )}`}
                  >
                    {doraAnalysis.overall_level}
                  </span>
                </div>

                {/* Metrics Grid */}
                <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4 mb-8">
                  {/* Deployment Frequency */}
                  <div className="rounded-lg border bg-card p-6">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <GitBranch className="h-4 w-4" />
                      <span className="text-sm">Deployment Frequency</span>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold">
                        {doraAnalysis.metrics.deployment_frequency.value.toFixed(2)}
                      </div>
                      <div className="text-sm text-muted-foreground">per day</div>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${getLevelColor(
                          doraAnalysis.metrics.deployment_frequency.level
                        )}`}
                      >
                        {doraAnalysis.metrics.deployment_frequency.level}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {doraAnalysis.metrics.deployment_frequency.trend}
                      </span>
                    </div>
                  </div>

                  {/* Lead Time */}
                  <div className="rounded-lg border bg-card p-6">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <Clock className="h-4 w-4" />
                      <span className="text-sm">Lead Time for Changes</span>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold">
                        {doraAnalysis.metrics.lead_time.value.toFixed(1)}
                      </div>
                      <div className="text-sm text-muted-foreground">hours</div>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${getLevelColor(
                          doraAnalysis.metrics.lead_time.level
                        )}`}
                      >
                        {doraAnalysis.metrics.lead_time.level}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {doraAnalysis.metrics.lead_time.trend}
                      </span>
                    </div>
                  </div>

                  {/* MTTR */}
                  <div className="rounded-lg border bg-card p-6">
                    <div className="flex items-center gap-2 text-muted-foreground">
                      <ArrowUpRight className="h-4 w-4" />
                      <span className="text-sm">Mean Time to Recovery</span>
                    </div>
                    <div className="mt-4">
                      <div className="text-3xl font-bold">
                        {doraAnalysis.metrics.mttr.value.toFixed(1)}
                      </div>
                      <div className="text-sm text-muted-foreground">hours</div>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${getLevelColor(
                          doraAnalysis.metrics.mttr.level
                        )}`}
                      >
                        {doraAnalysis.metrics.mttr.level}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {doraAnalysis.metrics.mttr.trend}
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
                        {doraAnalysis.metrics.change_failure_rate.value.toFixed(1)}
                      </div>
                      <div className="text-sm text-muted-foreground">%</div>
                    </div>
                    <div className="mt-2 flex items-center justify-between">
                      <span
                        className={`text-sm font-medium px-2 py-0.5 rounded ${getLevelColor(
                          doraAnalysis.metrics.change_failure_rate.level
                        )}`}
                      >
                        {doraAnalysis.metrics.change_failure_rate.level}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {doraAnalysis.metrics.change_failure_rate.trend}
                      </span>
                    </div>
                  </div>
                </div>

                {/* Recommendations */}
                {doraAnalysis.recommendations.length > 0 && (
                  <section className="mb-8">
                    <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
                    <div className="space-y-2">
                      {doraAnalysis.recommendations.map((rec, index) => (
                        <div
                          key={index}
                          className="flex items-start gap-3 p-3 rounded-lg bg-muted"
                        >
                          <ChevronRight className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                          <span className="text-sm">{rec}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}

                {/* Insights */}
                {doraAnalysis.insights.length > 0 && (
                  <section>
                    <h3 className="text-lg font-semibold mb-4">Insights</h3>
                    <div className="space-y-2">
                      {doraAnalysis.insights.map((insight, index) => (
                        <div
                          key={index}
                          className="p-3 rounded-lg border"
                        >
                          <span className="text-sm">{insight}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </>
            ) : (
              <div className="text-center py-12">
                <BarChart3 className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No DORA Analysis Yet</h3>
                <p className="mt-2 text-muted-foreground">
                  Enter a project ID and click "Analyze DORA Metrics" to get started.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Adoption Tab */}
        {activeTab === 'adoption' && (
          <div>
            {adoptionAnalysis ? (
              <div className="space-y-6">
                <div className="grid gap-4 md:grid-cols-3">
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Adoption Rate</div>
                    <div className="text-3xl font-bold mt-2">
                      {(adoptionAnalysis.adoption_rate as number)?.toFixed(1) || 0}%
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Active Users</div>
                    <div className="text-3xl font-bold mt-2">
                      {(adoptionAnalysis.active_users as number) || 0}
                    </div>
                  </div>
                  <div className="rounded-lg border p-4">
                    <div className="text-sm text-muted-foreground">Top Tool</div>
                    <div className="text-xl font-bold mt-2">
                      {(adoptionAnalysis.top_tool as string) || 'N/A'}
                    </div>
                  </div>
                </div>

                {Array.isArray(adoptionAnalysis.recommendations) && adoptionAnalysis.recommendations.length > 0 && (
                  <section>
                    <h3 className="text-lg font-semibold mb-4">Recommendations</h3>
                    <div className="space-y-2">
                      {(adoptionAnalysis.recommendations as string[]).map((rec: string, index: number) => (
                        <div
                          key={index}
                          className="flex items-start gap-3 p-3 rounded-lg bg-muted"
                        >
                          <ChevronRight className="h-4 w-4 mt-0.5 text-primary shrink-0" />
                          <span className="text-sm">{String(rec)}</span>
                        </div>
                      ))}
                    </div>
                  </section>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <Users className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No Adoption Analysis Yet</h3>
                <p className="mt-2 text-muted-foreground">
                  Enter an organization ID and click "Analyze AI Adoption" to get started.
                </p>
              </div>
            )}
          </div>
        )}

        {/* Workflow Tab */}
        {activeTab === 'workflow' && (
          <div>
            {workflow ? (
              <div className="space-y-6">
                {/* Workflow Status */}
                <div className="rounded-lg border p-4">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <h3 className="font-semibold">{workflow.workflow_type}</h3>
                      <p className="text-sm text-muted-foreground">
                        ID: {workflow.workflow_id}
                      </p>
                    </div>
                    <div className="flex items-center gap-2">
                      {getStatusIcon(workflow.status)}
                      <span className="font-medium">{workflow.status}</span>
                    </div>
                  </div>

                  {/* Steps */}
                  <div className="space-y-3">
                    {workflow.steps.map((step) => (
                      <div
                        key={step.step_number}
                        className="flex items-center gap-4 p-3 rounded-lg bg-muted"
                      >
                        <div className="flex h-8 w-8 items-center justify-center rounded-full bg-background">
                          {step.step_number}
                        </div>
                        <div className="flex-1">
                          <div className="font-medium">{step.agent_name}</div>
                          <div className="text-xs text-muted-foreground">
                            {step.started_at
                              ? new Date(step.started_at).toLocaleTimeString()
                              : 'Not started'}
                          </div>
                        </div>
                        {getStatusIcon(step.status)}
                      </div>
                    ))}
                  </div>
                </div>

                {/* Final Output */}
                {workflow.final_output && (
                  <div className="rounded-lg border p-4">
                    <h3 className="font-semibold mb-4">Output</h3>
                    <pre className="text-sm bg-muted p-4 rounded-lg overflow-auto max-h-96">
                      {JSON.stringify(workflow.final_output, null, 2)}
                    </pre>
                  </div>
                )}
              </div>
            ) : (
              <div className="text-center py-12">
                <Activity className="mx-auto h-12 w-12 text-muted-foreground" />
                <h3 className="mt-4 text-lg font-medium">No Workflow Running</h3>
                <p className="mt-2 text-muted-foreground">
                  Click "Run Full Workflow" to execute the agent orchestration pipeline.
                </p>
              </div>
            )}
          </div>
        )}
      </main>
    </div>
  );
}
