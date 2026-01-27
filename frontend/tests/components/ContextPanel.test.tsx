/**
 * ContextPanel component tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import {
  ContextPanel,
  type RepoContext,
  type PRContext,
  type IncidentContext,
  type TimeframeContext,
} from '@/components/chat/context-panel';

describe('ContextPanel Component', () => {
  const mockRepo: RepoContext = {
    id: '1',
    name: 'my-repo',
    full_name: 'org/my-repo',
    url: 'https://github.com/org/my-repo',
    default_branch: 'main',
    language: 'TypeScript',
    last_commit: '2025-01-15T10:00:00Z',
  };

  const mockPR: PRContext = {
    id: '123',
    number: 42,
    title: 'Add new feature',
    url: 'https://github.com/org/my-repo/pull/42',
    state: 'open',
    author: 'developer',
    created_at: '2025-01-14T10:00:00Z',
    files_changed: 5,
    additions: 100,
    deletions: 20,
  };

  const mockIncident: IncidentContext = {
    id: 'inc-1',
    title: 'Database connection timeout',
    severity: 'high',
    status: 'investigating',
    started_at: '2025-01-15T08:00:00Z',
    affected_services: ['api', 'web'],
  };

  const mockTimeframe: TimeframeContext = {
    start: '2025-01-01T00:00:00Z',
    end: '2025-01-15T23:59:59Z',
    preset: 'last_7d',
  };

  describe('rendering', () => {
    it('renders empty state when no context provided', () => {
      render(<ContextPanel />);
      expect(screen.getByText('No context selected')).toBeInTheDocument();
    });

    it('renders repository context correctly', () => {
      render(<ContextPanel repo={mockRepo} />);
      expect(screen.getByText('Repository')).toBeInTheDocument();
      expect(screen.getByText('my-repo')).toBeInTheDocument();
      expect(screen.getByText('org/my-repo')).toBeInTheDocument();
      expect(screen.getByText('main')).toBeInTheDocument();
      expect(screen.getByText('TypeScript')).toBeInTheDocument();
    });

    it('renders PR context correctly', () => {
      render(<ContextPanel pr={mockPR} />);
      expect(screen.getByText('Pull Request')).toBeInTheDocument();
      expect(screen.getByText('#42')).toBeInTheDocument();
      expect(screen.getByText('Add new feature')).toBeInTheDocument();
      expect(screen.getByText('developer')).toBeInTheDocument();
      expect(screen.getByText('open')).toBeInTheDocument();
    });

    it('renders incident context correctly', () => {
      render(<ContextPanel incident={mockIncident} />);
      expect(screen.getByText('Incident')).toBeInTheDocument();
      expect(screen.getByText('Database connection timeout')).toBeInTheDocument();
      // Note: severity text is lowercase in DOM, CSS renders it uppercase
      expect(screen.getByText('high')).toBeInTheDocument();
      expect(screen.getByText('investigating')).toBeInTheDocument();
    });

    it('renders timeframe context correctly', () => {
      render(<ContextPanel timeframe={mockTimeframe} />);
      expect(screen.getByText('Timeframe')).toBeInTheDocument();
      expect(screen.getByText('Last 7 days')).toBeInTheDocument();
    });

    it('renders multiple contexts together', () => {
      render(
        <ContextPanel
          repo={mockRepo}
          pr={mockPR}
          incident={mockIncident}
          timeframe={mockTimeframe}
        />
      );
      expect(screen.getByText('Repository')).toBeInTheDocument();
      expect(screen.getByText('Pull Request')).toBeInTheDocument();
      expect(screen.getByText('Incident')).toBeInTheDocument();
      expect(screen.getByText('Timeframe')).toBeInTheDocument();
    });
  });

  describe('collapsed state', () => {
    it('renders collapsed view when collapsed prop is true', () => {
      const onToggle = vi.fn();
      render(
        <ContextPanel
          repo={mockRepo}
          collapsed={true}
          onToggleCollapse={onToggle}
        />
      );
      expect(screen.getByLabelText('Expand context panel')).toBeInTheDocument();
    });

    it('calls onToggleCollapse when expand button clicked', () => {
      const onToggle = vi.fn();
      render(
        <ContextPanel
          repo={mockRepo}
          collapsed={true}
          onToggleCollapse={onToggle}
        />
      );
      fireEvent.click(screen.getByLabelText('Expand context panel'));
      expect(onToggle).toHaveBeenCalled();
    });
  });

  describe('context removal', () => {
    it('calls onRepoChange with null when repo is removed', () => {
      const onRepoChange = vi.fn();
      render(<ContextPanel repo={mockRepo} onRepoChange={onRepoChange} />);

      const removeButton = screen.getByLabelText('Remove repository');
      fireEvent.click(removeButton);

      expect(onRepoChange).toHaveBeenCalledWith(null);
    });

    it('calls onPRChange with null when PR is removed', () => {
      const onPRChange = vi.fn();
      render(<ContextPanel pr={mockPR} onPRChange={onPRChange} />);

      const removeButton = screen.getByLabelText('Remove pull request');
      fireEvent.click(removeButton);

      expect(onPRChange).toHaveBeenCalledWith(null);
    });

    it('calls onIncidentChange with null when incident is removed', () => {
      const onIncidentChange = vi.fn();
      render(
        <ContextPanel incident={mockIncident} onIncidentChange={onIncidentChange} />
      );

      const removeButton = screen.getByLabelText('Remove incident');
      fireEvent.click(removeButton);

      expect(onIncidentChange).toHaveBeenCalledWith(null);
    });

    it('clears all context when "Clear all" is clicked', () => {
      const onRepoChange = vi.fn();
      const onPRChange = vi.fn();
      const onIncidentChange = vi.fn();
      const onTimeframeChange = vi.fn();
      const onFiltersChange = vi.fn();

      render(
        <ContextPanel
          repo={mockRepo}
          pr={mockPR}
          incident={mockIncident}
          timeframe={mockTimeframe}
          onRepoChange={onRepoChange}
          onPRChange={onPRChange}
          onIncidentChange={onIncidentChange}
          onTimeframeChange={onTimeframeChange}
          onFiltersChange={onFiltersChange}
        />
      );

      fireEvent.click(screen.getByText('Clear all'));

      expect(onRepoChange).toHaveBeenCalledWith(null);
      expect(onPRChange).toHaveBeenCalledWith(null);
      expect(onIncidentChange).toHaveBeenCalledWith(null);
      expect(onTimeframeChange).toHaveBeenCalledWith(null);
      expect(onFiltersChange).toHaveBeenCalledWith({});
    });
  });

  describe('filters', () => {
    it('renders active filters', () => {
      const filters = { status: 'open', author: 'developer' };
      render(<ContextPanel filters={filters} />);

      expect(screen.getByText('Filters')).toBeInTheDocument();
      expect(screen.getByText('status:')).toBeInTheDocument();
      expect(screen.getByText('open')).toBeInTheDocument();
      expect(screen.getByText('author:')).toBeInTheDocument();
      expect(screen.getByText('developer')).toBeInTheDocument();
    });

    it('removes individual filter when X is clicked', () => {
      const filters = { status: 'open', author: 'developer' };
      const onFiltersChange = vi.fn();

      render(
        <ContextPanel filters={filters} onFiltersChange={onFiltersChange} />
      );

      const removeButtons = screen.getAllByLabelText(/Remove .* filter/);
      fireEvent.click(removeButtons[0]);

      expect(onFiltersChange).toHaveBeenCalled();
    });
  });

  describe('external links', () => {
    it('renders external link for repository', () => {
      render(<ContextPanel repo={mockRepo} />);
      const link = screen.getByLabelText('Open repository in new tab');
      expect(link).toHaveAttribute('href', mockRepo.url);
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('renders external link for PR', () => {
      render(<ContextPanel pr={mockPR} />);
      const link = screen.getByLabelText('Open pull request in new tab');
      expect(link).toHaveAttribute('href', mockPR.url);
      expect(link).toHaveAttribute('target', '_blank');
    });
  });

  describe('PR state badges', () => {
    it('shows correct badge for open PR', () => {
      render(<ContextPanel pr={{ ...mockPR, state: 'open' }} />);
      expect(screen.getByText('open')).toHaveClass('bg-green-100');
    });

    it('shows correct badge for closed PR', () => {
      render(<ContextPanel pr={{ ...mockPR, state: 'closed' }} />);
      expect(screen.getByText('closed')).toHaveClass('bg-red-100');
    });

    it('shows correct badge for merged PR', () => {
      render(<ContextPanel pr={{ ...mockPR, state: 'merged' }} />);
      expect(screen.getByText('merged')).toHaveClass('bg-purple-100');
    });
  });

  describe('incident severity badges', () => {
    // Note: severity text is lowercase in DOM, CSS renders it uppercase
    it('shows correct badge for critical severity', () => {
      render(
        <ContextPanel incident={{ ...mockIncident, severity: 'critical' }} />
      );
      expect(screen.getByText('critical')).toHaveClass('bg-red-100');
    });

    it('shows correct badge for high severity', () => {
      render(
        <ContextPanel incident={{ ...mockIncident, severity: 'high' }} />
      );
      expect(screen.getByText('high')).toHaveClass('bg-orange-100');
    });

    it('shows correct badge for medium severity', () => {
      render(
        <ContextPanel incident={{ ...mockIncident, severity: 'medium' }} />
      );
      expect(screen.getByText('medium')).toHaveClass('bg-yellow-100');
    });

    it('shows correct badge for low severity', () => {
      render(
        <ContextPanel incident={{ ...mockIncident, severity: 'low' }} />
      );
      expect(screen.getByText('low')).toHaveClass('bg-blue-100');
    });
  });

  describe('accessibility', () => {
    it('has proper ARIA label for the panel', () => {
      render(<ContextPanel repo={mockRepo} />);
      expect(screen.getByRole('complementary')).toHaveAttribute(
        'aria-label',
        'Context panel'
      );
    });

    it('has proper heading structure', () => {
      render(<ContextPanel repo={mockRepo} />);
      expect(screen.getByRole('heading', { level: 2 })).toHaveTextContent(
        'Context'
      );
    });
  });
});
