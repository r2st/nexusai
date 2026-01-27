/**
 * Visual Regression Tests
 *
 * Tests that capture screenshots and compare them against baselines
 * to detect unintended visual changes.
 */

import { test, expect } from '@playwright/test';

test.describe('Visual Regression', () => {
  test.describe('Login Page', () => {
    test('login page matches snapshot', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');

      // Wait for fonts and animations to settle
      await page.waitForTimeout(500);

      await expect(page).toHaveScreenshot('login-page.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('login page with filled form', async ({ page }) => {
      await page.goto('/login');
      await page.locator('#email').fill('test@example.com');
      await page.locator('#password').fill('password');

      await expect(page).toHaveScreenshot('login-page-filled.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('login page on mobile', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/login');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('login-page-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Register Page', () => {
    test('register page matches snapshot', async ({ page }) => {
      await page.goto('/register');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('register-page.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Chat Page', () => {
    test('empty chat state matches snapshot', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      await expect(page).toHaveScreenshot('chat-empty.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('chat with message matches snapshot', async ({ page }) => {
      // Mock a conversation with messages
      await page.route('**/api/v1/chat/conversations/*/messages', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: '1', role: 'user', content: 'Hello, how are you?', created_at: new Date().toISOString() },
            { id: '2', role: 'assistant', content: 'I\'m doing great! How can I help you today?', created_at: new Date().toISOString() },
          ]),
        });
      });

      await page.goto('/chat/1');
      await page.waitForLoadState('networkidle');
      await page.waitForTimeout(500);

      await expect(page).toHaveScreenshot('chat-with-messages.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('chat sidebar matches snapshot', async ({ page }) => {
      // Mock conversations list
      await page.route('**/api/v1/chat/conversations', async (route) => {
        await route.fulfill({
          status: 200,
          contentType: 'application/json',
          body: JSON.stringify([
            { id: '1', title: 'Python Help', created_at: new Date().toISOString() },
            { id: '2', title: 'Code Review', created_at: new Date().toISOString() },
            { id: '3', title: 'Architecture Discussion', created_at: new Date().toISOString() },
          ]),
        });
      });

      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      // Screenshot just the sidebar
      const sidebar = page.locator('aside, [data-sidebar]').first();
      await expect(sidebar).toHaveScreenshot('chat-sidebar.png', {
        animations: 'disabled',
      });
    });

    test('chat on mobile matches snapshot', async ({ page }) => {
      await page.setViewportSize({ width: 375, height: 667 });
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('chat-mobile.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Dark Mode', () => {
    test.beforeEach(async ({ page }) => {
      // Enable dark mode
      await page.emulateMedia({ colorScheme: 'dark' });
    });

    test('login page dark mode', async ({ page }) => {
      await page.goto('/login');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('login-page-dark.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });

    test('chat page dark mode', async ({ page }) => {
      await page.goto('/chat');
      await page.waitForLoadState('networkidle');

      await expect(page).toHaveScreenshot('chat-page-dark.png', {
        fullPage: true,
        animations: 'disabled',
      });
    });
  });

  test.describe('Component Snapshots', () => {
    test('button variants', async ({ page }) => {
      await page.goto('/login');

      // Screenshot the sign in button
      const primaryButton = page.getByRole('button', { name: /sign in/i });
      await expect(primaryButton).toHaveScreenshot('button-primary.png');

      // Screenshot outline buttons
      const outlineButton = page.getByRole('button', { name: /google/i });
      await expect(outlineButton).toHaveScreenshot('button-outline.png');
    });

    test('input fields', async ({ page }) => {
      await page.goto('/login');

      // Empty input
      const emailInput = page.locator('#email');
      await expect(emailInput).toHaveScreenshot('input-empty.png');

      // Filled input
      await emailInput.fill('test@example.com');
      await expect(emailInput).toHaveScreenshot('input-filled.png');

      // Focused input
      await emailInput.focus();
      await expect(emailInput).toHaveScreenshot('input-focused.png');
    });
  });

  test.describe('Responsive Breakpoints', () => {
    const breakpoints = [
      { name: 'mobile', width: 375, height: 667 },
      { name: 'tablet', width: 768, height: 1024 },
      { name: 'desktop', width: 1280, height: 800 },
      { name: 'wide', width: 1920, height: 1080 },
    ];

    for (const breakpoint of breakpoints) {
      test(`chat page at ${breakpoint.name} breakpoint`, async ({ page }) => {
        await page.setViewportSize({ width: breakpoint.width, height: breakpoint.height });
        await page.goto('/chat');
        await page.waitForLoadState('networkidle');

        await expect(page).toHaveScreenshot(`chat-${breakpoint.name}.png`, {
          fullPage: true,
          animations: 'disabled',
        });
      });
    }
  });
});

test.describe('Error State Visuals', () => {
  test('login error state', async ({ page }) => {
    // Mock failed login
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      });
    });

    await page.goto('/login');
    await page.locator('#email').fill('test@example.com');
    await page.locator('#password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in/i }).click();

    // Wait for error to appear
    await page.waitForSelector('[data-sonner-toast]');

    await expect(page).toHaveScreenshot('login-error.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });

  test('404 page', async ({ page }) => {
    await page.goto('/non-existent-page');
    await page.waitForLoadState('networkidle');

    await expect(page).toHaveScreenshot('404-page.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});

test.describe('Loading States', () => {
  test('chat loading state', async ({ page }) => {
    // Mock slow response
    await page.route('**/api/v1/chat/**', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 5000));
      await route.continue();
    });

    await page.goto('/chat');

    // Fill and send message
    await page.locator('textarea, [data-chat-input]').fill('Test message');
    await page.getByRole('button', { name: /send/i }).click();

    // Capture loading state
    await expect(page).toHaveScreenshot('chat-loading.png', {
      fullPage: true,
      animations: 'disabled',
    });
  });
});
