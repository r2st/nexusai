import type { ToolCallPayload, ToolPayload, MCPErrorPayload, MCPErrorCategory, MCPErrorSuggestion } from './types';

const TOOL_CALL_FENCE = /```tool_call\s*([\s\S]*?)```/g;
const TOOL_RESULT_FENCE = /```tool_result\s*([\s\S]*?)```/g;
const MCP_ERROR_FENCE = /```mcp_error\s*([\s\S]*?)```/g;
const INLINE_TOOL_CALL = /\[Calling tool:\s*([^\]]+)\]/g;
const INLINE_TOOL_RESULT = /\[Tool result:\s*([^\]]+)\]/g;
const INLINE_MCP_ERROR = /\[MCP Error:\s*([^\]]+)\]/g;

const VALID_ERROR_CATEGORIES: MCPErrorCategory[] = [
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

function parseJsonBlock(block: string): Record<string, unknown> | null {
  const trimmed = block.trim();
  if (!trimmed) return null;
  try {
    return JSON.parse(trimmed) as Record<string, unknown>;
  } catch {
    return null;
  }
}

function isValidErrorCategory(category: unknown): category is MCPErrorCategory {
  return typeof category === 'string' && VALID_ERROR_CATEGORIES.includes(category as MCPErrorCategory);
}

function parseSuggestions(raw: unknown): MCPErrorSuggestion[] | undefined {
  if (!Array.isArray(raw)) return undefined;

  const suggestions: MCPErrorSuggestion[] = [];
  for (const item of raw) {
    if (
      typeof item === 'object' &&
      item !== null &&
      typeof (item as Record<string, unknown>).action === 'string' &&
      typeof (item as Record<string, unknown>).description === 'string'
    ) {
      suggestions.push({
        action: (item as Record<string, unknown>).action as string,
        description: (item as Record<string, unknown>).description as string,
        command: typeof (item as Record<string, unknown>).command === 'string'
          ? ((item as Record<string, unknown>).command as string)
          : undefined,
      });
    }
  }
  return suggestions.length > 0 ? suggestions : undefined;
}

function parseMCPError(parsed: Record<string, unknown>): MCPErrorPayload | null {
  const message = typeof parsed.message === 'string' ? parsed.message : null;
  if (!message) return null;

  const category = isValidErrorCategory(parsed.category) ? parsed.category : 'unknown';

  return {
    type: 'mcp_error',
    category,
    code: typeof parsed.code === 'string' ? parsed.code : undefined,
    message,
    toolName: typeof parsed.toolName === 'string' ? parsed.toolName : undefined,
    suggestions: parseSuggestions(parsed.suggestions),
    details: typeof parsed.details === 'object' && parsed.details !== null
      ? (parsed.details as Record<string, unknown>)
      : undefined,
    retryable: typeof parsed.retryable === 'boolean' ? parsed.retryable : undefined,
    documentationUrl: typeof parsed.documentationUrl === 'string' ? parsed.documentationUrl : undefined,
  };
}

export function parseToolBlocks(content: string): {
  content: string;
  tools: ToolPayload[];
} {
  const tools: ToolPayload[] = [];

  let cleaned = content.replace(TOOL_CALL_FENCE, (_match, jsonBlock: string) => {
    const parsed = parseJsonBlock(jsonBlock);
    if (parsed && typeof parsed.name === 'string') {
      const status = typeof parsed.status === 'string'
        ? (parsed.status as ToolCallPayload['status'])
        : undefined;

      tools.push({
        type: 'tool_call',
        name: parsed.name,
        args: typeof parsed.args === 'object' ? (parsed.args as Record<string, unknown>) : undefined,
        status,
        id: typeof parsed.id === 'string' ? parsed.id : undefined,
      });
    }
    return '';
  });

  cleaned = cleaned.replace(TOOL_RESULT_FENCE, (_match, jsonBlock: string) => {
    const parsed = parseJsonBlock(jsonBlock);
    if (parsed) {
      tools.push({
        type: 'tool_result',
        name: typeof parsed.name === 'string' ? parsed.name : undefined,
        output: typeof parsed.output === 'string' ? parsed.output : undefined,
        success: typeof parsed.success === 'boolean' ? parsed.success : undefined,
        id: typeof parsed.id === 'string' ? parsed.id : undefined,
      });
    }
    return '';
  });

  // Parse MCP error blocks
  cleaned = cleaned.replace(MCP_ERROR_FENCE, (_match, jsonBlock: string) => {
    const parsed = parseJsonBlock(jsonBlock);
    if (parsed) {
      const error = parseMCPError(parsed);
      if (error) {
        tools.push(error);
      }
    }
    return '';
  });

  cleaned = cleaned.replace(INLINE_TOOL_CALL, (_match, name: string) => {
    const cleanName = name.replace('...', '').trim();
    if (cleanName) {
      tools.push({ type: 'tool_call', name: cleanName, status: 'running' });
    }
    return '';
  });

  cleaned = cleaned.replace(INLINE_TOOL_RESULT, (_match, output: string) => {
    const cleanOutput = output.trim();
    tools.push({
      type: 'tool_result',
      output: cleanOutput,
      success: true,
    });
    return '';
  });

  // Parse inline MCP errors (simple format)
  cleaned = cleaned.replace(INLINE_MCP_ERROR, (_match, errorMsg: string) => {
    const cleanError = errorMsg.trim();
    if (cleanError) {
      tools.push({
        type: 'mcp_error',
        category: 'unknown',
        message: cleanError,
      });
    }
    return '';
  });

  return {
    content: cleaned.trim(),
    tools,
  };
}
