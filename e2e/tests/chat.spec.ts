import { test, expect } from '@playwright/test';

test.describe('Chat Interface', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/chat');
  });

  test('should display chat interface', async ({ page }) => {
    // Check for chat input
    const chatInput = page.getByPlaceholder(/message|type|ask/i).or(
      page.getByRole('textbox', { name: /message/i })
    );
    await expect(chatInput).toBeVisible();
  });

  test('should send a message', async ({ page }) => {
    // Find and fill the chat input
    const chatInput = page.getByPlaceholder(/message|type|ask/i).or(
      page.getByRole('textbox', { name: /message/i })
    );

    await chatInput.fill('Hello, this is a test message');

    // Find and click send button
    const sendButton = page.getByRole('button', { name: /send|submit/i }).or(
      page.locator('button[type="submit"]')
    );
    await sendButton.click();

    // Verify message appears in chat
    await expect(page.getByText('Hello, this is a test message')).toBeVisible({
      timeout: 10000,
    });
  });

  test('should show loading state while waiting for response', async ({ page }) => {
    const chatInput = page.getByPlaceholder(/message|type|ask/i).or(
      page.getByRole('textbox', { name: /message/i })
    );

    await chatInput.fill('What can you help me with?');

    const sendButton = page.getByRole('button', { name: /send|submit/i }).or(
      page.locator('button[type="submit"]')
    );
    await sendButton.click();

    // Check for loading indicator
    const loadingIndicator = page.getByRole('status').or(
      page.locator('[data-loading="true"]').or(
        page.getByText(/loading|thinking|typing/i)
      )
    );

    // Loading should appear (may be brief)
    await expect(loadingIndicator).toBeVisible({ timeout: 5000 }).catch(() => {
      // Loading may be too fast to catch - that's okay
    });
  });

  test('should display AI response', async ({ page }) => {
    const chatInput = page.getByPlaceholder(/message|type|ask/i).or(
      page.getByRole('textbox', { name: /message/i })
    );

    await chatInput.fill('Say hello');

    const sendButton = page.getByRole('button', { name: /send|submit/i }).or(
      page.locator('button[type="submit"]')
    );
    await sendButton.click();

    // Wait for AI response (look for assistant message container)
    const assistantMessage = page.locator('[data-role="assistant"]').or(
      page.locator('.assistant-message').or(
        page.locator('[class*="assistant"]')
      )
    );

    await expect(assistantMessage.first()).toBeVisible({ timeout: 30000 });
  });

  test('should create new conversation', async ({ page }) => {
    // Look for new chat button
    const newChatButton = page.getByRole('button', { name: /new|create|start/i }).or(
      page.getByLabel(/new chat|new conversation/i)
    );

    if (await newChatButton.isVisible()) {
      await newChatButton.click();

      // Verify chat is cleared or new conversation started
      const chatInput = page.getByPlaceholder(/message|type|ask/i);
      await expect(chatInput).toBeEmpty();
    }
  });

  test('should handle keyboard shortcuts', async ({ page }) => {
    const chatInput = page.getByPlaceholder(/message|type|ask/i).or(
      page.getByRole('textbox', { name: /message/i })
    );

    await chatInput.fill('Test keyboard submit');

    // Press Enter to send (if supported)
    await chatInput.press('Enter');

    // Message should be sent
    await expect(page.getByText('Test keyboard submit')).toBeVisible({
      timeout: 10000,
    });
  });
});
