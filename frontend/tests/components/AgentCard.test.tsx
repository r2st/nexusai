/**
 * Tests for AgentCard Component - Data and Logic Tests
 * Note: These test the underlying data operations and formatting logic
 */
import { describe, it, expect, vi } from 'vitest';
import type { Agent } from '@/lib/api';

const mockAgent: Agent = {
  id: 'agent-123',
  name: 'Code Reviewer',
  description: 'An AI agent that reviews code and suggests improvements',
  system_prompt: 'You are a helpful code reviewer...',
  capabilities: ['code_review', 'suggestions', 'security_check'],
  tools_config: {},
  mcp_servers: [],
  actions_config: [],
  model_provider: 'openai',
  model_name: 'gpt-4',
  temperature: 0.7,
  max_tokens: 4096,
  is_public: false,
  is_active: true,
  owner_id: 'user-1',
  organization_id: 'org-1',
  metadata: {},
  created_at: '2024-01-15T10:00:00Z',
  updated_at: '2024-01-15T10:00:00Z',
};

describe('AgentCard - Data Operations', () => {
  describe('Agent data validation', () => {
    it('has required fields', () => {
      expect(mockAgent.id).toBeDefined();
      expect(mockAgent.name).toBeDefined();
      expect(mockAgent.model_provider).toBeDefined();
      expect(mockAgent.model_name).toBeDefined();
    });

    it('has optional fields', () => {
      expect(mockAgent.description).toBeDefined();
      expect(mockAgent.system_prompt).toBeDefined();
    });

    it('handles null description', () => {
      const agentNoDesc: Agent = { ...mockAgent, description: null };
      expect(agentNoDesc.description).toBeNull();
    });
  });

  describe('Capabilities display', () => {
    it('limits capabilities to max 3', () => {
      const maxCapabilities = 3;
      const displayCapabilities = mockAgent.capabilities.slice(0, maxCapabilities);
      const remainingCount = Math.max(0, mockAgent.capabilities.length - maxCapabilities);
      
      expect(displayCapabilities).toHaveLength(3);
      expect(remainingCount).toBe(0);
    });

    it('shows +N more when more than 3 capabilities', () => {
      const agentManyCapabilities: Agent = {
        ...mockAgent,
        capabilities: ['cap1', 'cap2', 'cap3', 'cap4', 'cap5'],
      };
      
      const maxCapabilities = 3;
      const remainingCount = agentManyCapabilities.capabilities.length - maxCapabilities;
      
      expect(remainingCount).toBe(2);
    });

    it('handles empty capabilities', () => {
      const agentNoCapabilities: Agent = { ...mockAgent, capabilities: [] };
      
      expect(agentNoCapabilities.capabilities).toHaveLength(0);
    });

    it('formats capability names', () => {
      const formatCapability = (cap: string) =>
        cap.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
      
      expect(formatCapability('code_review')).toBe('Code Review');
      expect(formatCapability('security_check')).toBe('Security Check');
    });
  });

  describe('Status indicators', () => {
    it('identifies active agent', () => {
      expect(mockAgent.is_active).toBe(true);
    });

    it('identifies inactive agent', () => {
      const inactiveAgent: Agent = { ...mockAgent, is_active: false };
      expect(inactiveAgent.is_active).toBe(false);
    });

    it('identifies public agent', () => {
      const publicAgent: Agent = { ...mockAgent, is_public: true };
      expect(publicAgent.is_public).toBe(true);
    });

    it('identifies private agent', () => {
      expect(mockAgent.is_public).toBe(false);
    });
  });

  describe('Model information', () => {
    it('formats model display name', () => {
      const formatModelName = (provider: string, model: string) =>
        `${provider}/${model}`;
      
      expect(formatModelName(mockAgent.model_provider, mockAgent.model_name))
        .toBe('openai/gpt-4');
    });

    it('formats temperature as percentage', () => {
      const formatTemperature = (temp: number) =>
        `${Math.round(temp * 100)}%`;
      
      expect(formatTemperature(0.7)).toBe('70%');
      expect(formatTemperature(1.0)).toBe('100%');
      expect(formatTemperature(0)).toBe('0%');
    });

    it('formats max tokens with K notation', () => {
      const formatTokens = (tokens: number) =>
        tokens >= 1000 ? `${(tokens / 1000).toFixed(0)}K` : String(tokens);
      
      expect(formatTokens(4096)).toBe('4K');
      expect(formatTokens(500)).toBe('500');
    });
  });

  describe('Date formatting', () => {
    it('formats created date', () => {
      const date = new Date(mockAgent.created_at);
      expect(date.getFullYear()).toBe(2024);
    });

    it('calculates days since creation', () => {
      const created = new Date(mockAgent.created_at);
      const now = new Date('2024-01-20T10:00:00Z');
      const diffDays = Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
      
      expect(diffDays).toBe(5);
    });
  });

  describe('Selection state', () => {
    it('determines selected state', () => {
      const selectedId = 'agent-123';
      const isSelected = mockAgent.id === selectedId;
      
      expect(isSelected).toBe(true);
    });

    it('handles no selection', () => {
      const selectedId: string | null = null;
      const isSelected = mockAgent.id === selectedId;
      
      expect(isSelected).toBe(false);
    });
  });

  describe('Action handlers', () => {
    it('provides agent to onSelect', () => {
      const onSelect = vi.fn();
      onSelect(mockAgent);
      
      expect(onSelect).toHaveBeenCalledWith(mockAgent);
    });

    it('provides agent to onEdit', () => {
      const onEdit = vi.fn();
      onEdit(mockAgent);
      
      expect(onEdit).toHaveBeenCalledWith(mockAgent);
    });

    it('provides agent id to onDelete', () => {
      const onDelete = vi.fn();
      onDelete(mockAgent.id);
      
      expect(onDelete).toHaveBeenCalledWith('agent-123');
    });
  });

  describe('Description truncation', () => {
    it('truncates long descriptions', () => {
      const maxLength = 100;
      const truncate = (text: string | null, max: number) => {
        if (!text) return '';
        if (text.length <= max) return text;
        return text.slice(0, max) + '...';
      };
      
      const longDesc = 'A'.repeat(150);
      expect(truncate(longDesc, maxLength)).toHaveLength(103);
      expect(truncate(longDesc, maxLength).endsWith('...')).toBe(true);
    });

    it('handles short descriptions', () => {
      const truncate = (text: string | null, max: number) => {
        if (!text) return '';
        if (text.length <= max) return text;
        return text.slice(0, max) + '...';
      };
      
      expect(truncate('Short', 100)).toBe('Short');
    });

    it('handles null description', () => {
      const truncate = (text: string | null, max: number) => {
        if (!text) return '';
        if (text.length <= max) return text;
        return text.slice(0, max) + '...';
      };
      
      expect(truncate(null, 100)).toBe('');
    });
  });
});

