/**
 * Test Data Fixtures
 */

export const testUsers = {
  valid: {
    email: process.env.TEST_USER_EMAIL || 'user@nexusai.dev',
    password: process.env.TEST_USER_PASSWORD || 'user123',
    name: 'Test User',
  },
  admin: {
    email: process.env.TEST_ADMIN_EMAIL || 'admin@nexusai.dev',
    password: process.env.TEST_ADMIN_PASSWORD || 'admin123',
    name: 'Admin User',
  },
  development: {
    // Development user seeded in the database
    email: process.env.TEST_DEV_EMAIL || 'user@nexusai.dev',
    password: process.env.TEST_DEV_PASSWORD || 'user123',
    name: 'Development User',
  },
  viewer: {
    email: process.env.TEST_VIEWER_EMAIL || 'viewer@nexusai.dev',
    password: process.env.TEST_VIEWER_PASSWORD || 'viewer123',
    name: 'Viewer User',
  },
} as const;

export const invalidCredentials = {
  wrongPassword: {
    email: 'test@example.com',
    password: 'WrongPassword123!',
  },
  nonExistentUser: {
    email: 'nonexistent@example.com',
    password: 'SomePassword123!',
  },
  invalidEmail: {
    email: 'invalid-email',
    password: 'SomePassword123!',
  },
  emptyPassword: {
    email: 'test@example.com',
    password: '',
  },
  shortPassword: {
    email: 'test@example.com',
    password: '123',
  },
} as const;

export const testMessages = {
  simple: 'Hello, how are you?',
  codeQuestion: 'Write a Python function to calculate factorial',
  mathQuestion: 'What is 2 + 2?',
  longMessage: `This is a longer message that spans multiple lines.
It contains several paragraphs and tests how the chat handles
longer content that might need to be scrolled or formatted
differently in the UI.`,
  markdown: `Can you explain this with:
- Bullet points
- **Bold text**
- *Italic text*
- \`code\``,
  specialCharacters: 'Test <script>alert("xss")</script> & special "chars"',
  emoji: 'Hello! 👋 How are you doing today? 🤔',
  unicode: 'Test unicode: 你好世界 مرحبا العالم שלום עולם',
} as const;

export const testConversations = {
  titles: [
    'Test Conversation 1',
    'Python Help',
    'Code Review Discussion',
    'Architecture Planning',
  ],
} as const;

