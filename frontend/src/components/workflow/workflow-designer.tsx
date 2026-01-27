"use client";

import React, { useState, useCallback, useRef, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { Textarea } from "@/components/ui/textarea";
import { Switch } from "@/components/ui/switch";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Play,
  Pause,
  Save,
  Trash2,
  Plus,
  Settings,
  GitBranch,
  Zap,
  Mail,
  MessageSquare,
  Webhook,
  Clock,
  Shield,
  AlertTriangle,
  CheckCircle,
  XCircle,
  ArrowRight,
  GripVertical,
  Copy,
  MoreVertical,
  Undo,
  Redo,
  Download,
  Upload,
  Eye,
} from "lucide-react";

// Types
interface WorkflowNode {
  id: string;
  type: NodeType;
  name: string;
  config: Record<string, any>;
  position: { x: number; y: number };
  connections: string[];
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
  condition?: string;
}

interface Workflow {
  id: string;
  name: string;
  description: string;
  enabled: boolean;
  trigger: TriggerConfig;
  nodes: WorkflowNode[];
  edges: WorkflowEdge[];
  createdAt: string;
  updatedAt: string;
}

interface TriggerConfig {
  type: TriggerType;
  config: Record<string, any>;
}

type NodeType =
  | "action"
  | "condition"
  | "notification"
  | "webhook"
  | "delay"
  | "approval"
  | "transform";

type TriggerType =
  | "pr_opened"
  | "pr_merged"
  | "commit_pushed"
  | "quality_gate"
  | "security_alert"
  | "schedule"
  | "webhook"
  | "manual";

// Node type definitions
const NODE_TYPES: Record<
  NodeType,
  { label: string; icon: React.ElementType; color: string }
> = {
  action: { label: "Action", icon: Zap, color: "bg-blue-500" },
  condition: { label: "Condition", icon: GitBranch, color: "bg-yellow-500" },
  notification: { label: "Notification", icon: Mail, color: "bg-green-500" },
  webhook: { label: "Webhook", icon: Webhook, color: "bg-purple-500" },
  delay: { label: "Delay", icon: Clock, color: "bg-orange-500" },
  approval: { label: "Approval", icon: Shield, color: "bg-red-500" },
  transform: { label: "Transform", icon: Settings, color: "bg-gray-500" },
};

const TRIGGER_TYPES: Record<TriggerType, { label: string; icon: React.ElementType }> = {
  pr_opened: { label: "PR Opened", icon: GitBranch },
  pr_merged: { label: "PR Merged", icon: CheckCircle },
  commit_pushed: { label: "Commit Pushed", icon: ArrowRight },
  quality_gate: { label: "Quality Gate", icon: Shield },
  security_alert: { label: "Security Alert", icon: AlertTriangle },
  schedule: { label: "Schedule (Cron)", icon: Clock },
  webhook: { label: "Webhook", icon: Webhook },
  manual: { label: "Manual Trigger", icon: Play },
};

