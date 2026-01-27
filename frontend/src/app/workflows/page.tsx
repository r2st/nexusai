"use client";

import React, { useState } from "react";
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
} from "lucide-react";

// Mock data for existing workflows
const MOCK_WORKFLOWS = [
  {
    id: "wf-1",
    name: "PR Quality Gate",
    description: "Run quality checks on every PR",
    enabled: true,
    trigger: "pr_opened",
    lastRun: "2 hours ago",
    runCount: 145,
    successRate: 94,
    status: "active",
  },
  {
    id: "wf-2",
    name: "Security Alert Handler",
    description: "Create tickets for critical vulnerabilities",
    enabled: true,
    trigger: "security_alert",
    lastRun: "1 day ago",
    runCount: 23,
    successRate: 100,
    status: "active",
  },
  {
    id: "wf-3",
    name: "Weekly Report",
    description: "Generate and send weekly engineering report",
    enabled: false,
    trigger: "schedule",
    lastRun: "5 days ago",
    runCount: 12,
    successRate: 83,
    status: "paused",
  },
  {
    id: "wf-4",
    name: "Deploy Tracker",
    description: "Track deployments and notify team",
    enabled: true,
    trigger: "webhook",
    lastRun: "30 min ago",
    runCount: 89,
    successRate: 98,
    status: "active",
  },
];

export default function WorkflowsPage() {
  const [searchQuery, setSearchQuery] = useState("");
  const [activeTab, setActiveTab] = useState("my-workflows");
  const [showDesigner, setShowDesigner] = useState(false);
  const [selectedWorkflow, setSelectedWorkflow] = useState<any>(null);

  const filteredWorkflows = MOCK_WORKFLOWS.filter(
    (w) =>
      w.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      w.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const handleCreateFromTemplate = (template: WorkflowTemplate) => {
    // Create new workflow from template
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

  const handleSaveWorkflow = (workflow: any) => {
    console.log("Saving workflow:", workflow);
    setShowDesigner(false);
    // API call to save workflow
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
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground" />
              <Input
                placeholder="Search workflows..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-9"
              />
            </div>
          )}
        </div>

        <TabsContent value="my-workflows">
          {filteredWorkflows.length === 0 ? (
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
                          <Button variant="ghost" size="icon">
                            <MoreVertical className="h-4 w-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEditWorkflow(workflow)}>
                            <Edit className="h-4 w-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem>
                            <Copy className="h-4 w-4 mr-2" />
                            Duplicate
                          </DropdownMenuItem>
                          <DropdownMenuItem>
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
                          <DropdownMenuItem>
                            <History className="h-4 w-4 mr-2" />
                            View History
                          </DropdownMenuItem>
                          <DropdownMenuSeparator />
                          <DropdownMenuItem className="text-destructive">
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
                      <div className="flex items-center gap-1.5">
                        <Play className="h-4 w-4" />
                        <span>{workflow.runCount} runs</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle className="h-4 w-4 text-green-500" />
                        <span>{workflow.successRate}% success</span>
                      </div>
                      <div className="flex items-center gap-1.5">
                        <span>Last run: {workflow.lastRun}</span>
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
              <div className="space-y-4">
                {[
                  {
                    workflow: "PR Quality Gate",
                    status: "success",
                    duration: "2.3s",
                    time: "2 hours ago",
                    trigger: "PR #142 opened",
                  },
                  {
                    workflow: "Deploy Tracker",
                    status: "success",
                    duration: "1.1s",
                    time: "30 min ago",
                    trigger: "Webhook from CI",
                  },
                  {
                    workflow: "PR Quality Gate",
                    status: "failed",
                    duration: "5.2s",
                    time: "3 hours ago",
                    trigger: "PR #141 opened",
                  },
                  {
                    workflow: "Security Alert Handler",
                    status: "success",
                    duration: "3.8s",
                    time: "1 day ago",
                    trigger: "Security alert detected",
                  },
                  {
                    workflow: "Weekly Report",
                    status: "success",
                    duration: "12.4s",
                    time: "5 days ago",
                    trigger: "Scheduled (Monday 9am)",
                  },
                ].map((run, index) => (
                  <div
                    key={index}
                    className="flex items-center justify-between py-3 border-b last:border-0"
                  >
                    <div className="flex items-center gap-3">
                      {run.status === "success" ? (
                        <CheckCircle className="h-5 w-5 text-green-500" />
                      ) : (
                        <XCircle className="h-5 w-5 text-red-500" />
                      )}
                      <div>
                        <p className="font-medium">{run.workflow}</p>
                        <p className="text-sm text-muted-foreground">
                          {run.trigger}
                        </p>
                      </div>
                    </div>
                    <div className="text-right text-sm">
                      <p className="text-muted-foreground">{run.time}</p>
                      <p className="text-muted-foreground">
                        Duration: {run.duration}
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}
