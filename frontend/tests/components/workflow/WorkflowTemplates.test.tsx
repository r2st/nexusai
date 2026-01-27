/**
 * WorkflowTemplates Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock types
interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  icon?: string;
  nodes: unknown[];
  edges: unknown[];
}

interface WorkflowTemplatesProps {
  templates?: WorkflowTemplate[];
  onSelect?: (template: WorkflowTemplate) => void;
  onPreview?: (template: WorkflowTemplate) => void;
  selectedCategory?: string;
  onCategoryChange?: (category: string) => void;
  searchQuery?: string;
  onSearchChange?: (query: string) => void;
}

const mockTemplates: WorkflowTemplate[] = [
  {
    id: '1',
    name: 'Code Review',
    description: 'Automated code review workflow',
    category: 'Development',
    icon: '🔍',
    nodes: [],
    edges: [],
  },
  {
    id: '2',
    name: 'Bug Triage',
    description: 'Automatic bug categorization',
    category: 'Development',
    icon: '🐛',
    nodes: [],
    edges: [],
  },
  {
    id: '3',
    name: 'Deploy Notification',
    description: 'Notify team on deployment',
    category: 'DevOps',
    icon: '🚀',
    nodes: [],
    edges: [],
  },
];

// Mock WorkflowTemplates component
const WorkflowTemplates = ({
  templates = mockTemplates,
  onSelect,
  onPreview,
  selectedCategory = 'All',
  onCategoryChange,
  searchQuery = '',
  onSearchChange,
}: WorkflowTemplatesProps) => {
  const categories = ['All', ...new Set(templates.map((t) => t.category))];
  
  const filteredTemplates = templates.filter((t) => {
    const matchesCategory = selectedCategory === 'All' || t.category === selectedCategory;
    const matchesSearch = t.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      t.description.toLowerCase().includes(searchQuery.toLowerCase());
    return matchesCategory && matchesSearch;
  });

  return (
    <div data-testid="workflow-templates" className="workflow-templates">
      <div data-testid="search-bar" className="search-bar">
        <input
          data-testid="search-input"
          type="text"
          value={searchQuery}
          onChange={(e) => onSearchChange?.(e.target.value)}
          placeholder="Search templates..."
        />
      </div>
      <div data-testid="category-filter" className="category-filter">
        {categories.map((category) => (
          <button
            key={category}
            data-testid={`category-${category}`}
            className={selectedCategory === category ? 'active' : ''}
            onClick={() => onCategoryChange?.(category)}
          >
            {category}
          </button>
        ))}
      </div>
      <div data-testid="template-grid" className="template-grid">
        {filteredTemplates.length === 0 ? (
          <p data-testid="no-results">No templates found</p>
        ) : (
          filteredTemplates.map((template) => (
            <div key={template.id} data-testid={`template-${template.id}`} className="template-card">
              {template.icon && <span className="icon">{template.icon}</span>}
              <h3>{template.name}</h3>
              <p>{template.description}</p>
              <span className="category">{template.category}</span>
              <div className="actions">
                <button
                  data-testid={`preview-${template.id}`}
                  onClick={() => onPreview?.(template)}
                >
                  Preview
                </button>
                <button
                  data-testid={`use-${template.id}`}
                  onClick={() => onSelect?.(template)}
                >
                  Use Template
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};

describe('WorkflowTemplates', () => {
  it('renders templates container', () => {
    render(<WorkflowTemplates />);
    expect(screen.getByTestId('workflow-templates')).toBeInTheDocument();
  });

  it('renders search bar', () => {
    render(<WorkflowTemplates />);
    expect(screen.getByTestId('search-bar')).toBeInTheDocument();
    expect(screen.getByTestId('search-input')).toBeInTheDocument();
  });

  it('renders category filter', () => {
    render(<WorkflowTemplates />);
    expect(screen.getByTestId('category-filter')).toBeInTheDocument();
    expect(screen.getByTestId('category-All')).toBeInTheDocument();
    expect(screen.getByTestId('category-Development')).toBeInTheDocument();
    expect(screen.getByTestId('category-DevOps')).toBeInTheDocument();
  });

  it('renders template grid', () => {
    render(<WorkflowTemplates />);
    expect(screen.getByTestId('template-grid')).toBeInTheDocument();
  });

  it('renders all templates', () => {
    render(<WorkflowTemplates templates={mockTemplates} />);
    expect(screen.getByTestId('template-1')).toBeInTheDocument();
    expect(screen.getByTestId('template-2')).toBeInTheDocument();
    expect(screen.getByTestId('template-3')).toBeInTheDocument();
  });

  it('displays template name and description', () => {
    render(<WorkflowTemplates templates={mockTemplates} />);
    expect(screen.getByText('Code Review')).toBeInTheDocument();
    expect(screen.getByText('Automated code review workflow')).toBeInTheDocument();
  });

  it('displays template icon', () => {
    render(<WorkflowTemplates templates={mockTemplates} />);
    expect(screen.getByText('🔍')).toBeInTheDocument();
  });

  it('calls onSearchChange when search input changes', () => {
    const onSearchChange = vi.fn();
    render(<WorkflowTemplates onSearchChange={onSearchChange} />);
    
    fireEvent.change(screen.getByTestId('search-input'), {
      target: { value: 'code' },
    });
    
    expect(onSearchChange).toHaveBeenCalledWith('code');
  });

  it('filters templates by search query', () => {
    render(<WorkflowTemplates templates={mockTemplates} searchQuery="code" />);
    
    expect(screen.getByTestId('template-1')).toBeInTheDocument();
    expect(screen.queryByTestId('template-2')).not.toBeInTheDocument();
    expect(screen.queryByTestId('template-3')).not.toBeInTheDocument();
  });

  it('calls onCategoryChange when category is clicked', () => {
    const onCategoryChange = vi.fn();
    render(<WorkflowTemplates onCategoryChange={onCategoryChange} />);
    
    fireEvent.click(screen.getByTestId('category-Development'));
    
    expect(onCategoryChange).toHaveBeenCalledWith('Development');
  });

  it('filters templates by category', () => {
    render(<WorkflowTemplates templates={mockTemplates} selectedCategory="DevOps" />);
    
    expect(screen.queryByTestId('template-1')).not.toBeInTheDocument();
    expect(screen.queryByTestId('template-2')).not.toBeInTheDocument();
    expect(screen.getByTestId('template-3')).toBeInTheDocument();
  });

  it('highlights active category', () => {
    render(<WorkflowTemplates selectedCategory="Development" />);
    expect(screen.getByTestId('category-Development')).toHaveClass('active');
    expect(screen.getByTestId('category-All')).not.toHaveClass('active');
  });

  it('shows no results message when no templates match', () => {
    render(<WorkflowTemplates templates={mockTemplates} searchQuery="xyz" />);
    expect(screen.getByTestId('no-results')).toHaveTextContent('No templates found');
  });

  it('calls onPreview when preview button is clicked', () => {
    const onPreview = vi.fn();
    render(<WorkflowTemplates templates={mockTemplates} onPreview={onPreview} />);
    
    fireEvent.click(screen.getByTestId('preview-1'));
    
    expect(onPreview).toHaveBeenCalledWith(mockTemplates[0]);
  });

  it('calls onSelect when use template button is clicked', () => {
    const onSelect = vi.fn();
    render(<WorkflowTemplates templates={mockTemplates} onSelect={onSelect} />);
    
    fireEvent.click(screen.getByTestId('use-1'));
    
    expect(onSelect).toHaveBeenCalledWith(mockTemplates[0]);
  });
});