export const apiResponses = {
  loginSuccess: {
    user: {
      id: 'user-123',
      email: 'test@example.com',
      name: 'Test User',
    },
    tokens: {
      access_token: 'mock-access-token',
      refresh_token: 'mock-refresh-token',
    },
  },
  loginFailure: {
    detail: 'Invalid email or password',
  },
  conversationsList: [
    {
      id: 'conv-1',
      title: 'Test Conversation 1',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
    {
      id: 'conv-2',
      title: 'Test Conversation 2',
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
    },
  ],
  newConversation: {
    id: 'conv-new',
    title: 'New Conversation',
    created_at: new Date().toISOString(),
    updated_at: new Date().toISOString(),
  },
  chatResponse: {
    id: 'msg-123',
    role: 'assistant',
    content: 'This is a test response from the AI assistant.',
    model_name: 'gemini-2.5-flash',
    created_at: new Date().toISOString(),
  },
  streamingResponse: `data: {"content": "This "}
data: {"content": "is "}
data: {"content": "a "}
data: {"content": "streaming "}
data: {"content": "response."}
data: [DONE]`,
} as const;

export const errorMessages = {
  invalidCredentials: 'Invalid email or password',
  emailRequired: 'Email is required',
  passwordRequired: 'Password is required',
  invalidEmail: 'Invalid email format',
  passwordTooShort: 'Password must be at least 8 characters',
  networkError: 'Network error. Please try again.',
  serverError: 'Server error. Please try again later.',
  sessionExpired: 'Session expired. Please log in again.',
  rateLimited: 'Too many requests. Please wait a moment.',
} as const;

export const selectors = {
  // Common
  toast: '[data-sonner-toast]',
  toastSuccess: '[data-sonner-toast][data-type="success"]',
  toastError: '[data-sonner-toast][data-type="error"]',
  loadingSpinner: '.animate-spin, [aria-busy="true"]',

  // Forms
  formError: '[data-form-error], .text-destructive',
  formField: '[data-form-field]',

  // Navigation
  navbar: 'nav, [role="navigation"]',
  sidebar: 'aside, [data-sidebar]',

  // Chat
  chatInput: 'textarea[placeholder*="message"], [data-chat-input]',
  sendButton: 'button[type="submit"], [data-send-button]',
  messageContainer: '[data-message], [role="article"]',
} as const;

export const urls = {
  home: '/',
  login: '/login',
  register: '/register',
  forgotPassword: '/forgot-password',
  chat: '/chat',
  agents: '/agents',
  analytics: '/analytics',
  settings: '/settings',
  api: {
    login: '/api/v1/auth/login',
    register: '/api/v1/auth/register',
    conversations: '/api/v1/chat/conversations',
    messages: '/api/v1/chat/messages',
  },
} as const;

/**
 * Generate unique test data
 */
export function generateTestUser() {
  const timestamp = Date.now();
  return {
    email: `test-${timestamp}@example.com`,
    password: `TestPass${timestamp}!`,
    name: `Test User ${timestamp}`,
  };
}

export function generateConversationTitle() {
  return `Test Conversation ${new Date().toISOString()}`;
}

export function generateMessage(prefix = 'Test') {
  return `${prefix} message at ${new Date().toISOString()}`;
}

/**
 * DevLake Test Data
 */
export const devlakeTestData = {
  // Test project configuration
  testProject: {
    name: process.env.DEVLAKE_TEST_PROJECT_NAME || 'bmv-e2e-test',
    repo: process.env.DEVLAKE_TEST_GITHUB_REPO || 'r2st/bright-mind-vision',
  },

  // Chat messages for DevLake operations
  messages: {
    healthCheck: 'Check if DevLake is healthy',
    listProjects: 'List all DevLake projects',
    listConnections: 'Show me all DevLake connections',
    listBlueprints: 'What blueprints are available in DevLake?',
    listPipelines: 'List the last 5 DevLake pipeline runs',
    setupGitHub: (repo: string, projectName: string) =>
      `Setup a DevLake project for ${repo} with project name ${projectName}`,
    getDORAMetrics: (projectName: string) =>
      `Show DORA metrics for project ${projectName}`,
    getPipelineStatus: (pipelineId: number) =>
      `Get the status of pipeline ${pipelineId}`,
  },

  // Tool calls
  toolCalls: {
    healthCheck: 'TOOL_CALL: devlake_health_check()',
    getPipeline: (id: number) => `TOOL_CALL: devlake_get_pipeline(pipeline_id=${id})`,
    getDORAMetrics: (project: string) =>
      `TOOL_CALL: devlake_get_dora_metrics(project_name='${project}')`,
    listProjects: (page = 1, limit = 10) =>
      `TOOL_CALL: devlake_list_projects(page=${page}, limit=${limit})`,
  },

  // Expected response patterns
  responsePatterns: {
    healthCheck: /health|status|devlake|running|available|connected/i,
    projectList: /project|no projects|list|found|available/i,
    connectionList: /connection|github|no connections|plugin/i,
    pipelineStatus: /pipeline|status|running|completed|failed|not found|error/i,
    doraMetrics: /dora|deployment frequency|lead time|change failure|mean time|no data|metrics/i,
    setupSuccess: /setup|created|project|connection|pipeline|success/i,
    error: /error|failed|not found|unavailable/i,
  },

  // Mock widget payloads
  widgets: {
    dora: {
      type: 'dora' as const,
      title: 'DORA Metrics',
      timeframe: 'Last 30 days',
      metrics: {
        deploymentFrequency: 2.5,
        leadTimeForChanges: 48,
        meanTimeToRecovery: 4,
        changeFailureRate: 15,
      },
      units: {
        deploymentFrequency: 'per day',
        leadTimeForChanges: 'hours',
        meanTimeToRecovery: 'hours',
        changeFailureRate: '%',
      },
    },
    pipelineProgress: {
      type: 'pipeline_progress' as const,
      title: 'Data Sync Progress',
      pipelineId: 1,
      pipelineName: 'sync-bmv',
      status: 'TASK_RUNNING' as const,
      progress: 45,
      totalTasks: 4,
      finishedTasks: 2,
      projectName: 'bmv',
      repoName: 'r2st/bright-mind-vision',
      pollUrl: '/api/v1/devlake/pipelines/1',
    },
    insights: {
      type: 'insights' as const,
      title: 'Engineering Insights',
      summary: 'Key metrics from your repository',
      items: [
        { label: 'Total Commits', value: '150', trend: 'up' as const },
        { label: 'Pull Requests', value: '32', trend: 'up' as const },
        { label: 'Issues Closed', value: '18', trend: 'flat' as const },
        { label: 'Active Contributors', value: '5', trend: 'down' as const },
      ],
    },
  },
} as const;
