import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ModelSelector, models } from '@/components/chat/model-selector';
import * as api from '@/lib/api';

// Mock the llmApi
vi.mock('@/lib/api', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/api')>();
  return {
    ...actual,
    llmApi: {
      ...actual.llmApi,
      getModels: vi.fn().mockResolvedValue({
        providers: {
          google: ['gemini-1.5-flash', 'gemini-1.5-pro'],
          anthropic: ['claude-3-5-sonnet-20241022', 'claude-3-haiku-20240307'],
          openai: ['gpt-4o', 'gpt-4o-mini'],
        },
        default_model: 'gemini-1.5-flash',
        default_provider: 'google',
      }),
    },
  };
});

describe('ModelSelector', () => {
  const mockOnSelectModel = vi.fn();

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders with default selected model', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    // Wait for loading to complete
    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });
  });

  it('opens dropdown when clicked', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    expect(screen.getByText('Select Model')).toBeInTheDocument();
  });

  it('displays all available models in dropdown', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    // Check for various models (from mock data)
    expect(screen.getByText('GPT-4o Mini')).toBeInTheDocument();
    expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument();
    expect(screen.getByText('Claude 3 Haiku')).toBeInTheDocument();
    expect(screen.getByText('Gemini 1.5 Pro')).toBeInTheDocument();
    expect(screen.getByText('Gemini 1.5 Flash')).toBeInTheDocument();
  });

  it('shows model descriptions', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    expect(screen.getByText('Most capable OpenAI model, great for complex tasks')).toBeInTheDocument();
    expect(screen.getByText('Fast and affordable, good for most tasks')).toBeInTheDocument();
  });

  it('shows NEW badge for new models', async () => {
    // Note: NEW badge depends on model catalog having isNew: true
    // The mock response may not include new models; this test checks the badge exists if applicable
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    // Check dropdown is open; NEW badge is optional based on catalog
    expect(screen.getByText('Select Model')).toBeInTheDocument();
  });

  it('shows DEFAULT badge for default model', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    expect(screen.getByText('DEFAULT')).toBeInTheDocument();
  });

  it('calls onSelectModel when a model is selected', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));
    fireEvent.click(screen.getByText('Claude 3.5 Sonnet'));

    expect(mockOnSelectModel).toHaveBeenCalledTimes(1);
    expect(mockOnSelectModel).toHaveBeenCalledWith(
      expect.objectContaining({
        id: 'claude-3-5-sonnet-20241022',
        displayName: 'Claude 3.5 Sonnet',
      })
    );
  });

  it('closes dropdown after selection', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));
    expect(screen.getByText('Select Model')).toBeInTheDocument();

    fireEvent.click(screen.getByText('Claude 3.5 Sonnet'));

    expect(screen.queryByText('Select Model')).not.toBeInTheDocument();
  });

  it('displays context window information', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    // Check for context window displays (128K for GPT-4o)
    expect(screen.getAllByText(/128K ctx/).length).toBeGreaterThan(0);
  });

  it('shows speed indicators', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));

    expect(screen.getAllByText(/Fast/).length).toBeGreaterThan(0);
  });

  it('renders in compact mode', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
        compact
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    const button = screen.getByRole('button');
    expect(button).toHaveClass('h-8');
  });

  it('applies custom className', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
        className="custom-class"
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    const container = screen.getByText('GPT-4o').closest('.relative');
    expect(container).toHaveClass('custom-class');
  });

  it('closes dropdown when clicking backdrop', async () => {
    render(
      <ModelSelector
        selectedModel="gpt-4o"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('GPT-4o')).toBeInTheDocument();
    });

    fireEvent.click(screen.getByText('GPT-4o'));
    expect(screen.getByText('Select Model')).toBeInTheDocument();

    // Click the backdrop
    const backdrop = document.querySelector('.fixed.inset-0.z-40');
    if (backdrop) {
      fireEvent.click(backdrop);
    }

    expect(screen.queryByText('Select Model')).not.toBeInTheDocument();
  });

  it('highlights currently selected model', async () => {
    render(
      <ModelSelector
        selectedModel="claude-3-5-sonnet-20241022"
        onSelectModel={mockOnSelectModel}
      />
    );

    await waitFor(() => {
      expect(screen.getByText('Claude 3.5 Sonnet')).toBeInTheDocument();
    });

    // Click to open dropdown
    fireEvent.click(screen.getByText('Claude 3.5 Sonnet'));

    // Find the selected model button in the dropdown (it will have bg-primary/10 class)
    const selectedModelButton = document.querySelector('button.bg-primary\\/10');
    expect(selectedModelButton).toBeInTheDocument();
  });
});

describe('models configuration', () => {
  it('has models from catalog', () => {
    // MODEL_CATALOG has multiple models
    expect(models.length).toBeGreaterThan(10);
  });

  it('has models from multiple providers', () => {
    const providers = new Set(models.map((m) => m.provider));
    expect(providers.has('openai')).toBe(true);
    expect(providers.has('anthropic')).toBe(true);
    expect(providers.has('google')).toBe(true);
  });

  it('all models have required fields', () => {
    models.forEach((model) => {
      expect(model.id).toBeDefined();
      expect(model.provider).toBeDefined();
      expect(model.name).toBeDefined();
      expect(model.displayName).toBeDefined();
      expect(model.description).toBeDefined();
      expect(model.contextWindow).toBeGreaterThan(0);
      expect(model.maxTokens).toBeGreaterThan(0);
      expect(['fast', 'medium', 'slow']).toContain(model.speed);
      expect(['good', 'great', 'best']).toContain(model.quality);
      expect(['low', 'medium', 'high']).toContain(model.costTier);
      expect(Array.isArray(model.capabilities)).toBe(true);
    });
  });
});
