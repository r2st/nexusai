'use client';

import { useState, useEffect, useRef, useCallback } from 'react';
import { Bot, Send, ArrowLeft, X, Loader2, Settings, ChevronRight, Sparkles } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import {
  setupAssistantApi,
  SetupMessage,
  SetupChatResponse,
  QuickReply,
  PluginInfo,
} from '@/lib/api';

interface SetupAssistantProps {
  onClose?: () => void;
  initialFlowType?: 'connection' | 'project' | 'pipeline' | 'onboarding';
  initialPlugin?: string;
  className?: string;
}

export function SetupAssistant({
  onClose,
  initialFlowType,
  initialPlugin,
  className,
}: SetupAssistantProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<SetupMessage[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isInitializing, setIsInitializing] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [canGoBack, setCanGoBack] = useState(false);
  const [currentStep, setCurrentStep] = useState<string | null>(null);
  const [isComplete, setIsComplete] = useState(false);
  const [collectedData, setCollectedData] = useState<Record<string, unknown>>({});

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  // Scroll to bottom when messages change
  const scrollToBottom = useCallback(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages, scrollToBottom]);

  // Initialize session
  useEffect(() => {
    const initSession = async () => {
      try {
        setIsInitializing(true);
        setError(null);

        let result;
        if (initialFlowType === 'onboarding') {
          result = await setupAssistantApi.startOnboarding();
        } else if (initialPlugin) {
          result = await setupAssistantApi.quickSetup(initialPlugin);
        } else {
          result = await setupAssistantApi.startSession({
            flow_type: initialFlowType,
            plugin: initialPlugin,
          });
        }

        setSessionId(result.session_id);
        setMessages([result.message]);
        setCurrentStep(result.current_step || null);
      } catch (err) {
        console.error('Failed to start session:', err);
        setError('Failed to start setup assistant. Please try again.');
      } finally {
        setIsInitializing(false);
      }
    };

    initSession();
  }, [initialFlowType, initialPlugin]);

  // Handle sending a message
  const handleSendMessage = async (message: string, isQuickReply = false) => {
    if (!sessionId || !message.trim() || isLoading) return;

    // Add user message to UI immediately
    const userMessage: SetupMessage = {
      id: crypto.randomUUID(),
      role: 'user',
      content: message,
      timestamp: new Date().toISOString(),
      quick_replies: [],
      actions: [],
      metadata: {},
    };
    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);
    setError(null);

    try {
      const response = await setupAssistantApi.sendMessage(
        sessionId,
        message,
        isQuickReply
      );

      setMessages((prev) => [...prev, response.message]);
      setCanGoBack(response.can_go_back);
      setCurrentStep(response.current_step || null);
      setIsComplete(response.is_complete);
      setCollectedData(response.collected_data);

      if (response.errors.length > 0) {
        setError(response.errors.join(', '));
      }
    } catch (err) {
      console.error('Failed to send message:', err);
      setError('Failed to send message. Please try again.');
    } finally {
      setIsLoading(false);
      inputRef.current?.focus();
    }
  };

  // Handle quick reply click
  const handleQuickReply = (reply: QuickReply) => {
    handleSendMessage(reply.value, true);
  };

  // Handle going back
  const handleGoBack = async () => {
    if (!sessionId || !canGoBack || isLoading) return;
    handleSendMessage('back', true);
  };

  // Handle form submission
  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    handleSendMessage(inputValue);
  };

  // Render loading state
  if (isInitializing) {
    return (
      <div className={cn('flex flex-col h-full bg-background', className)}>
        <div className="flex items-center justify-center h-full">
          <div className="text-center space-y-4">
            <Loader2 className="h-8 w-8 animate-spin mx-auto text-primary" />
            <p className="text-muted-foreground">Starting setup assistant...</p>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={cn('flex flex-col h-full bg-background', className)}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30">
        <div className="flex items-center gap-3">
          {canGoBack && (
            <button
              onClick={handleGoBack}
              disabled={isLoading}
              className="p-1 hover:bg-muted rounded-md transition-colors disabled:opacity-50"
              title="Go back"
            >
              <ArrowLeft className="h-5 w-5" />
            </button>
          )}
          <div className="flex items-center gap-2">
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <div>
              <h2 className="font-semibold text-sm">Setup Assistant</h2>
              {currentStep && (
                <p className="text-xs text-muted-foreground capitalize">
                  {currentStep.replace(/_/g, ' ')}
                </p>
              )}
            </div>
          </div>
        </div>
        {onClose && (
          <button
            onClick={onClose}
            className="p-1 hover:bg-muted rounded-md transition-colors"
            title="Close"
          >
            <X className="h-5 w-5" />
          </button>
        )}
      </div>

      {/* Progress indicator */}
      {messages.length > 0 && messages[messages.length - 1].progress_percent !== undefined && (
        <div className="px-4 py-2 border-b">
          <div className="flex items-center justify-between text-xs text-muted-foreground mb-1">
            <span>
              Step {messages[messages.length - 1].step_number} of{' '}
              {messages[messages.length - 1].total_steps}
            </span>
            <span>{Math.round(messages[messages.length - 1].progress_percent || 0)}%</span>
          </div>
          <div className="h-1.5 bg-muted rounded-full overflow-hidden">
            <div
              className="h-full bg-primary transition-all duration-300 ease-out rounded-full"
              style={{ width: `${messages[messages.length - 1].progress_percent || 0}%` }}
            />
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        <div className="space-y-1">
          {messages.map((message) => (
            <MessageBubble
              key={message.id}
              message={message}
              onQuickReply={handleQuickReply}
              isLoading={isLoading}
            />
          ))}

          {/* Loading indicator */}
          {isLoading && (
            <div className="flex gap-4 px-4 py-6 bg-muted/50">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary">
                <Bot className="h-4 w-4" />
              </div>
              <div className="flex items-center gap-2">
                <Loader2 className="h-4 w-4 animate-spin" />
                <span className="text-sm text-muted-foreground">Thinking...</span>
              </div>
            </div>
          )}
        </div>
        <div ref={messagesEndRef} />
      </div>

      {/* Error message */}
      {error && (
        <div className="px-4 py-2 bg-destructive/10 border-t border-destructive/20">
          <p className="text-sm text-destructive">{error}</p>
        </div>
      )}

      {/* Input */}
      {!isComplete && (
        <form onSubmit={handleSubmit} className="p-4 border-t bg-background">
          <div className="flex gap-2">
            <input
              ref={inputRef}
              type="text"
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder="Type your response..."
              disabled={isLoading}
              className="flex-1 px-4 py-2 border rounded-lg focus:outline-none focus:ring-2 focus:ring-primary/50 disabled:opacity-50 bg-background"
            />
            <button
              type="submit"
              disabled={!inputValue.trim() || isLoading}
              className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              <Send className="h-4 w-4" />
            </button>
          </div>
        </form>
      )}

      {/* Completion state */}
      {isComplete && (
        <div className="p-4 border-t bg-muted/30">
          <div className="text-center space-y-3">
            <p className="text-sm text-muted-foreground">
              Setup complete! You can close this assistant or start a new setup.
            </p>
            <div className="flex gap-2 justify-center">
              <button
                onClick={onClose}
                className="px-4 py-2 border rounded-lg hover:bg-muted transition-colors text-sm"
              >
                Close
              </button>
              <button
                onClick={() => window.location.reload()}
                className="px-4 py-2 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90 transition-colors text-sm"
              >
                New Setup
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Message bubble component
function MessageBubble({
  message,
  onQuickReply,
  isLoading,
}: {
  message: SetupMessage;
  onQuickReply: (reply: QuickReply) => void;
  isLoading: boolean;
}) {
  const isUser = message.role === 'user';

  return (
    <div
      className={cn(
        'flex gap-4 px-4 py-6',
        isUser ? 'bg-background' : 'bg-muted/50'
      )}
    >
      {/* Avatar */}
      <div
        className={cn(
          'flex h-8 w-8 shrink-0 items-center justify-center rounded-full',
          isUser
            ? 'bg-primary text-primary-foreground'
            : 'bg-gradient-to-br from-primary to-primary/70 text-primary-foreground'
        )}
      >
        {isUser ? (
          <span className="text-sm font-medium">Y</span>
        ) : (
          <Sparkles className="h-4 w-4" />
        )}
      </div>

      {/* Content */}
      <div className="flex-1 space-y-3 overflow-hidden">
        <div className="text-sm font-medium">
          {isUser ? 'You' : 'Setup Assistant'}
        </div>

        {/* Message content */}
        <div className="prose prose-sm dark:prose-invert max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {message.content}
          </ReactMarkdown>
        </div>

        {/* Quick replies */}
        {!isUser && message.quick_replies && message.quick_replies.length > 0 && (
          <div className="flex flex-wrap gap-2 pt-2">
            {message.quick_replies.map((reply) => (
              <button
                key={reply.id || reply.value}
                onClick={() => onQuickReply(reply)}
                disabled={isLoading}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm border rounded-full hover:bg-muted transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                {reply.icon && <span>{reply.icon}</span>}
                <span>{reply.label}</span>
                <ChevronRight className="h-3 w-3 text-muted-foreground" />
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// Plugin card component for quick setup
export function PluginCard({
  plugin,
  onClick,
}: {
  plugin: PluginInfo;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-start gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left w-full"
    >
      <div className="text-2xl">{plugin.icon}</div>
      <div className="flex-1 min-w-0">
        <h3 className="font-medium">{plugin.display_name}</h3>
        <p className="text-sm text-muted-foreground line-clamp-2">
          {plugin.description}
        </p>
        <div className="flex gap-1 mt-2">
          {plugin.scopes_supported.slice(0, 3).map((scope) => (
            <span
              key={scope}
              className="px-2 py-0.5 text-xs bg-muted rounded-full"
            >
              {scope}
            </span>
          ))}
        </div>
      </div>
      <ChevronRight className="h-5 w-5 text-muted-foreground shrink-0" />
    </button>
  );
}

// Default plugins when API is unavailable (e.g., user not logged in)
const DEFAULT_PLUGINS: PluginInfo[] = [
  {
    plugin_type: 'github',
    display_name: 'GitHub',
    description: 'Connect to GitHub repositories for code metrics, pull requests, and issues.',
    icon: '🐙',
    required_fields: ['token'],
    optional_fields: ['endpoint'],
    auth_type: 'token',
    endpoint_required: false,
    scopes_supported: ['repos', 'issues', 'pull_requests', 'commits'],
  },
  {
    plugin_type: 'gitlab',
    display_name: 'GitLab',
    description: 'Connect to GitLab for merge requests, pipelines, and repository analytics.',
    icon: '🦊',
    required_fields: ['token'],
    optional_fields: ['endpoint'],
    auth_type: 'token',
    endpoint_required: false,
    scopes_supported: ['projects', 'merge_requests', 'pipelines', 'issues'],
  },
  {
    plugin_type: 'jira',
    display_name: 'Jira',
    description: 'Connect to Jira for issue tracking, sprint metrics, and workflow analysis.',
    icon: '📋',
    required_fields: ['token', 'endpoint'],
    optional_fields: [],
    auth_type: 'token',
    endpoint_required: true,
    scopes_supported: ['boards', 'issues', 'sprints', 'projects'],
  },
  {
    plugin_type: 'jenkins',
    display_name: 'Jenkins',
    description: 'Connect to Jenkins for CI/CD pipeline metrics and build analytics.',
    icon: '🔧',
    required_fields: ['token', 'endpoint'],
    optional_fields: [],
    auth_type: 'basic',
    endpoint_required: true,
    scopes_supported: ['jobs', 'builds', 'pipelines'],
  },
  {
    plugin_type: 'bitbucket',
    display_name: 'Bitbucket',
    description: 'Connect to Bitbucket for repository metrics and pull request tracking.',
    icon: '🪣',
    required_fields: ['token'],
    optional_fields: ['endpoint'],
    auth_type: 'token',
    endpoint_required: false,
    scopes_supported: ['repos', 'pull_requests', 'pipelines'],
  },
  {
    plugin_type: 'sonarqube',
    display_name: 'SonarQube',
    description: 'Connect to SonarQube for code quality metrics and security analysis.',
    icon: '🔍',
    required_fields: ['token', 'endpoint'],
    optional_fields: [],
    auth_type: 'token',
    endpoint_required: true,
    scopes_supported: ['projects', 'issues', 'metrics'],
  },
];

// Setup launcher component
export function SetupLauncher({
  onStartSetup,
}: {
  onStartSetup: (type: 'connection' | 'project' | 'pipeline' | 'onboarding', plugin?: string) => void;
}) {
  const [plugins, setPlugins] = useState<PluginInfo[]>(DEFAULT_PLUGINS);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const loadPlugins = async () => {
      try {
        const result = await setupAssistantApi.listPlugins();
        if (result && result.length > 0) {
          setPlugins(result);
        }
        // If result is empty, keep the default plugins
      } catch (err) {
        // On 401 or any error, use default plugins (already set)
        console.log('Using default plugins (API unavailable or unauthorized)');
      } finally {
        setIsLoading(false);
      }
    };
    loadPlugins();
  }, []);

  return (
    <div className="space-y-6 p-6">
      {/* Quick actions */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Get Started</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <button
            onClick={() => onStartSetup('onboarding')}
            className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left"
          >
            <div className="h-10 w-10 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
              <Sparkles className="h-5 w-5 text-primary-foreground" />
            </div>
            <div>
              <h3 className="font-medium">Start Onboarding</h3>
              <p className="text-sm text-muted-foreground">
                Complete guided setup for new users
              </p>
            </div>
          </button>

          <button
            onClick={() => onStartSetup('project')}
            className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left"
          >
            <div className="h-10 w-10 rounded-full bg-blue-100 dark:bg-blue-900 flex items-center justify-center">
              <span className="text-xl">📦</span>
            </div>
            <div>
              <h3 className="font-medium">Create Project</h3>
              <p className="text-sm text-muted-foreground">
                Set up a new project for your metrics
              </p>
            </div>
          </button>

          <button
            onClick={() => onStartSetup('pipeline')}
            className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left"
          >
            <div className="h-10 w-10 rounded-full bg-green-100 dark:bg-green-900 flex items-center justify-center">
              <span className="text-xl">⏰</span>
            </div>
            <div>
              <h3 className="font-medium">Configure Pipeline</h3>
              <p className="text-sm text-muted-foreground">
                Set up automatic data collection
              </p>
            </div>
          </button>

          <button
            onClick={() => onStartSetup('connection')}
            className="flex items-center gap-4 p-4 border rounded-lg hover:bg-muted/50 transition-colors text-left"
          >
            <div className="h-10 w-10 rounded-full bg-orange-100 dark:bg-orange-900 flex items-center justify-center">
              <span className="text-xl">🔗</span>
            </div>
            <div>
              <h3 className="font-medium">Add Connection</h3>
              <p className="text-sm text-muted-foreground">
                Connect a new data source
              </p>
            </div>
          </button>

        </div>
      </div>

      {/* Plugin quick setup */}
      <div>
        <h2 className="text-lg font-semibold mb-4">Quick Connect</h2>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {plugins.map((plugin) => (
              <PluginCard
                key={plugin.plugin_type}
                plugin={plugin}
                onClick={() => onStartSetup('connection', plugin.plugin_type)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
