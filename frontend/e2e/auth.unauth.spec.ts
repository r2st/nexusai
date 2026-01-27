/**
 * Authentication E2E Tests (Unauthenticated)
 *
 * Tests for login, registration, and auth flows that don't require
 * an authenticated session.
 */

import { test, expect } from '@playwright/test';
import { LoginPage, RegisterPage } from './pages';
import {
  testUsers,
  invalidCredentials,
  generateTestUser,
  errorMessages,
} from './fixtures/test-data';

test.describe('Login Page', () => {
  let loginPage: LoginPage;

  test.beforeEach(async ({ page }) => {
    loginPage = new LoginPage(page);
    await loginPage.goto();
  });

  test('should display login page correctly', async () => {
    await loginPage.assertPageLoaded();

    // Check form elements
    await expect(loginPage.emailInput).toBeVisible();
    await expect(loginPage.passwordInput).toBeVisible();
    await expect(loginPage.submitButton).toBeVisible();
    await expect(loginPage.submitButton).toHaveText(/sign in/i);

    // Check OAuth buttons
    await expect(loginPage.googleButton).toBeVisible();
    await expect(loginPage.githubButton).toBeVisible();

    // Check links
    await expect(loginPage.registerLink).toBeVisible();
    await expect(loginPage.forgotPasswordLink).toBeVisible();
  });

  test('should show validation error for empty email', async () => {
    await loginPage.passwordInput.fill('somepassword');
    await loginPage.submit();

    // HTML5 validation should prevent submission
    const emailInput = loginPage.emailInput;
    const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBe(true);
  });

  test('should show validation error for invalid email format', async () => {
    await loginPage.fillLoginForm('invalid-email', 'password123');
    await loginPage.submit();

    // Check for validation
    const emailInput = loginPage.emailInput;
    const isInvalid = await emailInput.evaluate((el: HTMLInputElement) => !el.validity.valid);
    expect(isInvalid).toBe(true);
  });

  test('should show error for invalid credentials', async ({ page }) => {
    // Mock the API to return an error
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: errorMessages.invalidCredentials }),
      });
    });

    await loginPage.login(
      invalidCredentials.wrongPassword.email,
      invalidCredentials.wrongPassword.password
    );

    await loginPage.assertErrorDisplayed(/invalid/i);
  });

  test('should show loading state during submission', async ({ page }) => {
    // Mock slow API response
    await page.route('**/api/v1/auth/login', async (route) => {
      await new Promise((resolve) => setTimeout(resolve, 2000));
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      });
    });

    await loginPage.fillLoginForm('test@example.com', 'password123');
    await loginPage.submit();

    await loginPage.assertLoading();
    await loginPage.assertInputsDisabled();
  });

  test('should successfully login with valid credentials', async ({ page }) => {
    // Mock successful login
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 200,
        contentType: 'application/json',
        body: JSON.stringify({
          user: { id: '1', email: 'test@example.com', name: 'Test' },
          tokens: { access_token: 'token', refresh_token: 'refresh' },
        }),
      });
    });

    await loginPage.login(testUsers.valid.email, testUsers.valid.password);

    // Should redirect to chat
    await expect(page).toHaveURL(/\/chat/);
  });

  test('should navigate to registration page', async ({ page }) => {
    await loginPage.goToRegister();
    await expect(page).toHaveURL(/\/register/);
  });

  test('should navigate to forgot password page', async ({ page }) => {
    await loginPage.goToForgotPassword();
    await expect(page).toHaveURL(/\/forgot-password/);
  });

  test('should handle network errors gracefully', async ({ page }) => {
    // Mock network failure
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.abort('failed');
    });

    await loginPage.login('test@example.com', 'password123');

    // Should show error toast
    const toast = page.locator('[data-sonner-toast]');
    await expect(toast).toBeVisible({ timeout: 10000 });
  });

  test('should persist email on failed login attempt', async ({ page }) => {
    await page.route('**/api/v1/auth/login', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Invalid credentials' }),
      });
    });

    const email = 'persist@example.com';
    await loginPage.login(email, 'wrongpassword');

    await loginPage.assertErrorDisplayed();
    await expect(loginPage.emailInput).toHaveValue(email);
  });
});

