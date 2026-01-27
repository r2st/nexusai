/**
 * Register Page Object
 */

import { Page, Locator, expect } from '@playwright/test';
import { BasePage } from './base.page';

export class RegisterPage extends BasePage {
  readonly url = '/register';

  // Locators
  readonly nameInput: Locator;
  readonly emailInput: Locator;
  readonly passwordInput: Locator;
  readonly confirmPasswordInput: Locator;
  readonly termsCheckbox: Locator;
  readonly submitButton: Locator;
  readonly googleButton: Locator;
  readonly githubButton: Locator;
  readonly loginLink: Locator;
  readonly logo: Locator;
  readonly heading: Locator;
  readonly errorMessage: Locator;
  readonly successMessage: Locator;

  constructor(page: Page) {
    super(page);

    this.nameInput = page.locator('#name');
    this.emailInput = page.locator('#email');
    this.passwordInput = page.locator('#password');
    this.confirmPasswordInput = page.locator('#confirmPassword, #confirm-password');
    this.termsCheckbox = page.locator('input[type="checkbox"]').first();
    this.submitButton = page.getByRole('button', { name: /sign up|create account|register/i });
    this.googleButton = page.getByRole('button', { name: /google/i });
    this.githubButton = page.getByRole('button', { name: /github/i });
    this.loginLink = page.getByRole('link', { name: /sign in|log in/i });
    this.logo = page.locator('text=NexusAI');
    this.heading = page.getByRole('heading', { name: /create|sign up|register/i });
    this.errorMessage = page.locator('[data-sonner-toast][data-type="error"]');
    this.successMessage = page.locator('[data-sonner-toast][data-type="success"]');
  }

  /**
   * Fill registration form
   */
  async fillRegistrationForm(data: {
    name?: string;
    email: string;
    password: string;
    confirmPassword?: string;
  }): Promise<void> {
    if (data.name) {
      await this.nameInput.fill(data.name);
    }
    await this.emailInput.fill(data.email);
    await this.passwordInput.fill(data.password);
    if (data.confirmPassword && await this.confirmPasswordInput.isVisible()) {
      await this.confirmPasswordInput.fill(data.confirmPassword);
    }
  }

  /**
   * Accept terms and conditions
   */
  async acceptTerms(): Promise<void> {
    if (await this.termsCheckbox.isVisible()) {
      await this.termsCheckbox.check();
    }
  }

  /**
   * Submit registration form
   */
  async submit(): Promise<void> {
    await this.submitButton.click();
  }

  /**
   * Complete registration flow
   */
  async register(data: {
    name?: string;
    email: string;
    password: string;
    confirmPassword?: string;
    acceptTerms?: boolean;
  }): Promise<void> {
    await this.fillRegistrationForm({
      name: data.name,
      email: data.email,
      password: data.password,
      confirmPassword: data.confirmPassword ?? data.password,
    });

    if (data.acceptTerms !== false) {
      await this.acceptTerms();
    }

    await this.submit();
  }

  /**
   * Register and wait for redirect
   */
  async registerAndWaitForRedirect(data: {
    name?: string;
    email: string;
    password: string;
  }): Promise<void> {
    await this.fillRegistrationForm({
      name: data.name,
      email: data.email,
      password: data.password,
      confirmPassword: data.password,
    });
    await this.acceptTerms();

    await Promise.all([
      this.page.waitForURL(/\/(chat|login|verify)/),
      this.submitButton.click(),
    ]);
  }

  /**
   * Navigate to login page
   */
  async goToLogin(): Promise<void> {
    await this.loginLink.click();
    await this.page.waitForURL(/\/login/);
  }

  /**
   * Assert register page is displayed
   */
  async assertPageLoaded(): Promise<void> {
    await expect(this.logo).toBeVisible();
    await expect(this.heading).toBeVisible();
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
   * Assert success message is displayed
   */
  async assertSuccessDisplayed(message?: string | RegExp): Promise<void> {
    await expect(this.successMessage).toBeVisible({ timeout: 10000 });
    if (message) {
      await expect(this.successMessage).toContainText(message);
    }
  }

  /**
   * Assert password strength indicator
   */
  async assertPasswordStrength(strength: 'weak' | 'medium' | 'strong'): Promise<void> {
    const indicator = this.page.locator('[data-password-strength]');
    if (await indicator.isVisible()) {
      await expect(indicator).toHaveAttribute('data-password-strength', strength);
    }
  }

  /**
   * Assert password mismatch error
   */
  async assertPasswordMismatch(): Promise<void> {
    const errorText = this.page.getByText(/passwords? (do not|don't) match/i);
    await expect(errorText).toBeVisible();
  }

  /**
   * Assert email already exists error
   */
  async assertEmailExistsError(): Promise<void> {
    await expect(this.errorMessage).toContainText(/email.*(already|exists|taken)/i);
  }
}
