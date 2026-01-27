/**
 * Authentication Setup
 *
 * This file runs before all tests to authenticate and save the auth state.
 * Other tests can then reuse this authenticated state.
 */

import { test as setup, expect } from '@playwright/test';
import { testUsers } from './fixtures/test-data';
import { LoginPage } from './pages';

const authFile = 'e2e/.auth/user.json';

setup('authenticate', async ({ page }) => {
  const loginPage = new LoginPage(page);

  // Set consent before navigating to avoid banner blocking interactions
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('nexus_consent_accepted', 'true');
  });

  // Navigate to login page
  await loginPage.goto();
  await loginPage.assertPageLoaded();

  // Use development user credentials (seeded in database)
  const credentials = testUsers.development;

  // Fill and submit login form
  await loginPage.fillLoginForm(credentials.email, credentials.password);
  await loginPage.submit();

  // Wait for successful redirect to chat
  await page.waitForURL(/\/chat/, { timeout: 30000 });

  // Verify we're authenticated
  await expect(page.locator('textarea, [data-chat-input]')).toBeVisible({ timeout: 10000 });

  // Save authentication state
  await page.context().storageState({ path: authFile });
});

setup('authenticate admin', async ({ page }) => {
  const adminAuthFile = 'e2e/.auth/admin.json';
  const loginPage = new LoginPage(page);

  // Set consent before navigating to avoid banner blocking interactions
  await page.goto('/');
  await page.evaluate(() => {
    localStorage.setItem('nexus_consent_accepted', 'true');
  });

  // Navigate to login page
  await loginPage.goto();

  // Use admin credentials
  const credentials = testUsers.admin;

  // Fill and submit login form
  await loginPage.fillLoginForm(credentials.email, credentials.password);
  await loginPage.submit();

  // Wait for redirect (might fail if admin user doesn't exist)
  try {
    await page.waitForURL(/\/chat|\/admin/, { timeout: 30000 });
    await page.context().storageState({ path: adminAuthFile });
  } catch (error) {
    // Admin might not exist in test environment, skip
    console.log('Admin authentication skipped - user may not exist');
  }
});
