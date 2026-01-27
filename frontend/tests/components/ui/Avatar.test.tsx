/**
 * Avatar Component Tests
 */

import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { Avatar, AvatarImage, AvatarFallback, UserAvatar, AIAvatar, TeamAvatar } from '@/components/ui/avatar';

describe('Avatar', () => {
  it('renders avatar container', () => {
    render(
      <Avatar data-testid="avatar">
        <AvatarFallback>JD</AvatarFallback>
      </Avatar>
    );
    expect(screen.getByTestId('avatar')).toBeInTheDocument();
  });

  it('has correct base styles', () => {
    render(
      <Avatar data-testid="avatar">
        <AvatarFallback>JD</AvatarFallback>
      </Avatar>
    );
    const avatar = screen.getByTestId('avatar');
    expect(avatar).toHaveClass('relative', 'flex', 'h-10', 'w-10', 'shrink-0', 'overflow-hidden', 'rounded-full');
  });

  it('applies custom className', () => {
    render(
      <Avatar className="h-16 w-16" data-testid="avatar">
        <AvatarFallback>JD</AvatarFallback>
      </Avatar>
    );
    expect(screen.getByTestId('avatar')).toHaveClass('h-16', 'w-16');
  });
});

describe('AvatarFallback', () => {
  it('renders fallback content', () => {
    render(
      <Avatar>
        <AvatarFallback>JD</AvatarFallback>
      </Avatar>
    );
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('has correct fallback styles', () => {
    render(
      <Avatar>
        <AvatarFallback data-testid="fallback">JD</AvatarFallback>
      </Avatar>
    );
    const fallback = screen.getByTestId('fallback');
    expect(fallback).toHaveClass(
      'flex',
      'h-full',
      'w-full',
      'items-center',
      'justify-center',
      'rounded-full',
      'bg-muted'
    );
  });

  it('renders with icon as fallback', () => {
    render(
      <Avatar>
        <AvatarFallback>
          <span data-testid="icon">👤</span>
        </AvatarFallback>
      </Avatar>
    );
    expect(screen.getByTestId('icon')).toBeInTheDocument();
  });
});

describe('AvatarImage', () => {
  // Note: Radix Avatar doesn't render image until it's loaded,
  // so in tests with jsdom the image won't appear immediately
  it('renders AvatarImage component', () => {
    render(
      <Avatar>
        <AvatarImage src="test.jpg" alt="Test" />
        <AvatarFallback>FB</AvatarFallback>
      </Avatar>
    );
    // Fallback should be visible (image doesn't load in tests)
    expect(screen.getByText('FB')).toBeInTheDocument();
  });
});

describe('Avatar Sizes', () => {
  it('renders small avatar', () => {
    render(
      <Avatar className="h-8 w-8" data-testid="avatar">
        <AvatarFallback>S</AvatarFallback>
      </Avatar>
    );
    expect(screen.getByTestId('avatar')).toHaveClass('h-8', 'w-8');
  });

  it('renders large avatar', () => {
    render(
      <Avatar className="h-20 w-20" data-testid="avatar">
        <AvatarFallback>L</AvatarFallback>
      </Avatar>
    );
    expect(screen.getByTestId('avatar')).toHaveClass('h-20', 'w-20');
  });
});

describe('UserAvatar', () => {
  it('renders user initials from name', () => {
    render(<UserAvatar user={{ name: 'John Doe', email: 'john@example.com' }} />);
    expect(screen.getByText('JD')).toBeInTheDocument();
  });

  it('renders initial from email when no name', () => {
    render(<UserAvatar user={{ email: 'john@example.com' }} />);
    expect(screen.getByText('J')).toBeInTheDocument();
  });

  it('renders different sizes', () => {
    const { container, rerender } = render(<UserAvatar user={{ name: 'A B' }} size="sm" />);
    // The Avatar root span should have the size classes
    const avatar = container.querySelector('span.h-8.w-8');
    expect(avatar).toBeInTheDocument();

    rerender(<UserAvatar user={{ name: 'C D' }} size="lg" />);
    const largeAvatar = container.querySelector('span.h-12.w-12');
    expect(largeAvatar).toBeInTheDocument();
  });
});

describe('AIAvatar', () => {
  it('renders AI avatar', () => {
    render(<AIAvatar />);
    const avatar = screen.getByRole('img', { name: /AI avatar/i });
    expect(avatar).toBeInTheDocument();
  });

  it('renders with custom name', () => {
    render(<AIAvatar name="Assistant" />);
    expect(screen.getByRole('img', { name: 'Assistant avatar' })).toBeInTheDocument();
  });

  it('applies animated class when animated', () => {
    render(<AIAvatar animated />);
    const avatar = screen.getByRole('img');
    expect(avatar).toHaveClass('animate-pulse');
  });

  it('applies variant classes', () => {
    render(<AIAvatar variant="gradient" />);
    const avatar = screen.getByRole('img');
    expect(avatar).toHaveClass('bg-gradient-to-br');
  });
});

describe('TeamAvatar', () => {
  it('renders team initials', () => {
    render(<TeamAvatar name="Engineering Team" />);
    expect(screen.getByText('ET')).toBeInTheDocument();
  });

  it('has team avatar role', () => {
    render(<TeamAvatar name="Design" />);
    expect(screen.getByRole('img', { name: 'Design team avatar' })).toBeInTheDocument();
  });
});