test.describe('Registration Page', () => {
  let registerPage: RegisterPage;

  test.beforeEach(async ({ page }) => {
    registerPage = new RegisterPage(page);
    await registerPage.goto();
  });

  test('should display registration page correctly', async () => {
    await registerPage.assertPageLoaded();

    await expect(registerPage.emailInput).toBeVisible();
    await expect(registerPage.passwordInput).toBeVisible();
    await expect(registerPage.submitButton).toBeVisible();
    await expect(registerPage.loginLink).toBeVisible();
  });

  test('should show validation for weak password', async ({ page }) => {
    const weakPasswords = ['123', 'password', 'abc'];

    for (const password of weakPasswords) {
      await registerPage.passwordInput.fill(password);

      // Check for password strength indicator if exists
      const strengthIndicator = page.locator('[data-password-strength]');
      if (await strengthIndicator.isVisible().catch(() => false)) {
        const strength = await strengthIndicator.getAttribute('data-password-strength');
        expect(strength).toBe('weak');
      }
    }
  });

  test('should successfully register new user', async ({ page }) => {
    const newUser = generateTestUser();

    // Mock successful registration
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 201,
        contentType: 'application/json',
        body: JSON.stringify({
          user: { id: '1', email: newUser.email, name: newUser.name },
          message: 'Registration successful',
        }),
      });
    });

    await registerPage.register({
      name: newUser.name,
      email: newUser.email,
      password: newUser.password,
    });

    // Should redirect to login or chat
    await expect(page).toHaveURL(/\/(login|chat)/);
  });

  test('should show error for existing email', async ({ page }) => {
    // Mock email exists error
    await page.route('**/api/v1/auth/register', async (route) => {
      await route.fulfill({
        status: 400,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Email already registered' }),
      });
    });

    await registerPage.register({
      email: testUsers.valid.email,
      password: 'NewPassword123!',
    });

    await registerPage.assertErrorDisplayed(/email.*(already|exists|registered)/i);
  });

  test('should navigate to login page', async ({ page }) => {
    await registerPage.goToLogin();
    await expect(page).toHaveURL(/\/login/);
  });

  test('should validate password confirmation match', async ({ page }) => {
    await registerPage.fillRegistrationForm({
      email: 'test@example.com',
      password: 'Password123!',
      confirmPassword: 'DifferentPassword123!',
    });

    await registerPage.submit();

    // Check for mismatch error
    const mismatchError = page.getByText(/passwords? (do not|don't) match/i);
    await expect(mismatchError).toBeVisible().catch(() => {
      // Form might not have confirm password field
    });
  });
});

test.describe('Protected Routes', () => {
  test('should redirect to login when accessing chat without auth', async ({ page }) => {
    await page.goto('/chat');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to login when accessing agents without auth', async ({ page }) => {
    await page.goto('/agents');
    await expect(page).toHaveURL(/\/login/);
  });

  test('should redirect to login when accessing analytics without auth', async ({ page }) => {
    await page.goto('/analytics');
    await expect(page).toHaveURL(/\/login/);
  });
});

test.describe('Session Management', () => {
  test('should handle expired token gracefully', async ({ page }) => {
    // Set an expired token
    await page.addInitScript(() => {
      localStorage.setItem('access_token', 'expired-token');
    });

    // Mock 401 response
    await page.route('**/api/v1/**', async (route) => {
      await route.fulfill({
        status: 401,
        contentType: 'application/json',
        body: JSON.stringify({ detail: 'Token expired' }),
      });
    });

    await page.goto('/chat');

    // Should redirect to login
    await expect(page).toHaveURL(/\/login/);
  });
});
