'use client';

import { useState, useEffect, Suspense } from 'react';
import { useRouter, useSearchParams } from 'next/navigation';
import { SetupLauncher } from '@/components/setup-assistant';
import { AssistantChat } from '@/components/assistant-chat';
import { ArrowLeft, Loader2 } from 'lucide-react';
import { DoAideLogo } from '@/components/ui/doaide-logo';
import Link from 'next/link';

type FlowType = 'connection' | 'project' | 'pipeline' | 'onboarding';

function SetupPageLoading() {
  return (
    <div className="min-h-screen bg-background flex items-center justify-center">
      <Loader2 className="h-8 w-8 animate-spin text-primary" />
    </div>
  );
}

export default function SetupPage() {
  return (
    <Suspense fallback={<SetupPageLoading />}>
      <SetupPageContent />
    </Suspense>
  );
}

function SetupPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();

  const [activeSetup, setActiveSetup] = useState<{
    type: FlowType;
    plugin?: string;
  } | null>(null);

  // Check for URL params to start specific setup
  useEffect(() => {
    const type = searchParams.get('type') as FlowType | null;
    const plugin = searchParams.get('plugin');

    if (type) {
      setActiveSetup({ type, plugin: plugin || undefined });
    }
  }, [searchParams]);

  const handleStartSetup = (type: FlowType, plugin?: string) => {
    setActiveSetup({ type, plugin });
    // Update URL for bookmarking/sharing
    const params = new URLSearchParams();
    params.set('type', type);
    if (plugin) params.set('plugin', plugin);
    router.push(`/setup?${params.toString()}`);
  };

  const handleCloseSetup = () => {
    setActiveSetup(null);
    router.replace('/setup');
  };

  const handleComplete = (data: Record<string, unknown>) => {
    console.log('Setup completed with data:', data);
    // Could show a success toast or redirect
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Top Navigation */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-40">
        <div className="max-w-4xl mx-auto px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            {activeSetup && (
              <button
                onClick={handleCloseSetup}
                className="p-1.5 hover:bg-muted rounded-md transition-colors"
                title="Back to menu"
              >
                <ArrowLeft className="h-5 w-5" />
              </button>
            )}
            <Link href="/" className="flex items-center gap-2 hover:opacity-80 transition-opacity">
              <DoAideLogo size={20} />
              <span className="font-semibold">GSTIndia</span>
            </Link>
          </div>

          <nav className="flex items-center gap-4 text-sm">
            <Link
              href="/analytics"
              className="text-muted-foreground hover:text-foreground transition-colors"
            >
              Analytics
            </Link>
            <Link
              href="/setup"
              className="text-foreground font-medium"
            >
              Assistant
            </Link>
          </nav>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-4xl mx-auto">
        {activeSetup ? (
          /* Chat Interface */
          <div className="h-[calc(100vh-57px)]">
            <AssistantChat
              flowType={activeSetup.type}
              plugin={activeSetup.plugin}
              onClose={handleCloseSetup}
              onComplete={handleComplete}
              showHeader={true}
              showQuickReplies={true}
            />
          </div>
        ) : (
          /* Launcher Menu */
          <div className="py-8">
            {/* Welcome Section */}
            <div className="px-6 mb-8">
              <h1 className="text-3xl font-bold mb-2">GSTIndia Assistant</h1>
              <p className="text-muted-foreground text-lg">
                Connect data sources, view metrics, and manage your engineering analytics through conversation.
              </p>
            </div>

            {/* Feature Cards */}
            <div className="px-6 mb-8">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div className="p-4 rounded-lg border bg-gradient-to-br from-blue-50 to-blue-100/50 dark:from-blue-950 dark:to-blue-900/50">
                  <div className="text-2xl mb-2">🔗</div>
                  <h3 className="font-medium mb-1">Connect Sources</h3>
                  <p className="text-sm text-muted-foreground">
                    GitHub, GitLab, Jira, Jenkins, and 40+ tools
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-gradient-to-br from-purple-50 to-purple-100/50 dark:from-purple-950 dark:to-purple-900/50">
                  <div className="text-2xl mb-2">📊</div>
                  <h3 className="font-medium mb-1">View Metrics</h3>
                  <p className="text-sm text-muted-foreground">
                    DORA metrics, team insights, and productivity analytics
                  </p>
                </div>
                <div className="p-4 rounded-lg border bg-gradient-to-br from-green-50 to-green-100/50 dark:from-green-950 dark:to-green-900/50">
                  <div className="text-2xl mb-2">⚡</div>
                  <h3 className="font-medium mb-1">Automate</h3>
                  <p className="text-sm text-muted-foreground">
                    Set up pipelines for automatic data collection
                  </p>
                </div>
              </div>
            </div>

            {/* Launcher */}
            <SetupLauncher onStartSetup={handleStartSetup} />

            {/* Help Section */}
            <div className="px-6 mt-8 pt-8 border-t">
              <h2 className="text-lg font-semibold mb-4">Need Help?</h2>
              <div className="flex flex-wrap gap-3">
                <button
                  onClick={() => handleStartSetup('onboarding')}
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm"
                >
                  <span>🚀</span>
                  <span>Start Guided Tour</span>
                </button>
                <a
                  href="https://devlake.apache.org/docs"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm"
                >
                  <span>📚</span>
                  <span>DevLake Docs</span>
                </a>
                <a
                  href="http://localhost:4000"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm"
                >
                  <span>🔧</span>
                  <span>DevLake UI</span>
                </a>
                <a
                  href="http://localhost:3002"
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border hover:bg-muted transition-colors text-sm"
                >
                  <span>📈</span>
                  <span>Grafana Dashboards</span>
                </a>
              </div>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}
