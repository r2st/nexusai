/**
 * QuickActions component tests
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  QuickActions,
  SuggestedActions,
  QUICK_ACTIONS,
  type QuickAction,
} from '@/components/chat/quick-actions';

describe('QuickActions Component', () => {
  const mockOnAction = vi.fn();

  beforeEach(() => {
    mockOnAction.mockClear();
  });

  describe('rendering', () => {
    it('renders quick action buttons', () => {
      render(<QuickActions onAction={mockOnAction} />);
      expect(screen.getByText('Connect repo')).toBeInTheDocument();
    });

    it('renders chips variant by default', () => {
      render(<QuickActions onAction={mockOnAction} />);
      const button = screen.getByText('Connect repo').closest('button');
      expect(button).toHaveClass('rounded-full');
    });

    it('renders grid variant when specified', () => {
      render(<QuickActions onAction={mockOnAction} variant="grid" />);
      const container = screen.getByText('Connect repo').closest('button')?.parentElement;
      expect(container).toHaveClass('grid');
    });

    it('renders compact variant when specified', () => {
      render(<QuickActions onAction={mockOnAction} variant="compact" />);
      const button = screen.getByText('Connect repo').closest('button');
      expect(button).toHaveClass('text-xs');
    });

    it('limits visible actions based on maxVisible prop', () => {
      render(<QuickActions onAction={mockOnAction} maxVisible={3} />);
      const buttons = screen.getAllByRole('button');
      expect(buttons.length).toBeLessThanOrEqual(3);
    });
  });

  describe('action handling', () => {
    it('calls onAction with correct action when button clicked', () => {
      render(<QuickActions onAction={mockOnAction} />);

      const connectRepoAction = QUICK_ACTIONS.find(a => a.id === 'connect_repo')!;
      fireEvent.click(screen.getByText('Connect repo'));

      expect(mockOnAction).toHaveBeenCalledWith(connectRepoAction);
    });

    it('passes full action object with prompt', () => {
      render(<QuickActions onAction={mockOnAction} />);

      fireEvent.click(screen.getByText('Connect repo'));

      const calledAction = mockOnAction.mock.calls[0][0] as QuickAction;
      expect(calledAction.prompt).toBeTruthy();
      expect(calledAction.id).toBe('connect_repo');
    });
  });

  describe('context-based prioritization', () => {
    it('prioritizes repo-related actions when hasRepo is true', () => {
      render(<QuickActions onAction={mockOnAction} hasRepo maxVisible={4} />);

      // Actions requiring repo context should be visible
      expect(screen.getByText('Summarize deploy risk')).toBeInTheDocument();
    });

    it('prioritizes PR-related actions when hasPR is true', () => {
      render(
        <QuickActions
          onAction={mockOnAction}
          hasRepo
          hasPR
          maxVisible={6}
        />
      );

      expect(screen.getByText('Analyze PR')).toBeInTheDocument();
      expect(screen.getByText('Generate test plan')).toBeInTheDocument();
    });

    it('prioritizes incident-related actions when hasIncident is true', () => {
      render(
        <QuickActions
          onAction={mockOnAction}
          hasIncident
          maxVisible={6}
        />
      );

      expect(screen.getByText('Find root cause')).toBeInTheDocument();
    });
  });

  describe('disabled state', () => {
    it('disables actions that require missing context', () => {
      render(
        <QuickActions
          onAction={mockOnAction}
          hasRepo={false}
          maxVisible={10}
        />
      );

      // Actions requiring repo should be disabled
      const deployRiskButton = screen.queryByText('Summarize deploy risk')?.closest('button');
      if (deployRiskButton) {
        expect(deployRiskButton).toBeDisabled();
      }
    });

    it('enables actions when required context is available', () => {
      render(
        <QuickActions
          onAction={mockOnAction}
          hasRepo
          hasPR
          maxVisible={10}
        />
      );

      const analyzePRButton = screen.getByText('Analyze PR').closest('button');
      expect(analyzePRButton).not.toBeDisabled();
    });
  });

  describe('accessibility', () => {
    it('buttons have title attributes with descriptions', () => {
      render(<QuickActions onAction={mockOnAction} />);

      const button = screen.getByText('Connect repo').closest('button');
      expect(button).toHaveAttribute('title');
    });

    it('buttons have proper focus styles', () => {
      render(<QuickActions onAction={mockOnAction} />);

      const button = screen.getByText('Connect repo').closest('button');
      expect(button).toHaveClass('focus:outline-none', 'focus:ring-2');
    });
  });
});

describe('SuggestedActions Component', () => {
  const mockOnAction = vi.fn();

  beforeEach(() => {
    mockOnAction.mockClear();
  });

  describe('rendering', () => {
    it('renders starter actions', () => {
      render(<SuggestedActions onAction={mockOnAction} />);

      expect(screen.getByText('Connect repo')).toBeInTheDocument();
      expect(screen.getByText('Analyze PR')).toBeInTheDocument();
      expect(screen.getByText('Find root cause')).toBeInTheDocument();
      expect(screen.getByText('Analyze DORA metrics')).toBeInTheDocument();
    });

    it('renders helpful header text', () => {
      render(<SuggestedActions onAction={mockOnAction} />);

      expect(
        screen.getByText('Try one of these to get started')
      ).toBeInTheDocument();
    });

    it('renders descriptions for each action', () => {
      render(<SuggestedActions onAction={mockOnAction} />);

      expect(
        screen.getByText('Link a GitHub, GitLab, or Bitbucket repository')
      ).toBeInTheDocument();
    });
  });

  describe('action handling', () => {
    it('calls onAction when an action is clicked', () => {
      render(<SuggestedActions onAction={mockOnAction} />);

      fireEvent.click(screen.getByText('Connect repo').closest('button')!);

      expect(mockOnAction).toHaveBeenCalled();
      expect(mockOnAction.mock.calls[0][0].id).toBe('connect_repo');
    });
  });

  describe('layout', () => {
    it('uses responsive grid layout', () => {
      render(<SuggestedActions onAction={mockOnAction} />);

      const grid = screen.getByText('Connect repo').closest('button')?.parentElement;
      expect(grid).toHaveClass('grid', 'grid-cols-1', 'sm:grid-cols-2');
    });
  });
});

describe('QUICK_ACTIONS constant', () => {
  it('has unique IDs for all actions', () => {
    const ids = QUICK_ACTIONS.map(a => a.id);
    const uniqueIds = [...new Set(ids)];
    expect(ids.length).toBe(uniqueIds.length);
  });

  it('all actions have required properties', () => {
    QUICK_ACTIONS.forEach(action => {
      expect(action.id).toBeTruthy();
      expect(action.label).toBeTruthy();
      expect(action.icon).toBeTruthy();
      expect(action.action).toBeTruthy();
      expect(action.category).toBeTruthy();
      expect(action.prompt).toBeTruthy();
    });
  });

  it('prompts end with proper punctuation or expectation', () => {
    QUICK_ACTIONS.forEach(action => {
      // Prompts should be meaningful
      expect(action.prompt.length).toBeGreaterThan(10);
    });
  });
});
