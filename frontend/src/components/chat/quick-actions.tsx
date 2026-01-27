'use client';

import { memo, useMemo } from 'react';
import {
  GitBranch,
  GitPullRequest,
  AlertTriangle,
  Rocket,
  TestTube,
  BarChart3,
  Code,
  Workflow,
  Search,
  FileText,
  Zap,
  type LucideIcon,
} from 'lucide-react';
import { cn } from '@/lib/utils';

// -----------------------------------------------------------------------------
// Types
// -----------------------------------------------------------------------------

export type QuickActionType =
  | 'connect_repo'
  | 'analyze_pr'
  | 'find_root_cause'
  | 'summarize_deploy_risk'
  | 'generate_test_plan'
  | 'analyze_dora'
  | 'review_code'
  | 'create_workflow'
  | 'search_docs'
  | 'custom';

export type QuickActionCategory = 'repo' | 'pr' | 'incident' | 'deploy' | 'analytics' | 'general';

export interface QuickAction {
  id: string;
  label: string;
  description?: string;
  icon: LucideIcon;
  action: QuickActionType;
  category: QuickActionCategory;
  prompt: string;
  requiredContext?: ('repo' | 'pr' | 'incident')[];
}

export interface QuickActionsProps {
  onAction: (action: QuickAction) => void;
  hasRepo?: boolean;
  hasPR?: boolean;
  hasIncident?: boolean;
  className?: string;
  variant?: 'chips' | 'grid' | 'compact';
  maxVisible?: number;
}

// -----------------------------------------------------------------------------
// Predefined Quick Actions
// -----------------------------------------------------------------------------

export const QUICK_ACTIONS: QuickAction[] = [
  {
    id: 'connect_repo',
    label: 'Connect repo',
    description: 'Link a GitHub, GitLab, or Bitbucket repository',
    icon: GitBranch,
    action: 'connect_repo',
    category: 'repo',
    prompt: 'I want to connect a repository. Help me set up the integration.',
  },
  {
    id: 'analyze_pr',
    label: 'Analyze PR',
    description: 'Review code changes, identify risks, and suggest improvements',
    icon: GitPullRequest,
    action: 'analyze_pr',
    category: 'pr',
    prompt: 'Analyze this pull request. Review the changes, identify potential issues, and suggest improvements.',
    requiredContext: ['repo'],
  },
  {
    id: 'find_root_cause',
    label: 'Find root cause',
    description: 'Investigate incidents and identify the underlying cause',
    icon: AlertTriangle,
    action: 'find_root_cause',
    category: 'incident',
    prompt: 'Help me find the root cause of this incident. Analyze logs, traces, and recent changes.',
    requiredContext: ['incident'],
  },
  {
    id: 'summarize_deploy_risk',
    label: 'Summarize deploy risk',
    description: 'Assess deployment risks and provide recommendations',
    icon: Rocket,
    action: 'summarize_deploy_risk',
    category: 'deploy',
    prompt: 'Analyze the deployment risk for the current changes. Consider test coverage, recent incidents, and code complexity.',
    requiredContext: ['repo'],
  },
  {
    id: 'generate_test_plan',
    label: 'Generate test plan',
    description: 'Create comprehensive test cases for your changes',
    icon: TestTube,
    action: 'generate_test_plan',
    category: 'pr',
    prompt: 'Generate a comprehensive test plan for the current changes. Include unit tests, integration tests, and edge cases.',
    requiredContext: ['pr'],
  },
  {
    id: 'analyze_dora',
    label: 'Analyze DORA metrics',
    description: 'View deployment frequency, lead time, MTTR, and change failure rate',
    icon: BarChart3,
    action: 'analyze_dora',
    category: 'analytics',
    prompt: 'Analyze the DORA metrics for this project. Show deployment frequency, lead time, MTTR, and change failure rate.',
    requiredContext: ['repo'],
  },
  {
    id: 'review_code',
    label: 'Review code',
    description: 'Get AI-powered code review with best practice suggestions',
    icon: Code,
    action: 'review_code',
    category: 'pr',
    prompt: 'Review this code and provide feedback on code quality, security, performance, and best practices.',
    requiredContext: ['pr'],
  },
  {
    id: 'create_workflow',
    label: 'Create workflow',
    description: 'Build automated CI/CD workflows',
    icon: Workflow,
    action: 'create_workflow',
    category: 'deploy',
    prompt: 'Help me create a new CI/CD workflow. What kind of workflow do you want to set up?',
    requiredContext: ['repo'],
  },
  {
    id: 'search_docs',
    label: 'Search docs',
    description: 'Search through uploaded documentation',
    icon: Search,
    action: 'search_docs',
    category: 'general',
    prompt: 'Search the documentation for relevant information about: ',
  },
];

// -----------------------------------------------------------------------------
// Quick Actions Component
// -----------------------------------------------------------------------------

