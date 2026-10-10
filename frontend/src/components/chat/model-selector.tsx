'use client';

import { useState, useEffect, useMemo } from 'react';
import {
  ChevronDown,
  Sparkles,
  Zap,
  Brain,
  Check,
  Loader2,
  AlertCircle,
  Server,
} from 'lucide-react';
import { cn } from '@/lib/utils';
import { llmApi, type ModelsResponse } from '@/lib/api';

export interface AIModel {
  id: string;
  provider: string;
  name: string;
  displayName: string;
  description: string;
  contextWindow: number;
  maxTokens: number;
  speed: 'fast' | 'medium' | 'slow';
  quality: 'good' | 'great' | 'best';
  costTier: 'low' | 'medium' | 'high';
  capabilities: string[];
  isDefault?: boolean;
  isNew?: boolean;
  isAvailable?: boolean;
}

// Full model catalog with metadata (superset of all possible models)
const MODEL_CATALOG: Record<string, Omit<AIModel, 'id' | 'isDefault' | 'isAvailable'>> = {
  // Google models
  'gemini-1.5-flash': {
    provider: 'google',
    name: 'gemini-1.5-flash',
    displayName: 'Gemini 1.5 Flash',
    description: 'Fast and efficient - best for everyday tasks',
    contextWindow: 1000000,
    maxTokens: 8192,
    speed: 'fast',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Vision', 'Code', 'Analysis'],
  },
  'gemini-1.5-pro': {
    provider: 'google',
    name: 'gemini-1.5-pro',
    displayName: 'Gemini 1.5 Pro',
    description: "Google's most capable model with 1M context",
    contextWindow: 1000000,
    maxTokens: 8192,
    speed: 'medium',
    quality: 'best',
    costTier: 'medium',
    capabilities: ['Vision', 'Code', 'Analysis', 'Reasoning'],
  },
  'gemini-2.5-flash': {
    provider: 'google',
    name: 'gemini-2.5-flash',
    displayName: 'Gemini 2.5 Flash',
    description: 'Latest Gemini with thinking capabilities',
    contextWindow: 1000000,
    maxTokens: 8192,
    speed: 'fast',
    quality: 'best',
    costTier: 'low',
    capabilities: ['Vision', 'Code', 'Analysis', 'Agents', 'Thinking'],
    isNew: true,
  },
  'gemini-pro': {
    provider: 'google',
    name: 'gemini-pro',
    displayName: 'Gemini Pro',
    description: 'Balanced performance and cost',
    contextWindow: 32000,
    maxTokens: 8192,
    speed: 'medium',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  // OpenAI models
  'gpt-4o': {
    provider: 'openai',
    name: 'gpt-4o',
    displayName: 'GPT-4o',
    description: 'Most capable OpenAI model, great for complex tasks',
    contextWindow: 128000,
    maxTokens: 4096,
    speed: 'medium',
    quality: 'best',
    costTier: 'high',
    capabilities: ['Vision', 'Code', 'Analysis', 'Creative'],
  },
  'gpt-4o-mini': {
    provider: 'openai',
    name: 'gpt-4o-mini',
    displayName: 'GPT-4o Mini',
    description: 'Fast and affordable, good for most tasks',
    contextWindow: 128000,
    maxTokens: 4096,
    speed: 'fast',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  'gpt-4-turbo': {
    provider: 'openai',
    name: 'gpt-4-turbo',
    displayName: 'GPT-4 Turbo',
    description: 'Fast GPT-4 with vision capabilities',
    contextWindow: 128000,
    maxTokens: 4096,
    speed: 'medium',
    quality: 'best',
    costTier: 'high',
    capabilities: ['Vision', 'Code', 'Analysis'],
  },
  'gpt-4': {
    provider: 'openai',
    name: 'gpt-4',
    displayName: 'GPT-4',
    description: 'Original GPT-4 - reliable and powerful',
    contextWindow: 8192,
    maxTokens: 4096,
    speed: 'slow',
    quality: 'best',
    costTier: 'high',
    capabilities: ['Code', 'Analysis', 'Creative'],
  },
  'gpt-3.5-turbo': {
    provider: 'openai',
    name: 'gpt-3.5-turbo',
    displayName: 'GPT-3.5 Turbo',
    description: 'Fast and cost-effective for simple tasks',
    contextWindow: 16385,
    maxTokens: 4096,
    speed: 'fast',
    quality: 'good',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  // Anthropic models
  'claude-3-5-sonnet-20241022': {
    provider: 'anthropic',
    name: 'claude-3-5-sonnet-20241022',
    displayName: 'Claude 3.5 Sonnet',
    description: 'Excellent at coding and analysis',
    contextWindow: 200000,
    maxTokens: 8192,
    speed: 'medium',
    quality: 'best',
    costTier: 'medium',
    capabilities: ['Code', 'Analysis', 'Writing', 'Vision'],
  },
  'claude-sonnet-4-20250514': {
    provider: 'anthropic',
    name: 'claude-sonnet-4-20250514',
    displayName: 'Claude Sonnet 4',
    description: 'Latest Claude with improved reasoning',
    contextWindow: 200000,
    maxTokens: 8192,
    speed: 'medium',
    quality: 'best',
    costTier: 'medium',
    capabilities: ['Code', 'Analysis', 'Writing', 'Vision'],
    isNew: true,
  },
  'claude-3-opus-20240229': {
    provider: 'anthropic',
    name: 'claude-3-opus-20240229',
    displayName: 'Claude 3 Opus',
    description: 'Most powerful Claude for complex reasoning',
    contextWindow: 200000,
    maxTokens: 4096,
    speed: 'slow',
    quality: 'best',
    costTier: 'high',
    capabilities: ['Code', 'Analysis', 'Writing', 'Reasoning'],
  },
  'claude-3-haiku-20240307': {
    provider: 'anthropic',
    name: 'claude-3-haiku-20240307',
    displayName: 'Claude 3 Haiku',
    description: 'Fastest Claude model, great for quick tasks',
    contextWindow: 200000,
    maxTokens: 4096,
    speed: 'fast',
    quality: 'good',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  // Groq models
  'llama-3.3-70b-versatile': {
    provider: 'groq',
    name: 'llama-3.3-70b-versatile',
    displayName: 'Llama 3.3 70B',
    description: 'Fast Llama 3.3 on Groq - great for code',
    contextWindow: 128000,
    maxTokens: 8192,
    speed: 'fast',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  'mixtral-8x7b-32768': {
    provider: 'groq',
    name: 'mixtral-8x7b-32768',
    displayName: 'Mixtral 8x7B',
    description: 'Fast Mixtral on Groq',
    contextWindow: 32768,
    maxTokens: 4096,
    speed: 'fast',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  // Ollama models (local)
  'llama3': {
    provider: 'ollama',
    name: 'llama3',
    displayName: 'Llama 3 (Local)',
    description: 'Run locally with Ollama - free and private',
    contextWindow: 8192,
    maxTokens: 4096,
    speed: 'medium',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  'llama3.2': {
    provider: 'ollama',
    name: 'llama3.2',
    displayName: 'Llama 3.2 (Local)',
    description: 'Latest Llama locally - free and private',
    contextWindow: 8192,
    maxTokens: 4096,
    speed: 'medium',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  'mistral': {
    provider: 'ollama',
    name: 'mistral',
    displayName: 'Mistral (Local)',
    description: 'Fast local model - free and private',
    contextWindow: 8192,
    maxTokens: 4096,
    speed: 'fast',
    quality: 'good',
    costTier: 'low',
    capabilities: ['Code', 'Analysis'],
  },
  'codellama': {
    provider: 'ollama',
    name: 'codellama',
    displayName: 'CodeLlama (Local)',
    description: 'Specialized for code - free and private',
    contextWindow: 16384,
    maxTokens: 4096,
    speed: 'medium',
    quality: 'great',
    costTier: 'low',
    capabilities: ['Code'],
  },
};

// Provider display order
const PROVIDER_ORDER = ['google', 'anthropic', 'openai', 'groq', 'ollama'];

const providerLogos: Record<string, typeof Sparkles> = {
  openai: Sparkles,
  anthropic: Brain,
  google: Zap,
  groq: Zap,
  ollama: Server,
};

const providerNames: Record<string, string> = {
  openai: 'OpenAI',
  anthropic: 'Anthropic',
  google: 'Google',
  groq: 'Groq',
  ollama: 'Ollama (Local)',
};

interface ModelSelectorProps {
  selectedModel: string;
  onSelectModel: (model: AIModel) => void;
  className?: string;
  compact?: boolean;
}

export function ModelSelector({
  selectedModel,
  onSelectModel,
  className,
  compact = false,
}: ModelSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [hoveredModel, setHoveredModel] = useState<string | null>(null);
  const [modelsData, setModelsData] = useState<ModelsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Fetch available models from API
  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const data = await llmApi.getModels();
        setModelsData(data);
      } catch (err) {
        console.error('Failed to fetch models:', err);
        setError('Failed to load models');
        // Set fallback data
        setModelsData({
          providers: {
            google: ['gemini-1.5-flash', 'gemini-1.5-pro'],
          },
          default_model: 'gemini-1.5-flash',
          default_provider: 'google',
        });
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, []);

  // Build available models list from API response
  const availableModels = useMemo(() => {
    if (!modelsData) return [];

    const models: AIModel[] = [];
    const defaultModel = modelsData.default_model;

    // Iterate through providers in display order
    for (const provider of PROVIDER_ORDER) {
      const providerModels = modelsData.providers[provider];
      if (!providerModels) continue;

      for (const modelName of providerModels) {
        const catalogEntry = MODEL_CATALOG[modelName];
        if (catalogEntry) {
          models.push({
            id: modelName,
            ...catalogEntry,
            isDefault: modelName === defaultModel,
            isAvailable: true,
            isNew: catalogEntry.isNew,
          });
        } else {
          // Model not in catalog - create basic entry
          models.push({
            id: modelName,
            provider,
            name: modelName,
            displayName: modelName,
            description: `${providerNames[provider] || provider} model`,
            contextWindow: 8192,
            maxTokens: 4096,
            speed: 'medium',
            quality: 'good',
            costTier: 'medium',
            capabilities: [],
            isDefault: modelName === defaultModel,
            isAvailable: true,
          });
        }
      }
    }

    return models;
  }, [modelsData]);

  // Get current model
  const currentModel = useMemo(() => {
    // Try to find selected model in available models
    let model = availableModels.find((m) => m.id === selectedModel || m.name === selectedModel);

    // If not found, try the default model
    if (!model && modelsData?.default_model) {
      model = availableModels.find((m) => m.id === modelsData.default_model || m.name === modelsData.default_model);
    }

    // If still not found, use first available
    if (!model && availableModels.length > 0) {
      model = availableModels[0];
    }

    // Fallback to catalog lookup for display
    if (!model) {
      const catalogEntry = MODEL_CATALOG[selectedModel];
      if (catalogEntry) {
        model = {
          id: selectedModel,
          ...catalogEntry,
          isAvailable: false,
        };
      }
    }

    return model;
  }, [selectedModel, availableModels, modelsData]);

  // Auto-select default model on first load
  useEffect(() => {
    if (modelsData && availableModels.length > 0) {
      const defaultModel = availableModels.find((m) => m.isDefault);
      const selectedExists = availableModels.some((m) => m.id === selectedModel || m.name === selectedModel);

      // If current selection is not available, switch to default
      if (!selectedExists && defaultModel) {
        onSelectModel(defaultModel);
      }
    }
  }, [modelsData, availableModels, selectedModel, onSelectModel]);

  const ProviderIcon = currentModel ? (providerLogos[currentModel.provider] || Sparkles) : Sparkles;

  const getSpeedLabel = (speed: string) => {
    switch (speed) {
      case 'fast':
        return '⚡ Fast';
      case 'medium':
        return '⚡⚡ Medium';
      case 'slow':
        return '⚡⚡⚡ Slower';
      default:
        return speed;
    }
  };

  const getQualityLabel = (quality: string) => {
    switch (quality) {
      case 'good':
        return '★ Good';
      case 'great':
        return '★★ Great';
      case 'best':
        return '★★★ Best';
      default:
        return quality;
    }
  };

  const formatContextWindow = (tokens: number) => {
    if (tokens >= 1000000) return `${(tokens / 1000000).toFixed(0)}M`;
    if (tokens >= 1000) return `${(tokens / 1000).toFixed(0)}K`;
    return tokens.toString();
  };

  // Group models by provider for display
  const modelsByProvider = useMemo(() => {
    const grouped: Record<string, AIModel[]> = {};
    for (const model of availableModels) {
      if (!grouped[model.provider]) {
        grouped[model.provider] = [];
      }
      grouped[model.provider].push(model);
    }
    return grouped;
  }, [availableModels]);

  if (isLoading) {
    return (
      <div className={cn('flex items-center gap-2 rounded-lg border bg-background px-3 py-2', compact ? 'h-8' : 'h-10', className)}>
        <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" aria-hidden="true" />
        <span className="text-sm text-muted-foreground">Loading models...</span>
      </div>
    );
  }

  if (error && !modelsData) {
    return (
      <div className={cn('flex items-center gap-2 rounded-lg border border-destructive/50 bg-background px-3 py-2', compact ? 'h-8' : 'h-10', className)}>
        <AlertCircle className="h-4 w-4 text-destructive" aria-hidden="true" />
        <span className="text-sm text-destructive">{error}</span>
      </div>
    );
  }

  return (
    <div className={cn('relative', className)}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        aria-label={`Model: ${currentModel?.displayName || 'Select Model'}`}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
        className={cn(
          'flex items-center gap-2 rounded-lg border bg-background px-3 py-2 text-sm font-medium transition-colors hover:bg-muted',
          compact ? 'h-8' : 'h-10'
        )}
      >
        <ProviderIcon className="h-4 w-4 text-muted-foreground" aria-hidden="true" />
        <span className="truncate">{currentModel?.displayName || 'Select Model'}</span>
        {currentModel?.isDefault && (
          <span className="text-[10px] bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1 py-0.5 rounded">
            DEFAULT
          </span>
        )}
        <ChevronDown
          className={cn(
            'h-4 w-4 text-muted-foreground transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown */}
          <div className="absolute left-0 top-full mt-2 z-50 w-96 rounded-lg border bg-popover shadow-lg">
            <div className="p-2">
              <div className="flex items-center justify-between px-2 py-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Select Model
                </p>
                {modelsData?.default_provider && (
                  <p className="text-[10px] text-muted-foreground">
                    {Object.keys(modelsData.providers).length} provider(s) available
                  </p>
                )}
              </div>

              <div className="space-y-3 max-h-96 overflow-y-auto">
                {PROVIDER_ORDER.map((provider) => {
                  const models = modelsByProvider[provider];
                  if (!models || models.length === 0) return null;

                  const ProviderLogo = providerLogos[provider] || Sparkles;

                  return (
                    <div key={provider}>
                      <div className="flex items-center gap-2 px-2 py-1 text-xs font-medium text-muted-foreground">
                        <ProviderLogo className="h-3 w-3" />
                        <span>{providerNames[provider] || provider}</span>
                        <span className="text-[10px] opacity-60">({models.length})</span>
                      </div>
                      <div className="space-y-1">
                        {models.map((model) => {
                          const ModelIcon = providerLogos[model.provider] || Sparkles;
                          const isSelected = model.id === selectedModel || model.name === selectedModel;
                          const isHovered = model.id === hoveredModel;

                          return (
                            <button
                              key={model.id}
                              onClick={() => {
                                onSelectModel(model);
                                setIsOpen(false);
                              }}
                              onMouseEnter={() => setHoveredModel(model.id)}
                              onMouseLeave={() => setHoveredModel(null)}
                              className={cn(
                                'w-full flex items-start gap-3 rounded-md px-2 py-2 text-left transition-colors',
                                isSelected
                                  ? 'bg-primary/10'
                                  : 'hover:bg-muted'
                              )}
                            >
                              <div
                                className={cn(
                                  'h-8 w-8 rounded-lg flex items-center justify-center shrink-0',
                                  isSelected ? 'bg-primary/20' : 'bg-muted'
                                )}
                              >
                                <ModelIcon
                                  className={cn(
                                    'h-4 w-4',
                                    isSelected ? 'text-primary' : 'text-muted-foreground'
                                  )}
                                />
                              </div>
                              <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2">
                                  <span className="font-medium text-sm">
                                    {model.displayName}
                                  </span>
                                  {model.isNew && (
                                    <span className="text-[10px] bg-green-100 dark:bg-green-900 text-green-700 dark:text-green-300 px-1.5 py-0.5 rounded">
                                      NEW
                                    </span>
                                  )}
                                  {model.isDefault && (
                                    <span className="text-[10px] bg-blue-100 dark:bg-blue-900 text-blue-700 dark:text-blue-300 px-1.5 py-0.5 rounded">
                                      DEFAULT
                                    </span>
                                  )}
                                </div>
                                <p className="text-xs text-muted-foreground mt-0.5 line-clamp-1">
                                  {model.description}
                                </p>
                                <div className="flex items-center gap-2 mt-1 text-[10px] text-muted-foreground">
                                  <span>{getSpeedLabel(model.speed)}</span>
                                  <span>•</span>
                                  <span>{formatContextWindow(model.contextWindow)} ctx</span>
                                </div>
                              </div>
                              {isSelected && (
                                <Check className="h-4 w-4 text-primary shrink-0" />
                              )}
                            </button>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Model Details */}
            {hoveredModel && (
              <div className="border-t p-3 bg-muted/30">
                {(() => {
                  const model = availableModels.find((m) => m.id === hoveredModel);
                  if (!model) return null;
                  return (
                    <div className="space-y-2 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Quality</span>
                        <span>{getQualityLabel(model.quality)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Speed</span>
                        <span>{getSpeedLabel(model.speed)}</span>
                      </div>
                      <div className="flex items-center justify-between">
                        <span className="text-muted-foreground">Context</span>
                        <span>{formatContextWindow(model.contextWindow)} tokens</span>
                      </div>
                      <div className="flex flex-wrap gap-1 mt-2">
                        {model.capabilities.map((cap) => (
                          <span
                            key={cap}
                            className="px-1.5 py-0.5 bg-muted rounded text-[10px]"
                          >
                            {cap}
                          </span>
                        ))}
                      </div>
                    </div>
                  );
                })()}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}

/**
 * Inline model selector for the chat input area
 */
export function ModelSelectorInline({
  selectedModel,
  onSelectModel,
}: Omit<ModelSelectorProps, 'compact' | 'className'>) {
  return (
    <ModelSelector
      selectedModel={selectedModel}
      onSelectModel={onSelectModel}
      compact
    />
  );
}

// Export the models catalog for backward compatibility
export const models = Object.entries(MODEL_CATALOG).map(([id, model]) => ({
  id,
  ...model,
  isAvailable: true,
}));
