'use client';

/**
 * Assistant Provider Component
 *
 * Wraps the assistant-ui runtime provider with GSTIndia configuration
 */

import { type ReactNode, useMemo, useCallback, useState } from 'react';
import {
  AssistantRuntimeProvider,
  useNexusRuntime,
  type NexusAssistantConfig,
} from '@/lib/assistant-runtime';

interface AssistantProviderProps {
  children: ReactNode;
  flowType?: NexusAssistantConfig['flowType'];
  plugin?: string;
  onComplete?: (data: Record<string, unknown>) => void;
  onError?: (error: Error) => void;
}

export function AssistantProvider({
  children,
  flowType,
  plugin,
  onComplete,
  onError,
}: AssistantProviderProps) {
  const [sessionId, setSessionId] = useState<string | null>(null);

  const config: NexusAssistantConfig = useMemo(
    () => ({
      flowType,
      plugin,
      onSessionCreated: setSessionId,
      onFlowComplete: onComplete,
      onError,
    }),
    [flowType, plugin, onComplete, onError]
  );

  const runtime = useNexusRuntime(config);

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      {children}
    </AssistantRuntimeProvider>
  );
}
