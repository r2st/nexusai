export interface ToolCallPayload {
  type: 'tool_call';
  name: string;
  args?: Record<string, unknown>;
  status?: 'queued' | 'running' | 'completed' | 'failed';
  id?: string;
}

export interface ToolResultPayload {
  type: 'tool_result';
  name?: string;
  output?: string;
  success?: boolean;
  id?: string;
}

/**
 * MCP Error Categories for structured error handling
 */
export type MCPErrorCategory =
  | 'connection'      // Connection/network errors
  | 'authentication'  // Auth/permission errors
  | 'validation'      // Input validation errors
  | 'timeout'         // Request timeout errors
  | 'rate_limit'      // Rate limiting errors
  | 'not_found'       // Resource not found errors
  | 'server'          // Server-side errors
  | 'tool_execution'  // Tool execution failures
  | 'unknown';        // Unknown/unclassified errors

/**
 * Suggestion for resolving an MCP error
 */
export interface MCPErrorSuggestion {
  action: string;
  description: string;
  command?: string;
}

/**
 * Structured MCP error payload with category, suggestions, and context
 */
export interface MCPErrorPayload {
  type: 'mcp_error';
  category: MCPErrorCategory;
  code?: string;
  message: string;
  toolName?: string;
  suggestions?: MCPErrorSuggestion[];
  details?: Record<string, unknown>;
  retryable?: boolean;
  documentationUrl?: string;
}

export type ToolPayload = ToolCallPayload | ToolResultPayload | MCPErrorPayload;
