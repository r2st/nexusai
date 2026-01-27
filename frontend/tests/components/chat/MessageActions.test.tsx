/**
 * MessageActions Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';

// Mock MessageActions component
interface MessageActionsProps {
  messageId: string;
  content: string;
  onCopy?: () => void;
  onRegenerate?: () => void;
  onEdit?: () => void;
  onDelete?: () => void;
  onFeedback?: (type: 'positive' | 'negative') => void;
  showRegenerate?: boolean;
  showEdit?: boolean;
  showDelete?: boolean;
}

const MessageActions = ({
  messageId,
  content,
  onCopy,
  onRegenerate,
  onEdit,
  onDelete,
  onFeedback,
  showRegenerate = true,
  showEdit = false,
  showDelete = false,
}: MessageActionsProps) => {
  const handleCopy = async () => {
    await navigator.clipboard.writeText(content);
    onCopy?.();
  };

  return (
    <div data-testid="message-actions" className="message-actions">
      <button data-testid="copy-action" onClick={handleCopy} title="Copy">
        Copy
      </button>
      {showRegenerate && (
        <button data-testid="regenerate-action" onClick={onRegenerate} title="Regenerate">
          Regenerate
        </button>
      )}
      {showEdit && (
        <button data-testid="edit-action" onClick={onEdit} title="Edit">
          Edit
        </button>
      )}
      {showDelete && (
        <button data-testid="delete-action" onClick={onDelete} title="Delete">
          Delete
        </button>
      )}
      <button data-testid="thumbs-up" onClick={() => onFeedback?.('positive')} title="Good response">
        👍
      </button>
      <button data-testid="thumbs-down" onClick={() => onFeedback?.('negative')} title="Bad response">
        👎
      </button>
    </div>
  );
};

// Mock clipboard
beforeAll(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  });
});

describe('MessageActions', () => {
  const defaultProps = {
    messageId: '123',
    content: 'Test message content',
  };

  it('renders message actions container', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('message-actions')).toBeInTheDocument();
  });

  it('renders copy button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('copy-action')).toBeInTheDocument();
  });

  it('copies content to clipboard when copy is clicked', async () => {
    const onCopy = vi.fn();
    render(<MessageActions {...defaultProps} onCopy={onCopy} />);
    
    fireEvent.click(screen.getByTestId('copy-action'));
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('Test message content');
  });

  it('calls onCopy callback after copying', async () => {
    const onCopy = vi.fn();
    render(<MessageActions {...defaultProps} onCopy={onCopy} />);
    
    fireEvent.click(screen.getByTestId('copy-action'));
    
    await vi.waitFor(() => {
      expect(onCopy).toHaveBeenCalled();
    });
  });

  it('renders regenerate button by default', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('regenerate-action')).toBeInTheDocument();
  });

  it('hides regenerate button when showRegenerate is false', () => {
    render(<MessageActions {...defaultProps} showRegenerate={false} />);
    expect(screen.queryByTestId('regenerate-action')).not.toBeInTheDocument();
  });

  it('calls onRegenerate when clicked', () => {
    const onRegenerate = vi.fn();
    render(<MessageActions {...defaultProps} onRegenerate={onRegenerate} />);
    
    fireEvent.click(screen.getByTestId('regenerate-action'));
    expect(onRegenerate).toHaveBeenCalled();
  });

  it('shows edit button when showEdit is true', () => {
    render(<MessageActions {...defaultProps} showEdit={true} />);
    expect(screen.getByTestId('edit-action')).toBeInTheDocument();
  });

  it('hides edit button by default', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.queryByTestId('edit-action')).not.toBeInTheDocument();
  });

  it('calls onEdit when clicked', () => {
    const onEdit = vi.fn();
    render(<MessageActions {...defaultProps} showEdit={true} onEdit={onEdit} />);
    
    fireEvent.click(screen.getByTestId('edit-action'));
    expect(onEdit).toHaveBeenCalled();
  });

  it('shows delete button when showDelete is true', () => {
    render(<MessageActions {...defaultProps} showDelete={true} />);
    expect(screen.getByTestId('delete-action')).toBeInTheDocument();
  });

  it('calls onDelete when clicked', () => {
    const onDelete = vi.fn();
    render(<MessageActions {...defaultProps} showDelete={true} onDelete={onDelete} />);
    
    fireEvent.click(screen.getByTestId('delete-action'));
    expect(onDelete).toHaveBeenCalled();
  });
});

describe('MessageActions Feedback', () => {
  const defaultProps = {
    messageId: '123',
    content: 'Test message',
  };

  it('renders thumbs up button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('thumbs-up')).toBeInTheDocument();
  });

  it('renders thumbs down button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('thumbs-down')).toBeInTheDocument();
  });

  it('calls onFeedback with positive when thumbs up is clicked', () => {
    const onFeedback = vi.fn();
    render(<MessageActions {...defaultProps} onFeedback={onFeedback} />);
    
    fireEvent.click(screen.getByTestId('thumbs-up'));
    expect(onFeedback).toHaveBeenCalledWith('positive');
  });

  it('calls onFeedback with negative when thumbs down is clicked', () => {
    const onFeedback = vi.fn();
    render(<MessageActions {...defaultProps} onFeedback={onFeedback} />);
    
    fireEvent.click(screen.getByTestId('thumbs-down'));
    expect(onFeedback).toHaveBeenCalledWith('negative');
  });
});

describe('MessageActions Accessibility', () => {
  const defaultProps = {
    messageId: '123',
    content: 'Test message',
  };

  it('has title attribute on copy button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('copy-action')).toHaveAttribute('title', 'Copy');
  });

  it('has title attribute on regenerate button', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('regenerate-action')).toHaveAttribute('title', 'Regenerate');
  });

  it('has title attribute on feedback buttons', () => {
    render(<MessageActions {...defaultProps} />);
    expect(screen.getByTestId('thumbs-up')).toHaveAttribute('title', 'Good response');
    expect(screen.getByTestId('thumbs-down')).toHaveAttribute('title', 'Bad response');
  });
});
