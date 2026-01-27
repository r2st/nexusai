'use client';

import dynamic from 'next/dynamic';
import { ComponentType } from 'react';

// -----------------------------------------------------------------------------
// Lazy Load Configuration
// -----------------------------------------------------------------------------

interface LazyLoadOptions {
  ssr?: boolean;
  loading?: ComponentType;
}

// Default skeleton loader
export function DefaultSkeleton() {
  return (
    <div className="animate-pulse">
      <div className="h-8 w-full bg-muted rounded mb-4" />
      <div className="space-y-2">
        <div className="h-4 w-3/4 bg-muted rounded" />
        <div className="h-4 w-1/2 bg-muted rounded" />
      </div>
    </div>
  );
}

// Chat skeleton
export function ChatSkeleton() {
  return (
    <div className="flex h-screen">
      {/* Sidebar skeleton */}
      <div className="w-64 border-r bg-muted/30 animate-pulse">
        <div className="h-14 border-b px-4 flex items-center">
          <div className="h-4 w-24 bg-muted rounded" />
        </div>
        <div className="p-2 space-y-2">
          {[1, 2, 3, 4, 5].map((i) => (
            <div key={i} className="h-10 bg-muted rounded" />
          ))}
        </div>
      </div>
      {/* Main content skeleton */}
      <div className="flex-1 flex flex-col">
        <div className="flex-1 p-4 space-y-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="flex gap-4">
              <div className="h-8 w-8 rounded-full bg-muted" />
              <div className="flex-1 space-y-2">
                <div className="h-4 w-1/4 bg-muted rounded" />
                <div className="h-4 w-3/4 bg-muted rounded" />
              </div>
            </div>
          ))}
        </div>
        <div className="border-t p-4">
          <div className="h-12 bg-muted rounded" />
        </div>
      </div>
    </div>
  );
}

// Context panel skeleton
export function ContextPanelSkeleton() {
  return (
    <div className="w-80 border-l bg-muted/30 p-4 animate-pulse">
      <div className="h-6 w-20 bg-muted rounded mb-4" />
      {[1, 2, 3].map((i) => (
        <div key={i} className="rounded-lg border p-3 mb-3">
          <div className="h-4 w-24 bg-muted rounded mb-2" />
          <div className="h-3 w-full bg-muted rounded" />
        </div>
      ))}
    </div>
  );
}

// Analytics skeleton
export function AnalyticsSkeleton() {
  return (
    <div className="p-6 space-y-6 animate-pulse">
      <div className="h-8 w-48 bg-muted rounded" />
      <div className="grid grid-cols-4 gap-4">
        {[1, 2, 3, 4].map((i) => (
          <div key={i} className="h-32 bg-muted rounded" />
        ))}
      </div>
      <div className="h-64 bg-muted rounded" />
    </div>
  );
}

// -----------------------------------------------------------------------------
// Lazy Loaded Components
// -----------------------------------------------------------------------------

// Heavy chat components
export const LazyContextPanel = dynamic(
  () => import('@/components/chat/context-panel').then(mod => ({ default: mod.ContextPanel })),
  {
    ssr: false,
    loading: () => <ContextPanelSkeleton />,
  }
);

export const LazyQuickActions = dynamic(
  () => import('@/components/chat/quick-actions').then(mod => ({ default: mod.QuickActions })),
  {
    ssr: false,
  }
);

export const LazySuggestedActions = dynamic(
  () => import('@/components/chat/quick-actions').then(mod => ({ default: mod.SuggestedActions })),
  {
    ssr: false,
  }
);

// Heavy markdown renderer with syntax highlighting
export const LazyMarkdownRenderer = dynamic(
  () => import('@/components/chat/message').then(mod => ({ default: mod.ChatMessage })),
  {
    ssr: false,
  }
);

