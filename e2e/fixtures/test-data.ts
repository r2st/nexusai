/**
 * Test data fixtures for E2E tests
 */

export const TEST_USER = {
  email: 'test@example.com',
  password: 'testpassword123',
  fullName: 'Test User',
};

export const TEST_ADMIN = {
  email: 'admin@nexusai.com',
  password: 'adminpassword123',
  fullName: 'Admin User',
};

export const TEST_MESSAGES = [
  'Hello, how can you help me?',
  'What features does NexusAI have?',
  'Can you explain RAG?',
  'Help me with code review',
  'Summarize this document',
];

export const TEST_DOCUMENTS = [
  {
    name: 'test-document.pdf',
    type: 'application/pdf',
    size: 1024,
  },
  {
    name: 'sample-text.txt',
    type: 'text/plain',
    size: 512,
  },
  {
    name: 'data.json',
    type: 'application/json',
    size: 256,
  },
];

export const TEST_ORGANIZATION = {
  name: 'Test Organization',
  slug: 'test-org',
};

export const TEST_PROJECT = {
  name: 'Test Project',
  description: 'A test project for E2E testing',
};

/**
 * Generate a unique email for testing
 */
export function generateTestEmail(): string {
  const timestamp = Date.now();
  return `test-user-${timestamp}@example.com`;
}

/**
 * Generate a random conversation name
 */
export function generateConversationName(): string {
  const adjectives = ['Quick', 'Smart', 'Helpful', 'Test'];
  const nouns = ['Chat', 'Conversation', 'Discussion', 'Session'];
  const adj = adjectives[Math.floor(Math.random() * adjectives.length)];
  const noun = nouns[Math.floor(Math.random() * nouns.length)];
  return `${adj} ${noun} ${Date.now()}`;
}
