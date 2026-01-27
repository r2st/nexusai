/**
 * ShareConversation Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';

// Mock ShareConversation component
interface ShareConversationProps {
  conversationId: string;
  onShare?: (shareUrl: string) => void;
  onClose?: () => void;
  isOpen?: boolean;
}

const ShareConversation = ({
  conversationId,
  onShare,
  onClose,
  isOpen = true,
}: ShareConversationProps) => {
  const [shareUrl, setShareUrl] = React.useState('');
  const [isPublic, setIsPublic] = React.useState(false);
  const [isCopied, setIsCopied] = React.useState(false);

  const generateShareUrl = () => {
    const url = `https://nexusai.com/share/${conversationId}`;
    setShareUrl(url);
    onShare?.(url);
  };

  const handleCopy = async () => {
    await navigator.clipboard.writeText(shareUrl);
    setIsCopied(true);
    setTimeout(() => setIsCopied(false), 2000);
  };

  if (!isOpen) return null;

  return (
    <div data-testid="share-dialog" className="share-dialog">
      <div className="header">
        <h2>Share Conversation</h2>
        <button data-testid="close-button" onClick={onClose}>×</button>
      </div>
      <div className="content">
        <label>
          <input
            type="checkbox"
            data-testid="public-toggle"
            checked={isPublic}
            onChange={(e) => setIsPublic(e.target.checked)}
          />
          Make conversation public
        </label>
        {!shareUrl ? (
          <button data-testid="generate-link" onClick={generateShareUrl}>
            Generate Share Link
          </button>
        ) : (
          <div className="share-link">
            <input
              data-testid="share-url-input"
              type="text"
              value={shareUrl}
              readOnly
            />
            <button data-testid="copy-link" onClick={handleCopy}>
              {isCopied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

import React from 'react';

// Mock clipboard
beforeAll(() => {
  Object.assign(navigator, {
    clipboard: {
      writeText: vi.fn().mockResolvedValue(undefined),
    },
  });
});

describe('ShareConversation', () => {
  it('renders share dialog when open', () => {
    render(<ShareConversation conversationId="123" isOpen={true} />);
    expect(screen.getByTestId('share-dialog')).toBeInTheDocument();
  });

  it('does not render when closed', () => {
    render(<ShareConversation conversationId="123" isOpen={false} />);
    expect(screen.queryByTestId('share-dialog')).not.toBeInTheDocument();
  });

  it('renders close button', () => {
    render(<ShareConversation conversationId="123" />);
    expect(screen.getByTestId('close-button')).toBeInTheDocument();
  });

  it('calls onClose when close button is clicked', () => {
    const onClose = vi.fn();
    render(<ShareConversation conversationId="123" onClose={onClose} />);
    
    fireEvent.click(screen.getByTestId('close-button'));
    expect(onClose).toHaveBeenCalled();
  });

  it('renders public toggle', () => {
    render(<ShareConversation conversationId="123" />);
    expect(screen.getByTestId('public-toggle')).toBeInTheDocument();
  });

  it('toggles public state', () => {
    render(<ShareConversation conversationId="123" />);
    const toggle = screen.getByTestId('public-toggle');
    
    expect(toggle).not.toBeChecked();
    fireEvent.click(toggle);
    expect(toggle).toBeChecked();
  });

  it('renders generate link button initially', () => {
    render(<ShareConversation conversationId="123" />);
    expect(screen.getByTestId('generate-link')).toBeInTheDocument();
  });

  it('generates share URL when clicked', () => {
    const onShare = vi.fn();
    render(<ShareConversation conversationId="123" onShare={onShare} />);
    
    fireEvent.click(screen.getByTestId('generate-link'));
    
    expect(onShare).toHaveBeenCalledWith('https://nexusai.com/share/123');
  });

  it('shows share URL input after generating', () => {
    render(<ShareConversation conversationId="123" />);
    
    fireEvent.click(screen.getByTestId('generate-link'));
    
    expect(screen.getByTestId('share-url-input')).toBeInTheDocument();
    expect(screen.getByTestId('share-url-input')).toHaveValue('https://nexusai.com/share/123');
  });

  it('shows copy button after generating URL', () => {
    render(<ShareConversation conversationId="123" />);
    
    fireEvent.click(screen.getByTestId('generate-link'));
    
    expect(screen.getByTestId('copy-link')).toBeInTheDocument();
  });

  it('copies URL to clipboard when copy is clicked', async () => {
    render(<ShareConversation conversationId="123" />);
    
    fireEvent.click(screen.getByTestId('generate-link'));
    fireEvent.click(screen.getByTestId('copy-link'));
    
    expect(navigator.clipboard.writeText).toHaveBeenCalledWith('https://nexusai.com/share/123');
  });

  it('shows "Copied!" feedback after copying', async () => {
    render(<ShareConversation conversationId="123" />);
    
    fireEvent.click(screen.getByTestId('generate-link'));
    fireEvent.click(screen.getByTestId('copy-link'));
    
    await waitFor(() => {
      expect(screen.getByTestId('copy-link')).toHaveTextContent('Copied!');
    });
  });
});
