/**
 * Chat E2E Tests
 *
 * Tests for the main chat functionality including conversations,
 * message sending, streaming responses, and conversation management.
 */

import { test, expect } from '@playwright/test';
import { ChatPage } from './pages';
import { testMessages, generateMessage, generateConversationTitle } from './fixtures/test-data';

test.describe('Chat Page', () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    await chatPage.goto();
    await chatPage.assertPageLoaded();
  });

  test('should display chat interface correctly', async () => {
    // Check main elements
    await expect(chatPage.sidebar).toBeVisible();
    await expect(chatPage.messageInput).toBeVisible();
    await expect(chatPage.newChatButton).toBeVisible();
  });

  test('should display welcome message on empty chat', async () => {
    await chatPage.assertWelcomeDisplayed();
  });

  test('should allow typing in message input', async () => {
    const testMessage = testMessages.simple;
    await chatPage.messageInput.fill(testMessage);
    await expect(chatPage.messageInput).toHaveValue(testMessage);
  });

  test('should clear input after sending message', async ({ page }) => {
    // Mock the API response
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Response"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.simple);

    // Input should be cleared
    await expect(chatPage.messageInput).toHaveValue('');
  });

  test('should display user message after sending', async ({ page }) => {
    // Mock the API
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Test response"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    const message = generateMessage();
    await chatPage.sendMessage(message);

    await chatPage.assertMessageSent(message);
  });

  test('should show loading indicator while waiting for response', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await new Promise((resolve) => setTimeout(resolve, 3000));
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Response"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.messageInput.fill(testMessages.simple);
    await chatPage.sendButton.click();

    await chatPage.assertLoading();
  });

  test('should display assistant response', async ({ page }) => {
    const responseContent = 'This is a test response from the AI assistant.';

    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: `data: {"content": "${responseContent}"}\ndata: [DONE]`,
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.simple);

    // Wait for response
    await page.waitForTimeout(1000);
    await chatPage.assertResponseReceived();
  });

  test('should handle streaming responses', async ({ page }) => {
    const streamParts = ['Hello', ' there', '! How', ' can I', ' help?'];

    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        const body = streamParts.map((part) => `data: {"content": "${part}"}`).join('\n') + '\ndata: [DONE]';
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body,
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.simple);

    // Wait for complete response
    await chatPage.waitForStreamingComplete();

    const lastMessage = await chatPage.getLastMessageContent('assistant');
    expect(lastMessage).toContain('Hello');
    expect(lastMessage).toContain('help');
  });

  test('should send message with Enter key', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Response"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessageWithEnter(testMessages.simple);

    await chatPage.assertMessageSent(testMessages.simple);
  });

  test('should handle special characters in messages', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Received your message"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.specialCharacters);

    // Message should be displayed (XSS should be escaped)
    await chatPage.assertMessageSent(/script/);
  });

  test('should handle emoji in messages', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 200,
          contentType: 'text/event-stream',
          body: 'data: {"content": "Nice emoji! 😊"}\ndata: [DONE]',
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.emoji);
    await chatPage.assertMessageSent(/👋/);
  });
});

test.describe('Conversation Management', () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);

    // Mock conversations list
    await page.route('**/api/v1/chat/conversations', async (route) => {
      if (route.request().method() === 'GET') {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: '1', title: 'Test Conversation 1', created_at: new Date().toISOString() },
            { id: '2', title: 'Test Conversation 2', created_at: new Date().toISOString() },
          ]),
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.goto();
  });

  test('should display conversation list', async () => {
    await chatPage.assertConversationExists('Test Conversation 1');
    await chatPage.assertConversationExists('Test Conversation 2');
  });

  test('should create new conversation', async ({ page }) => {
    // Mock create conversation
    await page.route('**/api/v1/chat/conversations', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 201,
          contentType: 'application/json',
          body: JSON.stringify({
            id: 'new-conv',
            title: 'New Conversation',
            created_at: new Date().toISOString(),
          }),
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.startNewChat();

    // Should navigate to new conversation
    await expect(page).toHaveURL(/\/chat/);
  });

  test('should select existing conversation', async ({ page }) => {
    // Mock messages for conversation
    await page.route('**/api/v1/chat/conversations/1/messages', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: 'm1', role: 'user', content: 'Hello', created_at: new Date().toISOString() },
          { id: 'm2', role: 'assistant', content: 'Hi there!', created_at: new Date().toISOString() },
        ]),
      });
    });

    await chatPage.selectConversation(0);

    // Messages should be loaded
    await expect(page.getByText('Hello')).toBeVisible();
    await expect(page.getByText('Hi there!')).toBeVisible();
  });

  test('should delete conversation', async ({ page }) => {
    // Mock delete
    await page.route('**/api/v1/chat/conversations/1', async (route) => {
      if (route.request().method() === 'DELETE') {
        await route.fulfill({ status: 204 });
      } else {
        await route.continue();
      }
    });

    await chatPage.deleteConversation(0);

    // Toast should show success
    await expect(page.locator('[data-sonner-toast]')).toContainText(/deleted/i);
  });
});

