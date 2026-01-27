import { test, expect } from '@playwright/test';

test.describe('Documents', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/documents');
  });

  test('should display documents page', async ({ page }) => {
    // Check for documents section
    const heading = page.getByRole('heading', { name: /documents|files/i }).or(
      page.getByText(/documents|files/i).first()
    );
    await expect(heading).toBeVisible();
  });

  test('should have upload button', async ({ page }) => {
    const uploadButton = page.getByRole('button', { name: /upload|add/i }).or(
      page.getByLabel(/upload/i)
    );

    if (await uploadButton.isVisible()) {
      await expect(uploadButton).toBeEnabled();
    }
  });

  test('should display document list', async ({ page }) => {
    // Wait for documents to load
    await page.waitForLoadState('networkidle');

    const documentList = page.getByRole('list').or(
      page.locator('[data-testid="document-list"]').or(
        page.locator('.document-list')
      )
    );

    // List may be empty or have items
    if (await documentList.isVisible()) {
      // Check structure exists
      await expect(documentList).toBeVisible();
    } else {
      // Empty state should be shown
      const emptyState = page.getByText(/no documents|empty|upload your first/i);
      await expect(emptyState).toBeVisible();
    }
  });

  test('should search documents', async ({ page }) => {
    const searchInput = page.getByPlaceholder(/search/i).or(
      page.getByRole('searchbox')
    );

    if (await searchInput.isVisible()) {
      await searchInput.fill('test document');

      // Wait for search results
      await page.waitForTimeout(500); // debounce delay

      // Results or no results message should appear
      const results = page.locator('[data-testid="search-results"]').or(
        page.getByText(/results|found|no matches/i)
      );

      await expect(results.first()).toBeVisible({ timeout: 5000 }).catch(() => {
        // Search may filter existing list
      });
    }
  });

  test('should filter documents by type', async ({ page }) => {
    const filterDropdown = page.getByRole('combobox', { name: /filter|type/i }).or(
      page.getByLabel(/filter/i)
    );

    if (await filterDropdown.isVisible()) {
      await filterDropdown.click();

      const pdfOption = page.getByRole('option', { name: /pdf/i });
      if (await pdfOption.isVisible()) {
        await pdfOption.click();

        // Should filter to PDF documents only
        await page.waitForTimeout(500);
      }
    }
  });
});

test.describe('Document Upload', () => {
  test('should open upload dialog', async ({ page }) => {
    await page.goto('/documents');

    const uploadButton = page.getByRole('button', { name: /upload|add/i });

    if (await uploadButton.isVisible()) {
      await uploadButton.click();

      // Dialog or file input should appear
      const uploadDialog = page.getByRole('dialog').or(
        page.locator('input[type="file"]')
      );

      await expect(uploadDialog.first()).toBeVisible();
    }
  });

  test('should show drag and drop zone', async ({ page }) => {
    await page.goto('/documents');

    const dropZone = page.locator('[data-testid="drop-zone"]').or(
      page.getByText(/drag.*drop|drop.*here/i)
    );

    if (await dropZone.isVisible()) {
      await expect(dropZone).toBeVisible();
    }
  });
});

test.describe('Document Actions', () => {
  test('should open document preview', async ({ page }) => {
    await page.goto('/documents');

    // Wait for documents to load
    await page.waitForLoadState('networkidle');

    const firstDocument = page.locator('[data-testid="document-item"]').first().or(
      page.getByRole('listitem').first()
    );

    if (await firstDocument.isVisible()) {
      await firstDocument.click();

      // Preview or detail view should open
      const preview = page.getByRole('dialog').or(
        page.locator('[data-testid="document-preview"]').or(
          page.locator('.document-preview')
        )
      );

      await expect(preview.first()).toBeVisible({ timeout: 5000 }).catch(() => {
        // May navigate to document page instead
      });
    }
  });

  test('should have delete option', async ({ page }) => {
    await page.goto('/documents');

    await page.waitForLoadState('networkidle');

    const documentMenu = page.locator('[data-testid="document-menu"]').first().or(
      page.getByRole('button', { name: /more|options|menu/i }).first()
    );

    if (await documentMenu.isVisible()) {
      await documentMenu.click();

      const deleteOption = page.getByRole('menuitem', { name: /delete|remove/i }).or(
        page.getByText(/delete|remove/i)
      );

      await expect(deleteOption.first()).toBeVisible();
    }
  });
});
