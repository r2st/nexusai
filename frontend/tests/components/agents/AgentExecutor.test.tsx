/**
 * AgentExecutor Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import React from 'react';

// Mock types
interface AgentStep {
  id: string;
  type: 'thought' | 'action' | 'observation' | 'result';
  content: string;
  timestamp: string;
}

interface AgentExecutorProps {
  agentId: string;
  agentName: string;
  isRunning?: boolean;
  steps?: AgentStep[];
  onStart?: (input: string) => Promise<void>;
  onStop?: () => void;
  onClear?: () => void;
}

const mockSteps: AgentStep[] = [
  { id: '1', type: 'thought', content: 'Analyzing the request...', timestamp: '10:00:00' },
  { id: '2', type: 'action', content: 'Searching codebase for relevant files', timestamp: '10:00:01' },
  { id: '3', type: 'observation', content: 'Found 5 matching files', timestamp: '10:00:02' },
  { id: '4', type: 'result', content: 'Analysis complete. Here are the findings...', timestamp: '10:00:03' },
];

// Mock AgentExecutor component
const AgentExecutor = ({
  agentId,
  agentName,
  isRunning = false,
  steps = [],
  onStart,
  onStop,
  onClear,
}: AgentExecutorProps) => {
  const [input, setInput] = React.useState('');
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || !onStart) return;
    
    setIsSubmitting(true);
    try {
      await onStart(input);
    } finally {
      setIsSubmitting(false);
      setInput('');
    }
  };

  const getStepIcon = (type: string) => {
    switch (type) {
      case 'thought': return '💭';
      case 'action': return '⚡';
      case 'observation': return '👁';
      case 'result': return '✅';
      default: return '•';
    }
  };

  return (
    <div data-testid="agent-executor" className="agent-executor">
      <header>
        <h2 data-testid="agent-name">{agentName}</h2>
        <span data-testid="agent-id">ID: {agentId}</span>
        {isRunning && <span data-testid="running-indicator" className="running">Running</span>}
      </header>

      <form onSubmit={handleSubmit} data-testid="input-form">
        <textarea
          data-testid="agent-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Enter your request for the agent..."
          disabled={isRunning || isSubmitting}
        />
        <div className="form-actions">
          <button
            type="submit"
            data-testid="start-button"
            disabled={!input.trim() || isRunning || isSubmitting}
          >
            {isSubmitting ? 'Starting...' : 'Start Agent'}
          </button>
          {isRunning && (
            <button type="button" data-testid="stop-button" onClick={onStop}>
              Stop
            </button>
          )}
          <button type="button" data-testid="clear-button" onClick={onClear} disabled={steps.length === 0}>
            Clear
          </button>
        </div>
      </form>

      <div data-testid="execution-log" className="execution-log">
        {steps.length === 0 ? (
          <p data-testid="empty-log">No execution steps yet. Start the agent to see progress.</p>
        ) : (
          steps.map((step) => (
            <div key={step.id} data-testid={`step-${step.id}`} className={`step ${step.type}`}>
              <span className="icon">{getStepIcon(step.type)}</span>
              <span data-testid={`step-type-${step.id}`} className="type">{step.type}</span>
              <span className="timestamp">{step.timestamp}</span>
              <p className="content">{step.content}</p>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

describe('AgentExecutor', () => {
  const defaultProps = {
    agentId: 'agent-1',
    agentName: 'Code Analyzer',
  };

  it('renders agent executor', () => {
    render(<AgentExecutor {...defaultProps} />);
    expect(screen.getByTestId('agent-executor')).toBeInTheDocument();
  });

  it('displays agent name', () => {
    render(<AgentExecutor {...defaultProps} />);
    expect(screen.getByTestId('agent-name')).toHaveTextContent('Code Analyzer');
  });

  it('displays agent ID', () => {
    render(<AgentExecutor {...defaultProps} />);
    expect(screen.getByTestId('agent-id')).toHaveTextContent('ID: agent-1');
  });

  it('shows running indicator when running', () => {
    render(<AgentExecutor {...defaultProps} isRunning={true} />);
    expect(screen.getByTestId('running-indicator')).toBeInTheDocument();
  });

  it('hides running indicator when not running', () => {
    render(<AgentExecutor {...defaultProps} isRunning={false} />);
    expect(screen.queryByTestId('running-indicator')).not.toBeInTheDocument();
  });

  it('renders input form', () => {
    render(<AgentExecutor {...defaultProps} />);
    expect(screen.getByTestId('input-form')).toBeInTheDocument();
    expect(screen.getByTestId('agent-input')).toBeInTheDocument();
  });

  it('updates input value on change', () => {
    render(<AgentExecutor {...defaultProps} />);
    const input = screen.getByTestId('agent-input');
    
    fireEvent.change(input, { target: { value: 'Analyze this code' } });
    
    expect(input).toHaveValue('Analyze this code');
  });

  it('disables input when running', () => {
    render(<AgentExecutor {...defaultProps} isRunning={true} />);
    expect(screen.getByTestId('agent-input')).toBeDisabled();
  });

  it('disables start button when input is empty', () => {
    render(<AgentExecutor {...defaultProps} />);
    expect(screen.getByTestId('start-button')).toBeDisabled();
  });

  it('enables start button when input has value', () => {
    render(<AgentExecutor {...defaultProps} />);
    fireEvent.change(screen.getByTestId('agent-input'), { target: { value: 'test' } });
    expect(screen.getByTestId('start-button')).not.toBeDisabled();
  });

  it('calls onStart when form is submitted', async () => {
    const onStart = vi.fn().mockResolvedValue(undefined);
    render(<AgentExecutor {...defaultProps} onStart={onStart} />);
    
    fireEvent.change(screen.getByTestId('agent-input'), { target: { value: 'test input' } });
    fireEvent.submit(screen.getByTestId('input-form'));
    
    await waitFor(() => {
      expect(onStart).toHaveBeenCalledWith('test input');
    });
  });

  it('shows stop button when running', () => {
    render(<AgentExecutor {...defaultProps} isRunning={true} />);
    expect(screen.getByTestId('stop-button')).toBeInTheDocument();
  });

  it('hides stop button when not running', () => {
    render(<AgentExecutor {...defaultProps} isRunning={false} />);
    expect(screen.queryByTestId('stop-button')).not.toBeInTheDocument();
  });

  it('calls onStop when stop button is clicked', () => {
    const onStop = vi.fn();
    render(<AgentExecutor {...defaultProps} isRunning={true} onStop={onStop} />);
    
    fireEvent.click(screen.getByTestId('stop-button'));
    
    expect(onStop).toHaveBeenCalled();
  });

  it('calls onClear when clear button is clicked', () => {
    const onClear = vi.fn();
    render(<AgentExecutor {...defaultProps} steps={mockSteps} onClear={onClear} />);
    
    fireEvent.click(screen.getByTestId('clear-button'));
    
    expect(onClear).toHaveBeenCalled();
  });

  it('disables clear button when no steps', () => {
    render(<AgentExecutor {...defaultProps} steps={[]} />);
    expect(screen.getByTestId('clear-button')).toBeDisabled();
  });

  it('shows empty log message when no steps', () => {
    render(<AgentExecutor {...defaultProps} steps={[]} />);
    expect(screen.getByTestId('empty-log')).toBeInTheDocument();
  });

  it('renders execution steps', () => {
    render(<AgentExecutor {...defaultProps} steps={mockSteps} />);
    expect(screen.getByTestId('step-1')).toBeInTheDocument();
    expect(screen.getByTestId('step-2')).toBeInTheDocument();
    expect(screen.getByTestId('step-3')).toBeInTheDocument();
    expect(screen.getByTestId('step-4')).toBeInTheDocument();
  });

  it('displays step type', () => {
    render(<AgentExecutor {...defaultProps} steps={mockSteps} />);
    expect(screen.getByTestId('step-type-1')).toHaveTextContent('thought');
    expect(screen.getByTestId('step-type-2')).toHaveTextContent('action');
  });

  it('displays step content', () => {
    render(<AgentExecutor {...defaultProps} steps={mockSteps} />);
    expect(screen.getByText('Analyzing the request...')).toBeInTheDocument();
  });
});