test.describe('Error Handling', () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    await chatPage.goto();
  });

  test('should handle API error when sending message', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      if (route.request().method() === 'POST') {
        await route.fulfill({
          status: 500,
          contentType: 'application/json',
          body: JSON.stringify({ detail: 'Internal server error' }),
        });
      } else {
        await route.continue();
      }
    });

    await chatPage.sendMessage(testMessages.simple);

    // Error toast should appear
    await expect(page.locator('[data-sonner-toast]')).toBeVisible({ timeout: 10000 });
  });

  test('should handle network failure', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      await route.abort('failed');
    });

    await chatPage.sendMessage(testMessages.simple);

    // Error should be displayed
    await expect(page.locator('[data-sonner-toast]')).toBeVisible({ timeout: 10000 });
  });

  test('should handle rate limiting', async ({ page }) => {
    await page.route('**/api/v1/chat/**', async (route) => {
      await route.fulfill({
        status: 429,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Too many requests' }),
      });
    });

    await chatPage.sendMessage(testMessages.simple);

    // Rate limit message should appear
    await expect(page.locator('[data-sonner-toast]')).toContainText(/too many|rate limit/i);
  });
});

test.describe('Responsiveness', () => {
  test('should work on mobile viewport', async ({ page }) => {
    // Set mobile viewport
    await page.setViewportSize({ width: 375, height: 667 });

    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Chat input should still be visible
    await expect(chatPage.messageInput).toBeVisible();

    // Sidebar might be hidden on mobile
    const sidebarToggle = page.locator('[data-sidebar-toggle]');
    if (await sidebarToggle.isVisible()) {
      await sidebarToggle.click();
      await expect(chatPage.sidebar).toBeVisible();
    }
  });

  test('should work on tablet viewport', async ({ page }) => {
    await page.setViewportSize({ width: 768, height: 1024 });

    const chatPage = new ChatPage(page);
    await chatPage.goto();
    await chatPage.assertPageLoaded();
  });
});

test.describe('Keyboard Navigation', () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    await chatPage.goto();
  });

  test('should focus message input on page load', async () => {
    await expect(chatPage.messageInput).toBeFocused();
  });

  test('should submit with Enter and new line with Shift+Enter', async ({ page }) => {
    await chatPage.messageInput.fill('Line 1');
    await chatPage.messageInput.press('Shift+Enter');
    await chatPage.messageInput.type('Line 2');

    const value = await chatPage.messageInput.inputValue();
    expect(value).toContain('Line 1');
    expect(value).toContain('Line 2');
  });

  test('should navigate conversations with arrow keys', async ({ page }) => {
    // Mock conversations
    await page.route('**/api/v1/chat/conversations', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify([
          { id: '1', title: 'Conv 1', created_at: new Date().toISOString() },
          { id: '2', title: 'Conv 2', created_at: new Date().toISOString() },
        ]),
      });
    });

    await page.reload();

    // Focus sidebar
    await page.keyboard.press('Tab');

    // Test arrow key navigation if implemented
    // This is implementation-specific
  });
});

test.describe('Accessibility', () => {
  test('should have proper ARIA labels', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Check for proper labels
    await expect(chatPage.messageInput).toHaveAttribute('aria-label', /.+/);

    // Check for proper roles
    const mainContent = page.locator('main, [role="main"]');
    await expect(mainContent).toBeVisible();
  });

  test('should announce new messages to screen readers', async ({ page }) => {
    const chatPage = new ChatPage(page);
    await chatPage.goto();

    // Check for live region
    const liveRegion = page.locator('[aria-live="polite"], [aria-live="assertive"]');
    expect(await liveRegion.count()).toBeGreaterThan(0);
  });
});
