/**
 * CreateAgentModal Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface AgentConfig {
  name: string;
  description: string;
  model: string;
  tools: string[];
  systemPrompt: string;
}

interface CreateAgentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onCreate: (config: AgentConfig) => Promise<void>;
  availableTools?: string[];
  availableModels?: string[];
}

const mockTools = ['code_search', 'file_reader', 'code_executor', 'web_search', 'jira_tools'];
const mockModels = ['gpt-4', 'claude-3', 'gemini-pro'];

// Mock CreateAgentModal component
const CreateAgentModal = ({
  isOpen,
  onClose,
  onCreate,
  availableTools = mockTools,
  availableModels = mockModels,
}: CreateAgentModalProps) => {
  const [config, setConfig] = React.useState<AgentConfig>({
    name: '',
    description: '',
    model: mockModels[0],
    tools: [],
    systemPrompt: '',
  });
  const [isSubmitting, setIsSubmitting] = React.useState(false);
  const [errors, setErrors] = React.useState<Record<string, string>>({});

  const validate = (): boolean => {
    const newErrors: Record<string, string> = {};
    if (!config.name.trim()) newErrors.name = 'Name is required';
    if (config.name.length > 50) newErrors.name = 'Name must be less than 50 characters';
    if (!config.description.trim()) newErrors.description = 'Description is required';
    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validate()) return;
    
    setIsSubmitting(true);
    try {
      await onCreate(config);
      onClose();
    } finally {
      setIsSubmitting(false);
    }
  };

  const toggleTool = (tool: string) => {
    setConfig((prev) => ({
      ...prev,
      tools: prev.tools.includes(tool)
        ? prev.tools.filter((t) => t !== tool)
        : [...prev.tools, tool],
    }));
  };

  if (!isOpen) return null;

  return (
    <div data-testid="create-agent-modal" className="modal-overlay">
      <div className="modal-content" role="dialog" aria-labelledby="modal-title">
        <header>
          <h2 id="modal-title">Create New Agent</h2>
          <button data-testid="close-modal" onClick={onClose} aria-label="Close">×</button>
        </header>
        
        <form onSubmit={handleSubmit} data-testid="agent-form">
          <div className="form-group">
            <label htmlFor="agent-name">Name</label>
            <input
              id="agent-name"
              data-testid="name-input"
              type="text"
              value={config.name}
              onChange={(e) => setConfig((prev) => ({ ...prev, name: e.target.value }))}
              placeholder="Enter agent name"
            />
            {errors.name && <span data-testid="name-error" className="error">{errors.name}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="agent-description">Description</label>
            <textarea
              id="agent-description"
              data-testid="description-input"
              value={config.description}
              onChange={(e) => setConfig((prev) => ({ ...prev, description: e.target.value }))}
              placeholder="Describe what this agent does"
            />
            {errors.description && <span data-testid="description-error" className="error">{errors.description}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="agent-model">Model</label>
            <select
              id="agent-model"
              data-testid="model-select"
              value={config.model}
              onChange={(e) => setConfig((prev) => ({ ...prev, model: e.target.value }))}
            >
              {availableModels.map((model) => (
                <option key={model} value={model}>{model}</option>
              ))}
            </select>
          </div>

          <div className="form-group">
            <label>Tools</label>
            <div data-testid="tools-list" className="tools-list">
              {availableTools.map((tool) => (
                <label key={tool} className="tool-checkbox">
                  <input
                    type="checkbox"
                    data-testid={`tool-${tool}`}
                    checked={config.tools.includes(tool)}
                    onChange={() => toggleTool(tool)}
                  />
                  {tool}
                </label>
              ))}
            </div>
          </div>

          <div className="form-group">
            <label htmlFor="system-prompt">System Prompt</label>
            <textarea
              id="system-prompt"
              data-testid="prompt-input"
              value={config.systemPrompt}
              onChange={(e) => setConfig((prev) => ({ ...prev, systemPrompt: e.target.value }))}
              placeholder="Enter system prompt (optional)"
              rows={4}
            />
          </div>

          <footer className="modal-footer">
            <button type="button" data-testid="cancel-button" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" data-testid="create-button" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Agent'}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
};

describe('CreateAgentModal', () => {
  const defaultProps = {
    isOpen: true,
    onClose: vi.fn(),
    onCreate: vi.fn().mockResolvedValue(undefined),
  };

  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders modal when open', () => {
    render(<CreateAgentModal {...defaultProps} />);
    expect(screen.getByTestId('create-agent-modal')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<CreateAgentModal {...defaultProps} isOpen={false} />);
    expect(screen.queryByTestId('create-agent-modal')).not.toBeInTheDocument();
  });

  it('renders form elements', () => {
    render(<CreateAgentModal {...defaultProps} />);
    expect(screen.getByTestId('name-input')).toBeInTheDocument();
    expect(screen.getByTestId('description-input')).toBeInTheDocument();
    expect(screen.getByTestId('model-select')).toBeInTheDocument();
    expect(screen.getByTestId('tools-list')).toBeInTheDocument();
    expect(screen.getByTestId('prompt-input')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId('close-modal'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('calls onClose when cancel button is clicked', () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.click(screen.getByTestId('cancel-button'));
    expect(defaultProps.onClose).toHaveBeenCalled();
  });

  it('updates name input', () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'Test Agent' } });
    expect(screen.getByTestId('name-input')).toHaveValue('Test Agent');
  });

  it('updates description input', () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId('description-input'), { target: { value: 'Test description' } });
    expect(screen.getByTestId('description-input')).toHaveValue('Test description');
  });

  it('renders available models in select', () => {
    render(<CreateAgentModal {...defaultProps} availableModels={mockModels} />);
    const select = screen.getByTestId('model-select');
    expect(select.querySelectorAll('option')).toHaveLength(3);
  });

  it('updates model selection', () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId('model-select'), { target: { value: 'claude-3' } });
    expect(screen.getByTestId('model-select')).toHaveValue('claude-3');
  });

  it('renders tool checkboxes', () => {
    render(<CreateAgentModal {...defaultProps} availableTools={mockTools} />);
    mockTools.forEach((tool) => {
      expect(screen.getByTestId(`tool-${tool}`)).toBeInTheDocument();
    });
  });

  it('toggles tool selection', () => {
    render(<CreateAgentModal {...defaultProps} />);
    const toolCheckbox = screen.getByTestId('tool-code_search');
    
    expect(toolCheckbox).not.toBeChecked();
    fireEvent.click(toolCheckbox);
    expect(toolCheckbox).toBeChecked();
    fireEvent.click(toolCheckbox);
    expect(toolCheckbox).not.toBeChecked();
  });

  it('shows validation error for empty name', async () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId('description-input'), { target: { value: 'Test' } });
    fireEvent.submit(screen.getByTestId('agent-form'));
    
    await waitFor(() => {
      expect(screen.getByTestId('name-error')).toHaveTextContent('Name is required');
    });
  });

  it('shows validation error for empty description', async () => {
    render(<CreateAgentModal {...defaultProps} />);
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'Test' } });
    fireEvent.submit(screen.getByTestId('agent-form'));
    
    await waitFor(() => {
      expect(screen.getByTestId('description-error')).toHaveTextContent('Description is required');
    });
  });

  it('calls onCreate with config when form is valid', async () => {
    render(<CreateAgentModal {...defaultProps} />);
    
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'My Agent' } });
    fireEvent.change(screen.getByTestId('description-input'), { target: { value: 'Does stuff' } });
    fireEvent.click(screen.getByTestId('tool-code_search'));
    fireEvent.submit(screen.getByTestId('agent-form'));
    
    await waitFor(() => {
      expect(defaultProps.onCreate).toHaveBeenCalledWith({
        name: 'My Agent',
        description: 'Does stuff',
        model: 'gpt-4',
        tools: ['code_search'],
        systemPrompt: '',
      });
    });
  });

  it('disables create button while submitting', async () => {
    const onCreate = vi.fn().mockImplementation(
      () => new Promise((resolve) => setTimeout(resolve, 100))
    );
    render(<CreateAgentModal {...defaultProps} onCreate={onCreate} />);
    
    fireEvent.change(screen.getByTestId('name-input'), { target: { value: 'Test' } });
    fireEvent.change(screen.getByTestId('description-input'), { target: { value: 'Test' } });
    fireEvent.submit(screen.getByTestId('agent-form'));
    
    expect(screen.getByTestId('create-button')).toBeDisabled();
    expect(screen.getByTestId('create-button')).toHaveTextContent('Creating...');
  });
});
