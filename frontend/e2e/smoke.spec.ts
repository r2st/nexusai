/**
 * Smoke Tests
 *
 * Quick health check tests that verify the application is running
 * and core functionality is working. These should run fast and
 * catch major issues early.
 */

import { test, expect } from '@playwright/test';

test.describe('Smoke Tests', () => {
  test('application is accessible', async ({ page }) => {
    const response = await page.goto('/');
    expect(response?.status()).toBeLessThan(400);
  });

  test('login page loads', async ({ page }) => {
    await page.goto('/login');

    // Check key elements
    await expect(page.locator('text=NexusAI')).toBeVisible();
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
    await expect(page.getByRole('button', { name: /sign in/i })).toBeVisible();
  });

  test('register page loads', async ({ page }) => {
    await page.goto('/register');

    await expect(page.locator('text=NexusAI')).toBeVisible();
    await expect(page.locator('#email')).toBeVisible();
    await expect(page.locator('#password')).toBeVisible();
  });

  test('protected routes redirect to login', async ({ page }) => {
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/login/);
  });

  test('static assets load correctly', async ({ page }) => {
    const responses: { url: string; status: number }[] = [];

    page.on('response', (response) => {
      const url = response.url();
      if (url.includes('/_next/') || url.includes('/static/')) {
        responses.push({ url, status: response.status() });
      }
    });

    await page.goto('/login');

    // All static assets should load successfully
    const failedAssets = responses.filter((r) => r.status >= 400);
    expect(failedAssets).toHaveLength(0);
  });

  test('no console errors on page load', async ({ page }) => {
    const errors: string[] = [];

    page.on('console', (msg) => {
      if (msg.type() === 'error') {
        // Ignore some expected errors
        const text = msg.text();
        if (!text.includes('favicon') && !text.includes('404')) {
          errors.push(text);
        }
      }
    });

    await page.goto('/login');
    await page.waitForLoadState('networkidle');

    expect(errors).toHaveLength(0);
  });

  test('page responds within acceptable time', async ({ page }) => {
    const startTime = Date.now();
    await page.goto('/login');
    await page.waitForLoadState('domcontentloaded');
    const loadTime = Date.now() - startTime;

    // Page should load within 5 seconds
    expect(loadTime).toBeLessThan(5000);
  });

  test('critical CSS is loaded', async ({ page }) => {
    await page.goto('/login');

    // Check that Tailwind classes are working
    const button = page.getByRole('button', { name: /sign in/i });
    const backgroundColor = await button.evaluate(
      (el) => window.getComputedStyle(el).backgroundColor
    );

    // Button should have some background color (not transparent)
    expect(backgroundColor).not.toBe('rgba(0, 0, 0, 0)');
  });

  test('JavaScript is executing', async ({ page }) => {
    await page.goto('/login');

    // Fill and check that React state updates
    await page.locator('#email').fill('test@example.com');
    const value = await page.locator('#email').inputValue();
    expect(value).toBe('test@example.com');
  });
});

test.describe('API Health Checks', () => {
  test('health endpoint responds', async ({ request }) => {
    const response = await request.get('/api/v1/health');

    // Health endpoint should return 200
    expect(response.status()).toBe(200);
  });

  test('API returns proper error format', async ({ request }) => {
    const response = await request.post('/api/v1/auth/login', {
      data: { email: '', password: '' },
    });

    // Should return 400 or 422 for validation error
    expect([400, 422]).toContain(response.status());

    // Should return JSON
    const contentType = response.headers()['content-type'];
    expect(contentType).toContain('application/json');
  });
});

test.describe('Authenticated Smoke Tests', () => {
  test('chat page loads after auth', async ({ page }) => {
    await page.goto('/chat');
    await page.waitForLoadState('networkidle');

    // Should be on chat page (auth state from setup)
    await expect(page).toHaveURL(/\/chat/);

    // Chat interface should be visible
    await expect(page.locator('textarea, [data-chat-input]')).toBeVisible();
  });

  test('can navigate between pages', async ({ page }) => {
    // Start at chat
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/chat/);

    // Navigate to agents (if link exists)
    const agentsLink = page.locator('a[href="/agents"], [data-nav="agents"]');
    if (await agentsLink.isVisible()) {
      await agentsLink.click();
      await expect(page).toHaveURL(/\/agents/);
    }

    // Navigate to analytics (if link exists)
    const analyticsLink = page.locator('a[href="/analytics"], [data-nav="analytics"]');
    if (await analyticsLink.isVisible()) {
      await analyticsLink.click();
      await expect(page).toHaveURL(/\/analytics/);
    }
  });

  test('user session persists across pages', async ({ page }) => {
    await page.goto('/chat');
    await page.goto('/agents');
    await page.goto('/chat');

    // Should still be authenticated
    await expect(page).toHaveURL(/\/chat/);
    await expect(page.locator('textarea, [data-chat-input]')).toBeVisible();
  });
});
