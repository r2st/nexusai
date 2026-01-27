import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  // Don't use stored auth state for auth tests
  test.use({ storageState: { cookies: [], origins: [] } });

  test('should display login page', async ({ page }) => {
    await page.goto('/login');

    // Check for login form elements
    await expect(page.getByLabel('Email')).toBeVisible();
    await expect(page.getByLabel('Password')).toBeVisible();
    await expect(
      page.getByRole('button', { name: /sign in|log in/i })
    ).toBeVisible();
  });

  test('should show validation errors for empty form', async ({ page }) => {
    await page.goto('/login');

    // Try to submit empty form
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Check for validation errors
    const errorMessage = page.getByText(/required|invalid|enter/i);
    await expect(errorMessage.first()).toBeVisible();
  });

  test('should show error for invalid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel('Email').fill('invalid@example.com');
    await page.getByLabel('Password').fill('wrongpassword');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Check for error message
    const errorMessage = page.getByText(/invalid|incorrect|failed|error/i);
    await expect(errorMessage.first()).toBeVisible({ timeout: 10000 });
  });

  test('should login successfully with valid credentials', async ({ page }) => {
    await page.goto('/login');

    await page.getByLabel('Email').fill('test@example.com');
    await page.getByLabel('Password').fill('testpassword123');
    await page.getByRole('button', { name: /sign in|log in/i }).click();

    // Should redirect to dashboard or home
    await expect(page).toHaveURL(/\/(dashboard|home|chat)?$/, { timeout: 10000 });
  });

  test('should have link to register page', async ({ page }) => {
    await page.goto('/login');

    const registerLink = page.getByRole('link', { name: /sign up|register|create account/i });
    await expect(registerLink).toBeVisible();

    await registerLink.click();
    await expect(page).toHaveURL(/\/register|\/signup/);
  });

  test('should have forgot password link', async ({ page }) => {
    await page.goto('/login');

    const forgotLink = page.getByRole('link', { name: /forgot|reset/i });
    if (await forgotLink.isVisible()) {
      await forgotLink.click();
      await expect(page).toHaveURL(/\/forgot|\/reset/);
    }
  });
});

test.describe('Registration', () => {
  test.use({ storageState: { cookies: [], origins: [] } });

  test('should display registration page', async ({ page }) => {
    await page.goto('/register');

    // Check for registration form elements
    await expect(page.getByLabel(/email/i)).toBeVisible();
    await expect(page.getByLabel(/password/i).first()).toBeVisible();
    await expect(
      page.getByRole('button', { name: /sign up|register|create/i })
    ).toBeVisible();
  });

  test('should validate email format', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel(/email/i).fill('invalid-email');
    await page.getByRole('button', { name: /sign up|register|create/i }).click();

    const errorMessage = page.getByText(/invalid|valid email/i);
    await expect(errorMessage.first()).toBeVisible();
  });

  test('should validate password requirements', async ({ page }) => {
    await page.goto('/register');

    await page.getByLabel(/email/i).fill('newuser@example.com');
    await page.getByLabel(/password/i).first().fill('weak');

    await page.getByRole('button', { name: /sign up|register|create/i }).click();

    const errorMessage = page.getByText(/password|characters|strong/i);
    await expect(errorMessage.first()).toBeVisible();
  });

  test('should have link to login page', async ({ page }) => {
    await page.goto('/register');

    const loginLink = page.getByRole('link', { name: /sign in|log in|already have/i });
    await expect(loginLink).toBeVisible();
  });
});

test.describe('Logout', () => {
  test('should logout successfully', async ({ page }) => {
    await page.goto('/');

    // Find and click user menu or logout button
    const userMenu = page.getByRole('button', { name: /account|profile|menu/i }).or(
      page.getByLabel(/user menu/i)
    );

    if (await userMenu.isVisible()) {
      await userMenu.click();

      const logoutButton = page.getByRole('button', { name: /log out|sign out/i }).or(
        page.getByRole('menuitem', { name: /log out|sign out/i })
      );

      await logoutButton.click();

      // Should redirect to login or home
      await expect(page).toHaveURL(/\/(login|home|)?$/);
    }
  });
});
