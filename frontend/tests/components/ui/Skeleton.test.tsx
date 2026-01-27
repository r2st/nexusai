/**
 * Skeleton Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import {
  Skeleton,
  SkeletonText,
  SkeletonAvatar,
  SkeletonCard,
  SkeletonMessage,
  SkeletonChatList,
  SkeletonTable,
  SkeletonDashboardCard,
  SkeletonStatsGrid,
  SkeletonPage,
} from '@/components/ui/skeleton';

describe('Skeleton', () => {
  it('renders skeleton element', () => {
    const { container } = render(<Skeleton />);
    const skeleton = container.firstChild;
    expect(skeleton).toBeInTheDocument();
  });

  it('has animation class', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass('animate-pulse');
  });

  it('has correct base styles', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveClass('rounded-md', 'bg-muted');
  });

  it('applies custom className', () => {
    const { container } = render(<Skeleton className="h-12 w-full" />);
    const skeleton = container.firstChild;
    expect(skeleton).toHaveClass('h-12', 'w-full');
  });

  it('has aria-hidden attribute', () => {
    const { container } = render(<Skeleton />);
    expect(container.firstChild).toHaveAttribute('aria-hidden', 'true');
  });
});

describe('SkeletonText', () => {
  it('renders default 3 lines', () => {
    const { container } = render(<SkeletonText />);
    const lines = container.querySelectorAll('.animate-pulse');
    expect(lines).toHaveLength(3);
  });

  it('renders custom number of lines', () => {
    const { container } = render(<SkeletonText lines={5} />);
    const lines = container.querySelectorAll('.animate-pulse');
    expect(lines).toHaveLength(5);
  });

  it('applies custom className', () => {
    const { container } = render(<SkeletonText className="custom-class" />);
    expect(container.firstChild).toHaveClass('custom-class');
  });
});

describe('SkeletonAvatar', () => {
  it('renders avatar skeleton', () => {
    const { container } = render(<SkeletonAvatar />);
    expect(container.firstChild).toHaveClass('rounded-full');
  });

  it('renders different sizes', () => {
    const { container, rerender } = render(<SkeletonAvatar size="sm" />);
    expect(container.firstChild).toHaveClass('h-8', 'w-8');

    rerender(<SkeletonAvatar size="lg" />);
    expect(container.firstChild).toHaveClass('h-12', 'w-12');
  });
});

describe('SkeletonCard', () => {
  it('renders card skeleton', () => {
    const { container } = render(<SkeletonCard />);
    expect(container.firstChild).toHaveClass('rounded-lg', 'border');
  });

  it('contains avatar and text skeletons', () => {
    const { container } = render(<SkeletonCard />);
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(3);
  });
});

describe('SkeletonMessage', () => {
  it('renders message skeleton', () => {
    const { container } = render(<SkeletonMessage />);
    expect(container.firstChild).toHaveClass('flex', 'gap-4');
  });

  it('has different background for user vs assistant', () => {
    const { container, rerender } = render(<SkeletonMessage isUser={false} />);
    expect(container.firstChild).toHaveClass('bg-muted/50');

    rerender(<SkeletonMessage isUser={true} />);
    expect(container.firstChild).toHaveClass('bg-background');
  });
});

describe('SkeletonChatList', () => {
  it('renders default 5 items', () => {
    const { container } = render(<SkeletonChatList />);
    const items = container.querySelectorAll('.flex.items-center.gap-3');
    expect(items).toHaveLength(5);
  });

  it('renders custom count', () => {
    const { container } = render(<SkeletonChatList count={3} />);
    const items = container.querySelectorAll('.flex.items-center.gap-3');
    expect(items).toHaveLength(3);
  });
});

describe('SkeletonTable', () => {
  it('renders table skeleton', () => {
    const { container } = render(<SkeletonTable />);
    expect(container.firstChild).toHaveClass('rounded-lg', 'border');
  });

  it('renders header row', () => {
    const { container } = render(<SkeletonTable />);
    const header = container.querySelector('.bg-muted\\/50.border-b');
    expect(header).toBeInTheDocument();
  });

  it('renders correct number of rows', () => {
    const { container } = render(<SkeletonTable rows={3} columns={4} />);
    // Header + 3 data rows = 4 flex containers
    const rows = container.querySelectorAll('.flex.gap-4');
    expect(rows.length).toBeGreaterThanOrEqual(4);
  });
});

describe('SkeletonDashboardCard', () => {
  it('renders dashboard card skeleton', () => {
    const { container } = render(<SkeletonDashboardCard />);
    expect(container.firstChild).toHaveClass('rounded-lg', 'border', 'p-6');
  });
});

describe('SkeletonStatsGrid', () => {
  it('renders grid of dashboard cards', () => {
    const { container } = render(<SkeletonStatsGrid />);
    expect(container.firstChild).toHaveClass('grid');
  });

  it('renders default 4 cards', () => {
    const { container } = render(<SkeletonStatsGrid />);
    const cards = container.querySelectorAll('.rounded-lg.border.p-6');
    expect(cards).toHaveLength(4);
  });

  it('renders custom count', () => {
    const { container } = render(<SkeletonStatsGrid count={6} />);
    const cards = container.querySelectorAll('.rounded-lg.border.p-6');
    expect(cards).toHaveLength(6);
  });
});

describe('SkeletonPage', () => {
  it('renders full page skeleton', () => {
    const { container } = render(<SkeletonPage />);
    expect(container.firstChild).toHaveClass('p-6', 'space-y-6');
  });

  it('contains header, stats, and content sections', () => {
    const { container } = render(<SkeletonPage />);
    // Should have multiple skeleton elements
    const skeletons = container.querySelectorAll('.animate-pulse');
    expect(skeletons.length).toBeGreaterThan(10);
  });
});
