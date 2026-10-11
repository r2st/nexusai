'use client';

/**
 * Floating AI Assistant
 * 
 * A chatbot widget that can be embedded on any page to provide
 * contextual AI assistance. Supports different modes for different
 * page contexts.
 */

import { useState, useRef, useEffect, useCallback, KeyboardEvent } from 'react';
import {
  MessageSquare,
  X,
  Send,
  Loader2,
  Sparkles,
  Minimize2,
  Maximize2,
  RotateCcw,
  HelpCircle,
  Settings,
  FileText,
  Users,
  BarChart3,
  Zap,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { cn } from '@/lib/utils';
import { useChatStore, DEFAULT_MODEL } from '@/store/chat';
import { chatApi } from '@/lib/api';

// =============================================================================
// TYPES
// =============================================================================

export type AssistantContext =
  | 'general'      // Default help
  | 'documents'    // Document management
  | 'settings'     // Settings/configuration
  | 'team'         // Team management
  | 'analytics'    // Analytics/reports
  | 'integrations' // Third-party integrations
  | 'security'     // Security settings
  | 'billing';     // Billing/subscriptions

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

interface FloatingAssistantProps {
  /** The context/page type for contextual suggestions */
  context?: AssistantContext;
  /** Initial message to greet the user */
  initialMessage?: string;
  /** Position of the floating button */
  position?: 'bottom-right' | 'bottom-left';
  /** Custom quick actions for the context */
  quickActions?: QuickAction[];
  /** Callback when assistant suggests an action */
  onAction?: (action: string, data?: Record<string, unknown>) => void;
  /** Whether to show the assistant button */
  enabled?: boolean;
}

interface QuickAction {
  id: string;
  label: string;
  icon?: typeof HelpCircle;
  message: string;
}

// =============================================================================
// CONTEXT CONFIGURATIONS
// =============================================================================

const contextConfig: Record<AssistantContext, {
  title: string;
  welcomeMessage: string;
  icon: typeof HelpCircle;
  quickActions: QuickAction[];
  systemPrompt: string;
}> = {
  general: {
    title: 'AI Assistant',
    welcomeMessage: "Hi! I'm your AI assistant. How can I help you today?",
    icon: Sparkles,
    quickActions: [
      { id: 'help', label: 'How do I get started?', message: 'How do I get started with GSTIndia?' },
      { id: 'features', label: 'What can you do?', message: 'What features does GSTIndia offer?' },
      { id: 'pricing', label: 'Tell me about pricing', message: 'What are the pricing plans?' },
    ],
    systemPrompt: 'You are a helpful AI assistant for GSTIndia by DoAide. Help users navigate and use the GST compliance platform effectively.',
  },
  documents: {
    title: 'Document Helper',
    welcomeMessage: "Need help with documents? I can help you upload, organize, and search through your files.",
    icon: FileText,
    quickActions: [
      { id: 'upload', label: 'How to upload?', message: 'How do I upload a document?' },
      { id: 'search', label: 'Search documents', message: 'How do I search within my documents?' },
      { id: 'organize', label: 'Organize files', message: 'How can I organize my documents into folders?' },
    ],
    systemPrompt: 'You are a document management assistant. Help users upload, organize, search, and manage their documents.',
  },
  settings: {
    title: 'Settings Helper',
    welcomeMessage: "I can help you configure your account and preferences. What would you like to adjust?",
    icon: Settings,
    quickActions: [
      { id: 'profile', label: 'Update profile', message: 'How do I update my profile?' },
      { id: 'security', label: 'Security settings', message: 'How do I enable two-factor authentication?' },
      { id: 'notifications', label: 'Notifications', message: 'How do I manage notification preferences?' },
    ],
    systemPrompt: 'You are a settings configuration assistant. Help users configure their account, security, and preferences.',
  },
  team: {
    title: 'Team Assistant',
    welcomeMessage: "Let me help you manage your team. I can assist with invites, roles, and permissions.",
    icon: Users,
    quickActions: [
      { id: 'invite', label: 'Invite members', message: 'How do I invite team members?' },
      { id: 'roles', label: 'Manage roles', message: 'What roles are available and how do I assign them?' },
      { id: 'permissions', label: 'Permissions', message: 'How do permissions work?' },
    ],
    systemPrompt: 'You are a team management assistant. Help users invite members, manage roles, and configure permissions.',
  },
  analytics: {
    title: 'Analytics Helper',
    welcomeMessage: "I can help you understand your data and metrics. What insights are you looking for?",
    icon: BarChart3,
    quickActions: [
      { id: 'metrics', label: 'Key metrics', message: 'What are the most important metrics to track?' },
      { id: 'reports', label: 'Generate reports', message: 'How do I create a custom report?' },
      { id: 'export', label: 'Export data', message: 'How can I export my analytics data?' },
    ],
    systemPrompt: 'You are an analytics assistant. Help users understand their metrics, create reports, and derive insights.',
  },
  integrations: {
    title: 'Integration Helper',
    welcomeMessage: "Need help connecting your tools? I can guide you through setting up integrations.",
    icon: Zap,
    quickActions: [
      { id: 'connect', label: 'Connect a tool', message: 'How do I connect a new integration?' },
      { id: 'github', label: 'Setup GitHub', message: 'How do I integrate with GitHub?' },
      { id: 'slack', label: 'Setup Slack', message: 'How do I integrate with Slack?' },
    ],
    systemPrompt: 'You are an integrations assistant. Help users connect and configure third-party tools and services.',
  },
  security: {
    title: 'Security Assistant',
    welcomeMessage: "I can help you keep your account secure. What security concerns do you have?",
    icon: HelpCircle,
    quickActions: [
      { id: '2fa', label: 'Enable 2FA', message: 'How do I enable two-factor authentication?' },
      { id: 'password', label: 'Change password', message: 'How do I change my password?' },
      { id: 'sessions', label: 'Active sessions', message: 'How do I view and manage my active sessions?' },
    ],
    systemPrompt: 'You are a security assistant. Help users secure their accounts with 2FA, strong passwords, and session management.',
  },
  billing: {
    title: 'Billing Assistant',
    welcomeMessage: "I can help with billing questions. Need help with your subscription or invoices?",
    icon: HelpCircle,
    quickActions: [
      { id: 'plans', label: 'Compare plans', message: 'What are the differences between pricing plans?' },
      { id: 'upgrade', label: 'Upgrade plan', message: 'How do I upgrade my subscription?' },
      { id: 'invoice', label: 'View invoices', message: 'Where can I find my invoices?' },
    ],
    systemPrompt: 'You are a billing assistant. Help users understand pricing, manage subscriptions, and access invoices.',
  },
};

// =============================================================================
// FLOATING ASSISTANT COMPONENT
// =============================================================================

export function FloatingAssistant({
  context = 'general',
  initialMessage,
  position = 'bottom-right',
  quickActions: customQuickActions,
  onAction,
  enabled = true,
}: FloatingAssistantProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputValue, setInputValue] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const { selectedModel } = useChatStore();

  const config = contextConfig[context];
  const quickActions = customQuickActions || config.quickActions;
  const Icon = config.icon;

  // Scroll to bottom when messages change
  useEffect(() => {
    if (messagesEndRef.current?.scrollIntoView) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages]);

  // Add welcome message when opening
  useEffect(() => {
    if (isOpen && messages.length === 0) {
      const welcomeMsg = initialMessage || config.welcomeMessage;
      setMessages([
        {
          id: '1',
          role: 'assistant',
          content: welcomeMsg,
          timestamp: new Date(),
        },
      ]);
    }
  }, [isOpen, config.welcomeMessage, initialMessage, messages.length]);

  // Focus input when opened
  useEffect(() => {
    if (isOpen && !isMinimized) {
      setTimeout(() => inputRef.current?.focus(), 100);
    }
  }, [isOpen, isMinimized]);

  const handleSend = async (message?: string) => {
    const content = message || inputValue.trim();
    if (!content || isLoading) return;

    const userMessage: Message = {
      id: crypto.randomUUID(),
      role: 'user',
      content,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputValue('');
    setIsLoading(true);

    try {
      // Call the chat API
      const response = await chatApi.sendMessage(
        'floating-assistant', // Use a special conversation ID for the floating assistant
        content,
        { stream: false }
      );

      // Handle non-streaming response
      const messageResponse = response as { message: { content: string }; conversation: unknown };
      const responseContent = messageResponse.message?.content || "I'm sorry, I couldn't process that request. Please try again.";

      const assistantMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: responseContent,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      // Fallback response for demo/offline mode
      const fallbackMessage: Message = {
        id: crypto.randomUUID(),
        role: 'assistant',
        content: `I understand you're asking about "${content}". Let me help you with that. In the ${context} context, I can assist you with common tasks. Would you like me to guide you through any specific feature?`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, fallbackMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleReset = () => {
    setMessages([]);
  };

  if (!enabled) return null;

  return (
    <>
      {/* Floating Button */}
      {!isOpen && (
        <button
          onClick={() => setIsOpen(true)}
          className={cn(
            'fixed z-50 h-14 w-14 rounded-full bg-primary text-primary-foreground shadow-lg',
            'flex items-center justify-center',
            'hover:bg-primary/90 transition-all hover:scale-105',
            'focus:outline-none focus:ring-2 focus:ring-primary focus:ring-offset-2',
            position === 'bottom-right' ? 'bottom-6 right-6' : 'bottom-6 left-6'
          )}
          aria-label="Open AI Assistant"
        >
          <MessageSquare className="h-6 w-6" aria-hidden="true" />
        </button>
      )}

      {/* Chat Panel */}
      {isOpen && (
        <div
          role="dialog"
          aria-label={config.title}
          className={cn(
            'fixed z-50 flex flex-col bg-background border rounded-lg shadow-xl',
            'transition-all duration-200',
            position === 'bottom-right' ? 'bottom-6 right-6' : 'bottom-6 left-6',
            isMinimized ? 'w-72 h-12' : 'w-96 h-[32rem]'
          )}
        >
          {/* Header */}
          <div className="flex items-center justify-between px-4 py-3 border-b bg-muted/30 rounded-t-lg">
            <div className="flex items-center gap-2">
              <Icon className="h-5 w-5 text-primary" aria-hidden="true" />
              <span className="font-medium text-sm">{config.title}</span>
            </div>
            <div className="flex items-center gap-1">
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={handleReset}
                aria-label="Reset conversation"
              >
                <RotateCcw className="h-4 w-4" aria-hidden="true" />
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setIsMinimized(!isMinimized)}
                aria-label={isMinimized ? 'Expand assistant' : 'Minimize assistant'}
              >
                {isMinimized ? (
                  <Maximize2 className="h-4 w-4" aria-hidden="true" />
                ) : (
                  <Minimize2 className="h-4 w-4" aria-hidden="true" />
                )}
              </Button>
              <Button
                variant="ghost"
                size="icon"
                className="h-7 w-7"
                onClick={() => setIsOpen(false)}
                aria-label="Close assistant"
              >
                <X className="h-4 w-4" aria-hidden="true" />
              </Button>
            </div>
          </div>

          {!isMinimized && (
            <>
              {/* Messages */}
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {messages.map((msg) => (
                  <div
                    key={msg.id}
                    className={cn(
                      'flex',
                      msg.role === 'user' ? 'justify-end' : 'justify-start'
                    )}
                  >
                    <div
                      className={cn(
                        'max-w-[80%] rounded-lg px-3 py-2 text-sm',
                        msg.role === 'user'
                          ? 'bg-primary text-primary-foreground'
                          : 'bg-muted'
                      )}
                    >
                      {msg.content}
                    </div>
                  </div>
                ))}

                {isLoading && (
                  <div className="flex justify-start">
                    <div className="bg-muted rounded-lg px-3 py-2" role="status" aria-label="Loading response">
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    </div>
                  </div>
                )}

                <div ref={messagesEndRef} />
              </div>

              {/* Quick Actions */}
              {messages.length <= 1 && (
                <div className="px-4 pb-2">
                  <p className="text-xs text-muted-foreground mb-2">Quick questions:</p>
                  <div className="flex flex-wrap gap-1">
                    {quickActions.map((action) => (
                      <button
                        key={action.id}
                        onClick={() => handleSend(action.message)}
                        className="text-xs bg-muted hover:bg-muted/80 rounded-full px-3 py-1 transition-colors"
                      >
                        {action.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Input */}
              <div className="p-4 border-t">
                <div className="flex gap-2">
                  <input
                    ref={inputRef}
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Ask me anything..."
                    disabled={isLoading}
                    className={cn(
                      'flex-1 h-9 rounded-md border bg-background px-3 text-sm',
                      'placeholder:text-muted-foreground',
                      'focus:outline-none focus:ring-2 focus:ring-ring focus:ring-offset-1',
                      'disabled:opacity-50'
                    )}
                  />
                  <Button
                    size="icon"
                    className="h-9 w-9"
                    onClick={() => handleSend()}
                    disabled={!inputValue.trim() || isLoading}
                    aria-label="Send message"
                  >
                    <Send className="h-4 w-4" aria-hidden="true" />
                  </Button>
                </div>
                <p className="text-[10px] text-muted-foreground mt-1.5 text-center">
                  Powered by {selectedModel || DEFAULT_MODEL}
                </p>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}

// =============================================================================
// HOOK FOR PAGE CONTEXT
// =============================================================================

/**
 * Hook to easily add floating assistant to any page with automatic context
 */
export function useFloatingAssistant(context: AssistantContext) {
  const [isVisible, setIsVisible] = useState(true);

  return {
    context,
    isVisible,
    show: () => setIsVisible(true),
    hide: () => setIsVisible(false),
    toggle: () => setIsVisible((v) => !v),
  };
}