// Node Palette Component
function NodePalette({
  onDragStart,
}: {
  onDragStart: (type: NodeType) => void;
}) {
  return (
    <div className="w-64 border-r bg-muted/30 p-4">
      <h3 className="font-semibold mb-4">Nodes</h3>
      <div className="space-y-2">
        {Object.entries(NODE_TYPES).map(([type, config]) => {
          const Icon = config.icon;
          return (
            <div
              key={type}
              draggable
              onDragStart={() => onDragStart(type as NodeType)}
              className="flex items-center gap-3 p-3 bg-background rounded-lg border cursor-grab hover:border-primary transition-colors"
            >
              <div className={`p-2 rounded ${config.color}`}>
                <Icon className="h-4 w-4 text-white" />
              </div>
              <span className="text-sm font-medium">{config.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}

// Canvas Node Component
function CanvasNode({
  node,
  selected,
  onSelect,
  onDelete,
  onEdit,
  onConnect,
}: {
  node: WorkflowNode;
  selected: boolean;
  onSelect: () => void;
  onDelete: () => void;
  onEdit: () => void;
  onConnect: () => void;
}) {
  const nodeConfig = NODE_TYPES[node.type];
  const Icon = nodeConfig.icon;

  return (
    <div
      className={`absolute p-4 bg-background rounded-lg border-2 shadow-lg cursor-pointer transition-all min-w-[180px] ${
        selected ? "border-primary ring-2 ring-primary/20" : "border-border"
      }`}
      style={{ left: node.position.x, top: node.position.y }}
      onClick={onSelect}
    >
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <GripVertical className="h-4 w-4 text-muted-foreground cursor-grab" />
          <div className={`p-1.5 rounded ${nodeConfig.color}`}>
            <Icon className="h-3.5 w-3.5 text-white" />
          </div>
        </div>
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <Button variant="ghost" size="icon" className="h-6 w-6">
              <MoreVertical className="h-4 w-4" />
            </Button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end">
            <DropdownMenuItem onClick={onEdit}>
              <Settings className="h-4 w-4 mr-2" />
              Configure
            </DropdownMenuItem>
            <DropdownMenuItem onClick={onConnect}>
              <ArrowRight className="h-4 w-4 mr-2" />
              Connect
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={onDelete} className="text-destructive">
              <Trash2 className="h-4 w-4 mr-2" />
              Delete
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
      <p className="text-sm font-medium truncate">{node.name}</p>
      <p className="text-xs text-muted-foreground">{nodeConfig.label}</p>
      
      {/* Connection points */}
      <div className="absolute -right-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-primary rounded-full border-2 border-background cursor-crosshair" />
      <div className="absolute -left-2 top-1/2 -translate-y-1/2 w-4 h-4 bg-muted rounded-full border-2 border-background" />
    </div>
  );
}

// Trigger Configuration Component
function TriggerConfig({
  trigger,
  onChange,
}: {
  trigger: TriggerConfig;
  onChange: (trigger: TriggerConfig) => void;
}) {
  const TriggerIcon = TRIGGER_TYPES[trigger.type]?.icon || Zap;

  return (
    <div className="p-4 border rounded-lg bg-muted/30">
      <div className="flex items-center gap-2 mb-4">
        <TriggerIcon className="h-5 w-5" />
        <h4 className="font-medium">Trigger</h4>
      </div>
      
      <div className="space-y-4">
        <div>
          <Label>Trigger Type</Label>
          <Select
            value={trigger.type}
            onValueChange={(value) =>
              onChange({ ...trigger, type: value as TriggerType })
            }
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {Object.entries(TRIGGER_TYPES).map(([type, config]) => {
                const Icon = config.icon;
                return (
                  <SelectItem key={type} value={type}>
                    <div className="flex items-center gap-2">
                      <Icon className="h-4 w-4" />
                      {config.label}
                    </div>
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </div>

        {trigger.type === "schedule" && (
          <div>
            <Label>Cron Expression</Label>
            <Input
              placeholder="0 9 * * 1-5"
              value={trigger.config.cron || ""}
              onChange={(e) =>
                onChange({
                  ...trigger,
                  config: { ...trigger.config, cron: e.target.value },
                })
              }
            />
            <p className="text-xs text-muted-foreground mt-1">
              Example: 0 9 * * 1-5 (weekdays at 9am)
            </p>
          </div>
        )}

        {trigger.type === "webhook" && (
          <div>
            <Label>Webhook URL</Label>
            <div className="flex gap-2">
              <Input
                readOnly
                value={`https://api.nexusai.dev/webhooks/${trigger.config.id || "..."}`}
              />
              <Button variant="outline" size="icon">
                <Copy className="h-4 w-4" />
              </Button>
            </div>
          </div>
        )}

        {(trigger.type === "pr_opened" || trigger.type === "pr_merged") && (
          <div>
            <Label>Repository Filter (optional)</Label>
            <Input
              placeholder="owner/repo or leave empty for all"
              value={trigger.config.repository || ""}
              onChange={(e) =>
                onChange({
                  ...trigger,
                  config: { ...trigger.config, repository: e.target.value },
                })
              }
            />
          </div>
        )}
      </div>
    </div>
  );
}

// Node Configuration Dialog
function NodeConfigDialog({
  node,
  open,
  onClose,
  onSave,
}: {
  node: WorkflowNode | null;
  open: boolean;
  onClose: () => void;
  onSave: (node: WorkflowNode) => void;
}) {
  const [editedNode, setEditedNode] = useState<WorkflowNode | null>(node);

  useEffect(() => {
    setEditedNode(node);
  }, [node]);

  if (!editedNode) return null;

  const handleSave = () => {
    if (editedNode) {
      onSave(editedNode);
      onClose();
    }
  };

  return (
    <Dialog open={open} onOpenChange={onClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Configure {NODE_TYPES[editedNode.type].label}</DialogTitle>
          <DialogDescription>
            Set up the configuration for this workflow step.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4 py-4">
          <div>
            <Label>Name</Label>
            <Input
              value={editedNode.name}
              onChange={(e) =>
                setEditedNode({ ...editedNode, name: e.target.value })
              }
            />
          </div>

          {editedNode.type === "notification" && (
            <>
              <div>
                <Label>Channel</Label>
                <Select
                  value={editedNode.config.channel || "slack"}
                  onValueChange={(value) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, channel: value },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="slack">Slack</SelectItem>
                    <SelectItem value="teams">Microsoft Teams</SelectItem>
                    <SelectItem value="email">Email</SelectItem>
                    <SelectItem value="discord">Discord</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label>Message Template</Label>
                <Textarea
                  placeholder="Use {{variables}} for dynamic content"
                  value={editedNode.config.message || ""}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, message: e.target.value },
                    })
                  }
                />
              </div>
            </>
          )}

          {editedNode.type === "condition" && (
            <>
              <div>
                <Label>Condition Expression</Label>
                <Textarea
                  placeholder="e.g., data.score > 80"
                  value={editedNode.config.expression || ""}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, expression: e.target.value },
                    })
                  }
                />
              </div>
            </>
          )}

          {editedNode.type === "webhook" && (
            <>
              <div>
                <Label>URL</Label>
                <Input
                  placeholder="https://api.example.com/webhook"
                  value={editedNode.config.url || ""}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, url: e.target.value },
                    })
                  }
                />
              </div>
              <div>
                <Label>Method</Label>
                <Select
                  value={editedNode.config.method || "POST"}
                  onValueChange={(value) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, method: value },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="GET">GET</SelectItem>
                    <SelectItem value="POST">POST</SelectItem>
                    <SelectItem value="PUT">PUT</SelectItem>
                    <SelectItem value="PATCH">PATCH</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {editedNode.type === "delay" && (
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label>Duration</Label>
                <Input
                  type="number"
                  min="1"
                  value={editedNode.config.duration || 5}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: {
                        ...editedNode.config,
                        duration: parseInt(e.target.value),
                      },
                    })
                  }
                />
              </div>
              <div>
                <Label>Unit</Label>
                <Select
                  value={editedNode.config.unit || "minutes"}
                  onValueChange={(value) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, unit: value },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="seconds">Seconds</SelectItem>
                    <SelectItem value="minutes">Minutes</SelectItem>
                    <SelectItem value="hours">Hours</SelectItem>
                    <SelectItem value="days">Days</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </div>
          )}

          {editedNode.type === "approval" && (
            <>
              <div>
                <Label>Approvers</Label>
                <Input
                  placeholder="user@example.com, team@example.com"
                  value={editedNode.config.approvers || ""}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, approvers: e.target.value },
                    })
                  }
                />
              </div>
              <div>
                <Label>Timeout (hours)</Label>
                <Input
                  type="number"
                  min="1"
                  value={editedNode.config.timeout || 24}
                  onChange={(e) =>
                    setEditedNode({
                      ...editedNode,
                      config: {
                        ...editedNode.config,
                        timeout: parseInt(e.target.value),
                      },
                    })
                  }
                />
              </div>
            </>
          )}

          {editedNode.type === "action" && (
            <>
              <div>
                <Label>Action Type</Label>
                <Select
                  value={editedNode.config.actionType || "api_call"}
                  onValueChange={(value) =>
                    setEditedNode({
                      ...editedNode,
                      config: { ...editedNode.config, actionType: value },
                    })
                  }
                >
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="api_call">API Call</SelectItem>
                    <SelectItem value="create_issue">Create Issue</SelectItem>
                    <SelectItem value="run_analysis">Run Analysis</SelectItem>
                    <SelectItem value="update_status">Update Status</SelectItem>
                    <SelectItem value="assign_reviewer">Assign Reviewer</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancel
          </Button>
          <Button onClick={handleSave}>Save Changes</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

// Main Workflow Designer Component
export function WorkflowDesigner({
  workflow: initialWorkflow,
  onSave,
}: {
  workflow?: Workflow;
  onSave?: (workflow: Workflow) => void;
}) {
  const canvasRef = useRef<HTMLDivElement>(null);
  const [workflow, setWorkflow] = useState<Workflow>(
    initialWorkflow || {
      id: crypto.randomUUID(),
      name: "New Workflow",
      description: "",
      enabled: false,
      trigger: { type: "manual", config: {} },
      nodes: [],
      edges: [],
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    }
  );
  const [selectedNode, setSelectedNode] = useState<string | null>(null);
  const [editingNode, setEditingNode] = useState<WorkflowNode | null>(null);
  const [draggedType, setDraggedType] = useState<NodeType | null>(null);
  const [history, setHistory] = useState<Workflow[]>([]);
  const [historyIndex, setHistoryIndex] = useState(-1);

  // Save to history
  const saveToHistory = useCallback((newWorkflow: Workflow) => {
    setHistory((prev) => [...prev.slice(0, historyIndex + 1), newWorkflow]);
    setHistoryIndex((prev) => prev + 1);
  }, [historyIndex]);

  // Undo/Redo
  const undo = useCallback(() => {
    if (historyIndex > 0) {
      setHistoryIndex((prev) => prev - 1);
      setWorkflow(history[historyIndex - 1]);
    }
  }, [history, historyIndex]);

  const redo = useCallback(() => {
    if (historyIndex < history.length - 1) {
      setHistoryIndex((prev) => prev + 1);
      setWorkflow(history[historyIndex + 1]);
    }
  }, [history, historyIndex]);

  // Handle drop on canvas
  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      if (!draggedType || !canvasRef.current) return;

      const rect = canvasRef.current.getBoundingClientRect();
      const x = e.clientX - rect.left - 90;
      const y = e.clientY - rect.top - 40;

      const newNode: WorkflowNode = {
        id: crypto.randomUUID(),
        type: draggedType,
        name: `${NODE_TYPES[draggedType].label} ${workflow.nodes.length + 1}`,
        config: {},
        position: { x: Math.max(0, x), y: Math.max(0, y) },
        connections: [],
      };

      const newWorkflow = {
        ...workflow,
        nodes: [...workflow.nodes, newNode],
        updatedAt: new Date().toISOString(),
      };
      setWorkflow(newWorkflow);
      saveToHistory(newWorkflow);
      setDraggedType(null);
    },
    [draggedType, workflow, saveToHistory]
  );

  // Delete node
  const deleteNode = useCallback(
    (nodeId: string) => {
      const newWorkflow = {
        ...workflow,
        nodes: workflow.nodes.filter((n) => n.id !== nodeId),
        edges: workflow.edges.filter(
          (e) => e.source !== nodeId && e.target !== nodeId
        ),
        updatedAt: new Date().toISOString(),
      };
      setWorkflow(newWorkflow);
      saveToHistory(newWorkflow);
      setSelectedNode(null);
    },
    [workflow, saveToHistory]
  );

  // Update node
  const updateNode = useCallback(
    (updatedNode: WorkflowNode) => {
      const newWorkflow = {
        ...workflow,
        nodes: workflow.nodes.map((n) =>
          n.id === updatedNode.id ? updatedNode : n
        ),
        updatedAt: new Date().toISOString(),
      };
      setWorkflow(newWorkflow);
      saveToHistory(newWorkflow);
    },
    [workflow, saveToHistory]
  );

  // Save workflow
  const handleSave = useCallback(() => {
    onSave?.(workflow);
  }, [workflow, onSave]);

  // Export workflow
  const exportWorkflow = useCallback(() => {
    const data = JSON.stringify(workflow, null, 2);
    const blob = new Blob([data], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${workflow.name.toLowerCase().replace(/\s+/g, "-")}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [workflow]);

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="border-b p-3 flex items-center justify-between bg-background">
        <div className="flex items-center gap-4">
          <Input
            className="w-64 font-medium"
            value={workflow.name}
            onChange={(e) =>
              setWorkflow({ ...workflow, name: e.target.value })
            }
          />
          <div className="flex items-center gap-2">
            <Switch
              checked={workflow.enabled}
              onCheckedChange={(checked) =>
                setWorkflow({ ...workflow, enabled: checked })
              }
            />
            <Label className="text-sm">
              {workflow.enabled ? "Enabled" : "Disabled"}
            </Label>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={undo} disabled={historyIndex <= 0}>
            <Undo className="h-4 w-4" />
          </Button>
          <Button
            variant="outline"
            size="icon"
            onClick={redo}
            disabled={historyIndex >= history.length - 1}
          >
            <Redo className="h-4 w-4" />
          </Button>
          <div className="w-px h-6 bg-border mx-2" />
          <Button variant="outline" size="sm" onClick={exportWorkflow}>
            <Download className="h-4 w-4 mr-2" />
            Export
          </Button>
          <Button variant="outline" size="sm">
            <Eye className="h-4 w-4 mr-2" />
            Preview
          </Button>
          <Button size="sm" onClick={handleSave}>
            <Save className="h-4 w-4 mr-2" />
            Save
          </Button>
        </div>
      </div>

      {/* Main content */}
      <div className="flex-1 flex overflow-hidden">
        {/* Node Palette */}
        <NodePalette onDragStart={setDraggedType} />

        {/* Canvas */}
        <div className="flex-1 flex flex-col">
          {/* Trigger config */}
          <div className="p-4 border-b bg-muted/20">
            <TriggerConfig
              trigger={workflow.trigger}
              onChange={(trigger) => setWorkflow({ ...workflow, trigger })}
            />
          </div>

          {/* Canvas area */}
          <div
            ref={canvasRef}
            className="flex-1 relative bg-[url('/grid.svg')] bg-repeat overflow-auto"
            onDragOver={(e) => e.preventDefault()}
            onDrop={handleDrop}
          >
            {workflow.nodes.length === 0 && (
              <div className="absolute inset-0 flex items-center justify-center text-muted-foreground">
                <div className="text-center">
                  <Plus className="h-12 w-12 mx-auto mb-4 opacity-50" />
                  <p className="text-lg font-medium">Drag nodes here to build your workflow</p>
                  <p className="text-sm">Or use the templates to get started</p>
                </div>
              </div>
            )}

            {/* Render edges (connections) */}
            <svg className="absolute inset-0 pointer-events-none">
              {workflow.edges.map((edge) => {
                const sourceNode = workflow.nodes.find((n) => n.id === edge.source);
                const targetNode = workflow.nodes.find((n) => n.id === edge.target);
                if (!sourceNode || !targetNode) return null;

                const x1 = sourceNode.position.x + 180;
                const y1 = sourceNode.position.y + 40;
                const x2 = targetNode.position.x;
                const y2 = targetNode.position.y + 40;

                return (
                  <g key={edge.id}>
                    <path
                      d={`M ${x1} ${y1} C ${x1 + 50} ${y1}, ${x2 - 50} ${y2}, ${x2} ${y2}`}
                      fill="none"
                      stroke="hsl(var(--primary))"
                      strokeWidth="2"
                    />
                    <circle cx={x2} cy={y2} r="4" fill="hsl(var(--primary))" />
                  </g>
                );
              })}
            </svg>

            {/* Render nodes */}
            {workflow.nodes.map((node) => (
              <CanvasNode
                key={node.id}
                node={node}
                selected={selectedNode === node.id}
                onSelect={() => setSelectedNode(node.id)}
                onDelete={() => deleteNode(node.id)}
                onEdit={() => setEditingNode(node)}
                onConnect={() => {
                  // Handle connection creation
                }}
              />
            ))}
          </div>
        </div>

        {/* Properties Panel */}
        {selectedNode && (
          <div className="w-72 border-l bg-muted/30 p-4">
            <h3 className="font-semibold mb-4">Properties</h3>
            {(() => {
              const node = workflow.nodes.find((n) => n.id === selectedNode);
              if (!node) return null;
              const nodeConfig = NODE_TYPES[node.type];
              const Icon = nodeConfig.icon;

              return (
                <div className="space-y-4">
                  <div className="flex items-center gap-3">
                    <div className={`p-2 rounded ${nodeConfig.color}`}>
                      <Icon className="h-4 w-4 text-white" />
                    </div>
                    <div>
                      <p className="font-medium">{node.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {nodeConfig.label}
                      </p>
                    </div>
                  </div>

                  <Button
                    className="w-full"
                    variant="outline"
                    onClick={() => setEditingNode(node)}
                  >
                    <Settings className="h-4 w-4 mr-2" />
                    Configure
                  </Button>

                  <Button
                    className="w-full"
                    variant="destructive"
                    onClick={() => deleteNode(node.id)}
                  >
                    <Trash2 className="h-4 w-4 mr-2" />
                    Delete
                  </Button>
                </div>
              );
            })()}
          </div>
        )}
      </div>

      {/* Node Configuration Dialog */}
      <NodeConfigDialog
        node={editingNode}
        open={!!editingNode}
        onClose={() => setEditingNode(null)}
        onSave={updateNode}
      />
    </div>
  );
}

export default WorkflowDesigner;
