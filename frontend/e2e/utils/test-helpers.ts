/**
 * E2E Test Helpers and Utilities
 */

import { Page, expect, Locator } from '@playwright/test';

/**
 * Wait for network to be idle (no pending requests)
 */
export async function waitForNetworkIdle(page: Page, timeout = 5000): Promise<void> {
  await page.waitForLoadState('networkidle', { timeout });
}

/**
 * Wait for a specific API response
 */
export async function waitForApiResponse(
  page: Page,
  urlPattern: string | RegExp,
  options: { status?: number; timeout?: number } = {}
): Promise<void> {
  const { status = 200, timeout = 10000 } = options;

  await page.waitForResponse(
    (response) =>
      (typeof urlPattern === 'string'
        ? response.url().includes(urlPattern)
        : urlPattern.test(response.url())) && response.status() === status,
    { timeout }
  );
}

/**
 * Fill a form field with retry on failure
 */
export async function fillField(
  page: Page,
  selector: string,
  value: string,
  options: { clear?: boolean; delay?: number } = {}
): Promise<void> {
  const { clear = true, delay = 0 } = options;
  const field = page.locator(selector);

  await field.waitFor({ state: 'visible' });

  if (clear) {
    await field.clear();
  }

  await field.fill(value);

  if (delay > 0) {
    await page.waitForTimeout(delay);
  }
}

/**
 * Click an element with retry and wait for navigation
 */
export async function clickAndWait(
  page: Page,
  selector: string,
  waitForUrl?: string | RegExp
): Promise<void> {
  const element = page.locator(selector);
  await element.waitFor({ state: 'visible' });

  if (waitForUrl) {
    await Promise.all([page.waitForURL(waitForUrl), element.click()]);
  } else {
    await element.click();
  }
}

/**
 * Check if an element is visible
 */
export async function isVisible(page: Page, selector: string): Promise<boolean> {
  try {
    await page.locator(selector).waitFor({ state: 'visible', timeout: 3000 });
    return true;
  } catch {
    return false;
  }
}

/**
 * Wait for toast notification
 */
export async function waitForToast(
  page: Page,
  text: string | RegExp,
  type: 'success' | 'error' | 'info' = 'success'
): Promise<void> {
  const toastSelector = '[data-sonner-toast]';
  const toast = page.locator(toastSelector).filter({ hasText: text });

  await toast.waitFor({ state: 'visible', timeout: 10000 });

  // Verify toast type if specified
  if (type === 'success') {
    await expect(toast).toHaveAttribute('data-type', 'success');
  } else if (type === 'error') {
    await expect(toast).toHaveAttribute('data-type', 'error');
  }
}

/**
 * Take a screenshot with a descriptive name
 */
export async function takeScreenshot(
  page: Page,
  name: string,
  options: { fullPage?: boolean } = {}
): Promise<void> {
  await page.screenshot({
    path: `test-results/screenshots/${name}-${Date.now()}.png`,
    fullPage: options.fullPage ?? false,
  });
}

/**
 * Mock an API endpoint
 */
export async function mockApi(
  page: Page,
  urlPattern: string | RegExp,
  response: {
    status?: number;
    body?: object | string;
    headers?: Record<string, string>;
    delay?: number;
  }
): Promise<void> {
  await page.route(urlPattern, async (route) => {
    if (response.delay) {
      await new Promise((resolve) => setTimeout(resolve, response.delay));
    }

    await route.fulfill({
      status: response.status ?? 200,
      contentType: 'application/json',
      body:
        typeof response.body === 'string'
          ? response.body
          : JSON.stringify(response.body ?? {}),
      headers: response.headers,
    });
  });
}

/**
 * Generate random test data
 */
export const testData = {
  email: () => `test-${Date.now()}@example.com`,
  password: () => `TestPass123!${Math.random().toString(36).slice(2, 8)}`,
  name: () => `Test User ${Math.random().toString(36).slice(2, 8)}`,
  message: () => `Test message ${Date.now()}`,
  conversationTitle: () => `Test Conversation ${new Date().toISOString().slice(0, 10)}`,
};

/**
 * Wait for element to have specific text
 */
export async function waitForText(
  locator: Locator,
  text: string | RegExp,
  timeout = 10000
): Promise<void> {
  await expect(locator).toContainText(text, { timeout });
}

/**
 * Retry an action multiple times
 */
export async function retry<T>(
  action: () => Promise<T>,
  options: { attempts?: number; delay?: number } = {}
): Promise<T> {
  const { attempts = 3, delay = 1000 } = options;

  let lastError: Error | undefined;

  for (let i = 0; i < attempts; i++) {
    try {
      return await action();
    } catch (error) {
      lastError = error as Error;
      if (i < attempts - 1) {
        await new Promise((resolve) => setTimeout(resolve, delay));
      }
    }
  }

  throw lastError;
}

/**
 * Assert page has no console errors
 */
export async function assertNoConsoleErrors(page: Page): Promise<void> {
  const errors: string[] = [];

  page.on('console', (msg) => {
    if (msg.type() === 'error') {
      errors.push(msg.text());
    }
  });

  // Wait a bit for any async errors
  await page.waitForTimeout(500);

  if (errors.length > 0) {
    throw new Error(`Console errors found:\n${errors.join('\n')}`);
  }
}

/**
 * Assert element count
 */
export async function assertCount(
  locator: Locator,
  expectedCount: number
): Promise<void> {
  await expect(locator).toHaveCount(expectedCount);
}

/**
 * Scroll to element
 */
export async function scrollToElement(
  page: Page,
  selector: string
): Promise<void> {
  const element = page.locator(selector);
  await element.scrollIntoViewIfNeeded();
}

/**
 * Get computed style property
 */
export async function getComputedStyle(
  page: Page,
  selector: string,
  property: string
): Promise<string> {
  return page.locator(selector).evaluate(
    (el, prop) => window.getComputedStyle(el).getPropertyValue(prop),
    property
  );
}

/**
 * Check accessibility violations (basic)
 */
export async function checkAccessibility(page: Page): Promise<void> {
  // Check for missing alt text
  const imagesWithoutAlt = await page.locator('img:not([alt])').count();
  expect(imagesWithoutAlt).toBe(0);

  // Check for missing form labels
  const inputsWithoutLabel = await page.evaluate(() => {
    const inputs = document.querySelectorAll('input:not([type="hidden"])');
    let count = 0;
    inputs.forEach((input) => {
      const id = input.getAttribute('id');
      const hasLabel =
        id && document.querySelector(`label[for="${id}"]`) !== null;
      const hasAriaLabel = input.hasAttribute('aria-label');
      const hasAriaLabelledBy = input.hasAttribute('aria-labelledby');
      if (!hasLabel && !hasAriaLabel && !hasAriaLabelledBy) {
        count++;
      }
    });
    return count;
  });
  expect(inputsWithoutLabel).toBe(0);

  // Check for proper heading hierarchy
  const headings = await page.evaluate(() => {
    const h = document.querySelectorAll('h1, h2, h3, h4, h5, h6');
    return Array.from(h).map((el) => parseInt(el.tagName[1]));
  });

  for (let i = 1; i < headings.length; i++) {
    const jump = headings[i] - headings[i - 1];
    expect(jump).toBeLessThanOrEqual(1); // No skipping heading levels
  }
}
