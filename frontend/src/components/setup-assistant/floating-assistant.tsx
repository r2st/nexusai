'use client';

import { useState, useEffect } from 'react';
import { MessageCircle, X, Sparkles, Minimize2, Maximize2 } from 'lucide-react';
import { cn } from '@/lib/utils';
import { SetupAssistant } from './setup-assistant';

interface FloatingAssistantProps {
  className?: string;
  defaultOpen?: boolean;
  defaultMinimized?: boolean;
}

export function FloatingAssistant({
  className,
  defaultOpen = false,
  defaultMinimized = false,
}: FloatingAssistantProps) {
  const [isOpen, setIsOpen] = useState(defaultOpen);
  const [isMinimized, setIsMinimized] = useState(defaultMinimized);
  const [hasInteracted, setHasInteracted] = useState(false);

  // Show a welcome pulse on first load
  useEffect(() => {
    const hasSeenAssistant = localStorage.getItem('setup_assistant_seen');
    if (!hasSeenAssistant) {
      // Show subtle pulse animation
      setTimeout(() => {
        setHasInteracted(true);
      }, 3000);
    }
  }, []);

  const handleOpen = () => {
    setIsOpen(true);
    setIsMinimized(false);
    localStorage.setItem('setup_assistant_seen', 'true');
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const handleMinimize = () => {
    setIsMinimized(!isMinimized);
  };

  if (!isOpen) {
    return (
      <button
        onClick={handleOpen}
        className={cn(
          'fixed bottom-6 right-6 z-50',
          'h-14 w-14 rounded-full',
          'bg-gradient-to-br from-primary to-primary/80',
          'text-primary-foreground',
          'shadow-lg hover:shadow-xl',
          'transition-all duration-200',
          'flex items-center justify-center',
          'hover:scale-105 active:scale-95',
          !hasInteracted && 'animate-pulse',
          className
        )}
        title="Open Setup Assistant"
      >
        <Sparkles className="h-6 w-6" />
      </button>
    );
  }

  return (
    <div
      className={cn(
        'fixed z-50 transition-all duration-300 ease-out',
        isMinimized
          ? 'bottom-6 right-6 w-64 h-14'
          : 'bottom-6 right-6 w-[400px] h-[600px] max-h-[80vh]',
        className
      )}
    >
      <div
        className={cn(
          'w-full h-full bg-background rounded-2xl shadow-2xl border overflow-hidden',
          'flex flex-col'
        )}
      >
        {/* Minimized state */}
        {isMinimized ? (
          <button
            onClick={handleMinimize}
            className="w-full h-full flex items-center gap-3 px-4 hover:bg-muted/50 transition-colors"
          >
            <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center shrink-0">
              <Sparkles className="h-4 w-4 text-primary-foreground" />
            </div>
            <span className="font-medium text-sm">Setup Assistant</span>
            <Maximize2 className="h-4 w-4 ml-auto text-muted-foreground" />
          </button>
        ) : (
          <>
            {/* Expanded header with minimize/close */}
            <div className="flex items-center justify-between px-4 py-2 border-b bg-muted/30">
              <div className="flex items-center gap-2">
                <div className="h-8 w-8 rounded-full bg-gradient-to-br from-primary to-primary/70 flex items-center justify-center">
                  <Sparkles className="h-4 w-4 text-primary-foreground" />
                </div>
                <span className="font-semibold text-sm">Setup Assistant</span>
              </div>
              <div className="flex items-center gap-1">
                <button
                  onClick={handleMinimize}
                  className="p-1.5 hover:bg-muted rounded-md transition-colors"
                  title="Minimize"
                >
                  <Minimize2 className="h-4 w-4" />
                </button>
                <button
                  onClick={handleClose}
                  className="p-1.5 hover:bg-muted rounded-md transition-colors"
                  title="Close"
                >
                  <X className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Setup assistant content */}
            <div className="flex-1 overflow-hidden">
              <SetupAssistant onClose={handleClose} />
            </div>
          </>
        )}
      </div>
    </div>
  );
}

// Hook to programmatically control the assistant
export function useSetupAssistant() {
  const [isOpen, setIsOpen] = useState(false);
  const [flowType, setFlowType] = useState<
    'connection' | 'project' | 'pipeline' | 'onboarding' | 'metrics' | undefined
  >();
  const [plugin, setPlugin] = useState<string | undefined>();

  const open = (
    type?: 'connection' | 'project' | 'pipeline' | 'onboarding' | 'metrics',
    pluginId?: string
  ) => {
    setFlowType(type);
    setPlugin(pluginId);
    setIsOpen(true);
  };

  const close = () => {
    setIsOpen(false);
    setFlowType(undefined);
    setPlugin(undefined);
  };

  return {
    isOpen,
    flowType,
    plugin,
    open,
    close,
    openOnboarding: () => open('onboarding'),
    openConnection: (pluginId?: string) => open('connection', pluginId),
    openProject: () => open('project'),
    openPipeline: () => open('pipeline'),
    openMetrics: () => open('metrics'),
  };
}
