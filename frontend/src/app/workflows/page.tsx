"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { WorkflowDesigner } from "@/components/workflow/workflow-designer";
import { WorkflowTemplates, WORKFLOW_TEMPLATES, type WorkflowTemplate } from "@/components/workflow/workflow-templates";
import {
  Plus,
  Search,
  MoreVertical,
  Play,
  Pause,
  Edit,
  Trash2,
  Copy,
  History,
  Zap,
  CheckCircle,
  XCircle,
  Clock,
  LayoutTemplate,
  Loader2,
} from "lucide-react";
import { toast } from "sonner";

interface Workflow {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: string;
  lastRun: string;
  runCount: number;
  successRate: number;
  status: string;
}

interface ExecutionRecord {
  id: string;
  workflow_name: string;
  status: string;
  trigger_type: string;
  started_at: string | null;
  duration_ms: number | null;
}

export default function WorkflowsPage() {
  const [workflows, setWorkflows] = useState<Workflow[]>([]);
  const [executions, setExecutions] = useState<ExecutionRecord[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("my-workflows");
  const [showDesigner, setShowDesigner] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);

  const loadWorkflows = useCallback(async () => {
    setIsLoading(true);
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const [wfRes, exRes] = await Promise.all([
        fetch("/api/v1/workflows", { headers }),
        fetch("/api/v1/workflows/executions?limit=10", { headers }),
      ]);

      if (wfRes.ok) {
        const wfData = await wfRes.json();
        const mapped = (wfData.workflows || []).map((w: any) => ({
          id: w.id,
          name: w.name,
          description: w.description || "",
          enabled: w.status === "active",
          trigger: w.triggers?.[0]?.trigger_type || "manual",
          lastRun: "",
          runCount: 0,
          successRate: 0,
          status: w.status,
        }));
        setWorkflows(mapped);
      }

      if (exRes.ok) {
        const exData = await exRes.json();
        setExecutions(exData.executions || []);
      }
    } catch {
      toast.error("Failed to load workflows");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadWorkflows();
  }, [loadWorkflows]);

  const filteredWorkflows = workflows.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateFromTemplate = (template: WorkflowTemplate) => {
    const newWorkflow = {
      id: crypto.randomUUID(),
      name: template.name,
      description: template.description,
      enabled: false,
      trigger: template.trigger,
      nodes: template.nodes.map((node, index) => ({
        ...node,
        id: crypto.randomUUID(),
        position: { x: 100 + index * 220, y: 100 },
        connections: [],
      })),
      edges: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
    setSelectedWorkflow(newWorkflow);
    setShowDesigner(true);
  };

  const handleCreateNew = () => {
    setSelectedWorkflow(null);
    setShowDesigner(true);
  };

  const handleEditWorkflow = (workflow: any) => {
    setSelectedWorkflow(workflow);
    setShowDesigner(true);
  };

  const handleSaveWorkflow = async (workflow: any) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      await fetch("/api/v1/workflows", {
        method: "POST",
        headers,
        body: JSON.stringify({
          name: workflow.name,
          organization_id: workflow.organization_id || "default",
          description: workflow.description,
          triggers: workflow.triggers || [],
          steps: workflow.steps || [],
        }),
      });

      toast.success("Workflow saved");
      setShowDesigner(false);
      loadWorkflows();
    } catch {
      toast.error("Failed to save workflow");
    }
  };

  const handleToggleWorkflow = async (workflow: Workflow) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const endpoint = workflow.enabled
        ? `/api/v1/workflows/${workflow.id}/pause`
        : `/api/v1/workflows/${workflow.id}/activate`;

      const res = await fetch(endpoint, { method: "POST", headers });
      if (res.ok) {
        toast.success(workflow.enabled ? "Workflow paused" : "Workflow activated");
        loadWorkflows();
      } else {
        toast.error("Failed to update workflow");
      }
    } catch {
      toast.error("Failed to update workflow");
    }
  };

  const handleDeleteWorkflow = async (workflow: Workflow) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {};
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch(`/api/v1/workflows/${workflow.id}`, {
        method: "DELETE",
        headers,
      });
      if (res.ok) {
        toast.success("Workflow deleted");
        setWorkflows((prev) => prev.filter((w) => w.id !== workflow.id));
      } else {
        toast.error("Failed to delete workflow");
      }
    } catch {
      toast.error("Failed to delete workflow");
    }
  };

  const handleDuplicateWorkflow = async (workflow: Workflow) => {
    try {
      const token = localStorage.getItem("access_token");
      const headers: Record<string, string> = {
        "Content-Type": "application/json",
      };
      if (token) headers["Authorization"] = `Bearer ${token}`;

      const res = await fetch("/api/v1/workflows", {
        method: "POST",
        headers,
        body: JSON.stringify({
          name: `${workflow.name} (copy)`,
          organization_id: "default",
          description: workflow.description,
          triggers: [],
          steps: [],
        }),
      });

      if (res.ok) {
        toast.success("Workflow duplicated");
        loadWorkflows();
      } else {
        toast.error("Failed to duplicate workflow");
      }
    } catch {
      toast.error("Failed to duplicate workflow");
    }
  };

  const formatDuration = (ms: number | null): string => {
    if (ms == null) return "—";
    if (ms < 1000) return `${ms}ms`;
    return `${(ms / 1000).toFixed(1)}s`;
  };

  const formatTime = (iso: string | null): string => {
    if (!iso) return "—";
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 60000) return "just now";
    if (diff < 3600000) return `${Math.floor(diff / 60000)} min ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)} hours ago`;
    return `${Math.floor(diff / 86400000)} days ago`;
  };

  if (showDesigner) {
    return (
      <div className="h-screen flex flex-col">
        <div className="border-b p-3 flex items-center justify-between bg-background">
          <Button variant="ghost" onClick={() => setShowDesigner(false)}>
            ← Back to Workflows
          </Button>
        </div>
        <div className="flex-1">
          <WorkflowDesigner
            workflow={selectedWorkflow}
            onSave={handleSaveWorkflow}
          />
        </div>
      </div>
    );
  }

  return (
    <div className="container mx-auto py-8 px-4 max-w-7xl">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-3xl font-bold">Workflow Automation</h1>
          <p className="text-muted-foreground mt-1">
            Create automated workflows to streamline your development process
          </p>
        </div>
        <Button onClick={handleCreateNew}>
          <Plus className="h-4 w-4 mr-2" />
          New Workflow
        </Button>
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <div className="flex items-center justify-between mb-6">
          <TabsList>
            <TabsTrigger value="my-workflows">
              <Zap className="h-4 w-4 mr-2" />
              My Workflows
            </TabsTrigger>
            <TabsTrigger value="templates">
              <LayoutTemplate className="h-4 w-4 mr-2" />
              Templates
            </TabsTrigger>
            <TabsTrigger value="history">
              <History className="h-4 w-4 mr-2" />
              Run History
            </TabsTrigger>
          </TabsList>

          {activeTab === "my-workflows" && (
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" aria-hidden="true" />
              <Input
                placeholder="Search workflows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
                aria-label="Search workflows"
              />
            </div>
          )}
        </div>

        <TabsContent value="my-workflows">
          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredWorkflows.length === 0 ? (
            <Card className="text-center py-12">
              <CardContent>
                <Zap className="h-12 w-12 mx-auto text-muted-foreground mb-4" />
                <h3 className="text-lg font-medium mb-2">No workflows yet</h3>
                <p className="text-muted-foreground mb-4">
                  Create your first workflow to automate repetitive tasks
                </p>
                <div className="flex gap-2 justify-center">
                  <Button onClick={handleCreateNew}>
                    <Plus className="h-4 w-4 mr-2" />
                    Create Workflow
                  </Button>
                  <Button variant="outline" onClick={() => setActiveTab("templates")}>
                    Browse Templates
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4">
              {filteredWorkflows.map((workflow) => (
                <Card key={workflow.id} className="hover:border-primary/50 transition-colors">
                  <CardHeader className="pb-3">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div
                          className={`p-2 rounded-lg ${
                            workflow.enabled
                              ? "bg-green-500/10"
                              : "bg-muted"
                          }`}
                        >
                          <Zap
                            className={`h-5 w-5 ${
                              workflow.enabled
                                ? "text-green-500"
                                : "text-muted-foreground"
                            }`}
                          />
                        </div>
                        <div>
                          <CardTitle className="text-base flex items-center gap-2">
                            {workflow.name}
                            <Badge
                              variant={workflow.enabled ? "default" : "secondary"}
                            >
                              {workflow.enabled ? "Active" : "Paused"}
                            </Badge>
                          </CardTitle>
                          <CardDescription>{workflow.description}</CardDescription>
                        </div>
                      </div>
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="icon" aria-label={`Actions for ${workflow.name}`}>
                            <MoreVertical className="h-4 w-4" aria-hidden="true" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEditWorkflow(workflow)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleDuplicateWorkflow(workflow)}>
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => handleToggleWorkflow(workflow)}>
                            {workflow.enabled ? (
                              <>
                                <Pause className="h-4 w-4 mr-2" />
                                Pause
                              </>
                            ) : (
                              <>
                                <Play className="h-4 w-4 mr-2" />
                                Enable
                              </>
                            )}
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => setActiveTab("history")}>
                            <History className="h-4 w-4 mr-2" />
                            View History
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={() => handleDeleteWorkflow(workflow)}
                          >
                            <Trash2 className="h-4 w-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </CardHeader>
                  <CardContent>
                    <div className="flex items-center gap-6 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1.5">
                        <Clock className="h-4 w-4" />
                        <span>Trigger: {workflow.trigger.replace(/_/g, " ")}</span>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </TabsContent>

        <TabsContent value="templates">
          <WorkflowTemplates onSelect={handleCreateFromTemplate} />
        </TabsContent>

        <TabsContent value="history">
          <Card>
            <CardHeader>
              <CardTitle>Recent Workflow Runs</CardTitle>
              <CardDescription>
                View the execution history of your workflows
              </CardDescription>
            </CardHeader>
            <CardContent>
              {executions.length === 0 ? (
                <p className="text-center text-muted-foreground py-8">
                  No execution history yet
                </p>
              ) : (
                <div className="space-y-4">
                  {executions.map((run) => (
                    <div
                      key={run.id}
                      className="flex items-center justify-between py-3 border-b last:border-0"
                    >
                      <div className="flex items-center gap-3">
                        {run.status === "completed" ? (
                          <CheckCircle className="h-5 w-5 text-green-500" />
                        ) : run.status === "failed" ? (
                          <XCircle className="h-5 w-5 text-red-500" />
                        ) : (
                          <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
                        )}
                        <div>
                          <p className="font-medium">{run.workflow_name}</p>
                          <p className="text-sm text-muted-foreground">
                            {run.trigger_type.replace(/_/g, " ")}
                          </p>
                        </div>
                      </div>
                      <div className="text-right text-sm">
                        <p className="text-muted-foreground">
                          {formatTime(run.started_at)}
                        </p>
                        <p className="text-muted-foreground">
                          Duration: {formatDuration(run.duration_ms)}
                        </p>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
