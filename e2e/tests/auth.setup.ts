import { test as setup, expect } from '@playwright/test';
import path from 'path';

const authFile = path.join(__dirname, '../playwright/.auth/user.json');

/**
 * Authentication setup - runs before all tests to create authenticated state
 */
setup('authenticate', async ({ page }) => {
  // Navigate to login page
  await page.goto('/login');

  // Fill in login form
  await page.getByLabel('Email').fill('test@example.com');
  await page.getByLabel('Password').fill('testpassword123');

  // Click login button
  await page.getByRole('button', { name: /sign in|log in/i }).click();

  // Wait for successful login (redirect to dashboard or home)
  await expect(page).toHaveURL(/\/(dashboard|home|chat)?$/);

  // Verify we're logged in
  await expect(
    page.getByRole('button', { name: /account|profile|menu/i }).or(
      page.getByText(/welcome|dashboard/i)
    )
  ).toBeVisible({ timeout: 10000 });

  // Save storage state to file
  await page.context().storageState({ path: authFile });
});

setup('authenticate admin', async ({ page }) => {
  const adminAuthFile = path.join(__dirname, '../playwright/.auth/admin.json');

  // Navigate to login page
  await page.goto('/login');

  // Fill in admin credentials
  await page.getByLabel('Email').fill('admin@nexusai.com');
  await page.getByLabel('Password').fill('adminpassword123');

  // Click login button
  await page.getByRole('button', { name: /sign in|log in/i }).click();

  // Wait for successful login
  await expect(page).toHaveURL(/\/(dashboard|admin)?$/);

  // Save admin storage state
  await page.context().storageState({ path: adminAuthFile });
});
