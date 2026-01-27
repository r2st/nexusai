"use client";

import React from "react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  GitBranch,
  Shield,
  Rocket,
  FileText,
  AlertTriangle,
  Clock,
  Users,
  Zap,
} from "lucide-react";

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon: React.ElementType;
  trigger: {
    type: string;
    config: Record<string, any>;
  };
  nodes: Array<{
    type: string;
    name: string;
    config: Record<string, any>;
  }>;
  popularity: number;
}

export const WORKFLOW_TEMPLATES: WorkflowTemplate[] = [
  {
    id: "pr-quality-check",
    name: "PR Quality Check",
    description:
      "Automatically run code analysis and post review comments when a PR is opened",
    category: "Code Review",
    icon: GitBranch,
    trigger: { type: "pr_opened", config: {} },
    nodes: [
      {
        type: "action",
        name: "Run Code Analysis",
        config: { actionType: "run_analysis" },
      },
      {
        type: "condition",
        name: "Check Quality Score",
        config: { expression: "analysis.score >= 80" },
      },
      {
        type: "notification",
        name: "Notify on Failure",
        config: { channel: "slack", message: "PR {{pr.number}} needs attention" },
      },
    ],
    popularity: 95,
  },
  {
    id: "security-alert-response",
    name: "Security Alert Response",
    description:
      "Create tickets and notify security team when vulnerabilities are detected",
    category: "Security",
    icon: Shield,
    trigger: { type: "security_alert", config: {} },
    nodes: [
      {
        type: "condition",
        name: "Check Severity",
        config: { expression: "alert.severity === 'critical'" },
      },
      {
        type: "action",
        name: "Create Jira Ticket",
        config: { actionType: "create_issue" },
      },
      {
        type: "notification",
        name: "Alert Security Team",
        config: { channel: "slack", message: "🚨 Critical vulnerability: {{alert.title}}" },
      },
      {
        type: "approval",
        name: "Security Review",
        config: { approvers: "security-team@company.com", timeout: 24 },
      },
    ],
    popularity: 88,
  },
  {
    id: "deployment-tracking",
    name: "Deployment Tracking",
    description:
      "Track deployments and update DORA metrics when code is deployed",
    category: "DevOps",
    icon: Rocket,
    trigger: { type: "webhook", config: { source: "ci" } },
    nodes: [
      {
        type: "action",
        name: "Record Deployment",
        config: { actionType: "update_status" },
      },
      {
        type: "action",
        name: "Calculate Lead Time",
        config: { actionType: "run_analysis" },
      },
      {
        type: "notification",
        name: "Announce Deployment",
        config: { channel: "slack", message: "🚀 {{service}} deployed to {{environment}}" },
      },
    ],
    popularity: 82,
  },
  {
    id: "weekly-report",
    name: "Weekly Engineering Report",
    description:
      "Generate and distribute weekly engineering metrics report",
    category: "Reporting",
    icon: FileText,
    trigger: { type: "schedule", config: { cron: "0 9 * * 1" } },
    nodes: [
      {
        type: "action",
        name: "Gather Metrics",
        config: { actionType: "run_analysis" },
      },
      {
        type: "transform",
        name: "Generate Report",
        config: { template: "weekly_report" },
      },
      {
        type: "notification",
        name: "Send to Team",
        config: { channel: "email", message: "Weekly Engineering Report - {{week}}" },
      },
    ],
    popularity: 75,
  },
  {
    id: "incident-response",
    name: "Incident Response",
    description:
      "Coordinate incident response with automated notifications and tracking",
    category: "Operations",
    icon: AlertTriangle,
    trigger: { type: "webhook", config: { source: "pagerduty" } },
    nodes: [
      {
        type: "notification",
        name: "Alert On-Call",
        config: { channel: "slack", message: "🔥 Incident: {{incident.title}}" },
      },
      {
        type: "action",
        name: "Create War Room",
        config: { actionType: "api_call" },
      },
      {
        type: "delay",
        name: "Wait for Resolution",
        config: { duration: 30, unit: "minutes" },
      },
      {
        type: "action",
        name: "Generate Postmortem",
        config: { actionType: "run_analysis" },
      },
    ],
    popularity: 70,
  },
  {
    id: "standup-reminder",
    name: "Daily Standup Reminder",
    description: "Send daily standup reminders with yesterday's metrics",
    category: "Team",
    icon: Users,
    trigger: { type: "schedule", config: { cron: "0 9 * * 1-5" } },
    nodes: [
      {
        type: "action",
        name: "Gather Yesterday's Stats",
        config: { actionType: "run_analysis" },
      },
      {
        type: "notification",
        name: "Post to Slack",
        config: {
          channel: "slack",
          message: "Good morning! Here's what happened yesterday...",
        },
      },
    ],
    popularity: 65,
  },
  {
    id: "auto-assign-reviewer",
    name: "Auto-Assign Reviewers",
    description:
      "Automatically assign code reviewers based on file ownership",
    category: "Code Review",
    icon: Users,
    trigger: { type: "pr_opened", config: {} },
    nodes: [
      {
        type: "action",
        name: "Analyze Changed Files",
        config: { actionType: "run_analysis" },
      },
      {
        type: "action",
        name: "Assign Reviewers",
        config: { actionType: "assign_reviewer" },
      },
      {
        type: "notification",
        name: "Notify Reviewers",
        config: { channel: "slack", message: "You've been assigned to review {{pr.title}}" },
      },
    ],
    popularity: 78,
  },
  {
    id: "stale-pr-reminder",
    name: "Stale PR Reminder",
    description: "Remind developers about PRs that haven't been updated",
    category: "Code Review",
    icon: Clock,
    trigger: { type: "schedule", config: { cron: "0 10 * * 1-5" } },
    nodes: [
      {
        type: "action",
        name: "Find Stale PRs",
        config: { actionType: "api_call" },
      },
      {
        type: "condition",
        name: "Has Stale PRs",
        config: { expression: "stalePRs.length > 0" },
      },
      {
        type: "notification",
        name: "Send Reminders",
        config: {
          channel: "slack",
          message: "You have {{stalePRs.length}} PRs waiting for attention",
        },
      },
    ],
    popularity: 72,
  },
];

