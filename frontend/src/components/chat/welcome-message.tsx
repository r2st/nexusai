'use client';

import { useMemo } from 'react';
import {
  Sparkles,
  Code2,
  BarChart3,
  MessageSquare,
  Shield,
  Zap,
  Workflow,
  Bot,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';

interface ExampleQuery {
  id: string;
  text: string;
  category: string;
  icon?: React.ReactNode;
}

interface WelcomeMessageProps {
  userName?: string;
  userRole?: 'technical' | 'non-technical' | 'admin';
  onExampleClick: (query: string) => void;
  showCapabilities?: boolean;
  className?: string;
}

/**
 * Welcome message shown when starting a new conversation.
 * 
 * Introduces the AI assistant, shows capabilities, and provides
 * example queries to help users get started.
 */
export function WelcomeMessage({
  userName,
  userRole = 'technical',
  onExampleClick,
  showCapabilities = true,
  className,
}: WelcomeMessageProps) {
  const greeting = useMemo(() => {
    const hour = new Date().getHours();
    if (hour < 12) return 'Good morning';
    if (hour < 18) return 'Good afternoon';
    return 'Good evening';
  }, []);

  const examples = useMemo(
    () => getExamplesForRole(userRole),
    [userRole]
  );

  return (
    <div className={cn('flex flex-col items-center py-8 px-4', className)}>
      {/* Avatar */}
      <div className="flex h-16 w-16 items-center justify-center rounded-full bg-primary/10 mb-4">
        <Bot className="h-8 w-8 text-primary" aria-hidden="true" />
      </div>

      {/* Greeting */}
      <h1 className="text-2xl font-semibold text-center">
        {greeting}{userName ? `, ${userName}` : ''}!
      </h1>
      <p className="mt-2 text-muted-foreground text-center max-w-md">
        I&apos;m your AI assistant. I can help you with code, analytics, DevOps metrics,
        and much more. What would you like to explore today?
      </p>

      {/* Capabilities */}
      {showCapabilities && (
        <div className="mt-8 grid grid-cols-2 md:grid-cols-4 gap-4 w-full max-w-2xl">
          {CAPABILITIES.map((capability) => (
            <CapabilityCard
              key={capability.id}
              icon={capability.icon}
              title={capability.title}
              description={capability.description}
            />
          ))}
        </div>
      )}

      {/* Example queries */}
      <div className="mt-8 w-full max-w-2xl">
        <h2 className="text-sm font-medium text-muted-foreground mb-3 flex items-center gap-2">
          <Sparkles className="h-4 w-4" aria-hidden="true" />
          Try asking
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
          {examples.map((example) => (
            <ExampleCard
              key={example.id}
              text={example.text}
              category={example.category}
              icon={example.icon}
              onClick={() => onExampleClick(example.text)}
            />
          ))}
        </div>
      </div>

      {/* Footer hint */}
      <p className="mt-8 text-xs text-muted-foreground text-center">
        Type your question below or click an example to get started.
        <br />
        Press{' '}
        <kbd className="px-1 py-0.5 rounded bg-muted text-[10px]">⌘K</kbd>{' '}
        for quick actions.
      </p>
    </div>
  );
}

/**
 * Capability card showing what the AI can do
 */
function CapabilityCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="p-4 rounded-lg border bg-card">
      <div className="flex items-center gap-2 mb-2">
        <div className="p-1.5 rounded-md bg-primary/10 text-primary">
          {icon}
        </div>
        <span className="font-medium text-sm">{title}</span>
      </div>
      <p className="text-xs text-muted-foreground">{description}</p>
    </div>
  );
}

/**
 * Example query card
 */
function ExampleCard({
  text,
  category,
  icon,
  onClick,
}: {
  text: string;
  category: string;
  icon?: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <Button
      variant="outline"
      className="h-auto p-3 justify-start text-left hover:bg-muted hover:border-primary/50 transition-colors"
      onClick={onClick}
    >
      <div className="flex items-start gap-3 w-full">
        {icon && (
          <div className="shrink-0 mt-0.5 text-muted-foreground">
            {icon}
          </div>
        )}
        <div className="flex-1 min-w-0">
          <span className="text-sm line-clamp-2">{text}</span>
          <span className="block text-xs text-muted-foreground mt-1">
            {category}
          </span>
        </div>
      </div>
    </Button>
  );
}

/**
 * AI capabilities
 */
const CAPABILITIES = [
  {
    id: 'code',
    icon: <Code2 className="h-4 w-4" aria-hidden="true" />,
    title: 'Code Help',
    description: 'Write, review, and debug code',
  },
  {
    id: 'analytics',
    icon: <BarChart3 className="h-4 w-4" aria-hidden="true" />,
    title: 'Analytics',
    description: 'Analyze data and generate insights',
  },
  {
    id: 'devops',
    icon: <Workflow className="h-4 w-4" aria-hidden="true" />,
    title: 'DevOps',
    description: 'DORA metrics and CI/CD insights',
  },
  {
    id: 'security',
    icon: <Shield className="h-4 w-4" aria-hidden="true" />,
    title: 'Security',
    description: 'Security scanning and best practices',
  },
];

/**
 * Get example queries based on user role
 */
function getExamplesForRole(role: 'technical' | 'non-technical' | 'admin'): ExampleQuery[] {
  const technical: ExampleQuery[] = [
    {
      id: 't1',
      text: 'Explain this error and how to fix it',
      category: 'Debugging',
      icon: <Code2 className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 't2',
      text: 'Show me our DORA metrics for the last sprint',
      category: 'DevOps',
      icon: <BarChart3 className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 't3',
      text: 'Write unit tests for my authentication service',
      category: 'Code',
      icon: <Zap className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 't4',
      text: 'What are the security vulnerabilities in this code?',
      category: 'Security',
      icon: <Shield className="h-4 w-4" aria-hidden="true" />,
    },
  ];

  const nonTechnical: ExampleQuery[] = [
    {
      id: 'n1',
      text: 'How is our team performing this month?',
      category: 'Analytics',
      icon: <BarChart3 className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'n2',
      text: 'Summarize the key project updates',
      category: 'Summary',
      icon: <MessageSquare className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'n3',
      text: 'What are the blockers affecting delivery?',
      category: 'Insights',
      icon: <Workflow className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'n4',
      text: 'Create a status report for stakeholders',
      category: 'Reports',
      icon: <Zap className="h-4 w-4" aria-hidden="true" />,
    },
  ];

  const admin: ExampleQuery[] = [
    {
      id: 'a1',
      text: 'Show organization usage statistics',
      category: 'Admin',
      icon: <BarChart3 className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'a2',
      text: 'List all active integrations and their status',
      category: 'Integrations',
      icon: <Workflow className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'a3',
      text: 'Review security audit logs',
      category: 'Security',
      icon: <Shield className="h-4 w-4" aria-hidden="true" />,
    },
    {
      id: 'a4',
      text: 'Generate team productivity report',
      category: 'Reports',
      icon: <Zap className="h-4 w-4" aria-hidden="true" />,
    },
  ];

  switch (role) {
    case 'non-technical':
      return nonTechnical;
    case 'admin':
      return admin;
    default:
      return technical;
  }
}

export default WelcomeMessage;