export const QuickActions = memo(function QuickActions({
  onAction,
  hasRepo = false,
  hasPR = false,
  hasIncident = false,
  className,
  variant = 'chips',
  maxVisible = 6,
}: QuickActionsProps) {
  // Filter and sort actions based on available context
  const availableActions = useMemo(() => {
    // Prioritize actions based on context
    const prioritized = QUICK_ACTIONS.map(action => {
      let priority = 0;

      // Check if action has required context met
      if (action.requiredContext) {
        const contextMet = action.requiredContext.every(ctx => {
          if (ctx === 'repo') return hasRepo;
          if (ctx === 'pr') return hasPR;
          if (ctx === 'incident') return hasIncident;
          return true;
        });
        priority = contextMet ? 10 : -5;
      }

      // Boost relevant actions based on current context
      if (hasIncident && action.category === 'incident') priority += 5;
      if (hasPR && action.category === 'pr') priority += 4;
      if (hasRepo && (action.category === 'repo' || action.category === 'deploy')) priority += 3;

      // Always show general actions
      if (action.category === 'general') priority += 1;

      return { action, priority };
    });

    return prioritized
      .sort((a, b) => b.priority - a.priority)
      .slice(0, maxVisible)
      .map(p => p.action);
  }, [hasRepo, hasPR, hasIncident, maxVisible]);

  if (variant === 'compact') {
    return (
      <div className={cn('flex flex-wrap gap-1', className)}>
        {availableActions.map(action => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={() => onAction(action)}
              className={cn(
                'inline-flex items-center gap-1 px-2 py-1 rounded text-xs',
                'bg-muted hover:bg-muted/80 transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
              )}
              title={action.description}
            >
              <Icon className="h-3 w-3" aria-hidden="true" />
              {action.label}
            </button>
          );
        })}
      </div>
    );
  }

  if (variant === 'grid') {
    return (
      <div className={cn('grid grid-cols-2 sm:grid-cols-3 gap-2', className)}>
        {availableActions.map(action => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={() => onAction(action)}
              className={cn(
                'flex flex-col items-center gap-2 p-3 rounded-lg',
                'border bg-card hover:bg-accent transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1'
              )}
            >
              <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
              <span className="text-xs font-medium text-center">{action.label}</span>
            </button>
          );
        })}
      </div>
    );
  }

  // Default: chips variant
  return (
    <div className={cn('flex flex-wrap gap-2', className)}>
      {availableActions.map(action => {
        const Icon = action.icon;
        const isContextReady = !action.requiredContext || action.requiredContext.every(ctx => {
          if (ctx === 'repo') return hasRepo;
          if (ctx === 'pr') return hasPR;
          if (ctx === 'incident') return hasIncident;
          return true;
        });

        return (
          <button
            key={action.id}
            onClick={() => onAction(action)}
            disabled={!isContextReady && action.requiredContext !== undefined}
            className={cn(
              'inline-flex items-center gap-2 px-3 py-2 rounded-full',
              'border bg-card hover:bg-accent transition-colors',
              'text-sm font-medium',
              'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
              'disabled:opacity-50 disabled:cursor-not-allowed'
            )}
            title={action.description}
          >
            <Icon className="h-4 w-4" aria-hidden="true" />
            {action.label}
          </button>
        );
      })}
    </div>
  );
});

// -----------------------------------------------------------------------------
// Suggested Actions Component (for empty state)
// -----------------------------------------------------------------------------

export interface SuggestedActionsProps {
  onAction: (action: QuickAction) => void;
  className?: string;
}

export const SuggestedActions = memo(function SuggestedActions({
  onAction,
  className,
}: SuggestedActionsProps) {
  // Show a curated list of starter actions
  const starterActions = useMemo(() => [
    QUICK_ACTIONS.find(a => a.id === 'connect_repo')!,
    QUICK_ACTIONS.find(a => a.id === 'analyze_pr')!,
    QUICK_ACTIONS.find(a => a.id === 'find_root_cause')!,
    QUICK_ACTIONS.find(a => a.id === 'analyze_dora')!,
  ], []);

  return (
    <div className={cn('space-y-4', className)}>
      <h3 className="text-sm font-medium text-muted-foreground text-center">
        Try one of these to get started
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 max-w-2xl mx-auto">
        {starterActions.map(action => {
          const Icon = action.icon;
          return (
            <button
              key={action.id}
              onClick={() => onAction(action)}
              className={cn(
                'flex items-start gap-3 p-4 rounded-lg text-left',
                'border bg-card hover:bg-accent/50 transition-colors',
                'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                'group'
              )}
            >
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-primary/10 group-hover:bg-primary/20 transition-colors">
                <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
              </div>
              <div className="flex-1 min-w-0">
                <p className="font-medium">{action.label}</p>
                <p className="text-xs text-muted-foreground mt-1 line-clamp-2">
                  {action.description}
                </p>
              </div>
              <Zap className="h-4 w-4 text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
          );
        })}
      </div>
    </div>
  );
});

export default QuickActions;