interface WorkflowTemplatesProps {
  onSelect: (template: WorkflowTemplate) => void;
}

export function WorkflowTemplates({ onSelect }: WorkflowTemplatesProps) {
  const categories = Array.from(
    new Set(WORKFLOW_TEMPLATES.map((t) => t.category))
  );

  return (
    <div className="space-y-8">
      {categories.map((category) => (
        <div key={category}>
          <h3 className="text-lg font-semibold mb-4">{category}</h3>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {WORKFLOW_TEMPLATES.filter((t) => t.category === category).map(
              (template) => {
                const Icon = template.icon;
                return (
                  <Card
                    key={template.id}
                    className="cursor-pointer hover:border-primary transition-colors"
                    onClick={() => onSelect(template)}
                  >
                    <CardHeader className="pb-3">
                      <div className="flex items-start justify-between">
                        <div className="p-2 rounded-lg bg-primary/10">
                          <Icon className="h-5 w-5 text-primary" />
                        </div>
                        <Badge variant="secondary">
                          {template.popularity}% popular
                        </Badge>
                      </div>
                      <CardTitle className="text-base mt-3">
                        {template.name}
                      </CardTitle>
                      <CardDescription className="text-sm">
                        {template.description}
                      </CardDescription>
                    </CardHeader>
                    <CardContent>
                      <div className="flex items-center gap-2 text-xs text-muted-foreground">
                        <Zap className="h-3 w-3" />
                        <span>{template.nodes.length} steps</span>
                        <span className="mx-1">•</span>
                        <span>
                          Trigger:{" "}
                          {template.trigger.type.replace(/_/g, " ")}
                        </span>
                      </div>
                      <Button className="w-full mt-4" variant="outline" size="sm">
                        Use Template
                      </Button>
                    </CardContent>
                  </Card>
                );
              }
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

export default WorkflowTemplates;
