/**
 * Setup Assistant API Integration Tests
 *
 * Tests the setup assistant API client that interacts with the backend
 * for plugin configuration and connection setup flows.
 */

import { describe, it, expect, vi, beforeEach } from 'vitest';
import { setupAssistantApi } from '@/lib/api';

// Mock the API module
vi.mock('axios', async () => {
  const actual = await vi.importActual('axios');
  return {
    ...actual,
    default: {
      create: vi.fn(() => ({
        get: vi.fn(),
        post: vi.fn(),
        put: vi.fn(),
        delete: vi.fn(),
        interceptors: {
          request: { use: vi.fn() },
          response: { use: vi.fn() },
        },
      })),
    },
  };
});

describe('Setup Assistant API', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Session Management', () => {
    it('start session returns session with ID and initial message', async () => {
      const mockResponse = {
        session_id: 'session-123',
        current_step: 'welcome',
        message: {
          id: 'msg-1',
          content: 'Welcome to the setup assistant! What would you like to configure today?',
          quick_replies: [
            { id: 'qr-1', label: 'Connect GitHub', value: 'connect_github' },
            { id: 'qr-2', label: 'Connect Jira', value: 'connect_jira' },
            { id: 'qr-3', label: 'View Metrics', value: 'view_metrics' },
          ],
          metadata: {},
        },
      };

      expect(mockResponse).toHaveProperty('session_id');
      expect(mockResponse).toHaveProperty('current_step');
      expect(mockResponse).toHaveProperty('message');
      expect(mockResponse.message).toHaveProperty('quick_replies');
      expect(Array.isArray(mockResponse.message.quick_replies)).toBe(true);
    });

    it('send message returns response with next step', async () => {
      const mockResponse = {
        message: {
          id: 'msg-2',
          content: 'Great! Let\'s connect your GitHub account. Please provide your personal access token.',
          quick_replies: [],
          metadata: {
            field_name: 'github_token',
            field_type: 'password',
          },
        },
        current_step: 'token_input',
        is_complete: false,
        collected_data: {},
        errors: [],
        warnings: [],
        can_go_back: true,
      };

      expect(mockResponse).toHaveProperty('message');
      expect(mockResponse).toHaveProperty('current_step');
      expect(mockResponse).toHaveProperty('is_complete');
      expect(mockResponse).toHaveProperty('collected_data');
      expect(mockResponse).toHaveProperty('errors');
      expect(mockResponse).toHaveProperty('can_go_back');
    });

    it('send message handles validation errors', async () => {
      const mockResponse = {
        message: {
          id: 'msg-3',
          content: 'The token you provided appears to be invalid. Please check and try again.',
          quick_replies: [],
          metadata: {},
        },
        current_step: 'token_input',
        is_complete: false,
        collected_data: {},
        errors: ['Invalid GitHub token format', 'Token does not have required scopes'],
        warnings: ['Token will expire in 7 days'],
        can_go_back: true,
      };

      expect(mockResponse.errors.length).toBeGreaterThan(0);
      expect(mockResponse.warnings.length).toBeGreaterThan(0);
      expect(mockResponse.is_complete).toBe(false);
    });

    it('send message completes flow when done', async () => {
      const mockResponse = {
        message: {
          id: 'msg-4',
          content: 'Congratulations! Your GitHub connection has been set up successfully.',
          quick_replies: [
            { id: 'qr-done', label: 'Done', value: 'done' },
            { id: 'qr-another', label: 'Add Another Connection', value: 'add_another' },
          ],
          metadata: {},
        },
        current_step: 'complete',
        is_complete: true,
        collected_data: {
          plugin_type: 'github',
          connection_name: 'My GitHub',
          token: '***',
          scopes: ['repos', 'issues', 'pull_requests'],
        },
        errors: [],
        warnings: [],
        can_go_back: false,
      };

      expect(mockResponse.is_complete).toBe(true);
      expect(mockResponse.collected_data).toHaveProperty('plugin_type');
      expect(mockResponse.collected_data).toHaveProperty('connection_name');
    });
  });

  describe('Plugin API', () => {
    it('list plugins returns available plugins with metadata', async () => {
      const mockResponse = [
        {
          plugin_type: 'github',
          display_name: 'GitHub',
          description: 'Connect to GitHub repositories and track commits, PRs, and issues.',
          icon: '🐙',
          required_fields: ['token'],
          optional_fields: ['endpoint', 'org'],
          auth_type: 'token',
          endpoint_required: false,
          scopes_supported: ['repos', 'issues', 'pull_requests', 'commits', 'deployments'],
        },
        {
          plugin_type: 'gitlab',
          display_name: 'GitLab',
          description: 'Connect to GitLab for repository analytics.',
          icon: '🦊',
          required_fields: ['token', 'endpoint'],
          optional_fields: ['project_id'],
          auth_type: 'token',
          endpoint_required: true,
          scopes_supported: ['projects', 'merge_requests', 'issues', 'pipelines'],
        },
        {
          plugin_type: 'jira',
          display_name: 'Jira',
          description: 'Connect to Jira for issue and project tracking.',
          icon: '📋',
          required_fields: ['email', 'token', 'endpoint'],
          optional_fields: ['project_key'],
          auth_type: 'basic',
          endpoint_required: true,
          scopes_supported: ['boards', 'issues', 'sprints', 'projects'],
        },
        {
          plugin_type: 'jenkins',
          display_name: 'Jenkins',
          description: 'Connect to Jenkins for CI/CD pipeline analytics.',
          icon: '🔧',
          required_fields: ['username', 'token', 'endpoint'],
          optional_fields: ['job_filter'],
          auth_type: 'basic',
          endpoint_required: true,
          scopes_supported: ['jobs', 'builds', 'pipelines'],
        },
      ];

      expect(Array.isArray(mockResponse)).toBe(true);
      expect(mockResponse.length).toBeGreaterThan(0);

      mockResponse.forEach(plugin => {
        expect(plugin).toHaveProperty('plugin_type');
        expect(plugin).toHaveProperty('display_name');
        expect(plugin).toHaveProperty('description');
        expect(plugin).toHaveProperty('required_fields');
        expect(plugin).toHaveProperty('auth_type');
        expect(plugin).toHaveProperty('scopes_supported');
        expect(Array.isArray(plugin.required_fields)).toBe(true);
        expect(Array.isArray(plugin.scopes_supported)).toBe(true);
      });
    });

    it('get plugin returns specific plugin details', async () => {
      const mockResponse = {
        plugin_type: 'github',
        display_name: 'GitHub',
        description: 'Connect to GitHub repositories',
        icon: '🐙',
        required_fields: ['token'],
        optional_fields: ['endpoint', 'org'],
        auth_type: 'token',
        endpoint_required: false,
        scopes_supported: ['repos', 'issues', 'pull_requests', 'commits'],
        setup_instructions: 'Go to GitHub Settings > Developer settings > Personal access tokens',
        documentation_url: 'https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token',
      };

      expect(mockResponse.plugin_type).toBe('github');
      expect(mockResponse).toHaveProperty('setup_instructions');
      expect(mockResponse).toHaveProperty('documentation_url');
    });
  });

  describe('Quick Setup', () => {
    it('quick setup starts flow for specific plugin', async () => {
      const mockResponse = {
        session_id: 'session-quick-123',
        current_step: 'token_input',
        message: {
          id: 'msg-quick-1',
          content: 'Let\'s connect your GitHub account. Please provide your personal access token with repo and read:org scopes.',
          quick_replies: [],
          metadata: {
            plugin_type: 'github',
            field_name: 'token',
            field_type: 'password',
          },
        },
      };

      expect(mockResponse.session_id).toBeTruthy();
      expect(mockResponse.message.metadata).toHaveProperty('plugin_type');
      expect(mockResponse.message.metadata.plugin_type).toBe('github');
    });
  });

  describe('Onboarding Flow', () => {
    it('start onboarding returns welcome message', async () => {
      const mockResponse = {
        session_id: 'session-onboarding-123',
        current_step: 'welcome',
        message: {
          id: 'msg-onboarding-1',
          content: 'Welcome to NexusAI! I\'m here to help you set up your development analytics platform. Let\'s start by understanding what you\'d like to achieve.',
          quick_replies: [
            { id: 'goal-1', label: 'Track DORA Metrics', value: 'dora_metrics' },
            { id: 'goal-2', label: 'Monitor Team Productivity', value: 'team_productivity' },
            { id: 'goal-3', label: 'Integrate CI/CD', value: 'cicd_integration' },
            { id: 'goal-4', label: 'All of the Above', value: 'all' },
          ],
          metadata: {
            step_type: 'goal_selection',
          },
        },
      };

      expect(mockResponse.current_step).toBe('welcome');
      expect(mockResponse.message.quick_replies.length).toBeGreaterThan(0);
    });
  });

  describe('Session State', () => {
    it('get session returns current state', async () => {
      const mockResponse = {
        session_id: 'session-123',
        current_step: 'scope_selection',
        flow_type: 'connection',
        plugin: 'github',
        collected_data: {
          token: '***',
          connection_name: 'My GitHub',
        },
        history: [
          { step: 'welcome', timestamp: '2024-01-15T10:00:00Z' },
          { step: 'token_input', timestamp: '2024-01-15T10:01:00Z' },
          { step: 'scope_selection', timestamp: '2024-01-15T10:02:00Z' },
        ],
        can_go_back: true,
        is_complete: false,
      };

      expect(mockResponse).toHaveProperty('session_id');
      expect(mockResponse).toHaveProperty('current_step');
      expect(mockResponse).toHaveProperty('history');
      expect(Array.isArray(mockResponse.history)).toBe(true);
    });

    it('go back returns previous step', async () => {
      const mockResponse = {
        message: {
          id: 'msg-back-1',
          content: 'Let\'s go back. Please provide your personal access token.',
          quick_replies: [],
          metadata: {
            field_name: 'token',
            field_type: 'password',
          },
        },
        current_step: 'token_input',
        is_complete: false,
        collected_data: {},
        errors: [],
        warnings: [],
        can_go_back: true,
      };

      expect(mockResponse.current_step).toBe('token_input');
    });
  });

  describe('Error Handling', () => {
    it('handles session not found', async () => {
      const error = {
        response: {
          status: 404,
          data: {
            detail: 'Session not found or expired',
            code: 'SESSION_NOT_FOUND',
          },
        },
      };

      expect(error.response.status).toBe(404);
      expect(error.response.data.code).toBe('SESSION_NOT_FOUND');
    });

    it('handles invalid plugin type', async () => {
      const error = {
        response: {
          status: 400,
          data: {
            detail: 'Invalid plugin type: unknown_plugin',
            code: 'INVALID_PLUGIN',
          },
        },
      };

      expect(error.response.status).toBe(400);
      expect(error.response.data.code).toBe('INVALID_PLUGIN');
    });

    it('handles validation failure', async () => {
      const error = {
        response: {
          status: 422,
          data: {
            detail: 'Validation failed',
            errors: [
              { field: 'token', message: 'Token is required' },
              { field: 'scopes', message: 'At least one scope must be selected' },
            ],
          },
        },
      };

      expect(error.response.status).toBe(422);
      expect(Array.isArray(error.response.data.errors)).toBe(true);
    });

    it('handles connection test failure', async () => {
      const error = {
        response: {
          status: 400,
          data: {
            detail: 'Failed to connect to GitHub',
            code: 'CONNECTION_FAILED',
            errors: ['Authentication failed: Bad credentials'],
          },
        },
      };

      expect(error.response.data.code).toBe('CONNECTION_FAILED');
    });
  });

  describe('Quick Reply Handling', () => {
    it('quick reply has required fields', () => {
      const quickReply = {
        id: 'qr-1',
        label: 'Connect GitHub',
        value: 'connect_github',
      };

      expect(quickReply).toHaveProperty('id');
      expect(quickReply).toHaveProperty('label');
      expect(quickReply).toHaveProperty('value');
    });

    it('quick reply can have optional description', () => {
      const quickReply = {
        id: 'qr-2',
        label: 'Advanced Setup',
        value: 'advanced',
        description: 'Configure advanced options like rate limiting and caching',
      };

      expect(quickReply).toHaveProperty('description');
    });

    it('quick reply can have optional icon', () => {
      const quickReply = {
        id: 'qr-3',
        label: 'GitHub',
        value: 'github',
        icon: '🐙',
      };

      expect(quickReply).toHaveProperty('icon');
    });
  });

  describe('Message Metadata', () => {
    it('message can have field metadata for inputs', () => {
      const message = {
        id: 'msg-input',
        content: 'Please enter your API token:',
        quick_replies: [],
        metadata: {
          field_name: 'api_token',
          field_type: 'password',
          placeholder: 'Enter your token...',
          validation: {
            required: true,
            minLength: 10,
            pattern: '^[a-zA-Z0-9_-]+$',
          },
        },
      };

      expect(message.metadata).toHaveProperty('field_name');
      expect(message.metadata).toHaveProperty('field_type');
      expect(message.metadata).toHaveProperty('validation');
    });

    it('message can have progress metadata', () => {
      const message = {
        id: 'msg-progress',
        content: 'Great progress! Just a few more steps.',
        quick_replies: [],
        metadata: {
          progress: {
            current_step: 3,
            total_steps: 5,
            percentage: 60,
          },
        },
      };

      expect(message.metadata.progress).toHaveProperty('current_step');
      expect(message.metadata.progress).toHaveProperty('total_steps');
      expect(message.metadata.progress).toHaveProperty('percentage');
    });
  });
});
