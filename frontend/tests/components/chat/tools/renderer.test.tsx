/**
 * Tests for Tool Renderer component
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { ToolRenderer } from '@/components/chat/tools/renderer';
import type { ToolCallPayload, ToolResultPayload, MCPErrorPayload } from '@/components/chat/tools/types';

describe('ToolRenderer', () => {
  describe('tool_call rendering', () => {
    it('renders tool call with name', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'search_code',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText(/Tool Call:/)).toBeInTheDocument();
      expect(screen.getByText(/search_code/)).toBeInTheDocument();
    });

    it('renders tool call with running status', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'analyze',
        status: 'running',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Running')).toBeInTheDocument();
    });

    it('renders tool call with completed status', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'analyze',
        status: 'completed',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Completed')).toBeInTheDocument();
    });

    it('renders tool call with failed status', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'deploy',
        status: 'failed',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('renders tool call with queued status', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'build',
        status: 'queued',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Queued')).toBeInTheDocument();
    });

    it('renders tool call arguments when provided', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'search',
        args: { query: 'test', limit: 10 },
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText(/"query"/)).toBeInTheDocument();
      expect(screen.getByText(/"test"/)).toBeInTheDocument();
    });

    it('renders unknown status for undefined status', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'test',
        status: undefined,
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Unknown')).toBeInTheDocument();
    });
  });

  describe('tool_result rendering', () => {
    it('renders tool result with output', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
        output: 'Found 5 results',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText(/Tool Result/)).toBeInTheDocument();
      expect(screen.getByText('Found 5 results')).toBeInTheDocument();
    });

    it('renders tool result with name', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
        name: 'search_code',
        output: 'Results here',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText(/Tool Result: search_code/)).toBeInTheDocument();
    });

    it('renders success status badge', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
        output: 'Done',
        success: true,
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Success')).toBeInTheDocument();
    });

    it('renders failed status badge', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
        output: 'Error occurred',
        success: false,
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('Failed')).toBeInTheDocument();
    });

    it('renders no output message when output is empty', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByText('No output provided.')).toBeInTheDocument();
    });
  });

  describe('mcp_error rendering', () => {
    it('delegates to MCPErrorRenderer for mcp_error type', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'connection',
        message: 'Connection failed',
      };

      render(<ToolRenderer tool={error} />);

      // MCPErrorRenderer should be used
      expect(screen.getByRole('alert')).toBeInTheDocument();
      expect(screen.getByText('Connection Error')).toBeInTheDocument();
      expect(screen.getByText('Connection failed')).toBeInTheDocument();
    });

    it('passes onRetry to MCPErrorRenderer', () => {
      const onRetry = vi.fn();
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'timeout',
        message: 'Request timed out',
        retryable: true,
      };

      render(<ToolRenderer tool={error} onRetry={onRetry} />);

      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      expect(onRetry).toHaveBeenCalledTimes(1);
    });

    it('renders MCP error with all features', () => {
      const error: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'authentication',
        code: 'AUTH_FAILED',
        message: 'Invalid credentials',
        toolName: 'github_api',
        suggestions: [
          { action: 'Check token', description: 'Verify your GitHub token' },
        ],
        retryable: false,
      };

      render(<ToolRenderer tool={error} />);

      expect(screen.getByText('Authentication Error')).toBeInTheDocument();
      expect(screen.getByText('(AUTH_FAILED)')).toBeInTheDocument();
      expect(screen.getByText('Invalid credentials')).toBeInTheDocument();
      expect(screen.getByText('github_api')).toBeInTheDocument();
      expect(screen.getByText('Check token')).toBeInTheDocument();
    });
  });

  describe('type discrimination', () => {
    it('correctly identifies tool_call type', () => {
      const tool: ToolCallPayload = {
        type: 'tool_call',
        name: 'test',
      };

      const { container } = render(<ToolRenderer tool={tool} />);

      // Should render as section (tool call card), not alert (error)
      expect(container.querySelector('section')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('correctly identifies tool_result type', () => {
      const tool: ToolResultPayload = {
        type: 'tool_result',
        output: 'test',
      };

      const { container } = render(<ToolRenderer tool={tool} />);

      expect(container.querySelector('section')).toBeInTheDocument();
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });

    it('correctly identifies mcp_error type', () => {
      const tool: MCPErrorPayload = {
        type: 'mcp_error',
        category: 'unknown',
        message: 'test',
      };

      render(<ToolRenderer tool={tool} />);

      expect(screen.getByRole('alert')).toBeInTheDocument();
    });
  });
});