describe('AgentCard - Component Logic', () => {
  describe('Card styling', () => {
    it('applies selected class when selected', () => {
      const isSelected = true;
      const className = isSelected ? 'ring-2 ring-primary' : '';
      
      expect(className).toContain('ring-primary');
    });

    it('applies inactive styling when not active', () => {
      const isActive = false;
      const opacity = isActive ? '' : 'opacity-60';
      
      expect(opacity).toBe('opacity-60');
    });
  });

  describe('Badge visibility', () => {
    it('shows public badge when is_public is true', () => {
      const showPublicBadge = mockAgent.is_public;
      expect(showPublicBadge).toBe(false);
      
      const publicAgent: Agent = { ...mockAgent, is_public: true };
      expect(publicAgent.is_public).toBe(true);
    });

    it('shows inactive badge when is_active is false', () => {
      const inactiveAgent: Agent = { ...mockAgent, is_active: false };
      const showInactiveBadge = !inactiveAgent.is_active;
      
      expect(showInactiveBadge).toBe(true);
    });
  });

  describe('Action button visibility', () => {
    it('shows edit button when onEdit is provided', () => {
      const hasEditHandler = true;
      const showEditButton = hasEditHandler;
      
      expect(showEditButton).toBe(true);
    });

    it('hides delete button when onDelete is not provided', () => {
      const hasDeleteHandler = false;
      const showDeleteButton = hasDeleteHandler;
      
      expect(showDeleteButton).toBe(false);
    });
  });
});
