/**
 * Tests for QuickReplyBar Component - Unit tests that don't require full context
 * Note: Full integration tests should be done with the AssistantRuntimeProvider
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import type { QuickReply } from '@/lib/api';

// Since QuickReplyBar requires AssistantRuntimeProvider context,
// we test the underlying logic and types here

const mockQuickReplies: QuickReply[] = [
  {
    id: 'qr-1',
    label: 'Yes, continue',
    value: 'yes_continue',
    icon: '✓',
    description: 'Proceed with the current action',
  },
  {
    id: 'qr-2',
    label: 'No, cancel',
    value: 'no_cancel',
    icon: '✗',
    description: 'Cancel and go back',
  },
  {
    id: 'qr-3',
    label: 'Show more options',
    value: 'more_options',
    icon: '⋯',
  },
];

describe('QuickReplyBar - Data Types', () => {
  describe('QuickReply type validation', () => {
    it('quick reply has required fields', () => {
      const qr = mockQuickReplies[0];
      expect(qr.id).toBeDefined();
      expect(qr.label).toBeDefined();
      expect(qr.value).toBeDefined();
    });

    it('quick reply can have optional icon', () => {
      const qr = mockQuickReplies[0];
      expect(qr.icon).toBe('✓');
    });

    it('quick reply can have optional description', () => {
      const qr = mockQuickReplies[0];
      expect(qr.description).toBe('Proceed with the current action');
    });

    it('quick reply icon is optional', () => {
      const qrWithoutIcon: QuickReply = {
        id: 'test',
        label: 'Test',
        value: 'test_value',
      };
      expect(qrWithoutIcon.icon).toBeUndefined();
    });

    it('quick reply description is optional', () => {
      const qrWithoutDesc: QuickReply = {
        id: 'test',
        label: 'Test',
        value: 'test_value',
      };
      expect(qrWithoutDesc.description).toBeUndefined();
    });
  });

  describe('Quick reply array operations', () => {
    it('can map quick replies to values', () => {
      const values = mockQuickReplies.map(qr => qr.value);
      expect(values).toEqual(['yes_continue', 'no_cancel', 'more_options']);
    });

    it('can filter quick replies by pattern', () => {
      const filtered = mockQuickReplies.filter(qr => qr.value.includes('continue'));
      expect(filtered).toHaveLength(1);
      expect(filtered[0].label).toBe('Yes, continue');
    });

    it('can find quick reply by value', () => {
      const found = mockQuickReplies.find(qr => qr.value === 'no_cancel');
      expect(found?.label).toBe('No, cancel');
    });

    it('handles empty array', () => {
      const empty: QuickReply[] = [];
      expect(empty.length).toBe(0);
      expect(empty.find(qr => qr.value === 'test')).toBeUndefined();
    });
  });

  describe('Quick reply rendering helpers', () => {
    it('formats label with icon when present', () => {
      const formatWithIcon = (qr: QuickReply) => 
        qr.icon ? `${qr.icon} ${qr.label}` : qr.label;

      expect(formatWithIcon(mockQuickReplies[0])).toBe('✓ Yes, continue');
    });

    it('formats label without icon', () => {
      const qrNoIcon: QuickReply = {
        id: 'test',
        label: 'Test Label',
        value: 'test',
      };

      const formatWithIcon = (qr: QuickReply) => 
        qr.icon ? `${qr.icon} ${qr.label}` : qr.label;

      expect(formatWithIcon(qrNoIcon)).toBe('Test Label');
    });

    it('creates suggestions string from quick replies', () => {
      const suggestions = mockQuickReplies
        .map(qr => `${qr.icon || ''} ${qr.label}`.trim())
        .join(' • ');

      expect(suggestions).toContain('Yes, continue');
      expect(suggestions).toContain('No, cancel');
      expect(suggestions).toContain(' • ');
    });
  });

  describe('Quick reply selection logic', () => {
    it('matches by exact value', () => {
      const userInput = 'yes_continue';
      const isQuickReply = mockQuickReplies.some(qr => qr.value === userInput);
      expect(isQuickReply).toBe(true);
    });

    it('matches by label (case insensitive)', () => {
      const userInput = 'yes, continue';
      const isQuickReply = mockQuickReplies.some(
        qr => qr.label.toLowerCase() === userInput.toLowerCase()
      );
      expect(isQuickReply).toBe(true);
    });

    it('does not match partial input', () => {
      const userInput = 'yes';
      const isQuickReply = mockQuickReplies.some(
        qr => qr.value === userInput || qr.label.toLowerCase() === userInput.toLowerCase()
      );
      expect(isQuickReply).toBe(false);
    });

    it('handles special characters in value', () => {
      const qrWithSpecial: QuickReply = {
        id: 'special',
        label: 'Special Option',
        value: 'option/with/slashes',
      };
      expect(qrWithSpecial.value).toBe('option/with/slashes');
    });
  });
});

describe('QuickReplyBar - Button Rendering (mock component)', () => {
  // Create a simplified version for testing button rendering
  const SimpleQuickReplyButton = ({
    quickReply,
    onClick,
    disabled,
  }: {
    quickReply: QuickReply;
    onClick: (value: string) => void;
    disabled?: boolean;
  }) => (
    <button
      onClick={() => onClick(quickReply.value)}
      disabled={disabled}
      title={quickReply.description}
      data-testid={`qr-${quickReply.id}`}
    >
      {quickReply.icon && <span>{quickReply.icon}</span>}
      {quickReply.label}
    </button>
  );

  it('renders button with label', () => {
    const onClick = vi.fn();
    render(<SimpleQuickReplyButton quickReply={mockQuickReplies[0]} onClick={onClick} />);
    
    expect(screen.getByText('Yes, continue')).toBeInTheDocument();
  });

  it('renders button with icon', () => {
    const onClick = vi.fn();
    render(<SimpleQuickReplyButton quickReply={mockQuickReplies[0]} onClick={onClick} />);
    
    expect(screen.getByText('✓')).toBeInTheDocument();
  });

  it('calls onClick with value when clicked', () => {
    const onClick = vi.fn();
    render(<SimpleQuickReplyButton quickReply={mockQuickReplies[0]} onClick={onClick} />);
    
    fireEvent.click(screen.getByText('Yes, continue'));
    expect(onClick).toHaveBeenCalledWith('yes_continue');
  });

  it('does not call onClick when disabled', () => {
    const onClick = vi.fn();
    render(<SimpleQuickReplyButton quickReply={mockQuickReplies[0]} onClick={onClick} disabled />);
    
    fireEvent.click(screen.getByRole('button'));
    expect(onClick).not.toHaveBeenCalled();
  });

  it('shows description as title', () => {
    const onClick = vi.fn();
    render(<SimpleQuickReplyButton quickReply={mockQuickReplies[0]} onClick={onClick} />);
    
    expect(screen.getByRole('button')).toHaveAttribute('title', 'Proceed with the current action');
  });

  it('renders multiple buttons', () => {
    const onClick = vi.fn();
    render(
      <div>
        {mockQuickReplies.map(qr => (
          <SimpleQuickReplyButton key={qr.id} quickReply={qr} onClick={onClick} />
        ))}
      </div>
    );
    
    expect(screen.getAllByRole('button')).toHaveLength(3);
  });
});
