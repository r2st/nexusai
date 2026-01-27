'use client';

import { useState } from 'react';
import { X, Bot, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';

interface CreateAgentModalProps {
  onClose: () => void;
  onCreate: (data: {
    name: string;
    description?: string;
    system_prompt?: string;
    capabilities?: string[];
    model_provider?: string;
    model_name?: string;
    temperature?: number;
    max_tokens?: number;
    is_public?: boolean;
  }) => Promise<void>;
}

const MODEL_OPTIONS = [
  { provider: 'anthropic', model: 'claude-sonnet-4-20250514', label: 'Claude Sonnet 4' },
  { provider: 'anthropic', model: 'claude-3-5-sonnet-20241022', label: 'Claude 3.5 Sonnet' },
  { provider: 'anthropic', model: 'claude-3-opus-20240229', label: 'Claude 3 Opus' },
  { provider: 'openai', model: 'gpt-4o', label: 'GPT-4o' },
  { provider: 'openai', model: 'gpt-4-turbo', label: 'GPT-4 Turbo' },
  { provider: 'google', model: 'gemini-1.5-pro', label: 'Gemini 1.5 Pro' },
];

const CAPABILITY_OPTIONS = [
  'chat',
  'code_generation',
  'code_review',
  'document_analysis',
  'data_analysis',
  'web_search',
  'tool_use',
  'mcp_integration',
];

export function CreateAgentModal({ onClose, onCreate }: CreateAgentModalProps) {
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [formData, setFormData] = useState({
    name: '',
    description: '',
    system_prompt: '',
    selectedModel: MODEL_OPTIONS[0],
    temperature: 0.7,
    max_tokens: 4096,
    capabilities: [] as string[],
    is_public: false,
  });

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setIsSubmitting(true);

    try {
      await onCreate({
        name: formData.name,
        description: formData.description || undefined,
        system_prompt: formData.system_prompt || undefined,
        capabilities: formData.capabilities.length > 0 ? formData.capabilities : undefined,
        model_provider: formData.selectedModel.provider,
        model_name: formData.selectedModel.model,
        temperature: formData.temperature,
        max_tokens: formData.max_tokens,
        is_public: formData.is_public,
      });
    } catch (err) {
      setError('Failed to create agent. Please try again.');
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleCapability = (cap: string) => {
    setFormData((prev) => ({
      ...prev,
      capabilities: prev.capabilities.includes(cap)
        ? prev.capabilities.filter((c) => c !== cap)
        : [...prev.capabilities, cap],
    }));
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50"
        onClick={onClose}
      />

      {/* Modal */}
      <div className="relative z-10 w-full max-w-2xl max-h-[90vh] overflow-auto rounded-lg bg-background p-6 shadow-lg">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
              <Bot className="h-5 w-5 text-primary" />
            </div>
            <h2 className="text-xl font-semibold">Create New Agent</h2>
          </div>
          <Button variant="ghost" size="icon" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        {/* Form */}
        <form onSubmit={handleSubmit} className="space-y-6">
          {/* Name */}
          <div>
            <label className="text-sm font-medium">Agent Name *</label>
            <Input
              value={formData.name}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, name: e.target.value }))
              }
              placeholder="My Custom Agent"
              className="mt-1"
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="text-sm font-medium">Description</label>
            <Textarea
              value={formData.description}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, description: e.target.value }))
              }
              placeholder="What does this agent do?"
              className="mt-1"
              rows={2}
            />
          </div>

          {/* System Prompt */}
          <div>
            <label className="text-sm font-medium">System Prompt</label>
            <Textarea
              value={formData.system_prompt}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, system_prompt: e.target.value }))
              }
              placeholder="You are a helpful assistant that..."
              className="mt-1 font-mono text-sm"
              rows={4}
            />
          </div>

          {/* Model Selection */}
          <div>
            <label className="text-sm font-medium">Model</label>
            <select
              value={`${formData.selectedModel.provider}:${formData.selectedModel.model}`}
              onChange={(e) => {
                const [provider, model] = e.target.value.split(':');
                const selected = MODEL_OPTIONS.find(
                  (m) => m.provider === provider && m.model === model
                );
                if (selected) {
                  setFormData((prev) => ({ ...prev, selectedModel: selected }));
                }
              }}
              className="mt-1 w-full rounded-md border bg-background px-3 py-2"
            >
              {MODEL_OPTIONS.map((opt) => (
                <option key={`${opt.provider}:${opt.model}`} value={`${opt.provider}:${opt.model}`}>
                  {opt.label} ({opt.provider})
                </option>
              ))}
            </select>
          </div>

          {/* Temperature & Max Tokens */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="text-sm font-medium">
                Temperature: {formData.temperature}
              </label>
              <input
                type="range"
                min="0"
                max="2"
                step="0.1"
                value={formData.temperature}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    temperature: parseFloat(e.target.value),
                  }))
                }
                className="mt-2 w-full"
              />
            </div>
            <div>
              <label className="text-sm font-medium">Max Tokens</label>
              <Input
                type="number"
                value={formData.max_tokens}
                onChange={(e) =>
                  setFormData((prev) => ({
                    ...prev,
                    max_tokens: parseInt(e.target.value) || 4096,
                  }))
                }
                min={1}
                max={128000}
                className="mt-1"
              />
            </div>
          </div>

          {/* Capabilities */}
          <div>
            <label className="text-sm font-medium">Capabilities</label>
            <div className="mt-2 flex flex-wrap gap-2">
              {CAPABILITY_OPTIONS.map((cap) => (
                <button
                  key={cap}
                  type="button"
                  onClick={() => toggleCapability(cap)}
                  className={`px-3 py-1 rounded-full text-sm transition-colors ${
                    formData.capabilities.includes(cap)
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted text-muted-foreground hover:bg-muted/80'
                  }`}
                >
                  {cap.replace('_', ' ')}
                </button>
              ))}
            </div>
          </div>

          {/* Public Toggle */}
          <div className="flex items-center gap-2">
            <input
              type="checkbox"
              id="is_public"
              checked={formData.is_public}
              onChange={(e) =>
                setFormData((prev) => ({ ...prev, is_public: e.target.checked }))
              }
              className="rounded border-gray-300"
            />
            <label htmlFor="is_public" className="text-sm">
              Make this agent public (visible to all users)
            </label>
          </div>

          {/* Error */}
          {error && (
            <div className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}

          {/* Actions */}
          <div className="flex justify-end gap-3">
            <Button type="button" variant="outline" onClick={onClose}>
              Cancel
            </Button>
            <Button type="submit" disabled={isSubmitting || !formData.name}>
              {isSubmitting ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Creating...
                </>
              ) : (
                'Create Agent'
              )}
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
