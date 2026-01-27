/**
 * Base Page Object - Foundation for all page objects
 */

import { Page, Locator, expect } from '@playwright/test';

export abstract class BasePage {
  readonly page: Page;
  abstract readonly url: string;

  constructor(page: Page) {
    this.page = page;
  }

  /**
   * Navigate to this page
   */
  async goto(): Promise<void> {
    await this.page.goto(this.url);
    await this.waitForPageLoad();
    await this.dismissConsentBanner();
  }

  /**
   * Dismiss consent banner if present
   */
  async dismissConsentBanner(): Promise<void> {
    // Set localStorage to dismiss consent banner
    await this.page.evaluate(() => {
      localStorage.setItem('nexus_consent_accepted', 'true');
    });

    // Check if banner is visible and click Accept All if so
    const acceptButton = this.page.locator('button:has-text("Accept All")');
    if (await acceptButton.isVisible({ timeout: 1000 }).catch(() => false)) {
      await acceptButton.click();
      // Wait for banner to disappear
      await this.page.locator('.fixed.bottom-0').waitFor({ state: 'hidden', timeout: 3000 }).catch(() => {});
    }
  }

  /**
   * Wait for page to fully load
   */
  async waitForPageLoad(): Promise<void> {
    await this.page.waitForLoadState('domcontentloaded');
  }

  /**
   * Check if current URL matches this page
   */
  async isCurrentPage(): Promise<boolean> {
    const currentUrl = this.page.url();
    return currentUrl.includes(this.url);
  }

  /**
   * Get page title
   */
  async getTitle(): Promise<string> {
    return this.page.title();
  }

  /**
   * Wait for navigation to this page
   */
  async waitForNavigation(): Promise<void> {
    await this.page.waitForURL(`**${this.url}*`);
  }

  /**
   * Take screenshot of current state
   */
  async screenshot(name: string): Promise<void> {
    await this.page.screenshot({
      path: `test-results/screenshots/${name}.png`,
      fullPage: true,
    });
  }

  /**
   * Get element by test ID
   */
  getByTestId(testId: string): Locator {
    return this.page.getByTestId(testId);
  }

  /**
   * Get element by role
   */
  getByRole(role: Parameters<Page['getByRole']>[0], options?: Parameters<Page['getByRole']>[1]): Locator {
    return this.page.getByRole(role, options);
  }

  /**
   * Get element by text
   */
  getByText(text: string | RegExp, options?: Parameters<Page['getByText']>[1]): Locator {
    return this.page.getByText(text, options);
  }

  /**
   * Get element by label
   */
  getByLabel(text: string | RegExp, options?: Parameters<Page['getByLabel']>[1]): Locator {
    return this.page.getByLabel(text, options);
  }

  /**
   * Get element by placeholder
   */
  getByPlaceholder(text: string | RegExp, options?: Parameters<Page['getByPlaceholder']>[1]): Locator {
    return this.page.getByPlaceholder(text, options);
  }

  /**
   * Assert element is visible
   */
  async assertVisible(locator: Locator, timeout?: number): Promise<void> {
    await expect(locator).toBeVisible({ timeout });
  }

  /**
   * Assert element is hidden
   */
  async assertHidden(locator: Locator, timeout?: number): Promise<void> {
    await expect(locator).toBeHidden({ timeout });
  }

  /**
   * Assert element contains text
   */
  async assertText(locator: Locator, text: string | RegExp, timeout?: number): Promise<void> {
    await expect(locator).toContainText(text, { timeout });
  }

  /**
   * Assert URL contains path
   */
  async assertUrl(path: string | RegExp): Promise<void> {
    await expect(this.page).toHaveURL(path);
  }

  /**
   * Wait for loading spinner to disappear
   */
  async waitForLoadingComplete(): Promise<void> {
    const spinner = this.page.locator('[data-loading="true"], .animate-spin, [aria-busy="true"]');
    await spinner.waitFor({ state: 'hidden', timeout: 30000 }).catch(() => {
      // Spinner might not exist, which is fine
    });
  }

  /**
   * Fill form input
   */
  async fillInput(selector: string | Locator, value: string): Promise<void> {
    const locator = typeof selector === 'string' ? this.page.locator(selector) : selector;
    await locator.fill(value);
  }

  /**
   * Click element and wait
   */
  async clickAndWait(locator: Locator): Promise<void> {
    await locator.click();
    await this.waitForLoadingComplete();
  }
}