// Syntax highlighter (heavy)
export const LazySyntaxHighlighter = dynamic(
  () => import('react-syntax-highlighter').then(mod => ({ default: mod.Prism })),
  {
    ssr: false,
    loading: () => <div className="h-32 bg-muted rounded animate-pulse" />,
  }
);

// Charts and analytics (very heavy)
export const LazyAnalyticsDashboard = dynamic(
  () => import('@/app/analytics/page'),
  {
    ssr: false,
    loading: () => <AnalyticsSkeleton />,
  }
);

// Knowledge graph visualization (heavy)
export const LazyKnowledgeGraph = dynamic(
  () => import('@/app/knowledge-graph/page'),
  {
    ssr: false,
    loading: () => (
      <div className="h-96 bg-muted rounded animate-pulse flex items-center justify-center">
        <span className="text-muted-foreground">Loading visualization...</span>
      </div>
    ),
  }
);

// Agent executor (complex component)
export const LazyAgentExecutor = dynamic(
  () => import('@/components/agents/agent-executor').then(mod => ({ default: mod.AgentExecutor })),
  {
    ssr: false,
  }
);

// Document viewer (heavy with PDF support)
export const LazyDocumentViewer = dynamic(
  () => import('@/app/documents/page'),
  {
    ssr: false,
  }
);

// Settings forms (medium weight, but not critical for initial load)
export const LazySettingsPage = dynamic(
  () => import('@/app/settings/page'),
  {
    ssr: false,
  }
);

// Admin pages (not needed for most users)
export const LazyAdminUsersPage = dynamic(
  () => import('@/app/admin/users/page'),
  {
    ssr: false,
  }
);

// Team management
export const LazyTeamPage = dynamic(
  () => import('@/app/team/page'),
  {
    ssr: false,
  }
);

// -----------------------------------------------------------------------------
// Prefetching Utilities
// -----------------------------------------------------------------------------

/**
 * Prefetch component on hover/focus for faster subsequent load
 */
export function prefetchComponent(importFn: () => Promise<unknown>): void {
  // Trigger dynamic import to start loading
  importFn().catch(() => {
    // Silently fail - prefetch is just optimization
  });
}

/**
 * Prefetch likely next routes based on current page
 */
export function prefetchLikelyRoutes(currentPath: string): void {
  const routePrefetchMap: Record<string, (() => Promise<unknown>)[]> = {
    '/': [
      () => import('@/app/chat/page'),
      () => import('@/app/(auth)/login/page'),
    ],
    '/login': [
      () => import('@/app/chat/page'),
      () => import('@/app/(auth)/register/page'),
    ],
    '/chat': [
      () => import('@/components/chat/context-panel'),
      () => import('@/app/documents/page'),
      () => import('@/app/agents/page'),
    ],
    '/analytics': [
      () => import('@/app/devops/page'),
    ],
  };

  const prefetches = routePrefetchMap[currentPath];
  if (prefetches) {
    // Delay prefetch to not compete with initial load
    setTimeout(() => {
      prefetches.forEach(prefetchComponent);
    }, 2000);
  }
}

// -----------------------------------------------------------------------------
// Virtualization Helpers
// -----------------------------------------------------------------------------

/**
 * Calculate visible items for virtualized list
 */
export function calculateVisibleRange(
  scrollTop: number,
  viewportHeight: number,
  itemHeight: number,
  totalItems: number,
  overscan: number = 3
): { startIndex: number; endIndex: number } {
  const startIndex = Math.max(0, Math.floor(scrollTop / itemHeight) - overscan);
  const visibleCount = Math.ceil(viewportHeight / itemHeight);
  const endIndex = Math.min(totalItems - 1, startIndex + visibleCount + overscan * 2);

  return { startIndex, endIndex };
}

/**
 * Get style for virtualized item
 */
export function getVirtualizedItemStyle(
  index: number,
  itemHeight: number
): React.CSSProperties {
  return {
    position: 'absolute',
    top: index * itemHeight,
    left: 0,
    right: 0,
    height: itemHeight,
  };
}
