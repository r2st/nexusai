'use client';

import { useState, useCallback, useEffect } from 'react';
import { useRouter } from 'next/navigation';
import Link from 'next/link';
import {
  Sparkles,
  Bot,
  MessageSquare,
  BarChart3,
  FileText,
  Command,
  ArrowRight,
  Zap,
  Shield,
  Gauge,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { ChatInput } from '@/components/chat/input';
import { SuggestedActions, type QuickAction } from '@/components/chat/quick-actions';
import { useAuthStore, useAuthHydrated } from '@/store/auth';
import { useGlobalKeyboard } from '@/hooks/use-keyboard-shortcuts';
import { cn } from '@/lib/utils';

// -----------------------------------------------------------------------------
// Chatbot-First Landing Page
// -----------------------------------------------------------------------------

export default function Home() {
  const router = useRouter();
  const { isAuthenticated, user } = useAuthStore();
  const hasHydrated = useAuthHydrated();
  const [showCommandPalette, setShowCommandPalette] = useState(false);

  // Don't render auth-dependent content until hydrated to prevent hydration mismatch
  const showAuthenticatedUI = hasHydrated && isAuthenticated;

  // Global keyboard shortcuts
  useGlobalKeyboard({
    onCommandK: () => setShowCommandPalette(true),
    onEscape: () => setShowCommandPalette(false),
    enabled: true,
  });

  // Handle chat message from landing page
  const handleSendMessage = useCallback((message: string) => {
    if (showAuthenticatedUI) {
      // Store message in session storage to pass to chat page
      sessionStorage.setItem('pending_chat_message', message);
      router.push('/chat');
    } else {
      // Store message and redirect to login
      sessionStorage.setItem('pending_chat_message', message);
      router.push('/login?redirect=/chat');
    }
  }, [showAuthenticatedUI, router]);

  // Handle quick action selection
  const handleQuickAction = useCallback((action: QuickAction) => {
    handleSendMessage(action.prompt);
  }, [handleSendMessage]);

  // Handle command palette open
  const handleCommandK = useCallback(() => {
    setShowCommandPalette(true);
  }, []);

  return (
    <div className="min-h-screen bg-gradient-to-br from-background to-muted flex flex-col">
      {/* Header */}
      <header className="border-b bg-background/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto flex h-14 items-center justify-between px-4">
          <div className="flex items-center gap-2">
            <Sparkles className="h-5 w-5 text-primary" />
            <span className="text-lg font-bold">NexusAI</span>
          </div>
          <nav className="hidden md:flex items-center gap-4">
            <Link
              href="/analytics"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Analytics
            </Link>
            <Link
              href="/documents"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Docs
            </Link>
            <Link
              href="/pricing"
              className="text-sm font-medium text-muted-foreground hover:text-foreground transition-colors"
            >
              Pricing
            </Link>
          </nav>
          <div className="flex items-center gap-2">
            {showAuthenticatedUI ? (
              <>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/chat">
                    <MessageSquare className="h-4 w-4 mr-2" />
                    Chat
                  </Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/chat">Dashboard</Link>
                </Button>
              </>
            ) : (
              <>
                <Button variant="ghost" size="sm" asChild>
                  <Link href="/login">Login</Link>
                </Button>
                <Button size="sm" asChild>
                  <Link href="/register">Get Started</Link>
                </Button>
              </>
            )}
          </div>
        </div>
      </header>

      {/* Main Content - Chatbot First */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-8">
        <div className="w-full max-w-3xl space-y-8">
          {/* Hero */}
          <div className="text-center space-y-4">
            <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-primary/10 text-primary text-sm font-medium">
              <Zap className="h-4 w-4" />
              Software Intelligence Platform
            </div>
            <h1 className="text-4xl md:text-5xl font-bold tracking-tight">
              What can I help you with?
            </h1>
            <p className="text-lg text-muted-foreground max-w-xl mx-auto">
              Analyze repos, review PRs, investigate incidents, and track DORA metrics.
              Start with a question or choose an action below.
            </p>
          </div>

          {/* Chat Input - Primary CTA */}
          <div className="w-full">
            <ChatInput
              onSend={handleSendMessage}
              onCommandK={handleCommandK}
              placeholder="Ask about your repos, PRs, incidents, or DORA metrics..."
              showQuickActions={false}
              className="border-none p-0 [&>div]:max-w-none"
            />
          </div>

          {/* Quick Actions */}
          <SuggestedActions onAction={handleQuickAction} />

          {/* Keyboard shortcut hint */}
          <div className="text-center">
            <button
              onClick={handleCommandK}
              className="inline-flex items-center gap-2 text-sm text-muted-foreground hover:text-foreground transition-colors"
            >
              Press
              <kbd className="px-2 py-1 rounded bg-muted text-xs font-mono">
                <Command className="h-3 w-3 inline mr-1" />K
              </kbd>
              for command palette
            </button>
          </div>
        </div>
      </main>

      {/* Features Section - Below the fold */}
      <section className="border-t bg-muted/30 py-16">
        <div className="container mx-auto px-4">
          <div className="text-center mb-12">
            <h2 className="text-2xl font-bold">Everything you need for software intelligence</h2>
            <p className="mt-2 text-muted-foreground">
              Minimum clicks, maximum insights
            </p>
          </div>

          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
            <FeatureCard
              icon={<MessageSquare className="h-5 w-5" />}
              title="AI Chat"
              description="Multi-model support with streaming. Context-aware conversations about your codebase."
            />
            <FeatureCard
              icon={<BarChart3 className="h-5 w-5" />}
              title="DORA Metrics"
              description="Track deployment frequency, lead time, MTTR, and change failure rate."
            />
            <FeatureCard
              icon={<FileText className="h-5 w-5" />}
              title="Doc Intelligence"
              description="Search and chat with your documentation using vector search."
            />
            <FeatureCard
              icon={<Shield className="h-5 w-5" />}
              title="Security"
              description="RBAC, tenant isolation, and secure API access controls."
            />
          </div>

          {/* Performance metrics */}
          <div className="mt-16 grid gap-4 md:grid-cols-3">
            <MetricCard value="<100ms" label="Time to first token" />
            <MetricCard value="50+" label="Integrations supported" />
            <MetricCard value="99.9%" label="Uptime SLA" />
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="py-16 bg-primary text-primary-foreground">
        <div className="container mx-auto px-4 text-center">
          <h2 className="text-2xl md:text-3xl font-bold">
            Ready to supercharge your engineering team?
          </h2>
          <p className="mt-4 text-primary-foreground/80 max-w-xl mx-auto">
            Start your free trial today. No credit card required.
          </p>
          <div className="mt-8 flex items-center justify-center gap-4">
            <Button size="lg" variant="secondary" asChild>
              <Link href="/start-trial">
                Start Free Trial
                <ArrowRight className="h-4 w-4 ml-2" />
              </Link>
            </Button>
            <Button size="lg" variant="outline" className="text-primary-foreground border-primary-foreground/30 hover:bg-primary-foreground/10" asChild>
              <Link href="/pricing">View Pricing</Link>
            </Button>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t py-8 bg-background">
        <div className="container mx-auto px-4">
          <div className="flex flex-col md:flex-row items-center justify-between gap-4">
            <div className="flex items-center gap-2">
              <Sparkles className="h-4 w-4 text-primary" />
              <span className="font-semibold">NexusAI</span>
            </div>
            <nav className="flex items-center gap-6 text-sm text-muted-foreground">
              <Link href="/terms" className="hover:text-foreground transition-colors">
                Terms
              </Link>
              <Link href="/privacy" className="hover:text-foreground transition-colors">
                Privacy
              </Link>
              <Link href="/docs" className="hover:text-foreground transition-colors">
                Docs
              </Link>
              <Link href="/status" className="hover:text-foreground transition-colors">
                Status
              </Link>
            </nav>
            <p className="text-sm text-muted-foreground">
              &copy; {new Date().getFullYear()} NexusAI. Open Source under MIT License.
            </p>
          </div>
        </div>
      </footer>

      {/* Command Palette Modal (placeholder) */}
      {showCommandPalette && (
        <CommandPalette
          isOpen={showCommandPalette}
          onClose={() => setShowCommandPalette(false)}
          onSelect={handleSendMessage}
        />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Helper Components
// -----------------------------------------------------------------------------

function FeatureCard({
  icon,
  title,
  description,
}: {
  icon: React.ReactNode;
  title: string;
  description: string;
}) {
  return (
    <div className="rounded-lg border bg-card p-6 hover:shadow-md transition-shadow">
      <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10 text-primary">
        {icon}
      </div>
      <h3 className="mt-4 font-semibold">{title}</h3>
      <p className="mt-2 text-sm text-muted-foreground">{description}</p>
    </div>
  );
}

function MetricCard({ value, label }: { value: string; label: string }) {
  return (
    <div className="rounded-lg border bg-card p-6 text-center">
      <div className="text-3xl font-bold text-primary">{value}</div>
      <div className="mt-1 text-sm text-muted-foreground">{label}</div>
    </div>
  );
}

function CommandPalette({
  isOpen,
  onClose,
  onSelect,
}: {
  isOpen: boolean;
  onClose: () => void;
  onSelect: (command: string) => void;
}) {
  const commands = [
    { id: 'analyze_pr', label: 'Analyze a Pull Request', icon: '🔍' },
    { id: 'connect_repo', label: 'Connect a Repository', icon: '🔗' },
    { id: 'find_root_cause', label: 'Find Incident Root Cause', icon: '🔧' },
    { id: 'deploy_risk', label: 'Summarize Deploy Risk', icon: '🚀' },
    { id: 'dora_metrics', label: 'View DORA Metrics', icon: '📊' },
    { id: 'test_plan', label: 'Generate Test Plan', icon: '✅' },
  ];

  if (!isOpen) return null;

  return (
    <div
      className="fixed inset-0 z-50 bg-background/80 backdrop-blur-sm flex items-start justify-center pt-[20vh]"
      onClick={onClose}
    >
      <div
        className="w-full max-w-lg rounded-lg border bg-card shadow-lg"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="p-4 border-b">
          <input
            type="text"
            placeholder="Type a command or search..."
            className="w-full bg-transparent outline-none text-sm"
            autoFocus
          />
        </div>
        <div className="p-2 max-h-80 overflow-y-auto">
          {commands.map((cmd) => (
            <button
              key={cmd.id}
              className="w-full flex items-center gap-3 px-3 py-2 rounded-md hover:bg-muted text-left text-sm"
              onClick={() => {
                onSelect(cmd.label);
                onClose();
              }}
            >
              <span>{cmd.icon}</span>
              <span>{cmd.label}</span>
            </button>
          ))}
        </div>
        <div className="p-2 border-t text-xs text-muted-foreground flex items-center justify-between">
          <span>Navigate with \u2191\u2193 \u00b7 Select with Enter</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
}
