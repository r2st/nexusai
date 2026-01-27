/**
 * Tests for MCP Error Renderer component
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { MCPErrorRenderer } from '@/components/chat/tools/mcp-error-renderer';
import type { MCPErrorPayload } from '@/components/chat/tools/types';

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn().mockResolvedValue(undefined),
};

Object.assign(navigator, {
  clipboard: mockClipboard,
});

describe('MCPErrorRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('basic rendering', () => {
    it('renders error message', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Failed to connect to server',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('Failed to connect to server')).toBeInTheDocument();
    });

    it('renders category label', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'authentication',
        message: 'Auth failed',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('Authentication Error')).toBeInTheDocument();
    });

    it('renders error code when provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        code: 'ECONNREFUSED',
        message: 'Connection refused',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('(ECONNREFUSED)')).toBeInTheDocument();
    });

    it('renders tool name when provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'tool_execution',
        message: 'Tool failed',
        toolName: 'search_code',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText(/Tool:/)).toBeInTheDocument();
      expect(screen.getByText('search_code')).toBeInTheDocument();
    });
  });

  describe('category-specific rendering', () => {
    const categories: Array<{ category: MCPErrorPayload['category']; label: string }> = [
      { category: 'connection', label: 'Connection Error' },
      { category: 'authentication', label: 'Authentication Error' },
      { category: 'validation', label: 'Validation Error' },
      { category: 'timeout', label: 'Timeout Error' },
      { category: 'rate_limit', label: 'Rate Limit Exceeded' },
      { category: 'not_found', label: 'Not Found' },
      { category: 'server', label: 'Server Error' },
      { category: 'tool_execution', label: 'Tool Execution Error' },
      { category: 'unknown', label: 'Unknown Error' },
    ];

    it.each(categories)('renders correct label for $category category', ({ category, label }) => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category,
        message: 'Test error',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText(label)).toBeInTheDocument();
    });
  });

  describe('suggestions rendering', () => {
    it('renders suggestions section when provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Connection failed',
        suggestions: [
          {
            action: 'Check network',
            description: 'Verify your network connection is working',
          },
        ],
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('Suggested Actions')).toBeInTheDocument();
      expect(screen.getByText('Check network')).toBeInTheDocument();
      expect(screen.getByText('Verify your network connection is working')).toBeInTheDocument();
    });

    it('renders multiple suggestions', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'authentication',
        message: 'Auth failed',
        suggestions: [
          { action: 'Check API key', description: 'Verify API key is valid' },
          { action: 'Refresh token', description: 'Try refreshing your token' },
          { action: 'Contact support', description: 'Get help from support' },
        ],
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('Check API key')).toBeInTheDocument();
      expect(screen.getByText('Refresh token')).toBeInTheDocument();
      expect(screen.getByText('Contact support')).toBeInTheDocument();
    });

    it('renders command in suggestion when provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Failed',
        suggestions: [
          {
            action: 'Restart server',
            description: 'Restart the MCP server',
            command: 'docker restart mcp-server',
          },
        ],
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('docker restart mcp-server')).toBeInTheDocument();
    });

    it('copies command to clipboard when copy button clicked', async () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Failed',
        suggestions: [
          {
            action: 'Fix it',
            description: 'Run this command',
            command: 'npm run fix',
          },
        ],
      };

      render(<MCPErrorRenderer error={error} />);

      const copyButton = screen.getByTitle('Copy command');
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith('npm run fix');
      });
    });
  });

  describe('details toggle', () => {
    it('does not show details toggle when no details provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Error',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.queryByText('Show Details')).not.toBeInTheDocument();
    });

    it('shows details toggle when details provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Error',
        details: { host: 'localhost', port: 8080 },
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByText('Show Details')).toBeInTheDocument();
    });

    it('toggles details visibility when clicked', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Error',
        details: { host: 'localhost', port: 8080 },
      };

      render(<MCPErrorRenderer error={error} />);

      // Initially hidden
      expect(screen.queryByText(/"host"/)).not.toBeInTheDocument();

      // Click to show
      fireEvent.click(screen.getByText('Show Details'));
      expect(screen.getByText(/localhost/)).toBeInTheDocument();
      expect(screen.getByText('Hide Details')).toBeInTheDocument();

      // Click to hide
      fireEvent.click(screen.getByText('Hide Details'));
      expect(screen.queryByText(/"host"/)).not.toBeInTheDocument();
    });
  });

  describe('retry functionality', () => {
    it('does not show retry button when not retryable', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'validation',
        message: 'Invalid input',
        retryable: false,
      };

      render(<MCPErrorRenderer error={error} onRetry={() => {}} />);

      expect(screen.queryByText('Retry')).not.toBeInTheDocument();
    });

    it('does not show retry button when no onRetry callback', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'timeout',
        message: 'Timeout',
        retryable: true,
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.queryByText('Retry')).not.toBeInTheDocument();
    });

    it('shows retry button when retryable and callback provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'timeout',
        message: 'Timeout',
        retryable: true,
      };

      render(<MCPErrorRenderer error={error} onRetry={() => {}} />);

      expect(screen.getByText('Retry')).toBeInTheDocument();
    });

    it('calls onRetry when retry button clicked', () => {
      const onRetry = vi.fn();
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Connection lost',
        retryable: true,
      };

      render(<MCPErrorRenderer error={error} onRetry={onRetry} />);

      fireEvent.click(screen.getByText('Retry'));
      expect(onRetry).toHaveBeenCalledTimes(1);
    });
  });

  describe('documentation link', () => {
    it('does not show docs link when not provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Error',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.queryByText('View Documentation')).not.toBeInTheDocument();
    });

    it('shows docs link when provided', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Error',
        documentationUrl: 'https://docs.example.com/errors',
      };

      render(<MCPErrorRenderer error={error} />);

      const link = screen.getByText('View Documentation');
      expect(link).toBeInTheDocument();
      expect(link.closest('a')).toHaveAttribute('href', 'https://docs.example.com/errors');
      expect(link.closest('a')).toHaveAttribute('target', '_blank');
      expect(link.closest('a')).toHaveAttribute('rel', 'noopener noreferrer');
    });
  });

  describe('accessibility', () => {
    it('has role="alert" for screen readers', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'server',
        message: 'Server error',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });

    it('has aria-live="polite" for dynamic updates', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'server',
        message: 'Server error',
      };

      render(<MCPErrorRenderer error={error} />);

      expect(screen.getByRole('alert')).toHaveAttribute('aria-live', 'polite');
    });
  });
});
