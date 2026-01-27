/**
 * Tests for MCP tool/error parser
 */

import { describe, it, expect } from 'vitest';
import { parseToolBlocks } from '@/components/chat/tools/parser';

describe('parseToolBlocks', () => {
  describe('tool_call parsing', () => {
    it('parses fenced tool_call blocks with JSON', () => {
      const content = `Here is some text
\`\`\`tool_call
{"name": "search_code", "args": {"query": "test"}, "status": "running"}
\`\`\`
More text`;

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'tool_call',
        name: 'search_code',
        args: { query: 'test' },
        status: 'running',
        id: undefined,
      });
      expect(result.content).toBe('Here is some text\n\nMore text');
    });

    it('parses inline tool call format', () => {
      const content = 'Starting search [Calling tool: search_code...] waiting';

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'tool_call',
        name: 'search_code',
        status: 'running',
      });
      expect(result.content).toBe('Starting search  waiting');
    });

    it('handles tool_call with all fields', () => {
      const content = `\`\`\`tool_call
{"name": "get_metrics", "args": {"project": "nexus"}, "status": "completed", "id": "tool-123"}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools[0]).toEqual({
        type: 'tool_call',
        name: 'get_metrics',
        args: { project: 'nexus' },
        status: 'completed',
        id: 'tool-123',
      });
    });
  });

  describe('tool_result parsing', () => {
    it('parses fenced tool_result blocks', () => {
      const content = `\`\`\`tool_result
{"name": "search_code", "output": "Found 5 results", "success": true}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'tool_result',
        name: 'search_code',
        output: 'Found 5 results',
        success: true,
        id: undefined,
      });
    });

    it('parses inline tool result format', () => {
      const content = 'Here is the answer [Tool result: Operation completed] done';

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'tool_result',
        output: 'Operation completed',
        success: true,
      });
    });

    it('handles tool_result with failure', () => {
      const content = `\`\`\`tool_result
{"name": "deploy", "output": "Deployment failed", "success": false, "id": "result-456"}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools[0]).toEqual({
        type: 'tool_result',
        name: 'deploy',
        output: 'Deployment failed',
        success: false,
        id: 'result-456',
      });
    });
  });

  describe('mcp_error parsing', () => {
    it('parses fenced mcp_error blocks with all fields', () => {
      const content = `\`\`\`mcp_error
{
  "category": "connection",
  "code": "ECONNREFUSED",
  "message": "Failed to connect to MCP server",
  "toolName": "devlake_metrics",
  "suggestions": [
    {"action": "Check server status", "description": "Verify the MCP server is running", "command": "docker ps | grep mcp"}
  ],
  "details": {"host": "localhost", "port": 8080},
  "retryable": true,
  "documentationUrl": "https://docs.nexusai.com/mcp/errors"
}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'mcp_error',
        category: 'connection',
        code: 'ECONNREFUSED',
        message: 'Failed to connect to MCP server',
        toolName: 'devlake_metrics',
        suggestions: [
          {
            action: 'Check server status',
            description: 'Verify the MCP server is running',
            command: 'docker ps | grep mcp',
          },
        ],
        details: { host: 'localhost', port: 8080 },
        retryable: true,
        documentationUrl: 'https://docs.nexusai.com/mcp/errors',
      });
    });

    it('parses mcp_error with minimal fields', () => {
      const content = `\`\`\`mcp_error
{"message": "Something went wrong"}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools[0]).toEqual({
        type: 'mcp_error',
        category: 'unknown',
        message: 'Something went wrong',
        code: undefined,
        toolName: undefined,
        suggestions: undefined,
        details: undefined,
        retryable: undefined,
        documentationUrl: undefined,
      });
    });

    it('parses inline MCP error format', () => {
      const content = 'Processing failed [MCP Error: Connection timeout] please retry';

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(1);
      expect(result.tools[0]).toEqual({
        type: 'mcp_error',
        category: 'unknown',
        message: 'Connection timeout',
      });
      expect(result.content).toBe('Processing failed  please retry');
    });

    it('validates error categories', () => {
      const validCategories = [
        'connection',
        'authentication',
        'validation',
        'timeout',
        'rate_limit',
        'not_found',
        'server',
        'tool_execution',
        'unknown',
      ];

      for (const category of validCategories) {
        const content = `\`\`\`mcp_error
{"category": "${category}", "message": "Test error"}
\`\`\``;

        const result = parseToolBlocks(content);
        expect(result.tools[0]).toHaveProperty('category', category);
      }
    });

    it('defaults invalid category to unknown', () => {
      const content = `\`\`\`mcp_error
{"category": "invalid_category", "message": "Test error"}
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools[0]).toHaveProperty('category', 'unknown');
    });

    it('ignores mcp_error without message', () => {
      const content = `\`\`\`mcp_error
{"category": "connection", "code": "ERR001"}
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools).toHaveLength(0);
    });

    it('parses multiple suggestions correctly', () => {
      const content = `\`\`\`mcp_error
{
  "message": "Authentication failed",
  "category": "authentication",
  "suggestions": [
    {"action": "Check API key", "description": "Verify your API key is valid"},
    {"action": "Refresh token", "description": "Try refreshing your auth token", "command": "nexus auth refresh"},
    {"action": "Contact support", "description": "If issue persists, contact support"}
  ]
}
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools[0]).toHaveProperty('suggestions');
      const error = result.tools[0] as { suggestions: Array<{ action: string; description: string; command?: string }> };
      expect(error.suggestions).toHaveLength(3);
      expect(error.suggestions[0].command).toBeUndefined();
      expect(error.suggestions[1].command).toBe('nexus auth refresh');
    });

    it('filters invalid suggestions', () => {
      const content = `\`\`\`mcp_error
{
  "message": "Error",
  "suggestions": [
    {"action": "Valid", "description": "Valid suggestion"},
    {"action": "Missing description"},
    {"description": "Missing action"},
    "not an object",
    null
  ]
}
\`\`\``;

      const result = parseToolBlocks(content);
      const error = result.tools[0] as { suggestions?: Array<{ action: string; description: string }> };
      expect(error.suggestions).toHaveLength(1);
      expect(error.suggestions![0].action).toBe('Valid');
    });
  });

  describe('mixed content parsing', () => {
    it('parses multiple tool blocks in order', () => {
      const content = `Starting analysis
\`\`\`tool_call
{"name": "search", "status": "running"}
\`\`\`
Searching...
\`\`\`tool_result
{"name": "search", "output": "Found results", "success": true}
\`\`\`
Done`;

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(2);
      expect(result.tools[0].type).toBe('tool_call');
      expect(result.tools[1].type).toBe('tool_result');
      expect(result.content).toBe('Starting analysis\n\nSearching...\n\nDone');
    });

    it('handles tool call followed by error', () => {
      const content = `\`\`\`tool_call
{"name": "deploy", "status": "running"}
\`\`\`
\`\`\`mcp_error
{"message": "Deployment failed", "category": "server", "toolName": "deploy"}
\`\`\``;

      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(2);
      expect(result.tools[0].type).toBe('tool_call');
      expect(result.tools[1].type).toBe('mcp_error');
      expect((result.tools[1] as { toolName?: string }).toolName).toBe('deploy');
    });

    it('handles inline formats mixed with fenced blocks', () => {
      const content = `[Calling tool: search...]
\`\`\`tool_result
{"output": "Results found"}
\`\`\`
[MCP Error: Rate limited]`;

      const result = parseToolBlocks(content);

      // Parser processes in regex order: fenced blocks first, then inline
      // So tool_result (fenced) comes before tool_call (inline) and mcp_error (inline)
      expect(result.tools).toHaveLength(3);
      expect(result.tools[0].type).toBe('tool_result'); // fenced block processed first
      expect(result.tools[1].type).toBe('tool_call');   // inline tool_call
      expect(result.tools[2].type).toBe('mcp_error');   // inline mcp_error
    });
  });

  describe('edge cases', () => {
    it('handles empty content', () => {
      const result = parseToolBlocks('');
      expect(result.tools).toHaveLength(0);
      expect(result.content).toBe('');
    });

    it('handles content with no tool blocks', () => {
      const content = 'This is just regular text with no tools.';
      const result = parseToolBlocks(content);

      expect(result.tools).toHaveLength(0);
      expect(result.content).toBe(content);
    });

    it('handles malformed JSON gracefully', () => {
      const content = `\`\`\`tool_call
{not valid json}
\`\`\`
\`\`\`mcp_error
{also not valid}
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools).toHaveLength(0);
    });

    it('handles empty fenced blocks', () => {
      const content = `\`\`\`tool_call
\`\`\`
\`\`\`mcp_error
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools).toHaveLength(0);
    });

    it('preserves whitespace in cleaned content', () => {
      const content = `Line 1

\`\`\`tool_call
{"name": "test"}
\`\`\`

Line 2`;

      const result = parseToolBlocks(content);
      expect(result.content).toBe('Line 1\n\n\n\nLine 2');
    });

    it('handles nested code blocks in content', () => {
      const content = `Here is some code:
\`\`\`javascript
console.log("hello");
\`\`\`
And a tool call:
\`\`\`tool_call
{"name": "analyze"}
\`\`\``;

      const result = parseToolBlocks(content);
      expect(result.tools).toHaveLength(1);
      expect(result.content).toContain('```javascript');
    });
  });
});
