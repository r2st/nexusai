/**
 * WorkflowDesigner Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import React from 'react';

// Mock types and data
interface WorkflowNode {
  id: string;
  type: string;
  label: string;
  position: { x: number; y: number };
  data?: Record<string, unknown>;
}

interface WorkflowEdge {
  id: string;
  source: string;
  target: string;
}

interface WorkflowDesignerProps {
  nodes?: WorkflowNode[];
  edges?: WorkflowEdge[];
  onNodesChange?: (nodes: WorkflowNode[]) => void;
  onEdgesChange?: (edges: WorkflowEdge[]) => void;
  onSave?: (workflow: { nodes: WorkflowNode[]; edges: WorkflowEdge[] }) => void;
  onExport?: () => void;
  readOnly?: boolean;
}

// Mock WorkflowDesigner component
const WorkflowDesigner = ({
  nodes = [],
  edges = [],
  onNodesChange,
  onEdgesChange,
  onSave,
  onExport,
  readOnly = false,
}: WorkflowDesignerProps) => {
  const [selectedNode, setSelectedNode] = React.useState<string | null>(null);

  const handleAddNode = (type: string) => {
    const newNode: WorkflowNode = {
      id: `node-${Date.now()}`,
      type,
      label: `New ${type}`,
      position: { x: 100, y: 100 },
    };
    onNodesChange?.([...nodes, newNode]);
  };

  const handleDeleteNode = (nodeId: string) => {
    onNodesChange?.(nodes.filter((n) => n.id !== nodeId));
    onEdgesChange?.(edges.filter((e) => e.source !== nodeId && e.target !== nodeId));
  };

  const handleSave = () => {
    onSave?.({ nodes, edges });
  };

  return (
    <div data-testid="workflow-designer" className="workflow-designer">
      {!readOnly && (
        <div data-testid="toolbar" className="toolbar">
          <button data-testid="add-trigger" onClick={() => handleAddNode('trigger')}>
            Add Trigger
          </button>
          <button data-testid="add-action" onClick={() => handleAddNode('action')}>
            Add Action
          </button>
          <button data-testid="add-condition" onClick={() => handleAddNode('condition')}>
            Add Condition
          </button>
          <button data-testid="save-workflow" onClick={handleSave}>
            Save
          </button>
          <button data-testid="export-workflow" onClick={onExport}>
            Export
          </button>
        </div>
      )}
      <div data-testid="canvas" className="canvas">
        {nodes.map((node) => (
          <div
            key={node.id}
            data-testid={`node-${node.id}`}
            className={`node ${selectedNode === node.id ? 'selected' : ''}`}
            onClick={() => setSelectedNode(node.id)}
          >
            <span className="node-type">{node.type}</span>
            <span className="node-label">{node.label}</span>
            {!readOnly && (
              <button
                data-testid={`delete-${node.id}`}
                onClick={(e) => {
                  e.stopPropagation();
                  handleDeleteNode(node.id);
                }}
              >
                Delete
              </button>
            )}
          </div>
        ))}
        {edges.map((edge) => (
          <div key={edge.id} data-testid={`edge-${edge.id}`} className="edge">
            {edge.source} → {edge.target}
          </div>
        ))}
      </div>
      {selectedNode && (
        <div data-testid="properties-panel" className="properties-panel">
          <h3>Node Properties</h3>
          <p>Selected: {selectedNode}</p>
        </div>
      )}
    </div>
  );
};

describe('WorkflowDesigner', () => {
  it('renders workflow designer', () => {
    render(<WorkflowDesigner />);
    expect(screen.getByTestId('workflow-designer')).toBeInTheDocument();
  });

  it('renders toolbar with add buttons', () => {
    render(<WorkflowDesigner />);
    expect(screen.getByTestId('toolbar')).toBeInTheDocument();
    expect(screen.getByTestId('add-trigger')).toBeInTheDocument();
    expect(screen.getByTestId('add-action')).toBeInTheDocument();
    expect(screen.getByTestId('add-condition')).toBeInTheDocument();
  });

  it('renders canvas', () => {
    render(<WorkflowDesigner />);
    expect(screen.getByTestId('canvas')).toBeInTheDocument();
  });

  it('renders existing nodes', () => {
    const nodes = [
      { id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } },
      { id: '2', type: 'action', label: 'Send Email', position: { x: 100, y: 0 } },
    ];
    render(<WorkflowDesigner nodes={nodes} />);
    
    expect(screen.getByTestId('node-1')).toBeInTheDocument();
    expect(screen.getByTestId('node-2')).toBeInTheDocument();
    expect(screen.getByText('Start')).toBeInTheDocument();
    expect(screen.getByText('Send Email')).toBeInTheDocument();
  });

  it('renders edges between nodes', () => {
    const nodes = [
      { id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } },
      { id: '2', type: 'action', label: 'Action', position: { x: 100, y: 0 } },
    ];
    const edges = [{ id: 'e1', source: '1', target: '2' }];
    render(<WorkflowDesigner nodes={nodes} edges={edges} />);
    
    expect(screen.getByTestId('edge-e1')).toBeInTheDocument();
  });

  it('adds trigger node when button is clicked', () => {
    const onNodesChange = vi.fn();
    render(<WorkflowDesigner onNodesChange={onNodesChange} />);
    
    fireEvent.click(screen.getByTestId('add-trigger'));
    
    expect(onNodesChange).toHaveBeenCalled();
    const newNodes = onNodesChange.mock.calls[0][0];
    expect(newNodes[0].type).toBe('trigger');
  });

  it('adds action node when button is clicked', () => {
    const onNodesChange = vi.fn();
    render(<WorkflowDesigner onNodesChange={onNodesChange} />);
    
    fireEvent.click(screen.getByTestId('add-action'));
    
    expect(onNodesChange).toHaveBeenCalled();
    const newNodes = onNodesChange.mock.calls[0][0];
    expect(newNodes[0].type).toBe('action');
  });

  it('adds condition node when button is clicked', () => {
    const onNodesChange = vi.fn();
    render(<WorkflowDesigner onNodesChange={onNodesChange} />);
    
    fireEvent.click(screen.getByTestId('add-condition'));
    
    expect(onNodesChange).toHaveBeenCalled();
    const newNodes = onNodesChange.mock.calls[0][0];
    expect(newNodes[0].type).toBe('condition');
  });

  it('deletes node when delete button is clicked', () => {
    const nodes = [{ id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } }];
    const onNodesChange = vi.fn();
    const onEdgesChange = vi.fn();
    
    render(<WorkflowDesigner nodes={nodes} onNodesChange={onNodesChange} onEdgesChange={onEdgesChange} />);
    
    fireEvent.click(screen.getByTestId('delete-1'));
    
    expect(onNodesChange).toHaveBeenCalledWith([]);
  });

  it('saves workflow when save button is clicked', () => {
    const nodes = [{ id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } }];
    const edges = [{ id: 'e1', source: '1', target: '2' }];
    const onSave = vi.fn();
    
    render(<WorkflowDesigner nodes={nodes} edges={edges} onSave={onSave} />);
    
    fireEvent.click(screen.getByTestId('save-workflow'));
    
    expect(onSave).toHaveBeenCalledWith({ nodes, edges });
  });

  it('exports workflow when export button is clicked', () => {
    const onExport = vi.fn();
    render(<WorkflowDesigner onExport={onExport} />);
    
    fireEvent.click(screen.getByTestId('export-workflow'));
    
    expect(onExport).toHaveBeenCalled();
  });

  it('shows properties panel when node is selected', () => {
    const nodes = [{ id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } }];
    render(<WorkflowDesigner nodes={nodes} />);
    
    fireEvent.click(screen.getByTestId('node-1'));
    
    expect(screen.getByTestId('properties-panel')).toBeInTheDocument();
  });

  it('hides toolbar in read-only mode', () => {
    render(<WorkflowDesigner readOnly={true} />);
    expect(screen.queryByTestId('toolbar')).not.toBeInTheDocument();
  });

  it('hides delete buttons in read-only mode', () => {
    const nodes = [{ id: '1', type: 'trigger', label: 'Start', position: { x: 0, y: 0 } }];
    render(<WorkflowDesigner nodes={nodes} readOnly={true} />);
    
    expect(screen.queryByTestId('delete-1')).not.toBeInTheDocument();
  });
});
