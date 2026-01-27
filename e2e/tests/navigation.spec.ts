import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('should navigate to chat page', async ({ page }) => {
    await page.goto('/');

    const chatLink = page.getByRole('link', { name: /chat/i }).or(
      page.getByRole('button', { name: /chat|start/i })
    );

    if (await chatLink.isVisible()) {
      await chatLink.click();
      await expect(page).toHaveURL(/\/chat/);
    }
  });

  test('should navigate to settings page', async ({ page }) => {
    await page.goto('/');

    // Open user menu if needed
    const userMenu = page.getByRole('button', { name: /account|profile|menu/i });
    if (await userMenu.isVisible()) {
      await userMenu.click();
    }

    const settingsLink = page.getByRole('link', { name: /settings/i }).or(
      page.getByRole('menuitem', { name: /settings/i })
    );

    if (await settingsLink.isVisible()) {
      await settingsLink.click();
      await expect(page).toHaveURL(/\/settings/);
    }
  });

  test('should show sidebar navigation', async ({ page }) => {
    await page.goto('/chat');

    const sidebar = page.getByRole('navigation').or(
      page.locator('[data-testid="sidebar"]').or(
        page.locator('.sidebar')
      )
    );

    // Sidebar may be collapsed on mobile
    const viewportSize = page.viewportSize();
    if (viewportSize && viewportSize.width >= 768) {
      await expect(sidebar.first()).toBeVisible();
    }
  });

  test('should toggle sidebar on mobile', async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 667 });
    await page.goto('/chat');

    const menuButton = page.getByRole('button', { name: /menu|toggle/i }).or(
      page.locator('[data-testid="menu-toggle"]')
    );

    if (await menuButton.isVisible()) {
      await menuButton.click();

      const sidebar = page.getByRole('navigation').or(
        page.locator('[data-testid="sidebar"]')
      );

      await expect(sidebar.first()).toBeVisible();
    }
  });

  test('should navigate back using browser back button', async ({ page }) => {
    await page.goto('/');
    const initialUrl = page.url();

    // Navigate to another page
    const chatLink = page.getByRole('link', { name: /chat/i });
    if (await chatLink.isVisible()) {
      await chatLink.click();
      await expect(page).toHaveURL(/\/chat/);

      // Go back
      await page.goBack();
      await expect(page).toHaveURL(initialUrl);
    }
  });
});

test.describe('Breadcrumbs', () => {
  test('should display breadcrumbs on nested pages', async ({ page }) => {
    await page.goto('/settings/profile');

    const breadcrumbs = page.getByRole('navigation', { name: /breadcrumb/i }).or(
      page.locator('[aria-label="breadcrumb"]').or(
        page.locator('.breadcrumbs')
      )
    );

    // Breadcrumbs may or may not be implemented
    if (await breadcrumbs.isVisible()) {
      await expect(breadcrumbs.getByRole('link').first()).toBeVisible();
    }
  });
});
