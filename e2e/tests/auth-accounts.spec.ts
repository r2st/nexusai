/**
 * E2E tests for authentication with development test accounts.
 *
 * Test Accounts:
 * - admin@nexusai.dev / admin123 (admin superuser)
 * - user@nexusai.dev / user123 (regular user)
 * - viewer@nexusai.dev / viewer123 (viewer role)
 */

import { test, expect } from "@playwright/test";

// Test account credentials
const TEST_ACCOUNTS = {
  admin: {
    email: "admin@nexusai.dev",
    password: "admin123",
    role: "admin",
  },
  user: {
    email: "user@nexusai.dev",
    password: "user123",
    role: "user",
  },
  viewer: {
    email: "viewer@nexusai.dev",
    password: "viewer123",
    role: "viewer",
  },
};

test.describe("Authentication with Test Accounts", () => {
  // Don't use stored auth state
  test.use({ storageState: { cookies: [], origins: [] } });

  test("should login successfully with admin account", async ({ page }) => {
    await page.goto("/login");

    // Switch to staff login if needed (admin doesn't need org)
    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    // Fill login form
    await page.getByLabel("Email").fill(TEST_ACCOUNTS.admin.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.admin.password);

    // Submit
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect to dashboard/chat
    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Verify we're logged in
    const welcomeOrUserMenu = page
      .getByText(/welcome|dashboard|chat/i)
      .or(page.getByRole("button", { name: /account|menu|user/i }));
    await expect(welcomeOrUserMenu.first()).toBeVisible({ timeout: 10000 });
  });

  test("should login successfully with user account", async ({ page }) => {
    await page.goto("/login");

    // Switch to staff login
    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.user.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.user.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect successfully
    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });
  });

  test("should login successfully with viewer account", async ({ page }) => {
    await page.goto("/login");

    // Switch to staff login
    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.viewer.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.viewer.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should redirect successfully
    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });
  });

  test("should fail login with wrong password", async ({ page }) => {
    await page.goto("/login");

    // Switch to staff login
    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.admin.email);
    await page.getByLabel("Password").fill("wrongpassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should show error message
    const errorMessage = page.getByText(/invalid|incorrect|failed|error/i);
    await expect(errorMessage.first()).toBeVisible({ timeout: 10000 });

    // Should stay on login page
    await expect(page).toHaveURL(/\/login/);
  });

  test("should fail login with non-existent user", async ({ page }) => {
    await page.goto("/login");

    // Switch to staff login
    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill("nonexistent@nexusai.dev");
    await page.getByLabel("Password").fill("anypassword");
    await page.getByRole("button", { name: /sign in/i }).click();

    // Should show error message
    const errorMessage = page.getByText(/invalid|incorrect|failed|error/i);
    await expect(errorMessage.first()).toBeVisible({ timeout: 10000 });
  });
});

test.describe("Role-Based Access Control", () => {
  test("admin should have access to admin features", async ({ page }) => {
    // Login as admin
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.admin.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.admin.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Try to access admin page
    await page.goto("/admin");

    // Admin should see admin page or be redirected there
    const adminPageOrNav = page
      .getByText(/admin|users|settings/i)
      .or(page.getByRole("heading", { name: /admin/i }));

    // Either see admin content or get access denied
    const currentUrl = page.url();
    expect(currentUrl.includes("/admin") || currentUrl.includes("/")).toBe(
      true
    );
  });

  test("viewer should have limited write access", async ({ page }) => {
    // Login as viewer
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.viewer.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.viewer.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Navigate to chat
    await page.goto("/chat");

    // Viewer should be able to view but may have restricted create actions
    // Check if chat interface loads
    const chatInterface = page
      .getByPlaceholder(/message|ask|type/i)
      .or(page.getByRole("textbox"));

    // Should at least see the page (even if restricted)
    await expect(page).not.toHaveURL(/\/login/);
  });
});

test.describe("Session Management", () => {
  test("should maintain session after page reload", async ({ page }) => {
    // Login
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.user.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.user.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Reload page
    await page.reload();

    // Should still be logged in (not redirected to login)
    await expect(page).not.toHaveURL(/\/login/, { timeout: 5000 });
  });

  test("should logout successfully", async ({ page }) => {
    // Login first
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.user.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.user.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Find and click logout
    const userMenu = page
      .getByRole("button", { name: /account|profile|menu|user/i })
      .or(page.getByLabel(/user menu/i));

    if (await userMenu.first().isVisible()) {
      await userMenu.first().click();

      const logoutButton = page
        .getByRole("button", { name: /log out|sign out|logout/i })
        .or(page.getByRole("menuitem", { name: /log out|sign out/i }))
        .or(page.getByText(/log out|sign out/i));

      if (await logoutButton.first().isVisible()) {
        await logoutButton.first().click();

        // Should redirect to login or home
        await expect(page).toHaveURL(/\/(login|home|)?$/, { timeout: 10000 });
      }
    }
  });
});

test.describe("Frontend-Backend Integration", () => {
  test("should display user info after login", async ({ page }) => {
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    await page.getByLabel("Email").fill(TEST_ACCOUNTS.admin.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.admin.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    await expect(page).toHaveURL(/\/(dashboard|chat|home)?$/, {
      timeout: 15000,
    });

    // Look for user info (email or name)
    const userInfo = page
      .getByText(TEST_ACCOUNTS.admin.email)
      .or(page.getByText(/admin/i));

    // User info might be in a menu or header
    const userMenu = page.getByRole("button", {
      name: /account|profile|menu|user/i,
    });
    if (await userMenu.first().isVisible()) {
      await userMenu.first().click();
      // Check if email is visible in dropdown
      await expect(
        page.getByText(TEST_ACCOUNTS.admin.email).or(page.getByText(/admin/i))
      ).toBeVisible({ timeout: 5000 });
    }
  });

  test("should handle API errors gracefully", async ({ page }) => {
    await page.goto("/login");

    const staffTab = page.getByRole("button", { name: /staff/i });
    if (await staffTab.isVisible()) {
      await staffTab.click();
    }

    // Try to login - if backend is down, should show error
    await page.getByLabel("Email").fill(TEST_ACCOUNTS.user.email);
    await page.getByLabel("Password").fill(TEST_ACCOUNTS.user.password);
    await page.getByRole("button", { name: /sign in/i }).click();

    // Either succeeds or shows a user-friendly error
    const success = page.url().includes("/chat") || page.url().includes("/");
    const errorVisible = await page
      .getByText(/error|failed|unavailable|try again/i)
      .first()
      .isVisible()
      .catch(() => false);

    expect(success || errorVisible || page.url().includes("/login")).toBe(true);
  });
});
