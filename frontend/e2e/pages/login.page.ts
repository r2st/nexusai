/**
 * Login Page Object
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class LoginPage extends BasePage {
  readonly url = '/login';

  // Locators
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly submitButton: Locator;
  readonly googleButton: Locator;
  readonly githubButton: Locator;
  readonly registerLink: Locator;
  readonly forgotPasswordLink: Locator;
  readonly logo: Locator;
  readonly welcomeHeading: Locator;
  readonly errorMessage: Locator;

  constructor(page: Page) {
    super(page);

    this.emailInput = page.locator('#email');
    this.passwordInput = page.locator('#password');
    this.submitButton = page.getByRole('button', { name: /sign in/i });
    this.googleButton = page.getByRole('button', { name: /google/i });
    this.githubButton = page.getByRole('button', { name: /github/i });
    this.registerLink = page.getByRole('link', { name: /sign up/i });
    this.forgotPasswordLink = page.getByRole('link', { name: /forgot password/i });
    this.logo = page.locator('text=NexusAI');
    this.welcomeHeading = page.getByRole('heading', { name: /welcome back/i });
    this.errorMessage = page.locator('[data-sonner-toast][data-type="error"]');
  }

  /**
   * Fill login form
   */
  async fillLoginForm(email: string, password: string): Promise<void> {
    await this.emailInput.fill(email);
    await this.passwordInput.fill(password);
  }

  /**
   * Submit login form
   */
  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  /**
   * Complete login flow
   */
  async login(email: string, password: string): Promise<void> {
    await this.fillLoginForm(email, password);
    await this.submit();
  }

  /**
   * Login and wait for redirect
   */
  async loginAndWaitForRedirect(email: string, password: string): Promise<void> {
    await this.fillLoginForm(email, password);
    await Promise.all([
      this.page.waitForURL(/\/chat/),
      this.submitButton.click(),
    ]);
  }

  /**
   * Navigate to registration page
   */
  async goToRegister(): Promise<void> {
    await this.registerLink.click();
    await this.page.waitForURL(/\/register/);
  }

  /**
   * Navigate to forgot password page
   */
  async goToForgotPassword(): Promise<void> {
    await this.forgotPasswordLink.click();
    await this.page.waitForURL(/\/forgot-password/);
  }

  /**
   * Click Google OAuth button
   */
  async clickGoogleLogin(): Promise<void> {
    await this.googleButton.click();
  }

  /**
   * Click GitHub OAuth button
   */
  async clickGitHubLogin(): Promise<void> {
    await this.githubButton.click();
  }

  /**
   * Assert login page is displayed
   */
  async assertPageLoaded(): Promise<void> {
    await expect(this.logo).toBeVisible();
    await expect(this.welcomeHeading).toBeVisible();
    await expect(this.emailInput).toBeVisible();
    await expect(this.passwordInput).toBeVisible();
    await expect(this.submitButton).toBeVisible();
  }

  /**
   * Assert error message is displayed
   */
  async assertErrorDisplayed(message?: string | RegExp): Promise<void> {
    await expect(this.errorMessage).toBeVisible({ timeout: 10000 });
    if (message) {
      await expect(this.errorMessage).toContainText(message);
    }
  }

  /**
   * Assert form validation error
   */
  async assertValidationError(fieldName: 'email' | 'password'): Promise<void> {
    const field = fieldName === 'email' ? this.emailInput : this.passwordInput;
    await expect(field).toHaveAttribute('aria-invalid', 'true');
  }

  /**
   * Assert submit button is loading
   */
  async assertLoading(): Promise<void> {
    await expect(this.submitButton).toContainText(/signing in/i);
    await expect(this.submitButton).toBeDisabled();
  }

  /**
   * Assert submit button is not loading
   */
  async assertNotLoading(): Promise<void> {
    await expect(this.submitButton).toContainText(/sign in/i);
    await expect(this.submitButton).toBeEnabled();
  }

  /**
   * Assert inputs are disabled during submission
   */
  async assertInputsDisabled(): Promise<void> {
    await expect(this.emailInput).toBeDisabled();
    await expect(this.passwordInput).toBeDisabled();
  }

  /**
   * Assert inputs are enabled
   */
  async assertInputsEnabled(): Promise<void> {
    await expect(this.emailInput).toBeEnabled();
    await expect(this.passwordInput).toBeEnabled();
  }
}
